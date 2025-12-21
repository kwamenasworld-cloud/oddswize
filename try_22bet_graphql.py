#!/usr/bin/env python3
"""
Try 22Bet GraphQL and alternative API formats.
"""

import cloudscraper
import json

def try_graphql_and_alternatives():
    print("=" * 60)
    print("TRYING 22BET GRAPHQL & ALTERNATIVE FORMATS")
    print("=" * 60)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    scraper.headers.update({
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Referer': 'https://22bet.com.gh',
    })

    # Try GraphQL
    print("\n1. Testing GraphQL...")
    graphql_endpoints = [
        "https://platform.22bet.com.gh/graphql",
        "https://22bet.com.gh/graphql",
        "https://api.22bet.com.gh/graphql",
    ]

    graphql_query = {
        "query": """
        {
            sports(id: 1) {
                championships {
                    id
                    name
                    games {
                        homeTeam
                        awayTeam
                        odds
                    }
                }
            }
        }
        """
    }

    for endpoint in graphql_endpoints:
        try:
            resp = scraper.post(endpoint, json=graphql_query, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if 'data' in data:
                    print(f"  [FOUND] GraphQL works at: {endpoint}")
                    return endpoint
        except:
            pass

    # Try REST with different parameter names
    print("\n2. Testing REST with different parameters...")
    rest_tests = [
        "https://platform.22bet.com.gh/api/sportsbook/fixtures?sportId=1",
        "https://platform.22bet.com.gh/api/sportsbook/events?sport=Football",
        "https://platform.22bet.com.gh/api/v1/fixtures?sport=1",
        "https://platform.22bet.com.gh/api/v1/games?sportId=1",
        "https://platform.22bet.com.gh/api/prematch/sports/1/events",
        "https://platform.22bet.com.gh/api/prematch/football/leagues",
        "https://platform.22bet.com.gh/sportsbook/prematch/1",
    ]

    for url in rest_tests:
        try:
            resp = scraper.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    status = data.get('status')
                    if status == 'success':
                        print(f"  [FOUND] REST works at: {url}")
                        print(f"  Data: {json.dumps(data, indent=2)[:200]}")
                        return url
        except:
            pass

    # Try with authentication token (maybe they need one)
    print("\n3. Testing with session token...")
    # First get the main page to establish session
    scraper.get('https://22bet.com.gh', timeout=30)

    # Try the platform API again with cookies
    url = "https://platform.22bet.com.gh/LineFeed/GetChampsZip?sport=1&lng=en"
    try:
        resp = scraper.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and data.get('status') == 'success':
                print(f"  [FOUND] Works with session: {url}")
                return url
    except:
        pass

    # Try betradar API (they use it according to config)
    print("\n4. Testing Betradar integration...")
    betradar_tests = [
        "https://platform.22bet.com.gh/api/betradar/sport/1/tournaments",
        "https://platform.22bet.com.gh/betradar/v1/sports/1/matches",
    ]

    for url in betradar_tests:
        try:
            resp = scraper.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, (dict, list)) and data:
                    print(f"  [FOUND] Betradar works: {url}")
                    return url
        except:
            pass

    return None

if __name__ == '__main__':
    working_endpoint = try_graphql_and_alternatives()

    print(f"\n{'='*60}")
    if working_endpoint:
        print(f"[SUCCESS] Found working endpoint:")
        print(f"  {working_endpoint}")
    else:
        print("[FAILED] No alternative endpoints found")
    print('='*60)
