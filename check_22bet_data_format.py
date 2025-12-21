#!/usr/bin/env python3
"""
Check 22Bet new API data format.
"""

import cloudscraper
import json

def check_data_format():
    print("=" * 60)
    print("CHECKING 22BET API DATA FORMAT")
    print("=" * 60)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    url = "https://platform.22bet.com.gh/LineFeed/GetChampsZip?sport=1&lng=en"
    print(f"\nFetching: {url}")

    try:
        resp = scraper.get(url, timeout=30)
        print(f"Status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            print(f"\nTop-level keys: {list(data.keys())}")
            print(f"Status: {data.get('status')}")
            print(f"Code: {data.get('code')}")
            print(f"Messages: {data.get('messages')}")

            championships_data = data.get('data')
            print(f"\nData type: {type(championships_data)}")

            if isinstance(championships_data, dict):
                print(f"Data keys: {list(championships_data.keys())}")

                # Check if there's a Value key in data
                if 'Value' in championships_data:
                    champs = championships_data['Value']
                    print(f"\n[SUCCESS] Found championships in data.Value")
                    print(f"Championships: {len(champs)}")

                    print("\nFirst 5 championships:")
                    for i, c in enumerate(champs[:5]):
                        print(f"  {i+1}. {c.get('L')} (ID: {c.get('LI')}, Games: {c.get('GC')})")

                    # Look for Premier League
                    print("\nSearching for Premier League...")
                    pl = [c for c in champs if 'premier league' in c.get('L', '').lower()]
                    if pl:
                        print(f"\n[FOUND] Premier League championships:")
                        for p in pl:
                            print(f"  - {p.get('L')} (ID: {p.get('LI')}, Games: {c.get('GC')})")
                    else:
                        print("[NOT FOUND] No Premier League championship")

                else:
                    print(f"\nNo 'Value' key. Keys in data: {list(championships_data.keys())}")
                    # Print first item if it's nested
                    for key in list(championships_data.keys())[:3]:
                        print(f"\n{key}: {str(championships_data[key])[:200]}")

            elif isinstance(championships_data, list):
                print(f"Data is a list with {len(championships_data)} items")
                if championships_data:
                    print(f"\nFirst item: {json.dumps(championships_data[0], indent=2)[:500]}")

            else:
                print(f"Data is: {championships_data}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_data_format()
