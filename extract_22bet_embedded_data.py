#!/usr/bin/env python3
"""
Extract embedded data from 22Bet HTML.
"""

import cloudscraper
import re
import json

def extract_embedded_data():
    print("=" * 60)
    print("EXTRACTING EMBEDDED DATA FROM 22BET")
    print("=" * 60)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    # Get the Premier League page
    url = 'https://22bet.com.gh/line/football/england/premier-league'
    print(f"\nFetching: {url}")

    resp = scraper.get(url, timeout=30)
    html = resp.text

    print(f"HTML size: {len(html)} bytes")

    # Save HTML for inspection
    with open('22bet_page.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Saved to 22bet_page.html")

    # Look for all window.__ patterns
    print("\nSearching for embedded data...")

    window_vars = re.findall(r'window\.(__[A-Z_a-z0-9]+__)', html)
    if window_vars:
        print(f"\nFound {len(set(window_vars))} window variables:")
        for var in set(window_vars):
            print(f"  - {var}")

    # Try to extract the full assignment
    patterns = [
        r'window\.__([A-Z_]+)__\s*=\s*(.+?);?\s*</script>',
        r'window\.__([A-Z_]+)__\s*=\s*({.+?});',
        r'__([A-Z_]+)__\s*=\s*({.+?})',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html, re.DOTALL)
        if matches:
            print(f"\nPattern '{pattern[:40]}...' found {len(matches)} matches")

            for var_name, data_str in matches[:3]:
                print(f"\n  Variable: {var_name}")
                print(f"  Data length: {len(data_str)} chars")
                print(f"  Preview: {data_str[:200]}")

                # Try to parse as JSON
                try:
                    # Clean up the data string
                    data_str = data_str.strip()
                    if data_str.endswith(';'):
                        data_str = data_str[:-1]

                    data = json.loads(data_str)
                    print(f"  [SUCCESS] Parsed as JSON!")
                    print(f"  Type: {type(data)}")

                    if isinstance(data, dict):
                        print(f"  Keys: {list(data.keys())[:10]}")

                        # Look for matches/games/events
                        for key in data.keys():
                            if 'match' in key.lower() or 'game' in key.lower() or 'event' in key.lower():
                                print(f"\n  Found key '{key}': {type(data[key])}")
                                if isinstance(data[key], list):
                                    print(f"    Items: {len(data[key])}")
                                    if data[key]:
                                        print(f"    First item keys: {list(data[key][0].keys()) if isinstance(data[key][0], dict) else type(data[key][0])}")

                except Exception as e:
                    print(f"  JSON parse error: {str(e)[:100]}")

    # Also look for JSON-LD structured data
    print("\n" + "="*60)
    print("Looking for JSON-LD structured data...")
    print("="*60)

    json_ld = re.findall(r'<script type="application/ld\+json">(.+?)</script>', html, re.DOTALL)
    if json_ld:
        print(f"Found {len(json_ld)} JSON-LD blocks")
        for i, ld in enumerate(json_ld):
            try:
                data = json.loads(ld)
                print(f"\nBlock {i+1}:")
                print(f"  Type: {data.get('@type')}")
                print(json.dumps(data, indent=2)[:300])
            except:
                pass

if __name__ == '__main__':
    extract_embedded_data()
