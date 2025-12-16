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
import requests
import cloudscraper
import asyncio
from datetime import datetime
from typing import Dict, List, Set, Optional
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration - AGGRESSIVE MODE
CLOUDFLARE_WORKER_URL = os.getenv('CLOUDFLARE_WORKER_URL', '')
CLOUDFLARE_API_KEY = os.getenv('CLOUDFLARE_API_KEY', '')
MAX_MATCHES = 5000  # Push the limits even higher
MAX_CHAMPIONSHIPS = 300  # Even more leagues
TIMEOUT = 10  # Slightly longer timeout for reliability
BATCH_SIZE = 300  # Even larger batches
PARALLEL_PAGES = 10  # More concurrent page fetches

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

def fetch_sportybet_page(session, headers, page):
    """Fetch a single page from SportyBet."""
    try:
        url = f"{SPORTYBET_API}?sportId=sr%3Asport%3A1&marketId=1&pageSize=100&pageNum={page}"
        resp = session.get(url, headers=headers, timeout=TIMEOUT)
        data = resp.json()
        if data.get('bizCode') != 10000:
            return []
        return data.get('data', {}).get('tournaments', [])
    except:
        return []

def scrape_sportybet() -> List[Dict]:
    """Scrape SportyBet Ghana via API with parallel page fetching."""
    print("Scraping SportyBet Ghana (TURBO)...")
    matches = []
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
        time.sleep(1)
    except:
        pass

    headers = {
        **HEADERS,
        'Referer': 'https://www.sportybet.com/gh/',
    }

    # Fetch pages in parallel - increase to 80 pages for maximum coverage
    all_tournaments = []
    with ThreadPoolExecutor(max_workers=PARALLEL_PAGES) as executor:
        futures = {executor.submit(fetch_sportybet_page, session, headers, p): p for p in range(1, 81)}
        for future in as_completed(futures):
            tournaments = future.result()
            all_tournaments.extend(tournaments)

    # Parse all tournaments
    for tournament in all_tournaments:
        for event in tournament.get('events', []):
            if len(matches) >= MAX_MATCHES:
                break

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
            league = tourn.get('name', tournament.get('name', ''))

            start_time = event.get('estimateStartTime', 0)
            if start_time > 1000000000000:
                start_time = start_time // 1000

            seen_ids.add(event_id)
            matches.append({
                'bookmaker': 'SportyBet Ghana',
                'event_id': str(event_id),
                'home_team': home,
                'away_team': away,
                'home_odds': home_odds,
                'draw_odds': draw_odds or 0.0,
                'away_odds': away_odds,
                'league': league,
                'start_time': start_time,
            })

    print(f"  Total: {len(matches)} matches from SportyBet")
    return matches[:MAX_MATCHES]


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
# 22Bet Ghana Scraper - DIRECT API (Same structure as 1xBet)
# Using cloudscraper to bypass Cloudflare protection
# ============================================================================

TWENTYTWOBET_API = "https://22bet.com/gh/LineFeed"  # Note: .com/gh not .com.gh

def fetch_22bet_games(scraper, champ_id, champ_name):
    """Fetch games for a single championship."""
    matches = []
    try:
        resp = scraper.get(f"{TWENTYTWOBET_API}/GetChampZip?champ={champ_id}&lng=en", timeout=20)
        value = resp.json().get("Value", {})
        games = value.get("G", []) if isinstance(value, dict) else []

        game_ids = [g.get("I") for g in games if g.get("I")]
        if not game_ids:
            return []

        # Fetch all games in one batch
        ids_str = ",".join(str(i) for i in game_ids[:BATCH_SIZE])
        resp = scraper.get(f"{TWENTYTWOBET_API}/GetGamesZip?ids={ids_str}&lng=en", timeout=20)
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
                'bookmaker': '22Bet Ghana',
                'event_id': str(event_id),
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

