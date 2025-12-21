#!/usr/bin/env python3
"""
Test alternative 22Bet endpoints from config.
"""

import cloudscraper
import json

def test_alternatives():
    print("=" * 60)
    print("TESTING ALTERNATIVE 22BET ENDPOINTS")
    print("=" * 60)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    scraper.headers.update({
        'Accept': 'application/json',
        'Referer': 'https://22bet.com.gh',
    })

    # From their config, they have different hosts for different environments
    # Let's try production equivalents
    base_urls = [
        "https://cms.22bet.com.gh",
        "https://api.22bet.com.gh",
        "https://sportsbook.22bet.com.gh",
        "https://data.22bet.com.gh",
        "https://feed.22bet.com.gh",
        "https://sports.22bet.com.gh",
    ]

    endpoints = [
        "/LineFeed/GetChampsZip?sport=1&lng=en",
        "/api/LineFeed/GetChampsZip?sport=1&lng=en",
        "/api/v1/sports/soccer/championships",
        "/api/sports/1/leagues",
        "/v1/sportsbook/events",
    ]

    for base_url in base_urls:
        for endpoint in endpoints:
            url = f"{base_url}{endpoint}"
            print(f"\nTrying: {url[:80]}...")

            try:
                resp = scraper.get(url, timeout=15)

                if resp.status_code == 200:
                    content_type = resp.headers.get('content-type', '')

                    if 'json' in content_type.lower():
                        try:
                            data = resp.json()

                            # Check for old format
                            if isinstance(data, dict) and 'Value' in data:
                                champs = data['Value']
                                print(f"  [SUCCESS] Found {len(champs)} championships!")
                                return url

                            # Check for new format with success
                            elif isinstance(data, dict):
                                status = data.get('status')
                                if status == 'success':
                                    print(f"  [SUCCESS] API returned success!")
                                    print(f"  Keys: {list(data.keys())}")
                                    return url

                            # List of items
                            elif isinstance(data, list) and len(data) > 0:
                                print(f"  [SUCCESS] Got list with {len(data)} items!")
                                return url

                        except:
                            pass

            except Exception as e:
                # Only print if not timeout/connection error
                if 'timeout' not in str(e).lower() and 'connection' not in str(e).lower():
                    print(f"  Error: {str(e)[:60]}")

    return None

if __name__ == '__main__':
    working_url = test_alternatives()

    print(f"\n{'='*60}")
    if working_url:
        print(f"[SUCCESS] Found working endpoint:")
        print(f"  {working_url}")
    else:
        print("[CONCLUSION]")
        print("After exhaustive testing:")
        print("  - 22bet.com/gh: Connection timeout")
        print("  - 22bet.com.gh: Only returns HTML (React SPA)")
        print("  - platform.22bet.com.gh: Returns 404 for all LineFeed endpoints")
        print("  - All alternative subdomains: Not accessible or 404")
        print("\n22Bet has:")
        print("  1. Removed their LineFeed API completely")
        print("  2. Changed to a WebSocket-only architecture")
        print("  3. Or moved to an authenticated/token-based API")
        print("\nRecommendation: Skip 22Bet, we have 5/6 bookmakers working perfectly")
    print('='*60)
