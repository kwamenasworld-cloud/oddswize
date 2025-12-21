#!/usr/bin/env python3
"""
Test 22Bet with correct domain.
"""

import cloudscraper
import json

def test_correct_domain():
    print("=" * 60)
    print("TESTING 22BET WITH CORRECT DOMAIN")
    print("=" * 60)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    url = "https://22bet.com.gh/LineFeed/GetChampsZip?sport=1&lng=en"
    print(f"\nTesting: {url}")

    try:
        resp = scraper.get(url, timeout=30)
        print(f"Status: {resp.status_code}")

        if resp.status_code == 200:
            content_type = resp.headers.get('content-type', '')
            print(f"Content-Type: {content_type}")

            if 'json' in content_type.lower():
                data = resp.json()
                print(f"\n[SUCCESS] Got JSON response!")
                print(f"Type: {type(data)}")

                if isinstance(data, dict):
                    print(f"Keys: {list(data.keys())}")

                    # Old format
                    if 'Value' in data:
                        champs = data['Value']
                        print(f"\n[OLD FORMAT] Championships: {len(champs)}")
                        print("\nFirst 5 championships:")
                        for i, c in enumerate(champs[:5]):
                            print(f"  {i+1}. {c.get('L')} (ID: {c.get('LI')}, Games: {c.get('GC')})")

                        # Look for Premier League
                        pl = [c for c in champs if 'premier league' in c.get('L', '').lower()]
                        if pl:
                            print(f"\n[FOUND] Premier League:")
                            for p in pl:
                                print(f"  - {p.get('L')} (ID: {p.get('LI')}, Games: {p.get('GC')})")

                        return True

                    # New format
                    elif 'status' in data:
                        print(f"Status: {data.get('status')}")
                        print(f"Code: {data.get('code')}")
                        if data.get('status') == 'success':
                            api_data = data.get('data', {})
                            if 'Value' in api_data:
                                champs = api_data['Value']
                                print(f"\n[NEW FORMAT] Championships: {len(champs)}")
                                return True

            else:
                print(f"Non-JSON response: {resp.text[:200]}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    return False

if __name__ == '__main__':
    success = test_correct_domain()
    print(f"\n{'='*60}")
    if success:
        print("[SUCCESS] 22Bet API is working!")
    else:
        print("[FAILED] 22Bet API is not accessible")
    print('='*60)
