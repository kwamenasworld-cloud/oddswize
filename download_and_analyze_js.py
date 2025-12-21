#!/usr/bin/env python3
"""
Download 22Bet's JavaScript and analyze API calls.
"""

import cloudscraper
import re

def analyze_js():
    print("=" * 60)
    print("DOWNLOADING 22BET JAVASCRIPT BUNDLES")
    print("=" * 60)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    # From their CDN (found in config)
    js_sources = [
        "https://dwmu1hf7ovvid.cloudfront.net/remotes/remotes-manifest.js",
        "https://d1wfowvne3d4em.cloudfront.net/main.js",  # Guessing
        "https://d1wfowvne3d4em.cloudfront.net/app.js",   # Guessing
    ]

    # Also try getting from the page itself
    print("\n1. Fetching main page...")
    resp = scraper.get('https://22bet.com.gh', timeout=30)
    html = resp.text

    # Extract script URLs from HTML
    script_urls = re.findall(r'<script[^>]*src="([^"]+)"[^>]*>', html)
    print(f"Found {len(script_urls)} script URLs in HTML")

    for url in script_urls:
        if not url.startswith('http'):
            url = f"https://22bet.com.gh{url}" if url.startswith('/') else f"https://22bet.com.gh/{url}"
        js_sources.append(url)

    # Download and analyze each
    for i, url in enumerate(set(js_sources)):
        print(f"\n{'='*60}")
        print(f"Source {i+1}: {url[:80]}")
        print('='*60)

        try:
            resp = scraper.get(url, timeout=30)

            if resp.status_code == 200:
                js_code = resp.text
                print(f"Downloaded: {len(js_code)} bytes")

                # Search for API calls
                print("\nSearching for API patterns...")

                # Look for fetch/axios calls with URLs
                api_calls = re.findall(r'(?:fetch|axios\.get|axios\.post)\s*\(\s*["\']([^"\']+)["\']', js_code)

                if api_calls:
                    print(f"Found {len(api_calls)} API calls:")
                    for call in set(api_calls)[:10]:
                        if 'http' in call or 'api' in call.lower() or 'line' in call.lower():
                            print(f"  - {call}")

                # Look for URL construction patterns
                url_constructs = re.findall(r'platformApiUrl\s*\+\s*["\']([^"\']+)["\']', js_code)
                if url_constructs:
                    print(f"\nFound {len(url_constructs)} platformApiUrl constructions:")
                    for construct in set(url_constructs)[:10]:
                        print(f"  - platformApiUrl + '{construct}'")

                # Look for endpoints mentioned
                endpoints = re.findall(r'["\']/(api/[^"\'?]+)', js_code)
                if endpoints:
                    print(f"\nFound {len(set(endpoints))} /api/ endpoints:")
                    for endpoint in sorted(set(endpoints))[:20]:
                        print(f"  - /{endpoint}")

                # Save to file
                filename = f'22bet_js_{i}.js'
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(js_code)
                print(f"\nSaved to {filename}")

        except Exception as e:
            print(f"Error: {str(e)[:80]}")

if __name__ == '__main__':
    analyze_js()
