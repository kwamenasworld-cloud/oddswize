#!/usr/bin/env python3
"""
SoccaBet Ghana Scraper
Fetches football odds from SoccaBet Ghana API via /bet/odds.js endpoint
"""

import json
import requests
import time
from typing import Dict, List, Optional


def scrape_soccabet_ghana(max_matches: int = 800) -> List[Dict]:
    """
    Scrape football matches and odds from SoccaBet Ghana.
    Uses the /bet/odds.js endpoint which contains all matches with odds.
    """
    print("Scraping SoccaBet Ghana API...")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.soccabet.com/',
    }

    session = requests.Session()

    try:
        # First establish session
        session.get('https://www.soccabet.com/', headers=headers, timeout=15)
        time.sleep(0.05)

        # Get the full odds data
        resp = session.get(
            'https://www.soccabet.com/bet/odds.js',
            headers=headers,
            timeout=60  # Large file, needs more time
        )

        if resp.status_code != 200:
            print(f"  Error: HTTP {resp.status_code}")
            return []

        data = json.loads(resp.text)

        # Get soccer sport data (ID: 77)
        sports = data.get('sports', {})
        soccer = sports.get('77', {})

        if not soccer:
            print("  Error: No soccer data found")
            return []

        # Get market type definitions
        market_types = data.get('markets', {})

        # Find the 1x2 market type ID (type 10)
        market_1x2_id = None
        for mt_id, mt in market_types.items():
            if mt.get('market_type') == '10' and mt.get('is_live') == '0':
                market_1x2_id = mt_id
                break

        matches = []
        categories = soccer.get('categories', {})

        for cat_id, category in categories.items():
            cat_name = category.get('name', 'Unknown')
            tournaments = category.get('tournaments', {})

            for tourn_id, tournament in tournaments.items():
                tourn_name = tournament.get('name', 'Unknown')
                league = f"{cat_name}. {tourn_name}"
                raw_matches = tournament.get('matches', {})

                for match_id, match in raw_matches.items():
                    parsed = _parse_match(match, match_id, league, market_1x2_id)
                    if parsed:
                        matches.append(parsed)

                        if len(matches) >= max_matches:
                            print(f"Found {len(matches)} matches on SoccaBet")
                            return matches

        print(f"Found {len(matches)} matches on SoccaBet")
        return matches

    except requests.exceptions.RequestException as e:
        print(f"  Request error: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}")
        return []
    except Exception as e:
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return []


def _parse_match(match: Dict, match_id: str, league: str, market_1x2_id: str) -> Optional[Dict]:
    """Parse a single match from SoccaBet bet/odds.js data."""

    # Skip live matches
    if match.get('live'):
        return None

    # Get match name (format: "Team1 v Team2")
    name = match.get('name', '')
    if not name or ' v ' not in name:
        return None

    parts = name.split(' v ')
    if len(parts) != 2:
        return None

    home_team = parts[0].strip()
    away_team = parts[1].strip()

    # Skip eSports and simulated matches
    skip_patterns = ['esoccer', 'ebasketball', 'esports', '(thomas)', '(nathan)',
                     '(iron)', '(jason)', '(panther)', '(felix)', '(odin)', '(cleo)']
    full_name = f"{home_team} {away_team}".lower()
    if any(p in full_name for p in skip_patterns):
        return None

    # Get timestamp
    start_ts = match.get('ts', 0)

    # Find 1x2 market
    markets = match.get('markets', {})
    home_odds = 0
    draw_odds = 0
    away_odds = 0

    for mkt_id, mkt in markets.items():
        # Check if this is a 1x2 market (typeid 4102 or similar for type 10)
        type_id = mkt.get('typeid', '')

        # The market type definition maps typeid to market_type
        # 4102 is typically 1x2 for pre-match
        if type_id in ['4102', '4720']:  # 4102=prematch 1x2, 4720=live 1x2
            selections = mkt.get('selections', {})

            for sel_id, sel in selections.items():
                outcome = sel.get('n', '')
                odds_str = sel.get('o', '0')

                try:
                    odds = float(odds_str)
                except (ValueError, TypeError):
                    continue

                if outcome == '1':
                    home_odds = odds
                elif outcome == 'X':
                    draw_odds = odds
                elif outcome == '2':
                    away_odds = odds

            break  # Found 1x2 market, no need to continue

    # Validate odds
    if home_odds <= 1 or away_odds <= 1:
        return None

    # Draw odds validation (should be >= 2.0 for real football)
    if draw_odds > 0 and draw_odds < 2.0:
        return None

    return {
        'bookmaker': 'SoccaBet Ghana',
        'match_id': str(match_id),
        'home_team': home_team,
        'away_team': away_team,
        'league': league,
        'home_odds': home_odds,
        'draw_odds': draw_odds,
        'away_odds': away_odds,
        'start_time': start_ts,
    }


if __name__ == '__main__':
    matches = scrape_soccabet_ghana(max_matches=800)
    print(f"\nTotal matches: {len(matches)}")

    for m in matches[:10]:
        print(f"\n{m['home_team']} vs {m['away_team']}")
        print(f"  League: {m['league']}")
        print(f"  Home: {m['home_odds']}, Draw: {m['draw_odds']}, Away: {m['away_odds']}")
