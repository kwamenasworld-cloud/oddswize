#!/usr/bin/env python3
"""
Find 22Bet Ghana API endpoints by examining their website.
"""

import cloudscraper
import re

def find_22bet_api():
    print("=" * 60)
    print("FINDING 22BET GHANA API")
    print("=" * 60)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    scraper.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    })

    # Try to load the main site
    print("\nLoading 22bet.com.gh...")
    try:
        resp = scraper.get('https://22bet.com.gh', timeout=30)
        print(f"Status: {resp.status_code}")

        if resp.status_code == 200:
            html = resp.text

            # Look for API endpoints in the HTML
            print("\nSearching for API endpoints in HTML...")

            # Common patterns
            api_patterns = [
                r'https?://[^"\']+api[^"\']*',
                r'https?://[^"\']+LineFeed[^"\']*',
                r'https?://[^"\']+GetChamps[^"\']*',
                r'https?://[^"\']+feed[^"\']*',
                r'api[^"\']*url[^"\']*',
            ]

            found_urls = set()
            for pattern in api_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                found_urls.update(matches)

            if found_urls:
                print(f"\nFound {len(found_urls)} potential API URLs:")
                for url in sorted(found_urls)[:20]:
                    print(f"  - {url}")
            else:
                print("\nNo API URLs found in HTML")

            # Look for specific script files
            print("\nSearching for JavaScript files...")
            js_files = re.findall(r'src="([^"]+\.js[^"]*)"', html)
            print(f"Found {len(js_files)} JS files")
            for js_file in js_files[:10]:
                print(f"  - {js_file}")

    except Exception as e:
        print(f"Error: {e}")

    # Try the sportsbook page specifically
    print("\n" + "="*60)
    print("Trying sportsbook page...")
    print("="*60)

    try:
        resp = scraper.get('https://22bet.com.gh/line/football', timeout=30)
        print(f"Status: {resp.status_code}")

        if resp.status_code == 200:
            # Check response headers
            print("\nResponse Headers:")
            for key, value in resp.headers.items():
                if 'api' in key.lower() or 'content' in key.lower():
                    print(f"  {key}: {value}")

    except Exception as e:
        print(f"Error: {e}")

    # Try alternative domain patterns
    print("\n" + "="*60)
    print("Trying alternative API endpoints...")
    print("="*60)

    alternative_apis = [
        "https://22bet.com.gh/api/LineFeed/GetChampsZip?sport=1&lng=en",
        "https://22bet.com.gh/api/v1/LineFeed/GetChampsZip?sport=1&lng=en",
        "https://22bet.com.gh/LineFeed/GetChamps?sport=1&lng=en",
        "https://api.22bet.com.gh/LineFeed/GetChampsZip?sport=1&lng=en",
        "https://feed.22bet.com.gh/GetChampsZip?sport=1&lng=en",
    ]

    for api_url in alternative_apis:
        print(f"\nTrying: {api_url}")
        try:
            resp = scraper.get(api_url, timeout=15)
            print(f"  Status: {resp.status_code}")

            if resp.status_code == 200:
                content_type = resp.headers.get('content-type', '')
                print(f"  Content-Type: {content_type}")

                if 'json' in content_type:
                    try:
                        data = resp.json()
                        print(f"  [SUCCESS] Got JSON response!")
                        print(f"  Keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                        if isinstance(data, dict) and 'Value' in data:
                            print(f"  Championships: {len(data['Value'])}")
                            return api_url
                    except:
                        pass
                else:
                    print(f"  Response preview: {resp.text[:100]}")

        except Exception as e:
            print(f"  Error: {str(e)[:80]}")

if __name__ == '__main__':
    working_url = find_22bet_api()
    if working_url:
        print(f"\n{'='*60}")
        print(f"[SUCCESS] Working API URL found:")
        print(f"  {working_url}")
        print('='*60)
    else:
        print(f"\n{'='*60}")
        print("[FAILED] Could not find working 22Bet API")
        print('='*60)
