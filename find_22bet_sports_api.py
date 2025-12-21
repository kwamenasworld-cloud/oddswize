#!/usr/bin/env python3
"""
Download 22Bet JavaScript and search for sports API endpoints.
"""

import cloudscraper
import re

def find_sports_api():
    print("=" * 60)
    print("SEARCHING 22BET JAVASCRIPT FOR SPORTS API")
    print("=" * 60)

    scraper = cloudscraper.create_scraper()

    # Get the main page to find script URLs
    print("\n1. Fetching main page...")
    resp = scraper.get('https://22bet.com.gh', timeout=30)
    html = resp.text

    # Find all script tags
    script_urls = re.findall(r'<script[^>]*src="([^"]+)"[^>]*>', html)
    print(f"Found {len(script_urls)} script URLs")

    # Focus on the main app scripts
    main_scripts = [url for url in script_urls if any(x in url.lower() for x in ['main', 'app', 'bundle', 'chunk'])]

    if not main_scripts:
        # Get all external scripts
        main_scripts = [url for url in script_urls if url.startswith('http')]

    print(f"\nAnalyzing {len(main_scripts)} main scripts...")

    for i, url in enumerate(main_scripts[:5]):  # Limit to first 5
        print(f"\n{'='*60}")
        print(f"Script {i+1}: {url}")
        print('='*60)

        try:
            resp = scraper.get(url, timeout=30)
            if resp.status_code != 200:
                print(f"  Failed: {resp.status_code}")
                continue

            js_code = resp.text
            print(f"  Downloaded: {len(js_code):,} bytes")

            # Search for API endpoint patterns
            print("\n  Searching for API patterns...")

            # Look for /api/ paths in strings
            api_paths = re.findall(r'["\']/(api/[^"\'?\s]+)', js_code)
            if api_paths:
                unique_paths = sorted(set(api_paths))
                print(f"\n  Found {len(unique_paths)} unique /api/ paths:")
                for path in unique_paths[:20]:
                    print(f"    /{path}")

            # Look for service-api paths (like 1xBet uses)
            service_paths = re.findall(r'["\']/(service-api/[^"\'?\s]+)', js_code)
            if service_paths:
                unique_paths = sorted(set(service_paths))
                print(f"\n  Found {len(unique_paths)} unique /service-api/ paths:")
                for path in unique_paths[:20]:
                    print(f"    /{path}")

            # Look for fetch/axios calls with dynamic URLs
            fetch_patterns = re.findall(r'(?:fetch|axios\.get|axios\.post|request)\s*\([^)]{0,200}["\']([^"\']+)["\']', js_code)
            if fetch_patterns:
                api_patterns = [p for p in fetch_patterns if '/api' in p or 'sports' in p.lower() or 'line' in p.lower()]
                if api_patterns:
                    print(f"\n  Found {len(set(api_patterns))} API call patterns:")
                    for pattern in sorted(set(api_patterns))[:15]:
                        print(f"    {pattern}")

            # Look for WebSocket subscription patterns
            ws_patterns = re.findall(r'subscribe[^{]{0,100}["\']([^"\']+)["\']', js_code)
            if ws_patterns:
                unique_ws = sorted(set(ws_patterns))[:10]
                print(f"\n  Found {len(unique_ws)} WebSocket patterns:")
                for pattern in unique_ws:
                    print(f"    {pattern}")

            # Search for specific keywords
            keywords = ['LineFeed', 'GetChamps', 'GetGames', 'prematch', 'sportsbook', 'championships']
            for keyword in keywords:
                if keyword in js_code:
                    # Extract context around keyword
                    matches = re.finditer(keyword, js_code, re.IGNORECASE)
                    for match in list(matches)[:3]:
                        start = max(0, match.start() - 50)
                        end = min(len(js_code), match.end() + 50)
                        context = js_code[start:end].replace('\n', ' ')
                        print(f"\n  Found '{keyword}':")
                        print(f"    ...{context}...")
                        break

        except Exception as e:
            print(f"  Error: {str(e)[:100]}")

if __name__ == '__main__':
    find_sports_api()
