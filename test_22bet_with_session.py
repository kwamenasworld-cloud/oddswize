#!/usr/bin/env python3
"""
Test 22Bet by first establishing a session.
"""

import cloudscraper
import json
import time

def test_with_session():
    print("=" * 60)
    print("TESTING 22BET WITH SESSION")
    print("=" * 60)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    # Step 1: Visit the main site to establish session
    print("\nStep 1: Visiting main site to establish session...")
    resp = scraper.get('https://22bet.com.gh', timeout=30)
    print(f"Status: {resp.status_code}")
    print(f"Cookies: {len(scraper.cookies)} cookies set")

    # Show cookies
    for cookie in scraper.cookies:
        print(f"  - {cookie.name}: {cookie.value[:50]}")

    # Step 2: Visit the sports/football page
    print("\nStep 2: Visiting sports page...")
    resp = scraper.get('https://22bet.com.gh/line/football', timeout=30)
    print(f"Status: {resp.status_code}")
    print(f"Cookies: {len(scraper.cookies)} cookies now")

    # Wait a moment
    time.sleep(1)

    # Step 3: Now try the API with the established session
    print("\nStep 3: Trying API with established session...")

    # Update headers to match what browser would send
    scraper.headers.update({
        'Accept': 'application/json',
        'Referer': 'https://22bet.com.gh/line/football',
        'X-Requested-With': 'XMLHttpRequest',
    })

    # Try the platform API endpoints
    endpoints_to_try = [
        "/LineFeed/GetChampsZip?sport=1&lng=en",
        "/api/v1/sportsbook/sports/1/championships",
        "/api/v1/sports/1/leagues",
        "/api/v1/line/soccer",
        "/api/v1/prematch/soccer",
    ]

    for endpoint in endpoints_to_try:
        url = f"https://platform.22bet.com.gh{endpoint}"
        print(f"\n  Trying: {url}")

        try:
            resp = scraper.get(url, timeout=30)
            print(f"  Status: {resp.status_code}")

            if resp.status_code == 200:
                try:
                    data = resp.json()

                    if isinstance(data, dict):
                        status = data.get('status')
                        code = data.get('code')

                        if status == 'success' or code == 200:
                            print(f"  [SUCCESS] Working endpoint!")
                            print(f"  Response: {json.dumps(data, indent=2)[:300]}")
                            return url
                        elif status == 'error' and code == 404:
                            print(f"  [404] Endpoint not found")
                        elif 'Value' in data:
                            print(f"  [SUCCESS] Old format detected!")
                            return url
                    elif isinstance(data, list):
                        print(f"  [SUCCESS] Got list with {len(data)} items!")
                        return url

                except:
                    pass

        except Exception as e:
            print(f"  Error: {str(e)[:60]}")

    # Try looking at network requests the page makes
    print("\n" + "="*60)
    print("Checking if page loads data via AJAX...")
    print("="*60)

    # The page is a React SPA, it should make API calls
    # Let me try intercepting by looking at the page source for embedded data
    resp = scraper.get('https://22bet.com.gh/line/football/england/premier-league', timeout=30)

    # Check if there's any JSON data embedded in the HTML
    html = resp.text

    # Look for __INITIAL_STATE__ or similar
    if '_STATE' in html or 'window.__' in html:
        print("[FOUND] Page has embedded state data")
        # Try to extract it
        import re
        state_match = re.search(r'window\.__[A-Z_]+__\s*=\s*({.+?});', html, re.DOTALL)
        if state_match:
            print("Found embedded state!")
            try:
                state_data = json.loads(state_match.group(1))
                print(f"State keys: {list(state_data.keys())[:10]}")
            except:
                print("Could not parse state as JSON")

    return None

if __name__ == '__main__':
    working_url = test_with_session()

    print(f"\n{'='*60}")
    if working_url:
        print(f"[SUCCESS] Working endpoint:")
        print(f"  {working_url}")
    else:
        print("[FAILED] Could not find working endpoint with session")
    print('='*60)
