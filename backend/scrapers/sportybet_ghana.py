#!/usr/bin/env python3
"""SportyBet Ghana Odds Scraper (API-based)

Uses the pcUpcomingEvents API endpoint with pagination.
"""

import json
import os
import subprocess
import time
from typing import Dict, List, Optional, Set

API_URL = "https://www.sportybet.com/api/gh/factsCenter/pcUpcomingEvents"
DEFAULT_MAX_MATCHES = 1200
TOURNAMENT_LOOKUP_PAGES = int(os.getenv("SPORTYBET_TOURNAMENT_LOOKUP_PAGES", "10"))
TOURNAMENT_MAX_PAGES = int(os.getenv("SPORTYBET_TOURNAMENT_MAX_PAGES", "5"))
TOURNAMENT_PAGE_SIZE = int(os.getenv("SPORTYBET_TOURNAMENT_PAGE_SIZE", "100"))

MAJOR_LEAGUE_KEYWORDS = {
    "premier": ["premier league", "english premier league", "england premier league", "epl"],
    "laliga": ["la liga", "laliga", "primera division"],
    "seriea": ["serie a"],
    "bundesliga": ["bundesliga"],
    "ligue1": ["ligue 1"],
    "ucl": ["uefa champions league", "champions league", "ucl"],
}

MAJOR_LEAGUE_EXCLUSIONS = {
    "premier league cup",
    "premier league 2",
    "premier league u21",
    "premier league u 21",
    "premier league u-21",
}


def _fetch_page(page_num: int, page_size: int = 100, tournament_id: Optional[str] = None) -> dict:
    """Fetch a page of events from SportyBet API."""
    url = (
        f"{API_URL}?sportId=sr%3Asport%3A1"
        f"&marketId=1%2C18%2C10"
        f"&pageSize={page_size}"
        f"&pageNum={page_num}"
        f"&option=1"
    )
    if tournament_id:
        url += f"&tournamentId={tournament_id}"

    cmd = [
        "curl", "-s", "--compressed",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "-H", "Accept: application/json",
        "-H", "Referer: https://www.sportybet.com/gh/sport/football",
        "-H", "accept-language: en",
        "-H", "clientid: web",
        "-H", "operid: 3",
        "-H", "platform: web",
        url
    ]

    result = subprocess.run(cmd, capture_output=True, timeout=30)
    if result.returncode != 0 or not result.stdout:
        return {}

    return json.loads(result.stdout.decode('utf-8', errors='ignore'))


def _parse_events(tournaments: List[Dict], seen_ids: Set[str], major_ids: Set[str]) -> List[Dict]:
    """Parse events from tournament data."""
    matches = []

    for tournament in tournaments:
        tournament_name = tournament.get('name', '') or ''
        for event in tournament.get('events', []):
            try:
                event_id = event.get('eventId')
                if not event_id or event_id in seen_ids:
                    continue

                home = event.get('homeTeamName')
                away = event.get('awayTeamName')

                if not home or not away:
                    continue

                # Extract 1X2 odds from markets
                home_odds = draw_odds = away_odds = None
                markets = event.get('markets', [])

                for market in markets:
                    # Market ID 1 is typically 1X2
                    if market.get('id') == '1' or market.get('name') in ['1X2', '1x2', 'Match Result']:
                        outcomes = market.get('outcomes', [])
                        for outcome in outcomes:
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

                # Get league/tournament name
                sport = event.get('sport', {})
                category = sport.get('category', {})
                tournament = category.get('tournament', {})
                league = tournament.get('name', '') or tournament_name

                # Get start time (milliseconds to seconds)
                start_time = event.get('estimateStartTime', 0)
                if start_time > 1000000000000:  # If in milliseconds
                    start_time = start_time // 1000

                seen_ids.add(event_id)
                if _is_major_league(league) or _is_major_league(tournament_name):
                    major_ids.add(str(event_id))
                matches.append({
                    'bookmaker': 'SportyBet Ghana',
                    'event_id': event_id,
                    'home_team': home,
                    'away_team': away,
                    'teams': f"{home} vs {away}",
                    'home_odds': home_odds,
                    'draw_odds': draw_odds if draw_odds else 0.0,
                    'away_odds': away_odds,
                    'league': league,
                    'start_time': start_time,
                })

            except Exception:
                continue

    return matches


