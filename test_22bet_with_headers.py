#!/usr/bin/env python3
"""
Test 22Bet with proper headers that their frontend would send.
"""

import cloudscraper
import json

def test_with_proper_headers():
    print("=" * 60)
    print("TESTING 22BET WITH PROPER HEADERS")
    print("=" * 60)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    # Add headers that their frontend would send
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://22bet.com.gh/line/football',
        'Origin': 'https://22bet.com.gh',
        'X-Requested-With': 'XMLHttpRequest',
        'X-Platform': '19',  # From their config
        'X-Domain': '22bet.com.gh',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    scraper.headers.update(headers)

    # Try different endpoint variations
    urls_to_test = [
        # Direct API calls
        "https://22bet.com.gh/api/LineFeed/GetChampsZip?sport=1&lng=en",
        "https://22bet.com.gh/api/v1/LineFeed/GetChampsZip?sport=1&lng=en",

        # Platform API
        "https://platform.22bet.com.gh/LineFeed/GetChampsZip?sport=1&lng=en",
        "https://platform.22bet.com.gh/api/LineFeed/GetChampsZip?sport=1&lng=en",

        # Try without /LineFeed prefix
        "https://platform.22bet.com.gh/api/sports/soccer/championships",
        "https://platform.22bet.com.gh/api/sportsbook/v1/championships?sportId=1",

        # Try betradar (they use it according to config)
        "https://platform.22bet.com.gh/api/betradar/championships?sport=1",
    ]

    for url in urls_to_test:
        print(f"\n{'='*60}")
        print(f"Testing: {url}")
        print('='*60)

        try:
            resp = scraper.get(url, timeout=30)
            print(f"Status: {resp.status_code}")
            content_type = resp.headers.get('content-type', '')
            print(f"Content-Type: {content_type}")

            if resp.status_code == 200:
                if 'json' in content_type.lower():
                    try:
                        data = resp.json()
                        print(f"[JSON] Keys: {list(data.keys()) if isinstance(data, dict) else 'List'}")

                        if isinstance(data, dict):
                            # Check for success
                            status = data.get('status')
                            code = data.get('code')

                            if status == 'success' or code == 200:
                                print(f"[SUCCESS] API returned success!")
                                print(json.dumps(data, indent=2)[:500])
                                return url
                            elif 'Value' in data:
                                print(f"[OLD FORMAT] Found Value key!")
                                print(f"Championships: {len(data['Value'])}")
                                return url
                            else:
                                print(f"Status: {status}, Code: {code}")

                        elif isinstance(data, list) and len(data) > 0:
                            print(f"[SUCCESS] Got list with {len(data)} items")
                            return url

                    except Exception as e:
                        print(f"JSON parse error: {e}")

                else:
                    print(f"Response preview: {resp.text[:150]}")

        except Exception as e:
            print(f"Error: {str(e)[:100]}")

    return None

if __name__ == '__main__':
    working_url = test_with_proper_headers()

    print(f"\n{'='*60}")
    if working_url:
        print(f"[SUCCESS] Working URL found:")
        print(f"  {working_url}")
    else:
        print("[FAILED] No working URL with proper headers")
    print('='*60)
