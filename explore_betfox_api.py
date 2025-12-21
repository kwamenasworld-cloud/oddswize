#!/usr/bin/env python3
"""
Explore Betfox API to find how to get specific competitions.
"""

import cloudscraper
import json

def explore_betfox():
    print("=" * 60)
    print("EXPLORING BETFOX API")
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

    # Try to get competitions/categories
    endpoints_to_try = [
        'https://www.betfox.com.gh/api/offer/v4/sports',
        'https://www.betfox.com.gh/api/offer/v4/categories?sport=Football',
        'https://www.betfox.com.gh/api/offer/v4/competitions?sport=Football',
        'https://www.betfox.com.gh/api/offer/v4/fixtures/home/upcoming?first=200&sport=Football',
        'https://www.betfox.com.gh/api/offer/v4/fixtures/search?sport=Football&query=Premier League',
    ]

    for url in endpoints_to_try:
        try:
            print(f"\n{'='*60}")
            print(f"Trying: {url}")
            print('='*60)

            resp = scraper.get(url, timeout=15)
            print(f"Status: {resp.status_code}")

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    print(f"Response type: {type(data)}")

                    if isinstance(data, dict):
                        print(f"Keys: {list(data.keys())}")
                        if 'data' in data:
                            items = data['data']
                            if isinstance(items, list):
                                print(f"Items in 'data': {len(items)}")
                                if items and len(items) > 0:
                                    print(f"\nFirst item sample:")
                                    print(json.dumps(items[0], indent=2)[:500])
                    elif isinstance(data, list):
                        print(f"List length: {len(data)}")
                        if len(data) > 0:
                            print(f"\nFirst item sample:")
                            print(json.dumps(data[0], indent=2)[:500])

                except Exception as e:
                    print(f"JSON parsing error: {e}")
                    print(f"Raw response (first 500 chars): {resp.text[:500]}")
            else:
                print(f"Non-200 status code")

        except Exception as e:
            print(f"Request failed: {e}")

    # Try to get fixtures with larger first= parameter
    print(f"\n{'='*60}")
    print("Trying with first=500 parameter...")
    print('='*60)

    try:
        resp = scraper.get(
            'https://www.betfox.com.gh/api/offer/v4/fixtures/home/upcoming?first=500&sport=Football',
            timeout=15
        )

        if resp.status_code == 200:
            data = resp.json()
            fixtures = data.get('data', [])
            print(f"Fixtures returned: {len(fixtures)}")

            # Look for real Premier League (England)
            england_fixtures = [f for f in fixtures if f.get('category', {}).get('name', '').lower() in ['england', 'uk', 'united kingdom']]
            print(f"England fixtures: {len(england_fixtures)}")

            for i, f in enumerate(england_fixtures[:10]):
                comp = f.get('competitors', [])
                comp_name = f.get('competition', {}).get('name', '')
                if len(comp) >= 2:
                    print(f"  {i+1}. {comp[0].get('name')} vs {comp[1].get('name')} ({comp_name})")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    explore_betfox()
