#!/usr/bin/env python3
"""
Debug Betfox Newcastle vs Chelsea.
"""

import cloudscraper
import json

def debug_betfox():
    print("=" * 60)
    print("DEBUG BETFOX - Newcastle vs Chelsea")
    print("=" * 60)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    scraper.headers.update({
        'Accept': 'application/json',
        'Referer': 'https://www.betfox.com.gh/sportsbook',
        'x-betr-brand': 'betfox.com.gh',
        'x-locale': 'en',
    })

    try:
        # Get upcoming fixtures
        print("\nFetching upcoming fixtures...")
        resp = scraper.get(
            'https://www.betfox.com.gh/api/offer/v4/fixtures/home/upcoming?first=1000&sport=Football',
            timeout=15
        )

        if resp.status_code != 200:
            print(f"Error: Status {resp.status_code}")
            return

        data = resp.json()
        fixtures = data.get('data', [])
        print(f"Total upcoming fixtures: {len(fixtures)}")

        # Look for Newcastle vs Chelsea
        newcastle_chelsea = None
        for fixture in fixtures:
            competitors = fixture.get('competitors', [])
            if len(competitors) >= 2:
                home = competitors[0].get('name', '').lower()
                away = competitors[1].get('name', '').lower()

                if ('newcastle' in home and 'chelsea' in away) or ('chelsea' in home and 'newcastle' in away):
                    newcastle_chelsea = fixture
                    break

        if not newcastle_chelsea:
            print("\nNewcastle vs Chelsea NOT FOUND in upcoming fixtures")
            print("\nSearching in all Premier League fixtures...")

            # Show all Premier League fixtures
            pl_fixtures = [f for f in fixtures if 'premier league' in f.get('competition', {}).get('name', '').lower()]
            print(f"Premier League fixtures found: {len(pl_fixtures)}")

            for i, f in enumerate(pl_fixtures[:10]):
                comp = f.get('competitors', [])
                if len(comp) >= 2:
                    print(f"  {i+1}. {comp[0].get('name')} vs {comp[1].get('name')}")

            return

        print("\n" + "=" * 60)
        print("FOUND Newcastle vs Chelsea!")
        print("=" * 60)

        competitors = newcastle_chelsea.get('competitors', [])
        home_team = competitors[0].get('name', '')
        away_team = competitors[1].get('name', '')

        print(f"Fixture ID: {newcastle_chelsea.get('id')}")
        print(f"Home Team: {home_team}")
        print(f"Away Team: {away_team}")
        print(f"Competition: {newcastle_chelsea.get('competition', {}).get('name')}")
        print(f"Category: {newcastle_chelsea.get('category', {}).get('name')}")
        print(f"Start Time: {newcastle_chelsea.get('startTime')}")

        # Check markets
        markets = newcastle_chelsea.get('markets', [])
        print(f"\nTotal markets: {len(markets)}")

        # Show all market types
        market_types = [m.get('type') for m in markets]
        print(f"Market types: {set(market_types)}")

        # Find FOOTBALL_WINNER market
        winner_market = None
        for market in markets:
            if market.get('type') == 'FOOTBALL_WINNER':
                winner_market = market
                break

        if not winner_market:
            print("\n[PROBLEM] No FOOTBALL_WINNER market found!")
            print("\nAvailable markets:")
            for market in markets[:5]:
                print(f"  - Type: {market.get('type')}, Name: {market.get('name')}")
            return

        print("\n" + "=" * 60)
        print("FOOTBALL_WINNER MARKET FOUND")
        print("=" * 60)

        outcomes = winner_market.get('outcomes', [])
        print(f"Outcomes: {len(outcomes)}")

        for outcome in outcomes:
            print(f"\nOutcome Type: {outcome.get('value')}")
            print(f"  Odds: {outcome.get('odds')}")
            print(f"  Active: {outcome.get('active')}")

        # Check if all odds are present
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

        print("\n" + "=" * 60)
        print("ODDS PARSING RESULT")
        print("=" * 60)
        print(f"Home Odds: {home_odds}")
        print(f"Draw Odds: {draw_odds}")
        print(f"Away Odds: {away_odds}")

        if home_odds and away_odds:
            print("\n[OK] Would be included in scraper output!")
        else:
            print("\n[PROBLEM] Would be SKIPPED (missing home or away odds)")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_betfox()
