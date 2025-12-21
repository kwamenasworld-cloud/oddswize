#!/usr/bin/env python3
"""
Test 22Bet platform API endpoints.
"""

import cloudscraper
import json

def test_platform_api():
    print("=" * 60)
    print("TESTING 22BET PLATFORM API")
    print("=" * 60)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    base_url = "https://platform.22bet.com.gh"

    # Try common sports betting API endpoints
    endpoints_to_test = [
        "/LineFeed/GetChampsZip?sport=1&lng=en",
        "/api/LineFeed/GetChampsZip?sport=1&lng=en",
        "/v1/LineFeed/GetChampsZip?sport=1&lng=en",
        "/api/v1/LineFeed/GetChampsZip?sport=1&lng=en",
        "/sports/v1/championships?sport=1",
        "/api/sports/championships?sport=1",
        "/sportsbook/v1/championships",
        "/api/sportsbook/competitions",
    ]

    for endpoint in endpoints_to_test:
        url = f"{base_url}{endpoint}"
        print(f"\n{'='*60}")
        print(f"Testing: {url}")
        print('='*60)

        try:
            resp = scraper.get(url, timeout=30)
            print(f"Status: {resp.status_code}")

            if resp.status_code == 200:
                content_type = resp.headers.get('content-type', '')
                print(f"Content-Type: {content_type}")

                if 'json' in content_type.lower():
                    try:
                        data = resp.json()
                        print(f"[SUCCESS] Got JSON response!")

                        if isinstance(data, dict):
                            print(f"Keys: {list(data.keys())}")

                            if 'Value' in data:
                                champs = data['Value']
                                print(f"Championships found: {len(champs)}")
                                print("\nFirst 5 championships:")
                                for i, c in enumerate(champs[:5]):
                                    print(f"  {i+1}. {c.get('L')} (ID: {c.get('LI')}, Games: {c.get('GC')})")

                                # Look for Premier League
                                pl = [c for c in champs if 'premier league' in c.get('L', '').lower() and 'england' in c.get('L', '').lower()]
                                if pl:
                                    print(f"\n[FOUND] Premier League championship!")
                                    for p in pl:
                                        print(f"  - {p.get('L')} (ID: {p.get('LI')})")

                                return url  # Success!

                        elif isinstance(data, list):
                            print(f"Got list with {len(data)} items")
                            if data:
                                print(f"First item: {json.dumps(data[0], indent=2)[:200]}")

                    except Exception as e:
                        print(f"JSON parse error: {e}")
                        print(f"Response preview: {resp.text[:200]}")
                else:
                    print(f"Non-JSON response: {resp.text[:200]}")

            elif resp.status_code == 404:
                print("[NOT FOUND]")
            else:
                print(f"Response preview: {resp.text[:200]}")

        except Exception as e:
            print(f"Error: {str(e)[:100]}")

    return None

if __name__ == '__main__':
    working_url = test_platform_api()

    if working_url:
        print(f"\n{'='*60}")
        print(f"[SUCCESS] Working API URL:")
        print(f"  {working_url}")
        print('='*60)
    else:
        print(f"\n{'='*60}")
        print("[FAILED] No working API endpoint found")
        print('='*60)
