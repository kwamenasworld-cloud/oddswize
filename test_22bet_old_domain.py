#!/usr/bin/env python3
"""
Test the old 22bet.com/gh domain format.
"""

import cloudscraper
import json

def test_old_domain():
    print("=" * 60)
    print("TESTING OLD DOMAIN: 22bet.com/gh")
    print("=" * 60)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    # The original code used https://22bet.com/gh/LineFeed
    url = "https://22bet.com/gh/LineFeed/GetChampsZip?sport=1&lng=en"
    print(f"\nTesting: {url}")

    try:
        resp = scraper.get(url, timeout=60)  # Longer timeout
        print(f"Status: {resp.status_code}")

        if resp.status_code == 200:
            content_type = resp.headers.get('content-type', '')
            print(f"Content-Type: {content_type}")

            if 'json' in content_type.lower():
                data = resp.json()
                print(f"\n[SUCCESS] Got JSON response!")

                if isinstance(data, dict) and 'Value' in data:
                    champs = data['Value']
                    print(f"Championships: {len(champs)}")

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

    except Exception as e:
        error_str = str(e)
        print(f"Error: {error_str}")

        # Check if it's a timeout
        if 'timeout' in error_str.lower():
            print("\n[TIMEOUT] The old domain times out - it's not accessible")
        elif 'connection' in error_str.lower():
            print("\n[CONNECTION ERROR] Cannot connect to 22bet.com/gh")

    return False

if __name__ == '__main__':
    success = test_old_domain()

    print(f"\n{'='*60}")
    if success:
        print("[SUCCESS] Old domain works!")
    else:
        print("[FAILED] Old domain not accessible")
        print("\nCONCLUSION:")
        print("22Bet has completely changed their API structure.")
        print("Options:")
        print("  1. Skip 22Bet - we have 5/6 bookmakers working")
        print("  2. Use browser automation (slow)")
        print("  3. Find an alternative bookmaker to replace 22Bet")
    print('='*60)
