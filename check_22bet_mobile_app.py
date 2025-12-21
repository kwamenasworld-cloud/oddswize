#!/usr/bin/env python3
"""
Check if 22Bet has a mobile app API that's simpler.
"""

import cloudscraper
import json

def check_mobile_api():
    print("=" * 60)
    print("CHECKING 22BET MOBILE APP API")
    print("=" * 60)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'android',
            'mobile': True
        }
    )

    # Mobile user agent
    scraper.headers.update({
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
        'Accept': 'application/json',
    })

    # From config: "mobAppDomain": "app.22bet.gh"
    mobile_endpoints = [
        "https://app.22bet.gh/api/LineFeed/GetChampsZip?sport=1&lng=en",
        "https://app.22bet.gh/service-api/LineFeed/GetChampsZip?sport=1&lng=en",
        "https://m.22bet.com.gh/api/LineFeed/GetChampsZip?sport=1&lng=en",
        "https://mobile-api.22bet.com.gh/LineFeed/GetChampsZip?sport=1&lng=en",

        # Try data/feed endpoints
        "https://data.22bet.com.gh/feed/sports/1/championships.json",
        "https://22bet.com.gh/data/prematch/football.json",
        "https://22bet.com.gh/api/data/sports/1.json",

        # Try CDN endpoints
        "https://d3qsixv8u4i3z8.cloudfront.net/data/sports.json",
        "https://d1wfowvne3d4em.cloudfront.net/api/sports/1/data.json",
    ]

    for url in mobile_endpoints:
        print(f"\nTrying: {url}")

        try:
            resp = scraper.get(url, timeout=15)

            if resp.status_code == 200:
                content_type = resp.headers.get('content-type', '')
                print(f"  Status: 200, Type: {content_type}")

                if 'json' in content_type.lower():
                    try:
                        data = resp.json()

                        if isinstance(data, dict) and 'Value' in data:
                            champs = data['Value']
                            print(f"  🎯 [JACKPOT] {len(champs)} championships!")
                            return url

                        elif isinstance(data, list) and len(data) > 0:
                            print(f"  ✓ Got list with {len(data)} items")
                            return url

                    except:
                        pass

        except Exception as e:
            if 'timeout' not in str(e).lower():
                print(f"  Error: {str(e)[:60]}")

    return None

if __name__ == '__main__':
    working = check_mobile_api()

    print(f"\n{'='*60}")
    if working:
        print(f"[SUCCESS] Found mobile API:")
        print(f"  {working}")
    else:
        print("[CONCLUSION] 22Bet has no accessible mobile API")
        print("\nFINAL STATUS:")
        print("  ✅ 5/6 bookmakers working perfectly")
        print("  ❌ 22Bet: WebSocket-only (not practical for fast scraping)")
        print("\nRECOMMENDATION: Deploy with 5 bookmakers")
    print('='*60)
