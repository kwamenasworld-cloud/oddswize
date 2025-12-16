#!/usr/bin/env python3
"""
Test script to directly query bookmaker APIs for Premier League matches.
Helps diagnose missing matches in scraper.
"""

import requests
import cloudscraper
import json

# ============================================================================
# Test Betway for Premier League
# ============================================================================

def test_betway():
    print("="*60)
    print("TESTING BETWAY GHANA - Premier League")
    print("="*60)

    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.betway.com.gh/sport/soccer/upcoming',
    }

    # Try to get English Premier League matches
    skip = 0
    page_size = 1000

    url = f'https://www.betway.com.gh/api/Events/GetUpcomingEvents?sportId=4&skip={skip}&take={page_size}'

    try:
        resp = session.get(url, headers=headers, timeout=15)
        print(f"Status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            events = data.get('events', [])
            print(f"Total events fetched: {len(events)}")

            # Filter for Premier League
            pl_matches = []
            for event in events:
                comp_name = event.get('competitionName', '').lower()
                if 'premier league' in comp_name or 'england' in comp_name:
                    home = event.get('homeTeam', {}).get('name', 'Unknown')
                    away = event.get('awayTeam', {}).get('name', 'Unknown')
                    pl_matches.append({
                        'home': home,
                        'away': away,
                        'league': event.get('competitionName'),
                        'date': event.get('startDate')
                    })

            print(f"Premier League matches found: {len(pl_matches)}")
            for i, match in enumerate(pl_matches[:10]):
                print(f"  {i+1}. {match['home']} vs {match['away']}")
                print(f"      League: {match['league']}")
                print(f"      Date: {match['date']}")
                print()

            # Look specifically for Newcastle vs Chelsea
            newcastle_chelsea = [m for m in pl_matches
                                if ('newcastle' in m['home'].lower() and 'chelsea' in m['away'].lower()) or
                                   ('chelsea' in m['home'].lower() and 'newcastle' in m['away'].lower())]
            if newcastle_chelsea:
                print("✓ FOUND Newcastle vs Chelsea in Betway!")
                for match in newcastle_chelsea:
                    print(f"  {match['home']} vs {match['away']}")
            else:
                print("✗ Newcastle vs Chelsea NOT found in Betway")

    except Exception as e:
        print(f"Error: {e}")

    print()

# ============================================================================
# Test Betfox for Premier League
# ============================================================================

def test_betfox():
    print("="*60)
    print("TESTING BETFOX GHANA - Premier League")
    print("="*60)

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
        resp = scraper.get(
            'https://www.betfox.com.gh/api/offer/v4/fixtures/home/upcoming?first=1000&sport=Football',
            timeout=15
        )

        print(f"Status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            fixtures = data.get('data', [])
            print(f"Total fixtures fetched: {len(fixtures)}")

            # Debug: Print first few PL fixtures structure
            print("\nDEBUG - Looking for Premier League fixtures...")
            pl_count = 0
            for fixture in fixtures:
                comp_name = fixture.get('competition', {}).get('name', '')
                if 'Premier League' in comp_name and pl_count < 2:
                    print(f"\nFixture #{pl_count + 1} - {comp_name}:")
                    print(json.dumps(fixture, indent=2)[:1000])
                    pl_count += 1
            print()

            # Look for Premier League
            pl_matches = []
            for fixture in fixtures:
                comp_name = fixture.get('competition', {}).get('name', '').lower()
                if 'premier league' in comp_name or 'england' in comp_name:
                    # Try different possible team name locations
                    home = (fixture.get('home', {}).get('name') or
                           fixture.get('homeTeam', {}).get('name') or
                           fixture.get('participants', [{}])[0].get('name', 'Unknown'))
                    away = (fixture.get('away', {}).get('name') or
                           fixture.get('awayTeam', {}).get('name') or
                           fixture.get('participants', [{}])[1].get('name', 'Unknown') if len(fixture.get('participants', [])) > 1 else 'Unknown')

                    pl_matches.append({
                        'home': home,
                        'away': away,
                        'league': fixture.get('competition', {}).get('name'),
                        'date': fixture.get('startDate')
                    })

            print(f"Premier League matches found: {len(pl_matches)}")
            for i, match in enumerate(pl_matches[:10]):
                print(f"  {i+1}. {match['home']} vs {match['away']}")
                print(f"      League: {match['league']}")
                print()

            # Look specifically for Newcastle vs Chelsea
            newcastle_chelsea = [m for m in pl_matches
                                if ('newcastle' in m['home'].lower() and 'chelsea' in m['away'].lower()) or
                                   ('chelsea' in m['home'].lower() and 'newcastle' in m['away'].lower())]
            if newcastle_chelsea:
                print("✓ FOUND Newcastle vs Chelsea in Betfox!")
                for match in newcastle_chelsea:
                    print(f"  {match['home']} vs {match['away']}")
            else:
                print("✗ Newcastle vs Chelsea NOT found in Betfox")

    except Exception as e:
        print(f"Error: {e}")

    print()

# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    test_betway()
    test_betfox()
