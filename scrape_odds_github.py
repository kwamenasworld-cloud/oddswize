#!/usr/bin/env python3
"""
GitHub Actions Odds Scraper - TURBO MODE

Optimized for maximum throughput within 4 minutes.
Uses parallel requests, connection pooling, and aggressive batching.
"""

import json
import os
import re
import time
import unicodedata
import requests
import cloudscraper
import asyncio
import argparse
import sqlite3
from collections import Counter
from datetime import datetime
from typing import Dict, List, Set, Optional
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed

# Optional Postgres ingestion for canonical leagues
POSTGRES_DSN = os.getenv('POSTGRES_DSN')
if POSTGRES_DSN:
    try:
        import psycopg2
        from backend.core.canonical_leagues import LeagueMatcher
        from backend.core.ingest_canonical import fetch_leagues_and_aliases, ingest_matched_events
    except Exception as e:
        print(f"[WARN] POSTGRES_DSN set but failed to import DB modules: {e}")
        POSTGRES_DSN = None

def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except Exception:
        return default


def env_bool(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


# Configuration - AGGRESSIVE MODE
EXPECTED_BOOKMAKERS = [
    'Betway Ghana',
    'SportyBet Ghana',
    '1xBet Ghana',
    '22Bet Ghana',
    'SoccaBet Ghana',
    'Betfox Ghana',
]
OPTIONAL_BOOKMAKERS = [
    'Betfox Ghana',
]
REQUIRED_COVERAGE_BOOKMAKERS = [
    b for b in EXPECTED_BOOKMAKERS if b not in OPTIONAL_BOOKMAKERS
]
REQUIRE_FULL_TOP_LEAGUE_COVERAGE = os.getenv('REQUIRE_FULL_TOP_LEAGUE_COVERAGE', '1').strip().lower() in (
    "1", "true", "yes", "on"
)
REQUIRE_ALL_EXPECTED_BOOKIES = os.getenv('REQUIRE_ALL_EXPECTED_BOOKIES', '0').strip().lower() in (
    "1", "true", "yes", "on"
)
ALLOW_SINGLE_BOOKIE_MAJORS = env_bool("ALLOW_SINGLE_BOOKIE_MAJORS")
MATCH_TIME_TOLERANCE_SECONDS = env_int("MATCH_TIME_TOLERANCE_SECONDS", 6 * 3600)
CLOUDFLARE_WORKER_URL = os.getenv('CLOUDFLARE_WORKER_URL', '')
CLOUDFLARE_API_KEY = os.getenv('CLOUDFLARE_API_KEY', '')
D1_CANONICAL_INGEST = os.getenv('D1_CANONICAL_INGEST')  # optional override; defaults to CLOUDFLARE_WORKER_URL/api/canonical/ingest
FAST_MODE = env_bool("ODDS_FAST")
MAX_MATCHES = env_int("MAX_MATCHES", 2600)  # Increased depth to avoid dropping major leagues
MAX_CHAMPIONSHIPS = env_int("MAX_CHAMPIONSHIPS", 220)  # Broader championship coverage
TIMEOUT = env_int("TIMEOUT", 10)
BATCH_SIZE = env_int("BATCH_SIZE", 200)  # Trim batch size to reduce payload/latency
PARALLEL_PAGES = env_int("PARALLEL_PAGES", 8)  # Balanced parallelism for I/O
SPORTYBET_PAGES = env_int("SPORTYBET_PAGES", 45)
SPORTYBET_TOURNAMENT_LOOKUP_PAGES = env_int("SPORTYBET_TOURNAMENT_LOOKUP_PAGES", 12)
SPORTYBET_TOURNAMENT_MAX_PAGES = env_int("SPORTYBET_TOURNAMENT_MAX_PAGES", 6)
SPORTYBET_TOURNAMENT_PAGE_SIZE = env_int("SPORTYBET_TOURNAMENT_PAGE_SIZE", 100)
BETWAY_PAGE_SIZE = env_int("BETWAY_PAGE_SIZE", 1200)
BETWAY_MAX_SKIP = env_int("BETWAY_MAX_SKIP", 20000)
HISTORY_DIR = os.getenv("HISTORY_DIR", "data")
HISTORY_MATCHED_FILE = os.getenv("HISTORY_MATCHED_FILE", "odds_history.jsonl")
HISTORY_RAW_FILE = os.getenv("HISTORY_RAW_FILE", "raw_scraped_history.jsonl")
SAVE_RAW_HISTORY = env_bool("SAVE_RAW_HISTORY")
HISTORY_DB_PATH = os.getenv("HISTORY_DB_PATH", os.path.join(HISTORY_DIR, "odds_history.db"))
SAVE_HISTORY_DB = os.getenv("SAVE_HISTORY_DB", "1").strip().lower() in ("1", "true", "yes", "on")

def apply_fast_mode() -> None:
    global FAST_MODE, MAX_MATCHES, MAX_CHAMPIONSHIPS, TIMEOUT, BATCH_SIZE, PARALLEL_PAGES
    global SPORTYBET_PAGES, SPORTYBET_TOURNAMENT_LOOKUP_PAGES
    global SPORTYBET_TOURNAMENT_MAX_PAGES, SPORTYBET_TOURNAMENT_PAGE_SIZE
    global BETWAY_PAGE_SIZE, BETWAY_MAX_SKIP
    FAST_MODE = True
    MAX_MATCHES = env_int("MAX_MATCHES_FAST", 1100)
    MAX_CHAMPIONSHIPS = env_int("MAX_CHAMPIONSHIPS_FAST", 60)
    TIMEOUT = env_int("TIMEOUT_FAST", 6)
    BATCH_SIZE = env_int("BATCH_SIZE_FAST", 120)
    PARALLEL_PAGES = env_int("PARALLEL_PAGES_FAST", 12)
    SPORTYBET_PAGES = env_int("SPORTYBET_PAGES_FAST", 12)
    SPORTYBET_TOURNAMENT_LOOKUP_PAGES = env_int("SPORTYBET_TOURNAMENT_LOOKUP_PAGES_FAST", 6)
    SPORTYBET_TOURNAMENT_MAX_PAGES = env_int("SPORTYBET_TOURNAMENT_MAX_PAGES_FAST", 3)
    SPORTYBET_TOURNAMENT_PAGE_SIZE = env_int("SPORTYBET_TOURNAMENT_PAGE_SIZE_FAST", 100)
    BETWAY_PAGE_SIZE = env_int("BETWAY_PAGE_SIZE_FAST", 1200)
    BETWAY_MAX_SKIP = env_int("BETWAY_MAX_SKIP_FAST", 6000)


if FAST_MODE:
    apply_fast_mode()

def resolve_history_path(filename: str) -> str:
    if not filename:
        return ''
    if os.path.isabs(filename):
        return filename
    if HISTORY_DIR:
        return os.path.join(HISTORY_DIR, filename)
    return filename

def append_jsonl(path: str, record: Dict) -> None:
    if not path:
        return
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')

def slugify_simple(value: str) -> str:
    value = (value or '').strip().lower()
    value = re.sub(r'[^a-z0-9]+', '-', value)
    return value.strip('-')

def build_fixture_id(match: Dict) -> str:
    home = slugify_simple(match.get('home_team', ''))
    away = slugify_simple(match.get('away_team', ''))
    start = int(match.get('start_time') or 0)
    if home and away:
        return f"{home}-vs-{away}-{start}"
    return f"match-{start}"

def init_history_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            last_updated TEXT,
            total_scraped INTEGER,
            matched_events INTEGER,
            scrape_time_seconds REAL,
            fast_mode INTEGER,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            run_id TEXT,
            match_id TEXT,
            league TEXT,
            start_time INTEGER,
            home_team TEXT,
            away_team TEXT,
            PRIMARY KEY (run_id, match_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS odds (
            run_id TEXT,
            match_id TEXT,
            bookmaker TEXT,
            home_odds REAL,
            draw_odds REAL,
            away_odds REAL,
            PRIMARY KEY (run_id, match_id, bookmaker)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_league ON matches(league)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_start ON matches(start_time)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_odds_bookie ON odds(bookmaker)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_updated ON runs(last_updated)")

def save_history_sqlite(output: Dict) -> None:
    if not output:
        return
    db_path = resolve_history_path(HISTORY_DB_PATH)
    if not db_path:
        return
    directory = os.path.dirname(db_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    run_id = output.get('last_updated') or datetime.now().isoformat()
    stats = output.get('stats', {}) or {}

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        init_history_db(conn)
        conn.execute(
            """
            INSERT OR REPLACE INTO runs (
                run_id, last_updated, total_scraped, matched_events, scrape_time_seconds, fast_mode, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                output.get('last_updated'),
                stats.get('total_scraped'),
                stats.get('matched_events'),
                stats.get('scrape_time_seconds'),
                1 if FAST_MODE else 0,
                datetime.now().isoformat(),
            )
        )

        match_rows = []
        odds_rows = []
        for match in output.get('matches', []) or []:
            match_id = build_fixture_id(match)
            match_rows.append((
                run_id,
                match_id,
                match.get('league', ''),
                int(match.get('start_time') or 0),
                match.get('home_team', ''),
                match.get('away_team', ''),
            ))
            for odds in match.get('odds', []) or []:
                odds_rows.append((
                    run_id,
                    match_id,
                    odds.get('bookmaker', ''),
                    odds.get('home_odds'),
                    odds.get('draw_odds'),
                    odds.get('away_odds'),
                ))

        if match_rows:
            conn.executemany(
                "INSERT OR REPLACE INTO matches (run_id, match_id, league, start_time, home_team, away_team) VALUES (?, ?, ?, ?, ?, ?)",
                match_rows
            )
        if odds_rows:
            conn.executemany(
                "INSERT OR REPLACE INTO odds (run_id, match_id, bookmaker, home_odds, draw_odds, away_odds) VALUES (?, ?, ?, ?, ?, ?)",
                odds_rows
            )
        conn.commit()
    finally:
        conn.close()

def save_history_snapshot(output: Dict, all_matches: Dict[str, List[Dict]]) -> None:
    if not output:
        return
    run_id = output.get('last_updated') or datetime.now().isoformat()
    matched_path = resolve_history_path(HISTORY_MATCHED_FILE)
    history_record = {**output, 'run_id': run_id}
    append_jsonl(matched_path, history_record)
    if SAVE_RAW_HISTORY:
        raw_path = resolve_history_path(HISTORY_RAW_FILE)
        raw_record = {
            'run_id': run_id,
            'stats': output.get('stats', {}),
            'matches': all_matches,
        }
        append_jsonl(raw_path, raw_record)
    if SAVE_HISTORY_DB:
        save_history_sqlite(output)

# Top leagues to prioritize (keywords to search for in league names)
TOP_LEAGUE_KEYWORDS = [
    'premier league', 'epl', 'england',
    'la liga', 'laliga', 'spain',
    'serie a', 'italy',
    'bundesliga', 'germany',
    'ligue 1', 'france',
    'champions league', 'ucl', 'uefa',
    'europa league', 'europa',
    'championship', 'england championship',
]

MAJOR_LEAGUE_TARGETS = {
    'premier': ['premier league', 'english premier league', 'england premier league', 'epl'],
    'laliga': ['la liga', 'laliga', 'primera division'],
    'seriea': ['serie a'],
    'bundesliga': ['bundesliga'],
    'ligue1': ['ligue 1'],
    'ucl': ['uefa champions league', 'champions league', 'ucl'],
}

MAJOR_LEAGUE_EXCLUSIONS = [
    'premier league cup',
    'premier league 2',
    'premier league u21',
    'premier league u 21',
    'premier league u-21',
    'premier league 2 division',
]


def league_name_matches(name: str, keywords: List[str], exclusions: Optional[List[str]] = None) -> bool:
    if not name:
        return False
    lowered = name.lower()
    if exclusions and any(ex in lowered for ex in exclusions):
        return False
    return any(keyword in lowered for keyword in keywords)


def is_major_league_name(name: str) -> bool:
    return any(league_name_matches(name, keywords, MAJOR_LEAGUE_EXCLUSIONS) for keywords in MAJOR_LEAGUE_TARGETS.values())

# Common headers for API requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
}

# ============================================================================
# SportyBet Ghana Scraper - PARALLEL PAGES
# ============================================================================

SPORTYBET_API = "https://www.sportybet.com/api/gh/factsCenter/pcUpcomingEvents"

def fetch_sportybet_page(session, headers, page, page_size=100, tournament_id: Optional[str] = None):
    """Fetch a single page from SportyBet."""
    try:
        url = (
            f"{SPORTYBET_API}?sportId=sr%3Asport%3A1&marketId=1"
            f"&pageSize={page_size}&pageNum={page}"
        )
        if tournament_id:
            url += f"&tournamentId={tournament_id}"
        resp = session.get(url, headers=headers, timeout=TIMEOUT)
        data = resp.json()
        if data.get('bizCode') != 10000:
            return []
        return data.get('data', {}).get('tournaments', [])
    except:
        return []

def find_sportybet_tournament_ids(session, headers) -> Dict[str, Set[str]]:
    """Discover SportyBet tournament ids for major leagues."""
    found: Dict[str, Set[str]] = {key: set() for key in MAJOR_LEAGUE_TARGETS}
    for page in range(1, SPORTYBET_TOURNAMENT_LOOKUP_PAGES + 1):
        tournaments = fetch_sportybet_page(session, headers, page, page_size=SPORTYBET_TOURNAMENT_PAGE_SIZE)
        if not tournaments:
            break
        for tournament in tournaments:
            name = tournament.get('name', '') or ''
            tournament_id = tournament.get('id') or tournament.get('tournamentId')
            if not tournament_id:
                continue
            for league_key, keywords in MAJOR_LEAGUE_TARGETS.items():
                if league_name_matches(name, keywords, MAJOR_LEAGUE_EXCLUSIONS):
                    found[league_key].add(tournament_id)
    return found


def parse_sportybet_tournaments(tournaments, matches, seen_ids, major_ids):
    """Parse SportyBet tournament payloads into match list."""
    for tournament in tournaments:
        tournament_name = tournament.get('name', '') or ''
        for event in tournament.get('events', []):
            event_id = event.get('eventId')
            if not event_id or event_id in seen_ids:
                continue

            home = event.get('homeTeamName')
            away = event.get('awayTeamName')
            if not home or not away:
                continue

            home_odds = draw_odds = away_odds = None
            for market in event.get('markets', []):
                if market.get('id') == '1' or market.get('name') in ['1X2', '1x2', 'Match Result']:
                    for outcome in market.get('outcomes', []):
                        desc = outcome.get('desc', '').lower()
                        odds = outcome.get('odds')
                        if odds:
                            odds_val = float(odds) / 100 if float(odds) > 100 else float(odds)
                            if desc in ['1', 'home', 'w1']:
                                home_odds = odds_val
                            elif desc in ['x', 'draw']:
                                draw_odds = odds_val
                            elif desc in ['2', 'away', 'w2']:
                                away_odds = odds_val
                    break

            if not home_odds or not away_odds:
                continue

            sport = event.get('sport', {})
            category = sport.get('category', {})
            tourn = category.get('tournament', {})
            category_name = category.get('name', '')
            tourn_name = tourn.get('name', tournament_name)
            league = f"{category_name}. {tourn_name}" if category_name else tourn_name

            start_time = event.get('estimateStartTime', 0)
            if start_time > 1000000000000:
                start_time = start_time // 1000

            seen_ids.add(event_id)
            match = {
                'bookmaker': 'SportyBet Ghana',
                'event_id': str(event_id),
                'home_team': home,
                'away_team': away,
                'home_odds': home_odds,
                'draw_odds': draw_odds or 0.0,
                'away_odds': away_odds,
                'league': league,
                'start_time': start_time,
            }
            matches.append(match)

            if is_major_league_name(league) or is_major_league_name(tournament_name):
                major_ids.add(str(event_id))

def scrape_sportybet() -> List[Dict]:
    """Scrape SportyBet Ghana via API with parallel page fetching."""
    print("Scraping SportyBet Ghana (TURBO)...")
    matches = []
    major_ids = set()
    seen_ids = set()
    session = requests.Session()

    # Adapter for connection pooling
    adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
    session.mount('https://', adapter)

    # Get cookies first
    try:
        page_headers = {
            'User-Agent': HEADERS['User-Agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        session.get('https://www.sportybet.com/gh/', headers=page_headers, timeout=TIMEOUT)
        time.sleep(0.2 if FAST_MODE else 1)
    except:
        pass

    headers = {
        **HEADERS,
        'Referer': 'https://www.sportybet.com/gh/',
    }

    # Fetch pages in parallel - trimmed for speed
    all_tournaments = []
    with ThreadPoolExecutor(max_workers=PARALLEL_PAGES) as executor:
        futures = {
            executor.submit(fetch_sportybet_page, session, headers, p, 100): p
            for p in range(1, SPORTYBET_PAGES + 1)
        }
        for future in as_completed(futures):
            tournaments = future.result()
            all_tournaments.extend(tournaments)

    # Parse all tournaments
    parse_sportybet_tournaments(all_tournaments, matches, seen_ids, major_ids)

    # Targeted league fetch (Premier League, La Liga, etc.)
    tournament_ids = find_sportybet_tournament_ids(session, headers)
    for league_key, ids in tournament_ids.items():
        for tournament_id in ids:
            for page in range(1, SPORTYBET_TOURNAMENT_MAX_PAGES + 1):
                tournaments = fetch_sportybet_page(
                    session,
                    headers,
                    page,
                    page_size=SPORTYBET_TOURNAMENT_PAGE_SIZE,
                    tournament_id=tournament_id,
                )
                if not tournaments:
                    break
                parse_sportybet_tournaments(tournaments, matches, seen_ids, major_ids)

    print(f"  Total: {len(matches)} matches from SportyBet")
    major_first = [m for m in matches if m.get('event_id') in major_ids]
    other = [m for m in matches if m.get('event_id') not in major_ids]
    return (major_first + other)[:MAX_MATCHES]


# ============================================================================
# 1xBet Ghana Scraper - PARALLEL CHAMPIONSHIPS
# ============================================================================

ONEXBET_API = "https://1xbet.com.gh/service-api/LineFeed"

def fetch_1xbet_games(session, champ_id, champ_name):
    """Fetch games for a single championship."""
    matches = []
    try:
        resp = session.get(f"{ONEXBET_API}/GetChampZip?champ={champ_id}&lng=en", headers=HEADERS, timeout=TIMEOUT)
        value = resp.json().get("Value", {})
        games = value.get("G", []) if isinstance(value, dict) else []

        game_ids = [g.get("I") for g in games if g.get("I")]
        if not game_ids:
            return []

        # Fetch all games in one batch
        ids_str = ",".join(str(i) for i in game_ids[:BATCH_SIZE])
        resp = session.get(f"{ONEXBET_API}/GetGamesZip?ids={ids_str}&lng=en", headers=HEADERS, timeout=TIMEOUT)
        games_data = resp.json().get("Value", [])

        for game in games_data:
            event_id = game.get("I")
            if not event_id:
                continue

            home = game.get("O1") or game.get("O1E")
            away = game.get("O2") or game.get("O2E")

            home_odds = draw_odds = away_odds = None
            for o in game.get("E", []):
                if o.get("G") != 1:
                    continue
                ot = o.get("T")
                if ot == 1:
                    home_odds = o.get("C")
                elif ot == 2:
                    draw_odds = o.get("C")
                elif ot == 3:
                    away_odds = o.get("C")

            if not (home and away and home_odds and away_odds):
                continue

            try:
                home_odds = float(home_odds)
                away_odds = float(away_odds)
                draw_odds = float(draw_odds) if draw_odds else 0.0
                if home_odds < 1.01 or home_odds > 100 or away_odds < 1.01 or away_odds > 100:
                    continue
            except:
                continue

            matches.append({
                'bookmaker': '1xBet Ghana',
                'event_id': str(event_id),
                'league_id': game.get("LI") or champ_id,
                'home_team': home,
                'away_team': away,
                'home_odds': home_odds,
                'draw_odds': draw_odds,
                'away_odds': away_odds,
                'league': game.get("L", champ_name),
                'start_time': game.get("S", 0),
            })
    except:
        pass
    return matches

def scrape_1xbet() -> List[Dict]:
    """Scrape 1xBet Ghana with parallel championship fetching."""
    print("Scraping 1xBet Ghana (TURBO)...")
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
    session.mount('https://', adapter)

    try:
        resp = session.get(f"{ONEXBET_API}/GetChampsZip?sport=1&lng=en", headers=HEADERS, timeout=TIMEOUT)
        champs = resp.json().get("Value", [])
        champs = sorted(champs, key=lambda x: x.get("GC", 0), reverse=True)[:MAX_CHAMPIONSHIPS]
    except Exception as e:
        print(f"  1xBet error getting champs: {e}")
        return []

    skip_patterns = ["alternative", "team vs player", "specials", "fantasy", "esports"]
    valid_champs = [(c.get("LI"), c.get("L", "")) for c in champs
                    if not any(p in c.get("L", "").lower() for p in skip_patterns)]

    if FAST_MODE:
        top_champs = [
            (cid, cname) for cid, cname in valid_champs
            if any(k in (cname or "").lower() for k in TOP_LEAGUE_KEYWORDS)
        ]
        if len(top_champs) >= 10:
            valid_champs = top_champs

    # Parallel championship fetching
    all_matches = []
    with ThreadPoolExecutor(max_workers=PARALLEL_PAGES) as executor:
        futures = {executor.submit(fetch_1xbet_games, session, cid, cname): cid
                   for cid, cname in valid_champs}
        for future in as_completed(futures):
            matches = future.result()
            all_matches.extend(matches)
            if len(all_matches) >= MAX_MATCHES:
                break

    # Dedupe
    seen = set()
    unique = []
    for m in all_matches:
        eid = m['event_id']
        if eid not in seen:
            seen.add(eid)
            unique.append(m)

    print(f"  Total: {len(unique)} matches from 1xBet")
    return unique[:MAX_MATCHES]


# ============================================================================
# 22Bet Ghana Scraper - Platform API (fast, prematch with odds)
# ============================================================================
from backend.scrapers.twentytwobet_ghana import scrape_22bet_ghana  # uses platform.22bet.com.gh/api


# ============================================================================
# Betway Ghana Scraper - PARALLEL PAGES
# ============================================================================

BETWAY_API = "https://www.betway.com.gh/sportsapi/br/v1/BetBook/Upcoming/"

def fetch_betway_page(session, headers, skip, page_size):
    """Fetch a single page from Betway."""
    try:
        url = (
            f"{BETWAY_API}?countryCode=GH"
            f"&sportId=soccer"
            f"&cultureCode=en-US"
            f"&marketTypes=%5BWin%2FDraw%2FWin%5D"
            f"&isEsport=false"
            f"&Skip={skip}"
            f"&Take={page_size}"
        )
        resp = session.get(url, headers=headers, timeout=15)
        return resp.json()
    except:
        return {}

def scrape_betway() -> List[Dict]:
    """Scrape Betway Ghana with parallel page fetching."""
    print("Scraping Betway Ghana (TURBO)...")
    matches = []
    seen_ids = set()
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
    session.mount('https://', adapter)

    headers = {
        **HEADERS,
        'Referer': 'https://www.betway.com.gh/sport/soccer/upcoming',
    }

    page_size = BETWAY_PAGE_SIZE  # Large page size reduces page count

    # Fetch pages in parallel - trimmed range for speed
    all_data = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_betway_page, session, headers, skip, page_size): skip
                   for skip in range(0, BETWAY_MAX_SKIP, page_size)}
        for future in as_completed(futures):
            data = future.result()
            if data:
                all_data.append(data)

    # Parse all data
    for data in all_data:
        events = data.get('events', [])
        if not events:
            continue

        markets = data.get('markets', [])
        outcomes = data.get('outcomes', [])
        prices = data.get('prices', [])

        market_by_event = {}
        for m in markets:
            if m.get('name') == '[Win/Draw/Win]' or m.get('displayName') == '1X2':
                market_by_event[m.get('eventId')] = m

        outcomes_by_market = {}
        for o in outcomes:
            mid = o.get('marketId')
            if mid not in outcomes_by_market:
                outcomes_by_market[mid] = []
            outcomes_by_market[mid].append(o)

        price_by_outcome = {p.get('outcomeId'): p.get('priceDecimal') for p in prices}

        for event in events:
            if len(matches) >= MAX_MATCHES:
                break

            event_id = event.get('eventId')
            if not event_id or event_id in seen_ids:
                continue

            home = event.get('homeTeam')
            away = event.get('awayTeam')
            if not home or not away:
                continue

            # Debug for Newcastle/Chelsea
            is_target_match = any(team in home.lower() or team in away.lower() for team in ['newcastle', 'chelsea'])
            if is_target_match and any(team in home.lower() for team in ['newcastle', 'chelsea']) and \
               any(team in away.lower() for team in ['newcastle', 'chelsea']):
                print(f"  [BETWAY] Processing {home} vs {away}")

            market = market_by_event.get(event_id)
            if not market:
                if is_target_match and any(team in home.lower() for team in ['newcastle', 'chelsea']) and \
                   any(team in away.lower() for team in ['newcastle', 'chelsea']):
                    print(f"    -> No 1X2 market found, SKIPPING")
                continue

            market_id = market.get('marketId')
            market_outcomes = outcomes_by_market.get(market_id, [])

            home_odds = draw_odds = away_odds = None
            for outcome in market_outcomes:
                name = outcome.get('name', '')
                oid = outcome.get('outcomeId')
                price = price_by_outcome.get(oid)
                if not price:
                    continue

                # Betway uses team names, not Home/Away
                # Use fuzzy matching: normalize both and check if they match
                name_normalized = normalize_name(name)
                home_normalized = normalize_name(home)
                away_normalized = normalize_name(away)

                if name == home or name == 'Home' or name_normalized == home_normalized:
                    home_odds = price
                elif name.lower() == 'draw':
                    draw_odds = price
                elif name == away or name == 'Away' or name_normalized == away_normalized:
                    away_odds = price

            if not home_odds or not away_odds:
                if is_target_match and any(team in home.lower() for team in ['newcastle', 'chelsea']) and \
                   any(team in away.lower() for team in ['newcastle', 'chelsea']):
                    print(f"    -> Incomplete odds (H:{home_odds}, D:{draw_odds}, A:{away_odds}), SKIPPING")
                continue

            league = event.get('league', event.get('competition', {}).get('name', ''))
            start_time = event.get('expectedStartEpoch', 0)

            seen_ids.add(event_id)

            # Debug logging for Newcastle or Chelsea matches
            if any(team in home.lower() or team in away.lower() for team in ['newcastle', 'chelsea']):
                print(f"  [BETWAY DEBUG] Scraped: {home} vs {away} ({league})")

            matches.append({
                'bookmaker': 'Betway Ghana',
                'event_id': str(event_id),
                'home_team': home,
                'away_team': away,
                'home_odds': home_odds,
                'draw_odds': draw_odds or 0.0,
                'away_odds': away_odds,
                'league': league,
                'start_time': start_time,
            })

    print(f"  Total: {len(matches)} matches from Betway")
    return matches[:MAX_MATCHES]


# ============================================================================
# SoccaBet Ghana Scraper - SINGLE FAST CALL
# ============================================================================

SOCCABET_API = "https://www.soccabet.com/bet/odds.js"

def iter_dict_or_list(data):
    if isinstance(data, dict):
        return data.items()
    elif isinstance(data, list):
        return enumerate(data)
    return []

def scrape_soccabet() -> List[Dict]:
    """Scrape SoccaBet Ghana - already fast (single API call)."""
    print("Scraping SoccaBet Ghana...")
    matches = []

    headers = {
        **HEADERS,
        'Referer': 'https://www.soccabet.com/',
    }

    try:
        session = requests.Session()
        session.get('https://www.soccabet.com/', headers=headers, timeout=TIMEOUT)
        resp = session.get(SOCCABET_API, headers=headers, timeout=20)
        if resp.status_code != 200:
            return []

        data = resp.json()
        sports = data.get('sports', {})
        soccer = sports.get('77', sports.get('soccer', {}))

        if not soccer and isinstance(sports, list):
            for sport in sports:
                if sport.get('id') == 77 or sport.get('name', '').lower() == 'soccer':
                    soccer = sport
                    break

        if not soccer:
            return []

        categories = soccer.get('categories', soccer.get('regions', []))
        skip_patterns = ['esoccer', 'ebasketball', 'esports', '(thomas)', '(nathan)',
                         '(iron)', '(jason)', '(panther)', '(felix)', '(odin)', '(cleo)']

        for cat_id, category in iter_dict_or_list(categories):
            if len(matches) >= MAX_MATCHES:
                break

            if not isinstance(category, dict):
                continue

            cat_name = category.get('name', 'Unknown')
            tournaments = category.get('tournaments', category.get('competitions', []))

            for tourn_id, tournament in iter_dict_or_list(tournaments):
                if len(matches) >= MAX_MATCHES:
                    break

                if not isinstance(tournament, dict):
                    continue

                tourn_name = tournament.get('name', 'Unknown')
                tournament_id = tournament.get('id', tourn_id)
                league = f"{cat_name}. {tourn_name}"
                raw_matches = tournament.get('matches', tournament.get('events', []))

                for match_id, match in iter_dict_or_list(raw_matches):
                    if len(matches) >= MAX_MATCHES:
                        break

                    if not isinstance(match, dict) or match.get('live'):
                        continue

                    name = match.get('name', '')
                    if not name or ' v ' not in name:
                        home = match.get('home', match.get('homeTeam', ''))
                        away = match.get('away', match.get('awayTeam', ''))
                        if home and away:
                            name = f"{home} v {away}"
                        else:
                            continue

                    if ' v ' in name:
                        parts = name.split(' v ')
                    elif ' vs ' in name:
                        parts = name.split(' vs ')
                    else:
                        continue

                    if len(parts) != 2:
                        continue

                    home_team = parts[0].strip()
                    away_team = parts[1].strip()

                    full_name = f"{home_team} {away_team}".lower()
                    if any(p in full_name for p in skip_patterns):
                        continue

                    start_ts = match.get('ts', match.get('startTime', 0))
                    match_id_str = str(match.get('id', match_id))

                    markets_data = match.get('markets', match.get('odds', []))
                    home_odds = draw_odds = away_odds = 0

                    for mkt_id, mkt in iter_dict_or_list(markets_data):
                        if not isinstance(mkt, dict):
                            continue

                        type_id = str(mkt.get('typeid', mkt.get('typeId', mkt.get('marketType', ''))))
                        mkt_name = mkt.get('name', '').lower()

                        if type_id in ['4102', '4720', '1'] or '1x2' in mkt_name or 'match result' in mkt_name:
                            selections = mkt.get('selections', mkt.get('outcomes', []))

                            for sel_id, sel in iter_dict_or_list(selections):
                                if not isinstance(sel, dict):
                                    continue

                                outcome = str(sel.get('n', sel.get('name', sel.get('outcome', ''))))
                                odds_str = sel.get('o', sel.get('odds', sel.get('price', '0')))

                                try:
                                    odds = float(odds_str)
                                except:
                                    continue

                                if outcome in ['1', 'home', 'Home']:
                                    home_odds = odds
                                elif outcome in ['X', 'x', 'draw', 'Draw']:
                                    draw_odds = odds
                                elif outcome in ['2', 'away', 'Away']:
                                    away_odds = odds
                            break

                    if home_odds > 1 and away_odds > 1:
                        matches.append({
                            'bookmaker': 'SoccaBet Ghana',
                            'event_id': match_id_str,
                            'league_id': str(tournament_id) if tournament_id is not None else None,
                            'home_team': home_team,
                            'away_team': away_team,
                            'home_odds': home_odds,
                            'draw_odds': draw_odds,
                            'away_odds': away_odds,
                            'league': league,
                            'start_time': start_ts,
                        })

    except Exception as e:
        print(f"  SoccaBet error: {e}")

    print(f"  Total: {len(matches)} matches from SoccaBet")
    return matches[:MAX_MATCHES]


# ============================================================================
# Betfox Ghana Scraper - Using V4 API (upcoming + live endpoints)
# ============================================================================

def scrape_betfox() -> List[Dict]:
    """Scrape Betfox Ghana via V4 competitions API."""
    print("Scraping Betfox Ghana (V4 API)...")
    matches = []

    # Use cloudscraper to bypass Cloudflare
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    # Set required headers for Betfox API
    scraper.headers.update({
        'Accept': 'application/json',
        'Referer': 'https://www.betfox.com.gh/sportsbook',
        'x-betr-brand': 'betfox.com.gh',
        'x-locale': 'en',
    })

    try:
        # Get all fixtures from competitions endpoint (includes all major leagues)
        all_fixtures = []

        # Get competitions with embedded fixtures
        resp = scraper.get(
            'https://www.betfox.com.gh/api/offer/v4/competitions?sport=Football',
            timeout=TIMEOUT
        )

        if resp.status_code == 200:
            data = resp.json()
            competitions = data.get('enriched', [])
            print(f"  Competitions: {len(competitions)}")

            # Extract fixtures from each competition
            for comp in competitions:
                comp_fixtures = comp.get('fixtures', [])
                for fx in comp_fixtures:
                    # Ensure competition/category populated on fixture
                    if not fx.get('competition'):
                        fx['competition'] = {'name': comp.get('name', '')}
                    if not fx.get('category'):
                        fx['category'] = comp.get('category', {})
                    all_fixtures.append(fx)

            print(f"  Fixtures from competitions: {len(all_fixtures)}")

        # Also get live matches for additional coverage
        if not FAST_MODE:
            try:
                resp_live = scraper.get(
                    'https://www.betfox.com.gh/api/offer/v4/fixtures/home/live?first=100&sport=Football',
                    timeout=TIMEOUT
                )
                if resp_live.status_code == 200:
                    live_data = resp_live.json()
                    live_fixtures = live_data.get('data', [])
                    all_fixtures.extend(live_fixtures)
                    print(f"  Live fixtures: {len(live_fixtures)}")
            except:
                pass  # Live matches optional

        if not all_fixtures:
            print("  No fixtures found")
            return []

        print(f"  Total fetched: {len(all_fixtures)} fixtures")

        # Deduplicate fixtures by ID
        seen_ids = set()
        unique_fixtures = []
        for fixture in all_fixtures:
            fid = fixture.get('id')
            if fid and fid not in seen_ids:
                seen_ids.add(fid)
                unique_fixtures.append(fixture)

        print(f"  Unique fixtures: {len(unique_fixtures)}")

        for fixture in unique_fixtures:
            if len(matches) >= MAX_MATCHES:
                break

            try:
                event_id = fixture.get('id', '')
                if not event_id:
                    continue

                # Get competition and country info
                competition = fixture.get('competition', {})
                category = fixture.get('category', {})
                league_name = competition.get('name', '')
                country_name = category.get('name', '')
                league = f"{country_name}. {league_name}" if country_name else league_name
                if not league:
                    # Infer Premier League if both teams are PL clubs
                    if is_team_in_league(home, 'Premier League') and is_team_in_league(away, 'Premier League'):
                        league = 'Premier League'

                # Get competitors (teams)
                competitors = fixture.get('competitors', [])
                if len(competitors) < 2:
                    continue
                home = competitors[0].get('name', '')
                away = competitors[1].get('name', '')
                if not home or not away:
                    continue

                # Get odds from markets array (V4 API)
                # Find FOOTBALL_WINNER market (1X2 odds)
                markets = fixture.get('markets', [])
                winner_market = None
                for market in markets:
                    if market.get('type') == 'FOOTBALL_WINNER':
                        winner_market = market
                        break

                if not winner_market:
                    continue

                outcomes = winner_market.get('outcomes', [])

                home_odds = draw_odds = away_odds = None
                for outcome in outcomes:
                    odds_value = outcome.get('odds')
                    outcome_type = outcome.get('value', '').upper()

                    if odds_value:
                        if outcome_type == 'HOME':
                            home_odds = float(odds_value)
                        elif outcome_type == 'DRAW':
                            draw_odds = float(odds_value)
                        elif outcome_type == 'AWAY':
                            away_odds = float(odds_value)

                if not home_odds or not away_odds:
                    continue

                # Parse start time
                start_time_str = fixture.get('startTime', '')
                start_time = 0
                if start_time_str:
                    try:
                        dt = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                        start_time = int(dt.timestamp())
                    except:
                        pass

                matches.append({
                    'bookmaker': 'Betfox Ghana',
                    'event_id': event_id,
                    'home_team': home,
                    'away_team': away,
                    'home_odds': home_odds,
                    'draw_odds': draw_odds or 0.0,
                    'away_odds': away_odds,
                    'league': league,
                    'start_time': start_time,
                })

            except Exception as e:
                continue

    except Exception as e:
        print(f"  Betfox error: {e}")

    print(f"  Total: {len(matches)} matches from Betfox")
    return matches[:MAX_MATCHES]


# ============================================================================
# Event Matching
# ============================================================================

TRANSLITERATION = str.maketrans({
    "\u00f8": "o",
    "\u00d8": "o",
    "\u00e6": "ae",
    "\u00c6": "ae",
    "\u00e5": "a",
    "\u00c5": "a",
    "\u00df": "ss",
    "\u0153": "oe",
    "\u0152": "oe",
})

def normalize_name(name: str) -> str:
    """Normalize team name for matching."""
    if not name:
        return ''
    name = name.translate(TRANSLITERATION)
    name = unicodedata.normalize('NFKD', name)
    name = ''.join(ch for ch in name if not unicodedata.combining(ch))
    name = name.lower().strip()
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name)

    # Phrase-level replacements (apply before token-level handling)
    phrase_replacements = {
        'wolverhampton wanderers': 'wolverhampton',
        'wolverhampton wonderers': 'wolverhampton',  # common typo
        'wolverhampton wolverhampton': 'wolverhampton',
        'real sociedad san sebastian': 'real sociedad',
        'olympique marseille': 'marseille',
        'olympique lyonnais': 'lyon',
        'athletic club': 'bilbao',
        'athletic bilbao': 'bilbao',
        'celta de vigo': 'celta vigo',
        'paris saint germain': 'psg',
        'stade rennais': 'rennes',
        'borussia monchengladbach': 'monchengladbach',
    }
    for phrase, repl in phrase_replacements.items():
        if phrase in name:
            name = name.replace(phrase, repl)

    removals = [
        'fc', 'cf', 'sc', 'ac', 'afc', 'ssc', 'bc', 'fk', 'sk', 'nk', 'cd', 'ud', 'sd',
        'rc', 'rcd', 'sv', 'vfb', 'vfl', 'rb',
        'united', 'utd', 'city', 'town', 'athletic', 'sporting', 'hotspur', 'club',
        'de', 'del', 'la', 'le', 'calcio', 'stade', 'deportivo', 'balompie', 'seville', 'piraeus'
    ]
    replacements = {
        'nott': 'nottingham',
        'nottm': 'nottingham',
        'notts': 'nottingham',
        'forest': 'nottingham',
        'spurs': 'tottenham',
        'wolves': 'wolverhampton',
        'wanderers': 'wanderers',  # keep word but allow phrase normalization above to collapse team
        'whu': 'west ham',
        'hammers': 'west ham',
        'man': 'manchester',
        'man utd': 'manchester united',
        'man united': 'manchester united',
        'manchester utd': 'manchester united',
        'man city': 'manchester city',
        'saint': 'st',
        'st.': 'st',
        'madrid': 'real',
        'eindhoven': 'psv',
        'brighton': 'brighton hove',
        'hove': 'brighton hove',
    }
    words = []
    for w in name.split():
        w = replacements.get(w, w)
        if w.isdigit() or len(w) <= 1:
            continue
        if w in removals:
            continue
        words.append(w)
    if not words:
        return name
    deduped = []
    for w in words:
        if not deduped or deduped[-1] != w:
            deduped.append(w)
    return ' '.join(deduped)


def token_similarity(a: str, b: str) -> float:
    """Token Jaccard similarity."""
    ta = set(a.split())
    tb = set(b.split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)

def is_start_time_close(a: int, b: int, tolerance_seconds: int = MATCH_TIME_TOLERANCE_SECONDS) -> bool:
    """Return True if start times are within tolerance or missing."""
    try:
        a_val = int(a or 0)
        b_val = int(b or 0)
    except Exception:
        return True
    if a_val <= 0 or b_val <= 0:
        return True
    return abs(a_val - b_val) <= tolerance_seconds

# Known teams for major leagues (for validation to prevent cross-contamination)
RAW_LEAGUE_TEAMS = {
    'Premier League': [
        'AFC Bournemouth', 'Arsenal', 'Aston Villa', 'Brentford', 'Brighton & Hove Albion',
        'Burnley', 'Chelsea', 'Crystal Palace', 'Everton', 'Fulham', 'Leeds United',
        'Liverpool', 'Manchester City', 'Manchester United', 'Newcastle United',
        'Nottingham Forest', 'Sunderland', 'Tottenham Hotspur', 'West Ham United',
        'Wolverhampton Wanderers'
    ],
    'La Liga': [
        'Alaves', 'Athletic Club', 'Atletico Madrid', 'Barcelona', 'Celta Vigo',
        'Elche', 'Espanyol', 'Getafe', 'Girona', 'Levante',
        'Mallorca', 'Osasuna', 'Rayo Vallecano', 'Real Betis', 'Real Madrid',
        'Real Oviedo', 'Real Sociedad', 'Sevilla', 'Valencia', 'Villarreal'
    ],
    'Serie A': [
        'AC Milan', 'AS Roma', 'Atalanta', 'Bologna', 'Cagliari',
        'Como', 'Cremonese', 'Fiorentina', 'Genoa', 'Hellas Verona',
        'Internazionale', 'Juventus', 'Lazio', 'Lecce', 'Napoli',
        'Parma', 'Pisa', 'Sassuolo', 'Torino', 'Udinese'
    ],
    'Bundesliga': [
        '1. FC Heidenheim 1846', '1. FC Union Berlin', 'Bayer Leverkusen', 'Bayern Munich',
        'Borussia Dortmund', 'Borussia Monchengladbach', 'Eintracht Frankfurt', 'FC Augsburg',
        'FC Cologne', 'Hamburg SV', 'Mainz', 'RB Leipzig', 'SC Freiburg', 'St. Pauli',
        'TSG Hoffenheim', 'VfB Stuttgart', 'VfL Wolfsburg', 'Werder Bremen'
    ],
    'Ligue 1': [
        'AJ Auxerre', 'AS Monaco', 'Angers', 'Brest', 'Le Havre AC',
        'Lens', 'Lille', 'Lorient', 'Lyon', 'Marseille',
        'Metz', 'Nantes', 'Nice', 'Paris FC', 'Paris Saint-Germain',
        'Stade Rennais', 'Strasbourg', 'Toulouse'
    ],
    'Championship': [
        'Barnsley', 'Birmingham', 'Blackburn', 'Bristol City', 'Burnley',
        'Cardiff', 'Charlton', 'Charlton Athletic', 'Coventry', 'Derby', 'Derby County',
        'Hull', 'Hull City', 'Ipswich', 'Ipswich Town', 'Leeds', 'Leeds United',
        'Luton', 'Luton Town', 'Middlesbrough', 'Millwall', 'Norwich', 'Norwich City',
        'Plymouth', 'Portsmouth', 'Preston', 'QPR', 'Queens Park Rangers', 'Raith Rovers',
        'Raith Rovers FC', 'Sheffield United', 'Sheffield Wednesday', 'Southampton',
        'Southampton FC', 'Stoke', 'Stoke City', 'Sunderland', 'Swansea', 'Watford',
        'West Brom', 'Wrexham', 'Wrexham AFC'
    ],
}

LEAGUE_TEAMS = {
    league: {normalize_name(team) for team in teams if normalize_name(team)}
    for league, teams in RAW_LEAGUE_TEAMS.items()
}

def is_team_in_league(team_name: str, league: str) -> bool:
    """Check if a team belongs to a specific league."""
    if league not in LEAGUE_TEAMS:
        return True  # No validation data for this league, allow it

    known_teams = LEAGUE_TEAMS[league]
    normalized = normalize_name(team_name).lower()

    # Check if normalized name is in the known teams set
    if normalized in known_teams:
        return True

    # Also check if any known team name is contained in the team name
    for known_team in known_teams:
        if known_team in normalized or normalized in known_team:
            return True

    return False

def infer_league_from_teams(home_team: str, away_team: str) -> str:
    """
    Infer league when scraped league is empty by checking if both teams belong
    to the same known league (e.g., Premier League).
    """
    home = normalize_name(home_team).lower()
    away = normalize_name(away_team).lower()

    for league, teams in LEAGUE_TEAMS.items():
        if home in teams and away in teams:
            return league

    return ''

def build_match_key(match: Dict) -> str:
    """Build a stable match key using normalized teams + start time bucket."""
    home = normalize_name(match.get('home_team', ''))
    away = normalize_name(match.get('away_team', ''))
    if not home or not away:
        return ''
    start_time = match.get('start_time') or 0
    try:
        start_bucket = int(int(start_time) // 3600)
    except Exception:
        start_bucket = 0
    teams = sorted([home, away])
    return f"{teams[0]}|{teams[1]}|{start_bucket}"


def add_single_bookie_major_league_matches(
    all_matches: Dict[str, List[Dict]],
    matched_events: List[List[Dict]]
) -> List[List[Dict]]:
    """
    Ensure major-league fixtures appear at least once even if only one bookmaker has odds.
    """
    matched_keys = set()
    for group in matched_events:
        if not group:
            continue
        key = build_match_key(group[0])
        if key:
            matched_keys.add(key)

    added = 0
    for bookie, matches in all_matches.items():
        for match in matches:
            if not match.get('home_team') or not match.get('away_team'):
                continue
            if not match.get('home_odds') or not match.get('away_odds'):
                continue
            league = normalize_league(match.get('league', ''))
            if not league:
                league = infer_league_from_teams(match.get('home_team', ''), match.get('away_team', ''))
            if league not in LEAGUE_TEAMS:
                continue
            key = build_match_key(match)
            if not key or key in matched_keys:
                continue
            matched_keys.add(key)
            matched_events.append([match])
            added += 1

    if added:
        print(f"  [COVERAGE] Added {added} single-bookmaker major-league matches")
    return matched_events

def pick_league_for_group(event_group: List[Dict]) -> str:
    """Choose the best league label for a matched event group."""
    leagues_in_group = [
        normalize_league(m.get('league', ''))
        for m in event_group
        if m.get('league')
    ]
    league = ''
    if leagues_in_group:
        league = Counter(leagues_in_group).most_common(1)[0][0]
    if not league:
        league = normalize_league(event_group[0].get('league', ''))
    if not league:
        league = infer_league_from_teams(event_group[0].get('home_team', ''), event_group[0].get('away_team', ''))

    # Guard: if league is a known major league but teams are not members, fallback to raw label
    if league in LEAGUE_TEAMS:
        home = event_group[0].get('home_team', '')
        away = event_group[0].get('away_team', '')
        if not (is_team_in_league(home, league) and is_team_in_league(away, league)):
            inferred = infer_league_from_teams(home, away)
            if inferred and inferred != league:
                league = inferred
                return league
            raw_leagues = [m.get('league') for m in event_group if m.get('league')]
            fallback = raw_leagues[0] if raw_leagues else f'{league} (Other)'
            # If fallback is still ambiguous Premier League, force non-EPL label
            if league.lower() == 'premier league' and fallback.lower().strip() == 'premier league':
                # Try to detect country in any raw league label
                country_hint = ''
                for rl in raw_leagues:
                    rl_low = rl.lower()
                    for country in ['uganda', 'kenya', 'ghana', 'nigeria', 'tanzania', 'zambia', 'ethiopia']:
                        if country in rl_low:
                            country_hint = country.title()
                            break
                    if country_hint:
                        break
                if country_hint:
                    fallback = f'{country_hint} Premier League'
                else:
                    fallback = 'Premier League (Other)'
            league = fallback

    return league

def resolve_required_bookies(all_matches: Dict[str, List[Dict]]) -> List[str]:
    """Resolve which bookmakers are required for top-league full coverage."""
    base = EXPECTED_BOOKMAKERS if REQUIRE_ALL_EXPECTED_BOOKIES else REQUIRED_COVERAGE_BOOKMAKERS
    return [b for b in base if b in all_matches]

def filter_top_league_full_coverage(
    matched_events: List[List[Dict]],
    required_bookies: List[str]
) -> List[List[Dict]]:
    """Drop top-league matches that lack full bookmaker coverage."""
    if not matched_events or not required_bookies:
        return matched_events
    required_set = set(required_bookies)
    kept = []
    dropped = 0
    for group in matched_events:
        if not group:
            continue
        league = pick_league_for_group(group)
        is_top = league in LEAGUE_TEAMS or is_major_league_name(league)
        if not is_top:
            kept.append(group)
            continue
        group_bookies = {m.get('bookmaker') for m in group if m.get('bookmaker')}
        if required_set.issubset(group_bookies):
            kept.append(group)
        else:
            dropped += 1
    if dropped:
        print(f"  [COVERAGE] Dropped {dropped} top-league matches without full bookmaker coverage")
    return kept

def normalize_league(league: str) -> str:
    """Normalize league name to prevent duplicates across bookmakers."""
    if not league:
        return ''

    league = league.strip()

    # First normalize periods and spaces
    league = league.replace('. ', ' ').strip()  # "2. Bundesliga" -> "2 Bundesliga"

    # Normalize specific league name variations BEFORE country prefix removal
    # This ensures "Spain LaLiga" and "Spain La Liga" both become "Spain La Liga"
    league = league.replace('LaLiga', 'La Liga')  # "LaLiga" -> "La Liga"
    league = league.replace('2 Bundesliga', '2nd Bundesliga')
    league = league.replace('3 Bundesliga', '3rd Bundesliga')

    # Remove country prefixes for specific major leagues only
    # Important: "Premier League" without country means English Premier League
    # Other countries keep their prefix (e.g., "Kenya Premier League" stays as is)

    major_league_mappings = {
        'England Premier League': 'Premier League',  # English PL gets bare name
        'England Championship': 'Championship',
        'England League One': 'League One',
        'England League Two': 'League Two',
        'Spain La Liga': 'La Liga',
        'Spain La Liga 2': 'La Liga 2',
        'Italy Serie A': 'Serie A',
        'Italy Serie B': 'Serie B',
        'Germany Bundesliga': 'Bundesliga',
        'Germany 2nd Bundesliga': '2nd Bundesliga',
        'France Ligue 1': 'Ligue 1',
        'France Ligue 2': 'Ligue 2',
        'Portugal Primeira Liga': 'Primeira Liga',
        'Netherlands Eredivisie': 'Eredivisie',
        'Scotland Premiership': 'Scottish Premiership',
    }

    # Check for exact matches in major leagues
    if league in major_league_mappings:
        league = major_league_mappings[league]

    return league

def match_events(all_matches: Dict[str, List[Dict]]) -> List[List[Dict]]:
    """Match events across bookmakers."""
    print("\nMatching events...")

    groups = {}

    # Debug: Track specific matches to see why they don't match
    debug_teams = ['newcastle', 'chelsea']

    # Generic team names to filter out (these cause false matches)
    generic_names = {'home', 'away', 'team 1', 'team 2', 'team1', 'team2', 'home team', 'away team'}

    # Debug: Count Newcastle/Chelsea matches per bookmaker before matching
    newcastle_chelsea_count = {}
    for bookie, matches in all_matches.items():
        count = sum(1 for m in matches if ('newcastle' in m['home_team'].lower() and 'chelsea' in m['away_team'].lower()) or
                                          ('chelsea' in m['home_team'].lower() and 'newcastle' in m['away_team'].lower()))
        if count > 0:
            newcastle_chelsea_count[bookie] = count

    if newcastle_chelsea_count:
        print(f"\n  Newcastle vs Chelsea by bookmaker (before matching):")
        for bookie, count in newcastle_chelsea_count.items():
            print(f"    {bookie}: {count}")
        print()

    for bookie, matches in all_matches.items():
        for match in matches:
            home = normalize_name(match['home_team'])
            away = normalize_name(match['away_team'])

            # Debug logging for specific matches
            if any(team in home.lower() or team in away.lower() for team in debug_teams):
                if any(team in home.lower() for team in debug_teams) and any(team in away.lower() for team in debug_teams):
                    print(f"  [DEBUG] {bookie}: '{match['home_team']}' vs '{match['away_team']}' -> '{home}' vs '{away}'")

            # Skip matches with generic placeholder team names
            # Check for exact match or if name starts with/contains generic terms
            if (home in generic_names or away in generic_names or
                not home or not away or
                home.startswith('home') or away.startswith('away') or
                home.startswith('team') or away.startswith('team') or
                'special' in home.lower() or 'special' in away.lower()):
                continue

            # Try exact match first
            key = f"{home}|{away}"
            if key in groups:
                groups[key].append(match)
                continue
            reverse_key = f"{away}|{home}"
            if reverse_key in groups:
                groups[reverse_key].append(match)
                continue

            # Fuzzy matching
            matched = False
            for existing_key in list(groups.keys()):
                eh, ea = existing_key.split('|')
                existing_group = groups.get(existing_key) or []
                existing_time = existing_group[0].get('start_time') if existing_group else 0
                if not is_start_time_close(match.get('start_time'), existing_time):
                    continue
                home_sim = SequenceMatcher(None, home, eh).ratio()
                away_sim = SequenceMatcher(None, away, ea).ratio()
                home_tok = token_similarity(home, eh)
                away_tok = token_similarity(away, ea)
                home_sim_swap = SequenceMatcher(None, home, ea).ratio()
                away_sim_swap = SequenceMatcher(None, away, eh).ratio()
                home_tok_swap = token_similarity(home, ea)
                away_tok_swap = token_similarity(away, eh)

                if (
                    (home_sim > 0.75 and away_sim > 0.75)
                    or (home_tok >= 0.55 and away_tok >= 0.55)
                    or (home_sim_swap > 0.75 and away_sim_swap > 0.75)
                    or (home_tok_swap >= 0.55 and away_tok_swap >= 0.55)
                ):
                    groups[existing_key].append(match)
                    matched = True
                    break

            if not matched:
                groups[key] = [match]

    # Only return events with 2+ bookmakers
    matched = [g for g in groups.values() if len(g) >= 2]
    matched.sort(key=lambda x: len(x), reverse=True)

    print(f"  Matched {len(matched)} events across bookmakers")

    # Show distribution of bookmaker counts
    from collections import Counter
    bookmaker_counts = Counter(len(g) for g in matched)
    print("  Bookmaker coverage distribution:")
    for count in sorted(bookmaker_counts.keys(), reverse=True):
        print(f"    {count} bookmakers: {bookmaker_counts[count]} matches")

    # Show top matches with 6 bookmakers
    six_bookie_matches = [g for g in matched if len(g) == 6]
    if six_bookie_matches:
        print(f"\n  [OK] {len(six_bookie_matches)} matches with all 6 bookmakers")
        for match_group in six_bookie_matches[:5]:
            first = match_group[0]
            print(f"    - {first['home_team']} vs {first['away_team']} ({first.get('league', 'Unknown')})")
    else:
        print("\n  [WARNING] NO matches with all 6 bookmakers!")

    return matched


def serialize_matched_events(matched: List[List[Dict]], limit: int = 2000) -> List[Dict]:
    """Convert matched groups into API/output friendly structure."""
    serialized = []
    for e in matched[:limit]:
        serialized.append({
            'home_team': e[0]['home_team'],
            'away_team': e[0]['away_team'],
            'league': pick_league_for_group(e),
            'start_time': e[0].get('start_time', 0),
            'odds': [
                {
                    'bookmaker': m['bookmaker'],
                    'event_id': m.get('event_id') or m.get('match_id'),
                    'event_league_id': m.get('league_id'),
                    'home_odds': m.get('home_odds'),
                    'draw_odds': m.get('draw_odds'),
                    'away_odds': m.get('away_odds'),
                }
                for m in e
            ]
        })
    return serialized


def push_to_postgres(all_matches: Dict[str, List[Dict]]):
    """Optional: persist fixtures with canonical leagues if POSTGRES_DSN is set."""
    if not POSTGRES_DSN:
        return
    try:
        conn = psycopg2.connect(POSTGRES_DSN)
    except Exception as e:
        print(f"[WARN] Could not connect to Postgres: {e}")
        return

    try:
        leagues, aliases = fetch_leagues_and_aliases(conn)
        from backend.core.ingest_canonical import fetch_league_clubs
        league_clubs = fetch_league_clubs(conn)
        matcher = LeagueMatcher(leagues, aliases, league_clubs=league_clubs)

        # Map bookmaker names to provider slugs
        provider_map = {
            'Betway Ghana': 'betway',
            'SportyBet Ghana': 'sportybet',
            '1xBet Ghana': '1xbet',
            '22Bet Ghana': '22bet',
            'SoccaBet Ghana': 'soccabet',
            'Betfox Ghana': 'betfox',
        }

        for bookie, fixtures in all_matches.items():
            provider = provider_map.get(bookie)
            if not provider:
                continue
            ingest_matched_events(
                conn,
                matcher,
                provider=provider,
                fixtures=fixtures,
                default_sport="soccer",
                default_country=None,
                season=None,
            )
        print("[OK] Pushed fixtures to Postgres with canonical league matching")
    except Exception as e:
        print(f"[WARN] Postgres ingestion failed: {e}")
    finally:
        try:
            conn.close()
        except:
            pass


def push_to_d1(matched_events: List[List[Dict]]):
    """Push fixtures to Cloudflare Worker D1 canonical ingest."""
    if not CLOUDFLARE_API_KEY:
        return
    api_url = D1_CANONICAL_INGEST or CLOUDFLARE_WORKER_URL
    if not api_url:
        return
    api_url = api_url.rstrip('/')
    if not api_url.endswith('/api/canonical/ingest'):
        api_url += '/api/canonical/ingest'

    fixtures = []
    for e in matched_events:
        first = e[0]
        fixtures.append({
            'fixture_id': f"{first['home_team']}-{first['away_team']}-{first.get('start_time', 0)}".replace(' ', '-').lower(),
            'league_id': None,
            'provider': 'github-scraper',
            'provider_fixture_id': f"{first.get('start_time', 0)}-{first['home_team']}-{first['away_team']}",
            'home_team': first['home_team'],
            'away_team': first['away_team'],
            'kickoff_time': first.get('start_time', 0),
            'country_code': None,
            'sport': 'soccer',
            'raw_league_name': first.get('league', ''),
            'raw_league_id': first.get('league', ''),
            'confidence': None
        })

    try:
        resp = requests.post(api_url, json=fixtures, headers={'X-API-Key': CLOUDFLARE_API_KEY, 'Content-Type': 'application/json'}, timeout=30)
        print(f"[D1] Ingest response: {resp.status_code}")
        if resp.status_code != 200:
            print(resp.text[:300])
    except Exception as e:
        print(f"[D1] Ingest error: {e}")


# ============================================================================
# Cloudflare Push
# ============================================================================

def build_odds_endpoint(base_url: str, fast: bool) -> str:
    base = (base_url or '').rstrip('/')
    for suffix in ('/api/odds/update', '/api/odds/fast'):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    return f"{base}/api/odds/fast" if fast else f"{base}/api/odds/update"


def push_to_cloudflare(
    matched_events: List[List[Dict]],
    fast: bool = False,
    run_id: Optional[str] = None,
    last_updated: Optional[str] = None
):
    """Push matched events to Cloudflare Worker."""
    if not CLOUDFLARE_WORKER_URL or not CLOUDFLARE_API_KEY:
        print("\n" + "="*60)
        print("WARNING: Cloudflare credentials not set")
        print("="*60)
        print("  CLOUDFLARE_WORKER_URL:", "[SET]" if CLOUDFLARE_WORKER_URL else "[MISSING]")
        print("  CLOUDFLARE_API_KEY:", "[SET]" if CLOUDFLARE_API_KEY else "[MISSING]")
        print("\n  Data saved locally to odds_data.json but NOT pushed to Cloudflare.")
        print("  Website will NOT update with new odds.")
        print("\n  To fix: Set environment variables in GitHub Actions secrets:")
        print("    - CLOUDFLARE_WORKER_URL")
        print("    - CLOUDFLARE_API_KEY")
        print("="*60)
        return

    api_url = build_odds_endpoint(CLOUDFLARE_WORKER_URL, fast)

    print(f"\n{'='*60}")
    print(f"Pushing {len(matched_events)} events to Cloudflare{' (FAST)' if fast else ''}...")
    print(f"{'='*60}")
    print(f"  Target URL: {api_url}")
    print(f"  Events to push: {len(matched_events)}")

    # Group matches by league (Worker expects LeagueGroup[] format)
    league_groups = {}
    filtered_count = 0

    for event_group in matched_events[:1500]:  # Limit to 1500 matches
        if not event_group:
            continue

        first = event_group[0]
        league = pick_league_for_group(event_group)

        # Validate teams for specific leagues to prevent cross-contamination
        # Check if this league has validation data (Premier League, La Liga, Serie A, etc.)
        if league in LEAGUE_TEAMS:
            home_team = first.get('home_team', '')
            away_team = first.get('away_team', '')

            # Check if either team belongs to this league
            is_home_valid = is_team_in_league(home_team, league)
            is_away_valid = is_team_in_league(away_team, league)

            if not (is_home_valid or is_away_valid):
                # This match doesn't belong to this league - skip it
                print(f"  [FILTER] Skipping non-{league} match: {home_team} vs {away_team}")
                filtered_count += 1
                continue

        # Initialize league group if not exists
        if league not in league_groups:
            league_groups[league] = {
                'league': league,
                'matches': []
            }

        # Build match data
        match_data = {
            'id': f"{first['home_team']}-{first['away_team']}-{first.get('start_time', 0)}".replace(' ', '-').lower(),
            'home_team': first['home_team'],
            'away_team': first['away_team'],
            'league': league,
            'start_time': first.get('start_time', 0),
            'odds': []
        }

        for m in event_group:
            match_data['odds'].append({
                'bookmaker': m['bookmaker'],
                'home_odds': m['home_odds'],
                'draw_odds': m['draw_odds'],
                'away_odds': m['away_odds']
            })

        league_groups[league]['matches'].append(match_data)

    # Print filtering stats
    if filtered_count > 0:
        print(f"  [FILTER] Filtered out {filtered_count} mismatched matches from major leagues")

    # Convert to array format expected by Worker
    output = list(league_groups.values())

    try:
        print(f"  Sending POST request with {len(output)} leagues...")
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': CLOUDFLARE_API_KEY,
        }
        if run_id:
            headers['X-Run-Id'] = run_id
        if last_updated:
            headers['X-Run-Updated'] = last_updated

        resp = requests.post(
            api_url,
            json=output,
            headers=headers,
            timeout=30
        )
        print(f"  [OK] Cloudflare response: {resp.status_code}")

        if resp.status_code == 200:
            total_matches = sum(len(lg['matches']) for lg in output)
            print(f"  [SUCCESS] Pushed {total_matches} matches in {len(output)} leagues to Cloudflare!")
            print(f"  [SUCCESS] Website will update with new odds")
        else:
            print(f"  [WARNING] Unexpected status code: {resp.status_code}")
            print(f"  Response: {resp.text[:500]}")
    except Exception as e:
        print(f"  [ERROR] Cloudflare push error: {e}")
        print(f"  [ERROR] Website will NOT update with new odds")


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Odds scraper / matcher")
    parser.add_argument('--from-file', help='Load raw scraped data JSON instead of scraping')
    parser.add_argument('--no-push', action='store_true', help='Skip pushing to Cloudflare/D1/Postgres')
    parser.add_argument('--skip-scrape', action='store_true', help='Skip scraping (use with --from-file)')
    parser.add_argument('--fast', action='store_true', help='Use faster, lower-coverage scraping settings')
    args = parser.parse_args()

    if args.fast and not FAST_MODE:
        apply_fast_mode()

    if FAST_MODE:
        os.environ.setdefault("TWENTYTWOBET_MAX_MATCHES", str(env_int("TWENTYTWOBET_MAX_MATCHES_FAST", 300)))

    start_time = time.time()
    print("=" * 60)
    print("ODDS SCRAPER - TURBO MODE")
    print("=" * 60)
    if FAST_MODE:
        print("FAST MODE: reduced coverage for speed")

    all_matches = {}
    elapsed = 0.0

    if args.from_file:
        print(f"Loading raw data from {args.from_file} ...")
        with open(args.from_file, 'r', encoding='utf-8') as f:
            all_matches = json.load(f)
    elif not args.skip_scrape:
        scrapers = {
            'SportyBet Ghana': scrape_sportybet,
            '1xBet Ghana': scrape_1xbet,
            'Betway Ghana': scrape_betway,
            'SoccaBet Ghana': scrape_soccabet,
            '22Bet Ghana': scrape_22bet_ghana,  # Updated platform API scraper
            'Betfox Ghana': scrape_betfox,  # WORKING - Using V4 API (100+ fixtures from upcoming + live)
        }

        def timed_scraper(name, fn):
            started = time.time()
            matches = fn()
            duration = time.time() - started
            print(f"  [{name}] {len(matches)} matches in {duration:.1f}s")
            return matches

        print("\nRunning ALL scrapers in parallel...")
        with ThreadPoolExecutor(max_workers=6) as executor:
            future_to_bookie = {
                executor.submit(timed_scraper, bookie, scraper): bookie
                for bookie, scraper in scrapers.items()
            }
            for future in as_completed(future_to_bookie):
                bookie = future_to_bookie[future]
                try:
                    matches = future.result()
                    if matches:
                        all_matches[bookie] = matches
                except Exception as e:
                    print(f"  {bookie} failed: {e}")

        elapsed = time.time() - start_time
        total = sum(len(m) for m in all_matches.values())
        print(f"\n{'=' * 60}")
        print(f"SCRAPING COMPLETE in {elapsed:.1f} seconds")
        print(f"Total scraped: {total} matches from {len(all_matches)} bookmakers")
        for bookie, matches in all_matches.items():
            print(f"  - {bookie}: {len(matches)} matches")
        print(f"{'=' * 60}")

        if not all_matches:
            print("No matches scraped - exiting")
            return

        raw_data_file = 'raw_scraped_data.json'
        print(f"\nSaving raw scraped data to {raw_data_file}...")
        try:
            with open(raw_data_file, 'w', encoding='utf-8') as f:
                json.dump(all_matches, f, indent=2, ensure_ascii=False)
            print(f"  [OK] Saved {total} matches from {len(all_matches)} bookmakers")
        except Exception as e:
            print(f"  [WARNING] Failed to save raw data: {e}")
    else:
        print("No data source provided (use --from-file or run scrape). Exiting.")
        return

    matched = match_events(all_matches)
    if REQUIRE_FULL_TOP_LEAGUE_COVERAGE:
        required_targets = EXPECTED_BOOKMAKERS if REQUIRE_ALL_EXPECTED_BOOKIES else REQUIRED_COVERAGE_BOOKMAKERS
        missing_required = [b for b in required_targets if b not in all_matches]
        if missing_required:
            print(f"  [WARN] Missing required bookmakers this run: {', '.join(missing_required)}")
        optional_missing = [b for b in OPTIONAL_BOOKMAKERS if b not in all_matches]
        if optional_missing:
            print(f"  [INFO] Optional bookmakers missing (ignored for coverage): {', '.join(optional_missing)}")
        required_bookies = resolve_required_bookies(all_matches)
        matched = filter_top_league_full_coverage(matched, required_bookies)

    if ALLOW_SINGLE_BOOKIE_MAJORS and not REQUIRE_FULL_TOP_LEAGUE_COVERAGE:
        matched = add_single_bookie_major_league_matches(all_matches, matched)

    if not matched:
        print("No matched events - exiting")
        return

    total = sum(len(m) for m in all_matches.values())
    output = {
        'last_updated': datetime.now().isoformat(),
        'stats': {
            'total_scraped': total,
            'matched_events': len(matched),
            'bookmakers': list(all_matches.keys()),
            'scrape_time_seconds': elapsed,
        },
        'matches': serialize_matched_events(matched)
    }

    with open('odds_data.json', 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to odds_data.json")
    try:
        save_history_snapshot(output, all_matches)
        print(f"[HISTORY] Appended snapshot to {resolve_history_path(HISTORY_MATCHED_FILE)}")
        if SAVE_RAW_HISTORY:
            print(f"[HISTORY] Appended raw snapshot to {resolve_history_path(HISTORY_RAW_FILE)}")
        if SAVE_HISTORY_DB:
            print(f"[HISTORY] Stored snapshot in {resolve_history_path(HISTORY_DB_PATH)}")
    except Exception as e:
        print(f"[WARN] Failed to append history snapshot: {e}")

    if not args.no_push:
        run_id = output.get('last_updated')
        push_to_cloudflare(matched, fast=FAST_MODE, run_id=run_id, last_updated=run_id)
        if FAST_MODE:
            print("FAST MODE: skipping Postgres/D1 ingest for speed")
        else:
            push_to_postgres(all_matches)
            push_to_d1(matched)
    else:
        print("Skipping push (--no-push)")

    total_time = time.time() - start_time
    print(f"\nTOTAL TIME: {total_time:.1f} seconds")
    print("Done!")


if __name__ == '__main__':
    main()
