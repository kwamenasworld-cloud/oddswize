#!/usr/bin/env python3
"""
Explore platform.22bet.com.gh/api structure.
"""

import cloudscraper
import json

def explore_api():
    print("=" * 60)
    print("EXPLORING PLATFORM.22BET.COM.GH/API")
    print("=" * 60)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    base = "https://platform.22bet.com.gh/api"

    # Try common API paths
    paths_to_try = [
        "",  # Root
        "/sports",
        "/sports/1",  # Football
        "/sports/1/championships",
        "/sports/1/leagues",
        "/sports/1/events",
        "/sports/soccer",
        "/sportsbook",
        "/sportsbook/sports/1",
        "/prematch",
        "/prematch/sports/1",
        "/live",
        "/odds",
        "/odds/sports/1",
        "/line",
        "/line/football",
    ]

    for path in paths_to_try:
        url = f"{base}{path}"
        print(f"\n{url}")

        try:
            resp = scraper.get(url, timeout=15)
            print(f"  Status: {resp.status_code}")

            if resp.status_code == 200:
                try:
                    data = resp.json()

                    if isinstance(data, dict):
                        status = data.get('status')
                        code = data.get('code')

                        if status == 'ok' or code == 200:
                            print(f"  [SUCCESS] {status} {code}")
                            print(f"  Data: {json.dumps(data, indent=2)[:300]}")

                            # This is a valid endpoint!
                            if 'data' in data and data['data']:
                                return url

                        elif status == 'error' and code != 404:
                            print(f"  Error code: {code}")

                except Exception as e:
                    print(f"  Parse error: {e}")

        except Exception as e:
            print(f"  Request error: {str(e)[:60]}")

    return None

if __name__ == '__main__':
    working = explore_api()

    print(f"\n{'='*60}")
    if working:
        print(f"[SUCCESS] Found working endpoint: {working}")
    else:
        print("[INCOMPLETE] Need to explore further")
    print('='*60)
