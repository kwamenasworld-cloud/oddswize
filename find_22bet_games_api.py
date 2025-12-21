#!/usr/bin/env python3
"""
Find 22Bet games/fixtures API.
"""

import cloudscraper
import json

def find_games_api():
    print("=" * 60)
    print("FINDING 22BET GAMES API")
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
        'Referer': 'https://22bet.com.gh',
    })

    base_url = "https://platform.22bet.com.gh"

    # Try different game/fixture endpoints
    endpoints = [
        "/api/sportsbook/events?sport=1",
        "/api/sportsbook/fixtures?sport=1",
        "/api/sportsbook/upcoming?sport=1",
        "/api/sports/events?sport=1",
        "/api/sports/fixtures",
        "/sportsbook/v1/events",
        "/sportsbook/v1/fixtures",
        "/LineFeed/GetGames?sport=1&champ=0",
        "/LineFeed/GetGamesZip?sport=1&champ=0",
        "/api/LineFeed/GetGames?sport=1",
        "/api/v1/events?sportId=1",
        "/api/v1/fixtures?sportId=1",
    ]

    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        print(f"\n{'='*60}")
        print(f"Testing: {url}")
        print('='*60)

        try:
            resp = scraper.get(url, timeout=30)
            print(f"Status: {resp.status_code}")

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    print(f"JSON keys: {list(data.keys()) if isinstance(data, dict) else 'List'}")

                    if isinstance(data, dict):
                        status = data.get('status')
                        code = data.get('code')
                        print(f"API Status: {status}, Code: {code}")

                        if status == 'success' or code == 200:
                            api_data = data.get('data', data)
                            print(f"[SUCCESS] API returned success!")
                            print(f"Data type: {type(api_data)}")

                            if isinstance(api_data, list) and api_data:
                                print(f"Items: {len(api_data)}")
                                print(f"First item keys: {list(api_data[0].keys()) if isinstance(api_data[0], dict) else type(api_data[0])}")
                                return url
                            elif isinstance(api_data, dict):
                                print(f"Data keys: {list(api_data.keys())}")
                                if 'Value' in api_data:
                                    print(f"Value items: {len(api_data['Value'])}")
                                    return url

                    elif isinstance(data, list):
                        print(f"[SUCCESS] Got list with {len(data)} items")
                        if data:
                            print(f"First item: {json.dumps(data[0], indent=2)[:300]}")
                        return url

                except Exception as e:
                    print(f"JSON error: {e}")

        except Exception as e:
            print(f"Request error: {str(e)[:80]}")

    return None

if __name__ == '__main__':
    working_url = find_games_api()

    if working_url:
        print(f"\n{'='*60}")
        print(f"[SUCCESS] Working games API:")
        print(f"  {working_url}")
        print('='*60)
    else:
        print(f"\n{'='*60}")
        print("[FAILED] No working games API found")
        print('='*60)