def scrape_22bet() -> List[Dict]:
    """Scrape 22Bet Ghana (Direct API with Cloudflare bypass)."""
    print("Scraping 22Bet Ghana (with Cloudflare bypass)...")

    # Use cloudscraper to bypass Cloudflare
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    try:
        # Use longer timeout for 22Bet (they may be slower)
        resp = scraper.get(f"{TWENTYTWOBET_API}/GetChampsZip?sport=1&lng=en", timeout=20)
        if resp.status_code != 200:
            print(f"  22Bet API returned status {resp.status_code}")
            return []
        champs = resp.json().get("Value", [])
        champs = sorted(champs, key=lambda x: x.get("GC", 0), reverse=True)[:MAX_CHAMPIONSHIPS]
    except Exception as e:
        print(f"  22Bet error getting champs: {e}")
        return []

    skip_patterns = ["alternative", "team vs player", "specials", "fantasy", "esports"]
    valid_champs = [(c.get("LI"), c.get("L", "")) for c in champs
                    if not any(p in c.get("L", "").lower() for p in skip_patterns)]

    # Parallel championship fetching
    all_matches = []
    with ThreadPoolExecutor(max_workers=PARALLEL_PAGES) as executor:
        futures = {executor.submit(fetch_22bet_games, scraper, cid, cname): cid
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

    print(f"  Total: {len(unique)} matches from 22Bet")
    return unique[:MAX_MATCHES]


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

    page_size = 1000  # Push it higher

    # Fetch pages in parallel - increase range to 30000 for more coverage
    all_data = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_betway_page, session, headers, skip, page_size): skip
                   for skip in range(0, 30000, page_size)}
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

            market = market_by_event.get(event_id)
            if not market:
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
                if name == home or name == 'Home':
                    home_odds = price
                elif name.lower() == 'draw':
                    draw_odds = price
                elif name == away or name == 'Away':
                    away_odds = price

            if not home_odds or not away_odds:
                continue

            league = event.get('league', event.get('competition', {}).get('name', ''))
            start_time = event.get('expectedStartEpoch', 0)

            seen_ids.add(event_id)
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
    """Scrape Betfox Ghana via V4 fixtures API."""
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
        # Get football fixtures from V4 API (upcoming + live)
        all_fixtures = []

        # Get upcoming matches (V4 API returns 100 fixtures max)
        resp = scraper.get(
            'https://www.betfox.com.gh/api/offer/v4/fixtures/home/upcoming?first=1000&sport=Football',
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json()
            upcoming_fixtures = data.get('data', [])
            all_fixtures.extend(upcoming_fixtures)
            print(f"  Upcoming fixtures: {len(upcoming_fixtures)}")

        # Also get live matches for additional coverage
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

        print(f"  Total fetched: {len(all_fixtures)} fixtures (upcoming + live)")

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

def normalize_name(name: str) -> str:
    """Normalize team name for matching."""
    name = name.lower().strip()
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name)

    removals = ['fc', 'cf', 'sc', 'ac', 'afc', 'ssc', 'bc', 'fk', 'sk', 'nk',
                'united', 'utd', 'city', 'town', 'athletic', 'sporting']
    words = name.split()
    words = [w for w in words if w not in removals]
    return ' '.join(words) if words else name

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

    # Generic team names to filter out (these cause false matches)
    generic_names = {'home', 'away', 'team 1', 'team 2', 'team1', 'team2', 'home team', 'away team'}

    for bookie, matches in all_matches.items():
        for match in matches:
            home = normalize_name(match['home_team'])
            away = normalize_name(match['away_team'])

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

            # Fuzzy matching
            matched = False
            for existing_key in list(groups.keys()):
                eh, ea = existing_key.split('|')
                home_sim = SequenceMatcher(None, home, eh).ratio()
                away_sim = SequenceMatcher(None, away, ea).ratio()

                if home_sim > 0.8 and away_sim > 0.8:
                    groups[existing_key].append(match)
                    matched = True
                    break

            if not matched:
                groups[key] = [match]

    # Only return events with 2+ bookmakers
    matched = [g for g in groups.values() if len(g) >= 2]
    matched.sort(key=lambda x: len(x), reverse=True)

    print(f"  Matched {len(matched)} events across bookmakers")
    return matched


# ============================================================================
# Cloudflare Push
# ============================================================================

def push_to_cloudflare(matched_events: List[List[Dict]]):
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

    # Ensure URL ends with /api/odds/update
    api_url = CLOUDFLARE_WORKER_URL.rstrip('/')
    if not api_url.endswith('/api/odds/update'):
        api_url += '/api/odds/update'

    print(f"\n{'='*60}")
    print(f"Pushing {len(matched_events)} events to Cloudflare...")
    print(f"{'='*60}")
    print(f"  Target URL: {api_url}")
    print(f"  Events to push: {len(matched_events)}")

    # Group matches by league (Worker expects LeagueGroup[] format)
    league_groups = {}

    for event_group in matched_events[:1500]:  # Limit to 1500 matches
        if not event_group:
            continue

        first = event_group[0]
        league = first.get('league', 'Unknown League')

        # Normalize league name to prevent duplicates (e.g., "England. Premier League" -> "Premier League")
        league = normalize_league(league)

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

    # Convert to array format expected by Worker
    output = list(league_groups.values())

    try:
        print(f"  Sending POST request with {len(output)} leagues...")
        resp = requests.post(
            api_url,
            json=output,
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': CLOUDFLARE_API_KEY
            },
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
    start_time = time.time()
    print("=" * 60)
    print("ODDS SCRAPER - TURBO MODE")
    print("=" * 60)

    all_matches = {}

    scrapers = {
        'SportyBet Ghana': scrape_sportybet,
        '1xBet Ghana': scrape_1xbet,
        'Betway Ghana': scrape_betway,
        'SoccaBet Ghana': scrape_soccabet,
        '22Bet Ghana': scrape_22bet,  # WORKING - Using cloudscraper with correct API endpoint
        'Betfox Ghana': scrape_betfox,  # WORKING - Using V4 API (100+ fixtures from upcoming + live)
    }

    print("\nRunning ALL scrapers in parallel...")
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_bookie = {
            executor.submit(scraper): bookie
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

    matched = match_events(all_matches)

    if not matched:
        print("No matched events - exiting")
        return

    # Save to file
    output = {
        'last_updated': datetime.now().isoformat(),
        'stats': {
            'total_scraped': total,
            'matched_events': len(matched),
            'bookmakers': list(all_matches.keys()),
            'scrape_time_seconds': elapsed
        },
        'matches': [
            {
                'home_team': e[0]['home_team'],
                'away_team': e[0]['away_team'],
                'league': e[0].get('league', ''),
                'start_time': e[0].get('start_time', 0),
                'odds': [
                    {
                        'bookmaker': m['bookmaker'],
                        'home_odds': m['home_odds'],
                        'draw_odds': m['draw_odds'],
                        'away_odds': m['away_odds']
                    }
                    for m in e
                ]
            }
            for e in matched[:2000]  # Save more matches
        ]
    }

    with open('odds_data.json', 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to odds_data.json")

    push_to_cloudflare(matched)

    total_time = time.time() - start_time
    print(f"\nTOTAL TIME: {total_time:.1f} seconds")
    print("Done!")


if __name__ == '__main__':
    main()
