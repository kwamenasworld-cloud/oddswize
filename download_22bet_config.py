#!/usr/bin/env python3
"""
Download and analyze 22Bet configuration.js
"""

import cloudscraper
import re
import json

def analyze_config():
    print("=" * 60)
    print("ANALYZING 22BET CONFIGURATION")
    print("=" * 60)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    config_url = "https://22bet.com.gh/configuration.js"
    print(f"\nFetching: {config_url}")

    try:
        resp = scraper.get(config_url, timeout=30)
        config_js = resp.text

        print(f"Downloaded {len(config_js)} bytes")

        # Save to file for inspection
        with open('22bet_config.js', 'w', encoding='utf-8') as f:
            f.write(config_js)
        print("Saved to 22bet_config.js")

        # Look for all URLs
        print("\n" + "="*60)
        print("ALL URLs FOUND:")
        print("="*60)

        urls = re.findall(r'https?://[^\s"\',;)}\]]+', config_js)
        unique_urls = list(set(urls))

        for url in sorted(unique_urls):
            if any(keyword in url.lower() for keyword in ['22bet', 'api', 'feed', 'line', 'bet', 'sport']):
                print(f"  {url}")

        # Look for specific patterns
        print("\n" + "="*60)
        print("SEARCHING FOR API PATTERNS:")
        print("="*60)

        # Search for "LineFeed" or similar
        if 'LineFeed' in config_js:
            print("\n[FOUND] LineFeed mentioned in config")
            # Get context around LineFeed
            for match in re.finditer(r'.{50}LineFeed.{50}', config_js):
                print(f"  ...{match.group()}...")

        # Search for "GetChamps" or similar
        if 'GetChamps' in config_js or 'getChamps' in config_js:
            print("\n[FOUND] GetChamps mentioned in config")

        # Look for domain patterns
        print("\n" + "="*60)
        print("DOMAINS FOUND:")
        print("="*60)

        domains = re.findall(r'https?://([^/"\',\s]+)', config_js)
        unique_domains = list(set(domains))

        for domain in sorted(unique_domains):
            if 'bet' in domain.lower() or 'sport' in domain.lower():
                print(f"  {domain}")

        # Try to extract JSON-like config objects
        print("\n" + "="*60)
        print("SEARCHING FOR CONFIG OBJECTS:")
        print("="*60)

        # Look for window.config = {...}
        config_match = re.search(r'window\.config\s*=\s*({.+?});', config_js, re.DOTALL)
        if config_match:
            print("\n[FOUND] window.config object")
            config_str = config_match.group(1)
            print(config_str[:500])

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    analyze_config()
