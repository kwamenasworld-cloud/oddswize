#!/usr/bin/env python3
"""
Properly analyze 22Bet website to understand how it loads odds.
"""

import cloudscraper
import re
import json
from bs4 import BeautifulSoup

def analyze_website():
    print("=" * 60)
    print("ANALYZING 22BET WEBSITE PROPERLY")
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

    soup = BeautifulSoup(html, 'html.parser')

    # Find all script tags
    scripts = soup.find_all('script')
    print(f"\nFound {len(scripts)} script tags")

    # Look for the main JavaScript bundle
    for i, script in enumerate(scripts):
        src = script.get('src', '')

        if src and ('main' in src or 'app' in src or 'bundle' in src):
            if not src.startswith('http'):
                src = f"https://22bet.com.gh{src}"

            print(f"\nFetching main bundle: {src[:100]}")

            try:
                js_resp = scraper.get(src, timeout=30)
                js_code = js_resp.text

                print(f"Bundle size: {len(js_code)} bytes")

                # Save it
                with open(f'22bet_bundle_{i}.js', 'w', encoding='utf-8') as f:
                    f.write(js_code)

                print(f"Saved to 22bet_bundle_{i}.js")

                # Search for API endpoint patterns
                print("\nSearching for API patterns in bundle...")

                # Look for LineFeed
                if 'LineFeed' in js_code:
                    print("  [FOUND] LineFeed mentioned")

                    # Extract context around LineFeed
                    matches = list(re.finditer(r'.{100}LineFeed.{100}', js_code))
                    print(f"  Found {len(matches)} occurrences")

                    for match in matches[:3]:
                        context = match.group()
                        print(f"\n  Context: {context}")

                # Look for GetChamps
                if 'GetChamps' in js_code:
                    print("\n  [FOUND] GetChamps mentioned")

                    matches = list(re.finditer(r'.{100}GetChamps.{100}', js_code))
                    for match in matches[:3]:
                        print(f"  Context: {match.group()}")

                # Look for URL construction
                url_patterns = [
                    r'https://[^"\']+LineFeed[^"\']*',
                    r'["\'][^"\']*LineFeed[^"\']*["\']',
                    r'platformApiUrl[^"\']*["\']([^"\']+)["\']',
                ]

                for pattern in url_patterns:
                    matches = re.findall(pattern, js_code)
                    if matches:
                        print(f"\n  Pattern '{pattern[:40]}': {len(matches)} matches")
                        for match in set(matches)[:5]:
                            print(f"    - {match}")

            except Exception as e:
                print(f"Error loading bundle: {e}")

    # Also check if there's any inline data
    print("\n" + "="*60)
    print("Checking for inline data...")
    print("="*60)

    # Look for script tags with inline JSON
    for script in scripts:
        if not script.get('src'):  # Inline script
            content = script.string
            if content and len(content) > 100:
                if 'newcastle' in content.lower() or 'premier' in content.lower():
                    print(f"\n[FOUND] Inline script with relevant data:")
                    print(content[:500])

if __name__ == '__main__':
    analyze_website()
