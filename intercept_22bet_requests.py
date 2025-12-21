#!/usr/bin/env python3
"""
Simulate browsing to 22Bet football page and log all requests.
"""

import cloudscraper
import re

def intercept_requests():
    print("=" * 60)
    print("INTERCEPTING 22BET REQUESTS")
    print("=" * 60)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    # Step 1: Visit homepage
    print("\n1. Visiting homepage...")
    resp = scraper.get('https://22bet.com.gh', timeout=30)
    print(f"   Status: {resp.status_code}")
    print(f"   Cookies: {len(scraper.cookies)}")

    # Step 2: Visit prematch football page
    print("\n2. Visiting prematch football page...")
    resp = scraper.get('https://22bet.com.gh/line/football', timeout=30)
    print(f"   Status: {resp.status_code}")
    html = resp.text

    # Look for embedded data in the HTML
    print("\n3. Searching for embedded data...")

    # Look for __PRELOADED_STATE__ or similar
    preloaded = re.search(r'__PRELOADED_STATE__\s*=\s*({.+?});', html, re.DOTALL)
    if preloaded:
        print("   Found __PRELOADED_STATE__!")
        print(f"   Length: {len(preloaded.group(1))} chars")

    # Look for window.__APP_DATA__ or similar
    app_data = re.search(r'__APP_DATA__\s*=\s*({.+?});', html, re.DOTALL)
    if app_data:
        print("   Found __APP_DATA__!")
        print(f"   Length: {len(app_data.group(1))} chars")

    # Look for any large JSON objects embedded
    json_objects = re.findall(r'=\s*(\{[^{]{500,}?\})', html[:50000])
    if json_objects:
        print(f"   Found {len(json_objects)} large JSON objects embedded in page")

    # Look for API URLs in the page
    api_urls = re.findall(r'(https?://[^"\s<>]+/api[^"\s<>]+)', html)
    if api_urls:
        unique_urls = set(api_urls)
        print(f"\n4. Found {len(unique_urls)} API URLs in page:")
        for url in sorted(unique_urls)[:10]:
            print(f"   {url}")

            # Try to fetch each one
            try:
                test_resp = scraper.get(url, timeout=10)
                if test_resp.status_code == 200 and 'json' in test_resp.headers.get('content-type', ''):
                    data = test_resp.json()
                    print(f"      [WORKING!] Returns JSON")
                    if isinstance(data, dict) and 'Value' in data:
                        print(f"      [JACKPOT!] Has 'Value' key with {len(data['Value'])} items")
                        return url
            except:
                pass

    # Step 3: Try to find XHR/fetch requests in scripts
    print("\n5. Looking for fetch/XHR patterns in inline scripts...")

    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    for i, script in enumerate(scripts[:10]):
        # Look for fetch() or XMLHttpRequest
        fetches = re.findall(r'fetch\s*\(\s*["`\']([^"`\']+)["`\']', script)
        if fetches:
            print(f"   Script {i}: Found {len(fetches)} fetch calls")
            for url in fetches[:3]:
                print(f"      {url}")

    return None

if __name__ == '__main__':
    working_url = intercept_requests()

    print(f"\n{'='*60}")
    if working_url:
        print(f"[SUCCESS] Found working API: {working_url}")
    else:
        print("[INFO] No direct API URL found in page HTML")
        print("22Bet likely uses WebSocket for real-time data")
    print('='*60)
