#!/usr/bin/env python3
"""
Test 22Bet service-api endpoint (like 1xBet uses).
"""

import cloudscraper
import json

def test_service_api():
    print("=" * 60)
    print("TESTING 22BET /service-api/ ENDPOINT")
    print("=" * 60)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    url = "https://22bet.com.gh/service-api/LineFeed/GetChampsZip?sport=1&lng=en"
    print(f"\nTesting: {url}")

    try:
        resp = scraper.get(url, timeout=30)
        print(f"Status: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('content-type', 'N/A')}")
        print(f"Response length: {len(resp.text)} bytes")

        if resp.status_code == 200:
            # Try to parse as JSON
            try:
                data = resp.json()
                print(f"\n[SUCCESS] Got JSON response!")
                print(f"Type: {type(data)}")

                if isinstance(data, dict):
                    print(f"Keys: {list(data.keys())}")

                    if 'Value' in data:
                        champs = data['Value']
                        print(f"\n[JACKPOT] Championships: {len(champs)}")

                        print("\nFirst 5 championships:")
                        for i, c in enumerate(champs[:5]):
                            print(f"  {i+1}. {c.get('L')} (ID: {c.get('LI')}, Games: {c.get('GC')})")

                        # Look for Premier League
                        pl = [c for c in champs if 'premier' in c.get('L', '').lower() and 'england' in c.get('L', '').lower()]
                        if pl:
                            print(f"\n[FOUND] Premier League:")
                            for p in pl:
                                print(f"  - {p.get('L')} (ID: {p.get('LI')}, Games: {p.get('GC')})")

                        return True

            except Exception as e:
                print(f"\nJSON parse error: {e}")
                print(f"Response preview: {resp.text[:500]}")

        else:
            print(f"Response: {resp.text[:200]}")

    except Exception as e:
        print(f"Error: {e}")

    return False

if __name__ == '__main__':
    success = test_service_api()

    print(f"\n{'='*60}")
    if success:
        print("[SUCCESS] 22BET SERVICE-API WORKS!")
        print("Update scraper to use:")
        print("  https://22bet.com.gh/service-api/LineFeed")
    else:
        print("[FAILED] Service-API didn't work")
    print('='*60)
