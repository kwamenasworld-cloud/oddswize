#!/usr/bin/env python3
"""
Debug Betway Newcastle vs Chelsea odds parsing.
"""

import requests
import json

def debug_betway_newcastle():
    print("=" * 60)
    print("DEBUG BETWAY - Newcastle vs Chelsea")
    print("=" * 60)

    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.betway.com.gh/sport/soccer/upcoming',
    }

    # Fetch first page
    url = (
        "https://www.betway.com.gh/sportsapi/br/v1/BetBook/Upcoming/"
        "?countryCode=GH&sportId=soccer&cultureCode=en-US"
        "&marketTypes=%5BWin%2FDraw%2FWin%5D&isEsport=false"
        "&Skip=0&Take=1000"
    )

    try:
        resp = session.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"Error: Status {resp.status_code}")
            return

        data = resp.json()
        events = data.get('events', [])
        markets = data.get('markets', [])
        outcomes = data.get('outcomes', [])
        prices = data.get('prices', [])

        print(f"Total events: {len(events)}")
        print(f"Total markets: {len(markets)}")
        print(f"Total outcomes: {len(outcomes)}")
        print(f"Total prices: {len(prices)}")

        # Find Newcastle vs Chelsea event
        target_event = None
        for event in events:
            home = event.get('homeTeam', '').lower()
            away = event.get('awayTeam', '').lower()

            if ('newcastle' in home and 'chelsea' in away) or ('chelsea' in home and 'newcastle' in away):
                target_event = event
                break

        if not target_event:
            print("\nNewcastle vs Chelsea NOT FOUND in Betway API")
            return

        print("\n" + "=" * 60)
        print("FOUND Newcastle vs Chelsea!")
        print("=" * 60)
        print(f"Event ID: {target_event.get('eventId')}")
        print(f"Home Team: {target_event.get('homeTeam')}")
        print(f"Away Team: {target_event.get('awayTeam')}")
        print(f"League: {target_event.get('league')}")

        # Find 1X2 market for this event
        event_id = target_event.get('eventId')
        target_market = None

        for market in markets:
            if market.get('eventId') == event_id:
                name = market.get('name', '')
                display_name = market.get('displayName', '')
                if name == '[Win/Draw/Win]' or display_name == '1X2':
                    target_market = market
                    break

        if not target_market:
            print("\nNo 1X2 market found for this event!")
            return

        print(f"\nMarket ID: {target_market.get('marketId')}")
        print(f"Market Name: {target_market.get('name')}")
        print(f"Market Display Name: {target_market.get('displayName')}")

        # Get outcomes for this market
        market_id = target_market.get('marketId')
        market_outcomes = [o for o in outcomes if o.get('marketId') == market_id]

        print(f"\nOutcomes for this market: {len(market_outcomes)}")

        # Build price lookup
        price_by_outcome = {p.get('outcomeId'): p.get('priceDecimal') for p in prices}

        home_team = target_event.get('homeTeam')
        away_team = target_event.get('awayTeam')

        print("\n" + "=" * 60)
        print("OUTCOME ANALYSIS")
        print("=" * 60)
        print(f"Expected home team name: '{home_team}'")
        print(f"Expected away team name: '{away_team}'")
        print()

        for outcome in market_outcomes:
            outcome_id = outcome.get('outcomeId')
            outcome_name = outcome.get('name', '')
            price = price_by_outcome.get(outcome_id)

            print(f"Outcome: '{outcome_name}'")
            print(f"  - Outcome ID: {outcome_id}")
            print(f"  - Price: {price}")

            # Check matching logic
            if outcome_name == home_team or outcome_name == 'Home':
                print(f"  - [OK] Would match as HOME (exact match)")
            elif outcome_name.lower() == 'draw':
                print(f"  - [OK] Would match as DRAW")
            elif outcome_name == away_team or outcome_name == 'Away':
                print(f"  - [OK] Would match as AWAY (exact match)")
            else:
                print(f"  - [FAIL] WOULD NOT MATCH (no exact match to '{home_team}' or '{away_team}')")
            print()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_betway_newcastle()
