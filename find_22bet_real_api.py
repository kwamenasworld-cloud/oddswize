#!/usr/bin/env python3
"""
Find the real API by examining JavaScript bundles.
"""

import cloudscraper
import re

def find_real_api():
    print("=" * 60)
    print("FINDING REAL 22BET API FROM JAVASCRIPT")
    print("=" * 60)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    # Get the main page
    print("\nFetching main page...")
    resp = scraper.get('https://22bet.com.gh', timeout=30)
    html = resp.text

    # Find all JavaScript files
    js_files = re.findall(r'src="([^"]+\.js[^"]*)"', html)
    print(f"Found {len(js_files)} JavaScript files")

    # Look for the main app bundle
    for js_file in js_files:
        if not js_file.startswith('http'):
            js_file = f"https://22bet.com.gh/{js_file.lstrip('/')}"

        # Skip external domains we don't care about
        if '22bet' not in js_file:
            continue

        print(f"\nFetching: {js_file[:100]}...")

        try:
            resp = scraper.get(js_file, timeout=30)
            js_code = resp.text

            print(f"Size: {len(js_code)} bytes")

            # Look for API endpoint patterns
            patterns = [
                r'LineFeed["\']?\s*[+:]?\s*["\']([^"\']+)',
                r'GetChamps[a-zA-Z]*["\']?\s*[+:]?\s*["\']',
                r'https?://[^"\']+/LineFeed',
                r'https?://[^"\']+/api[^"\']*',
                r'/api/[^"\']+GetChamps',
                r'platformApiUrl["\']?\s*[+:]?\s*["\']([^"\']+)',
            ]

            found_anything = False
            for pattern in patterns:
                matches = re.findall(pattern, js_code, re.IGNORECASE)
                if matches:
                    found_anything = True
                    print(f"\nPattern '{pattern[:40]}...':")
                    for match in list(set(matches))[:5]:
                        if isinstance(match, str) and len(match) > 2:
                            print(f"  - {match}")

            # Look for specific API construction patterns
            # They might be building the URL dynamically
            if 'platformApiUrl' in js_code or 'LineFeed' in js_code:
                print("\n[FOUND] This file contains API references!")

                # Try to find the actual endpoint construction
                api_construction = re.findall(r'([a-zA-Z]+ApiUrl\+[^;]+)', js_code)
                if api_construction:
                    print("\nAPI URL construction patterns:")
                    for construct in api_construction[:5]:
                        print(f"  {construct}")

                # Look for fetch/axios calls
                fetch_calls = re.findall(r'fetch\([^)]+\)|axios\.[get|post]+\([^)]+\)', js_code)
                if fetch_calls:
                    print(f"\nFound {len(fetch_calls)} fetch/axios calls (showing first 3):")
                    for call in fetch_calls[:3]:
                        print(f"  {call[:100]}")

        except Exception as e:
            print(f"Error: {str(e)[:80]}")

    # Also check the config we already downloaded
    print("\n" + "="*60)
    print("CHECKING CONFIG FILE")
    print("="*60)

    try:
        with open('22bet_config.js', 'r', encoding='utf-8') as f:
            config = f.read()

        # The platform API URL is there
        platform_url = "https://platform.22bet.com.gh"
        print(f"\nPlatform API URL from config: {platform_url}")

        # Maybe they're using GraphQL?
        if 'graphql' in config.lower():
            print("[FOUND] GraphQL mentioned in config")

        # Look for any other API URLs
        all_urls = re.findall(r'https://[^"\']+22bet[^"\']+', config)
        print(f"\nAll 22bet URLs in config:")
        for url in set(all_urls):
            print(f"  - {url}")

    except Exception as e:
        print(f"Error reading config: {e}")

if __name__ == '__main__':
    find_real_api()
