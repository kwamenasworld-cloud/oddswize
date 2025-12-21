#!/usr/bin/env python3
"""
Debug 22Bet connection issues.
"""

import cloudscraper
import requests

def test_22bet_connection():
    print("=" * 60)
    print("TESTING 22BET CONNECTION")
    print("=" * 60)

    urls_to_test = [
        "https://22bet.com/gh/LineFeed/GetChampsZip?sport=1&lng=en",
        "https://22bet.com.gh/LineFeed/GetChampsZip?sport=1&lng=en",
        "https://www.22bet.com/gh/LineFeed/GetChampsZip?sport=1&lng=en",
    ]

    for url in urls_to_test:
        print(f"\n{'='*60}")
        print(f"Testing: {url}")
        print('='*60)

        # Try with cloudscraper
        print("\n[1] Trying with cloudscraper...")
        try:
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True
                }
            )
            resp = scraper.get(url, timeout=30)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    print(f"JSON keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    if isinstance(data, dict) and 'Value' in data:
                        champs = data['Value']
                        print(f"Championships found: {len(champs)}")
                        print(f"First 3 championships:")
                        for i, c in enumerate(champs[:3]):
                            print(f"  {i+1}. {c.get('L')} (ID: {c.get('LI')})")
                        print("\n[SUCCESS] This URL works!")
                        return url
                except Exception as e:
                    print(f"JSON parse error: {e}")
                    print(f"Response preview: {resp.text[:200]}")
            else:
                print(f"Response: {resp.text[:200]}")
        except Exception as e:
            print(f"Error: {e}")

        # Try with regular requests
        print("\n[2] Trying with regular requests...")
        try:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            })
            resp = session.get(url, timeout=30)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"Response preview: {resp.text[:200]}")
        except Exception as e:
            print(f"Error: {e}")

    print("\n" + "="*60)
    print("All URLs failed")
    return None

if __name__ == '__main__':
    working_url = test_22bet_connection()
    if working_url:
        print(f"\n[RESULT] Working URL: {working_url}")
    else:
        print("\n[RESULT] No working URL found - 22Bet may be blocking requests")
