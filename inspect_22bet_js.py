#!/usr/bin/env python3
"""
Inspect 22Bet JavaScript files to find API endpoints.
"""

import cloudscraper
import re
import json

def inspect_js_files():
    print("=" * 60)
    print("INSPECTING 22BET JAVASCRIPT FILES")
    print("=" * 60)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    # Get the main page to find the base URL
    print("\nFetching main page to find JS files...")
    try:
        resp = scraper.get('https://22bet.com.gh', timeout=30)
        html = resp.text

        # Extract the configuration.js URL
        config_js_match = re.search(r'src="([^"]*configuration\.js[^"]*)"', html)
        if config_js_match:
            config_url = config_js_match.group(1)
            if not config_url.startswith('http'):
                config_url = f"https://22bet.com.gh/{config_url.lstrip('/')}"

            print(f"\nFound configuration.js: {config_url}")
            print("Fetching configuration.js...")

            resp = scraper.get(config_url, timeout=30)
            config_js = resp.text

            print(f"Size: {len(config_js)} bytes")

            # Look for API endpoints
            print("\nSearching for API patterns...")

            # Look for URLs
            urls = re.findall(r'https?://[^\s"\',;)]+', config_js)
            if urls:
                print(f"\nFound {len(set(urls))} unique URLs:")
                for url in sorted(set(urls))[:30]:
                    if 'api' in url.lower() or 'feed' in url.lower() or '22bet' in url:
                        print(f"  - {url}")

            # Look for potential API keys or config
            print("\nSearching for configuration objects...")
            config_patterns = [
                r'apiUrl["\']?\s*:\s*["\']([^"\']+)',
                r'feedUrl["\']?\s*:\s*["\']([^"\']+)',
                r'baseUrl["\']?\s*:\s*["\']([^"\']+)',
                r'endpoint["\']?\s*:\s*["\']([^"\']+)',
            ]

            for pattern in config_patterns:
                matches = re.findall(pattern, config_js, re.IGNORECASE)
                if matches:
                    print(f"\nPattern '{pattern}':")
                    for match in set(matches)[:10]:
                        print(f"  - {match}")

    except Exception as e:
        print(f"Error: {e}")

    # Try to get the manifest file
    print("\n" + "="*60)
    print("Fetching remotes manifest...")
    print("="*60)

    try:
        manifest_url = "https://dwmu1hf7ovvid.cloudfront.net/remotes/remotes-manifest.js"
        print(f"URL: {manifest_url}")

        resp = scraper.get(manifest_url, timeout=30)
        print(f"Status: {resp.status_code}")

        if resp.status_code == 200:
            manifest = resp.text
            print(f"Size: {len(manifest)} bytes")

            # Look for module URLs
            print("\nSearching for remote modules...")
            module_urls = re.findall(r'https?://[^\s"\',;)]+', manifest)
            if module_urls:
                print(f"Found {len(set(module_urls))} module URLs")
                for url in sorted(set(module_urls))[:20]:
                    print(f"  - {url}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    inspect_js_files()
