#!/usr/bin/env python3
"""
Find Premier League competition ID in Betfox and fetch its fixtures.
"""

import cloudscraper
import json

def find_premier_league():
    print("=" * 60)
    print("FINDING PREMIER LEAGUE IN BETFOX")
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

    # Get competitions
    print("\nFetching competitions...")
    resp = scraper.get(
        'https://www.betfox.com.gh/api/offer/v4/competitions?sport=Football',
        timeout=15
    )

    if resp.status_code != 200:
        print(f"Error: {resp.status_code}")
        return

    data = resp.json()
    print(f"Response keys: {list(data.keys())}")

    # Check enriched competitions
    enriched = data.get('enriched', [])
    print(f"\nEnriched competitions: {len(enriched)}")

    # Search for Premier League
    premier_league = None
    for comp in enriched:
        comp_name = comp.get('name', '').lower()
        category_name = comp.get('category', {}).get('name', '').lower()

        if 'premier league' in comp_name and 'england' in category_name:
            premier_league = comp
            print(f"\n[FOUND] Premier League competition!")
            print(json.dumps(comp, indent=2))
            break

    if not premier_league:
        print("\n[NOT FOUND] Searching all England competitions...")
        england_comps = [c for c in enriched if 'england' in c.get('category', {}).get('name', '').lower()]
        print(f"England competitions: {len(england_comps)}")

        for comp in england_comps:
            print(f"  - {comp.get('name')} (ID: {comp.get('id')})")

        # Try broader search
        print("\n[SEARCHING] All competitions with 'premier' in name...")
        premier_comps = [c for c in enriched if 'premier' in c.get('name', '').lower()]
        for comp in premier_comps[:10]:
            category = comp.get('category', {}).get('name', '')
            print(f"  - {comp.get('name')} ({category}) - ID: {comp.get('id')}")

        return

    # Try to get fixtures for this competition
    comp_id = premier_league.get('id')
    print(f"\n{'='*60}")
    print(f"Fetching fixtures for Premier League (ID: {comp_id})...")
    print('='*60)

    # Try different endpoints
    endpoints = [
        f'https://www.betfox.com.gh/api/offer/v4/fixtures?competition={comp_id}&first=100',
        f'https://www.betfox.com.gh/api/offer/v4/fixtures/upcoming?competition={comp_id}&first=100',
        f'https://www.betfox.com.gh/api/offer/v4/competitions/{comp_id}/fixtures',
    ]

    for url in endpoints:
        try:
            print(f"\nTrying: {url}")
            resp = scraper.get(url, timeout=15)
            print(f"Status: {resp.status_code}")

            if resp.status_code == 200:
                fixtures_data = resp.json()

                if isinstance(fixtures_data, dict):
                    fixtures = fixtures_data.get('data', [])
                elif isinstance(fixtures_data, list):
                    fixtures = fixtures_data
                else:
                    fixtures = []

                print(f"Fixtures found: {len(fixtures)}")

                if fixtures:
                    print("\nFirst 10 fixtures:")
                    for i, f in enumerate(fixtures[:10]):
                        comp_names = f.get('competitors', [])
                        if len(comp_names) >= 2:
                            home = comp_names[0].get('name', '')
                            away = comp_names[1].get('name', '')
                            print(f"  {i+1}. {home} vs {away}")

                            # Check if Newcastle vs Chelsea
                            if ('newcastle' in home.lower() and 'chelsea' in away.lower()) or \
                               ('chelsea' in home.lower() and 'newcastle' in away.lower()):
                                print(f"      [FOUND] Newcastle vs Chelsea!")

        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    find_premier_league()
