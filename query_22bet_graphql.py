#!/usr/bin/env python3
"""
Query 22Bet GraphQL API to get football odds.
"""

import cloudscraper
import json

def query_graphql():
    print("=" * 60)
    print("QUERYING 22BET GRAPHQL FOR FOOTBALL ODDS")
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

    endpoint = "https://platform.22bet.com.gh/graphql"

    # Try different GraphQL queries
    queries_to_try = [
        # Query 1: Get sports with championships
        {
            "query": """
            {
                sports {
                    id
                    name
                    championships {
                        id
                        name
                        gamesCount
                    }
                }
            }
            """
        },
        # Query 2: Get football/soccer specifically
        {
            "query": """
            {
                sport(id: 1) {
                    id
                    name
                    championships {
                        id
                        name
                        gamesCount
                    }
                }
            }
            """
        },
        # Query 3: Try to get games directly
        {
            "query": """
            {
                prematch {
                    sport(id: 1) {
                        championships {
                            id
                            name
                            games {
                                id
                                homeTeam
                                awayTeam
                            }
                        }
                    }
                }
            }
            """
        },
        # Query 4: Introspection to see schema
        {
            "query": """
            {
                __schema {
                    queryType {
                        fields {
                            name
                            description
                        }
                    }
                }
            }
            """
        }
    ]

    for i, query_payload in enumerate(queries_to_try):
        print(f"\n{'='*60}")
        print(f"Query {i+1}:")
        print('='*60)

        try:
            resp = scraper.post(endpoint, json=query_payload, timeout=30)
            print(f"Status: {resp.status_code}")

            if resp.status_code == 200:
                data = resp.json()
                print(f"\nResponse:")
                print(json.dumps(data, indent=2)[:1000])

                # Check if we got useful data
                if 'data' in data and data['data']:
                    if 'errors' not in data:
                        print(f"\n[SUCCESS] Query {i+1} worked!")

                        # Save the response
                        with open(f'22bet_graphql_response_{i+1}.json', 'w') as f:
                            json.dumps(data, f, indent=2)

                        return data

                elif 'errors' in data:
                    print(f"\n[ERROR] GraphQL errors:")
                    for error in data['errors']:
                        print(f"  - {error.get('message')}")

        except Exception as e:
            print(f"Error: {e}")

    return None

if __name__ == '__main__':
    result = query_graphql()

    print(f"\n{'='*60}")
    if result:
        print("[SUCCESS] Got GraphQL response - check the output above")
    else:
        print("[FAILED] Could not get useful GraphQL response")
    print('='*60)
