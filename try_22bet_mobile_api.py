#!/usr/bin/env python3
"""
Try 22Bet mobile API.
"""

import cloudscraper
import json

def try_mobile_api():
    print("=" * 60)
    print("TRYING 22BET MOBILE API")
    print("=" * 60)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'android',  # Try mobile
            'mobile': True
        }
    )

    scraper.headers.update({
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
        'Referer': 'https://22bet.com.gh',
    })

    # Try mobile domain from config
    mobile_domains = [
        "https://app.22bet.gh",
        "https://m.22bet.com.gh",
        "https://mobile.22bet.com.gh",
    ]

    endpoints = [
        "/api/LineFeed/GetChampsZip?sport=1&lng=en",
        "/LineFeed/GetChampsZip?sport=1&lng=en",
    ]

    for domain in mobile_domains:
        for endpoint in endpoints:
            url = f"{domain}{endpoint}"
            print(f"\n{'='*60}")
            print(f"Trying: {url}")
            print('='*60)

            try:
                resp = scraper.get(url, timeout=30)
                print(f"Status: {resp.status_code}")

                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        print(f"JSON response!")

                        if isinstance(data, dict):
                            print(f"Keys: {list(data.keys())}")

                            # Check old format
                            if 'Value' in data:
                                champs = data['Value']
                                print(f"[OLD FORMAT] Championships: {len(champs)}")
                                return url

                            # Check new format
                            if 'data' in data:
                                api_data = data['data']
                                if isinstance(api_data, dict) and 'Value' in api_data:
                                    champs = api_data['Value']
                                    print(f"[NEW FORMAT] Championships: {len(champs)}")
                                    return url

                    except Exception as e:
                        print(f"JSON error: {e}")
                        print(f"Response preview: {resp.text[:200]}")

            except Exception as e:
                print(f"Error: {str(e)[:80]}")

    # Try the platform API with authentication headers
    print(f"\n{'='*60}")
    print("Trying platform API with authentication...")
    print('='*60)

    # Maybe they need an API key or session token
    scraper.headers.update({
        'X-Platform': '19',  # From config
        'X-Domain': '22bet.com.gh',
    })

    platform_urls = [
        "https://platform.22bet.com.gh/LineFeed/GetChampsZip?sport=1&lng=en",
    ]

    for url in platform_urls:
        print(f"\nTrying: {url}")
        try:
            resp = scraper.get(url, timeout=30)
            print(f"Status: {resp.status_code}")

            if resp.status_code == 200:
                data = resp.json()
                print(f"Response: {json.dumps(data, indent=2)[:300]}")

                status = data.get('status')
                if status == 'success':
                    print("[SUCCESS] Got valid response!")
                    return url

        except Exception as e:
            print(f"Error: {str(e)[:80]}")

if __name__ == '__main__':
    working_url = try_mobile_api()

    if working_url:
        print(f"\n{'='*60}")
        print(f"[SUCCESS] Working mobile API URL:")
        print(f"  {working_url}")
        print('='*60)
    else:
        print(f"\n{'='*60}")
        print("[CONCLUSION] 22Bet API is not accessible")
        print("They may have:")
        print("  1. Changed to a completely new API structure")
        print("  2. Implemented authentication requirements")
        print("  3. Blocked programmatic access")
        print("  4. Regional restrictions on the old domain")
        print('='*60)