def _is_major_league(name: str) -> bool:
    if not name:
        return False
    lowered = name.lower()
    if any(ex in lowered for ex in MAJOR_LEAGUE_EXCLUSIONS):
        return False
    return any(any(k in lowered for k in keywords) for keywords in MAJOR_LEAGUE_KEYWORDS.values())


def _find_tournament_ids() -> Dict[str, Set[str]]:
    """Discover tournament IDs for major leagues."""
    found: Dict[str, Set[str]] = {key: set() for key in MAJOR_LEAGUE_KEYWORDS}
    for page in range(1, TOURNAMENT_LOOKUP_PAGES + 1):
        data = _fetch_page(page, page_size=TOURNAMENT_PAGE_SIZE)
        if data.get('bizCode') != 10000:
            break
        tournaments = data.get('data', {}).get('tournaments', [])
        if not tournaments:
            break
        for tournament in tournaments:
            name = tournament.get('name', '') or ''
            tournament_id = tournament.get('id') or tournament.get('tournamentId')
            if not tournament_id:
                continue
            for league_key, keywords in MAJOR_LEAGUE_KEYWORDS.items():
                if any(k in name.lower() for k in keywords) and not any(ex in name.lower() for ex in MAJOR_LEAGUE_EXCLUSIONS):
                    found[league_key].add(tournament_id)
    return found


def scrape_sportybet_ghana(max_matches: int = DEFAULT_MAX_MATCHES) -> List[Dict]:
    """Scrape SportyBet Ghana via API with pagination."""
    max_matches = int(os.getenv("SPORTYBET_MAX_MATCHES", max_matches))

    print("Scraping SportyBet Ghana API...")

    matches: List[Dict] = []
    major_ids: Set[str] = set()
    seen_ids: Set[str] = set()

    page = 1
    max_pages = 20  # Safety limit

    while len(matches) < max_matches and page <= max_pages:
        try:
            data = _fetch_page(page)
            if data.get('bizCode') != 10000:
                print(f"  Page {page}: API error {data.get('bizCode')}")
                break

            tournaments = data.get('data', {}).get('tournaments', [])
            if not tournaments:
                print(f"  Page {page}: No more tournaments")
                break

            new_matches = _parse_events(tournaments, seen_ids, major_ids)
            matches.extend(new_matches)

            total_available = data.get('data', {}).get('totalNum', 0)
            print(f"  Page {page}: +{len(new_matches)} (total {len(matches)}/{total_available})")

            page += 1
            time.sleep(0.05)

        except Exception as e:
            print(f"  Page {page}: Error - {e}")
            break

    # Targeted league fetch to ensure coverage of major leagues
    tournament_ids = _find_tournament_ids()
    for league_key, ids in tournament_ids.items():
        for tournament_id in ids:
            for page in range(1, TOURNAMENT_MAX_PAGES + 1):
                data = _fetch_page(page, page_size=TOURNAMENT_PAGE_SIZE, tournament_id=tournament_id)
                if data.get('bizCode') != 10000:
                    break
                tournaments = data.get('data', {}).get('tournaments', [])
                if not tournaments:
                    break
                new_matches = _parse_events(tournaments, seen_ids, major_ids)
                matches.extend(new_matches)

    major_first = [m for m in matches if str(m.get('event_id')) in major_ids]
    other = [m for m in matches if str(m.get('event_id')) not in major_ids]
    matches = (major_first + other)[:max_matches]
    print(f"Found {len(matches)} matches on SportyBet")
    return matches


if __name__ == "__main__":
    data = scrape_sportybet_ghana()
    for m in data[:5]:
        print(f"{m['teams']}: {m['home_odds']} / {m['draw_odds']} / {m['away_odds']}")
