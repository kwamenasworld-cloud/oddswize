#!/usr/bin/env python3
"""Betway Ghana Odds Scraper (API-based)

Uses the Upcoming API endpoint with pagination.
"""

import json
import os
import subprocess
import time
from typing import Dict, List, Set

API_URL = "https://www.betway.com.gh/sportsapi/br/v1/BetBook/Upcoming/"
DEFAULT_MAX_MATCHES = 800
PAGE_SIZE = 500


def _fetch_page(skip: int = 0, take: int = PAGE_SIZE) -> dict:
    """Fetch a page of upcoming soccer events from Betway API."""
    url = (
        f"{API_URL}?countryCode=GH"
        f"&sportId=soccer"
        f"&cultureCode=en-US"
        f"&marketTypes=%5BWin%2FDraw%2FWin%5D"
        f"&isEsport=false"
        f"&Skip={skip}"
        f"&Take={take}"
    )

    cmd = [
        "curl", "-s", "--compressed",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "-H", "Accept: application/json",
        "-H", "Referer: https://www.betway.com.gh/sport/soccer/upcoming",
        url
    ]

    result = subprocess.run(cmd, capture_output=True, timeout=60)
    if result.returncode != 0 or not result.stdout:
        return {}

    return json.loads(result.stdout.decode('utf-8', errors='ignore'))


def _parse_events(data: dict, seen_ids: Set[int]) -> List[Dict]:
    """Parse events from API response into match format."""
    matches = []

    events = data.get('events', [])
    markets = data.get('markets', [])
    outcomes = data.get('outcomes', [])
    prices = data.get('prices', [])

    # Build lookup maps
    # markets by eventId
    market_by_event = {}
    for m in markets:
        if m.get('name') == '[Win/Draw/Win]' or m.get('displayName') == '1X2':
            market_by_event[m.get('eventId')] = m

    # outcomes by marketId
    outcomes_by_market = {}
    for o in outcomes:
        mid = o.get('marketId')
        if mid not in outcomes_by_market:
            outcomes_by_market[mid] = []
        outcomes_by_market[mid].append(o)

    # prices by outcomeId
    price_by_outcome = {p.get('outcomeId'): p.get('priceDecimal') for p in prices}

    for event in events:
        try:
            event_id = event.get('eventId')
            if not event_id or event_id in seen_ids:
                continue

            home = event.get('homeTeam')
            away = event.get('awayTeam')

            if not home or not away:
                continue

            # Find 1X2 market for this event
            market = market_by_event.get(event_id)
            if not market:
                continue

            market_id = market.get('marketId')
            market_outcomes = outcomes_by_market.get(market_id, [])

            home_odds = draw_odds = away_odds = None

            for outcome in market_outcomes:
                outcome_id = outcome.get('outcomeId')
                outcome_name = outcome.get('name', '').lower()
                price = price_by_outcome.get(outcome_id)

                if not price:
                    continue

                # Match outcome to home/draw/away
                if outcome_name == home.lower() or outcome.get('displayName', '').lower() == home.lower():
                    home_odds = price
                elif outcome_name == away.lower() or outcome.get('displayName', '').lower() == away.lower():
                    away_odds = price
                elif 'draw' in outcome_name or outcome_name == 'x':
                    draw_odds = price

            if not home_odds or not away_odds:
                continue

            seen_ids.add(event_id)
            matches.append({
                'bookmaker': 'Betway Ghana',
                'event_id': event_id,
                'home_team': home,
                'away_team': away,
                'teams': f"{home} vs {away}",
                'home_odds': home_odds,
                'draw_odds': draw_odds if draw_odds else 0.0,
                'away_odds': away_odds,
                'league': event.get('league', ''),
                'start_time': event.get('expectedStartEpoch', 0),
            })

        except Exception:
            continue

    return matches


def scrape_betway_ghana(max_matches: int = DEFAULT_MAX_MATCHES) -> List[Dict]:
    """Scrape Betway Ghana via API with pagination."""
    max_matches = int(os.getenv("BETWAY_MAX_MATCHES", max_matches))

    print("Scraping Betway Ghana API...")

    matches: List[Dict] = []
    seen_ids: Set[int] = set()

    skip = 0
    max_pages = 10  # Safety limit

    while len(matches) < max_matches and skip < max_pages * PAGE_SIZE:
        try:
            data = _fetch_page(skip=skip, take=PAGE_SIZE)

            events = data.get('events', [])
            if not events:
                print(f"  Skip {skip}: No more events")
                break

            new_matches = _parse_events(data, seen_ids)
            matches.extend(new_matches)

            is_final = data.get('isFinalPage', False)
            print(f"  Skip {skip}: +{len(new_matches)} matches (total {len(matches)}, isFinalPage={is_final})")

            if is_final:
                break

            skip += PAGE_SIZE
            time.sleep(0.05)

        except Exception as e:
            print(f"  Skip {skip}: Error - {e}")
            break

    matches = matches[:max_matches]
    print(f"Found {len(matches)} matches on Betway")
    return matches


if __name__ == "__main__":
    data = scrape_betway_ghana()
    for m in data[:5]:
        print(f"{m['teams']}: {m['home_odds']} / {m['draw_odds']} / {m['away_odds']}")
