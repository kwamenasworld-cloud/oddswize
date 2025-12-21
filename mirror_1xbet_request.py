#!/usr/bin/env python3
"""
Make exact same request to 22Bet as we do to 1xBet.
"""

import cloudscraper
import json

def test_exact_mirror():
    print("=" * 60)
    print("MIRRORING 1XBET REQUEST TO 22BET")
    print("=" * 60)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    # Use same headers as 1xBet
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://22bet.com.gh/line/football',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    scraper.headers.update(headers)

    # First, let's confirm 1xBet works
    print("\n1. Testing 1xBet (should work)...")
    url_1xbet = "https://1xbet.com.gh/service-api/LineFeed/GetChampsZip?sport=1&lng=en"

    try:
        resp = scraper.get(url_1xbet, timeout=30)
        print(f"   Status: {resp.status_code}")
        print(f"   Content-Type: {resp.headers.get('content-type')}")

        data = resp.json()
        if 'Value' in data:
            print(f"   ✓ Working! Championships: {len(data['Value'])}")

    except Exception as e:
        print(f"   Error: {e}")

    # Now try 22Bet with exact same setup
    print("\n2. Testing 22Bet (same request)...")
    url_22bet = "https://22bet.com.gh/service-api/LineFeed/GetChampsZip?sport=1&lng=en"

    try:
        resp = scraper.get(url_22bet, timeout=30)
        print(f"   Status: {resp.status_code}")
        print(f"   Content-Type: {resp.headers.get('content-type')}")

        # Check response
        if 'json' in resp.headers.get('content-type', '').lower():
            try:
                data = resp.json()
                print(f"   Keys: {list(data.keys())}")

                if 'Value' in data:
                    print(f"   ✓ IT WORKS! Championships: {len(data['Value'])}")
                    return True
                elif 'status' in data and data.get('status') == 'error':
                    print(f"   ✗ API Error: {data.get('code')}")
            except:
                pass
        else:
            print(f"   ✗ Returned HTML, not JSON")
            print(f"   Response preview: {resp.text[:150]}")

    except Exception as e:
        print(f"   Error: {e}")

    # Try with session establishment
    print("\n3. Testing with session (visit site first)...")
    scraper.get('https://22bet.com.gh', timeout=30)
    print(f"   Cookies: {len(scraper.cookies)}")

    try:
        resp = scraper.get(url_22bet, timeout=30)
        print(f"   Status: {resp.status_code}")

        if 'json' in resp.headers.get('content-type', '').lower():
            data = resp.json()
            if 'Value' in data:
                print(f"   ✓ Session helped! Championships: {len(data['Value'])}")
                return True

    except:
        pass

    return False

if __name__ == '__main__':
    success = test_exact_mirror()

    print(f"\n{'='*60}")
    if success:
        print("[SUCCESS] 22Bet API works!")
    else:
        print("[CONCLUSION] 22Bet API structure differs from 1xBet")
        print("Despite being sister companies, they use different backends.")
    print('='*60)
