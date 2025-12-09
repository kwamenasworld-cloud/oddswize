#!/usr/bin/env python3
"""
Push scraped odds data to Cloudflare Worker API

This script reads the scraped data and pushes it to the Cloudflare Worker
for caching and serving to the frontend.
"""

import json
import os
import requests
from datetime import datetime
from typing import Dict, List, Any

# Configuration
WORKER_URL = os.getenv('CLOUDFLARE_WORKER_URL', 'https://oddswize-api.YOUR_SUBDOMAIN.workers.dev')
API_KEY = os.getenv('CLOUDFLARE_API_KEY', 'your-api-key-here')
DATA_FILE = 'ghana_arb_results.json'


def load_scraped_data(filepath: str) -> Dict[str, Any]:
    """Load scraped data from JSON file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {filepath} not found")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return {}


def transform_to_api_format(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Transform scraped data to the API format expected by Cloudflare Worker

    Input format (from scraper):
    {
        "matches": [...],
        "arbitrage_opportunities": [...],
        ...
    }

    Output format (for API):
    [
        {
            "league": "English Premier League",
            "matches": [
                {
                    "id": "match_123",
                    "home_team": "Arsenal",
                    "away_team": "Chelsea",
                    "league": "English Premier League",
                    "kickoff": "2024-01-15T15:00:00Z",
                    "odds": [
                        {
                            "bookmaker": "Betway Ghana",
                            "home_odds": 2.10,
                            "draw_odds": 3.40,
                            "away_odds": 3.20
                        },
                        ...
                    ]
                },
                ...
            ]
        },
        ...
    ]
    """
    matches = data.get('matches', [])

    if not matches:
        print("No matches found in data")
        return []

    # Group matches by league
    leagues: Dict[str, List[Dict]] = {}

    for match in matches:
        league = match.get('league', 'Unknown League')

        if league not in leagues:
            leagues[league] = []

        # Transform match to API format
        transformed_match = {
            'id': match.get('id', f"match_{hash(match.get('home_team', '') + match.get('away_team', ''))}"),
            'home_team': match.get('home_team', 'Unknown'),
            'away_team': match.get('away_team', 'Unknown'),
            'league': league,
            'kickoff': match.get('kickoff', match.get('start_time', datetime.now().isoformat())),
            'is_live': match.get('is_live', False),
            'odds': []
        }

        # Transform odds
        odds_data = match.get('odds', [])
        for odds in odds_data:
            transformed_odds = {
                'bookmaker': odds.get('bookmaker', 'Unknown'),
                'home_odds': odds.get('home_odds') or odds.get('1') or None,
                'draw_odds': odds.get('draw_odds') or odds.get('X') or None,
                'away_odds': odds.get('away_odds') or odds.get('2') or None,
                'url': odds.get('url', ''),
                'last_updated': odds.get('last_updated', datetime.now().isoformat())
            }
            transformed_match['odds'].append(transformed_odds)

        leagues[league].append(transformed_match)

    # Convert to list format
    result = []
    for league_name, league_matches in leagues.items():
        result.append({
            'league': league_name,
            'matches': league_matches
        })

    return result


def push_to_cloudflare(data: List[Dict[str, Any]], worker_url: str, api_key: str) -> bool:
    """Push data to Cloudflare Worker API"""
    url = f"{worker_url}/api/odds/update"

    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': api_key
    }

    try:
        print(f"Pushing data to {url}...")
        response = requests.post(url, json=data, headers=headers, timeout=30)

        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result.get('message', 'Data updated')}")
            return True
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return False

    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return False


def main():
    """Main function"""
    print("=" * 50)
    print("OddsWize - Push to Cloudflare Worker")
    print("=" * 50)
    print(f"Time: {datetime.now().isoformat()}")
    print(f"Data file: {DATA_FILE}")
    print(f"Worker URL: {WORKER_URL}")
    print()

    # Load scraped data
    print("Loading scraped data...")
    raw_data = load_scraped_data(DATA_FILE)

    if not raw_data:
        print("No data to push")
        return

    # Transform to API format
    print("Transforming data...")
    api_data = transform_to_api_format(raw_data)

    total_matches = sum(len(league['matches']) for league in api_data)
    print(f"Prepared {total_matches} matches across {len(api_data)} leagues")

    if not api_data:
        print("No valid data to push")
        return

    # Push to Cloudflare
    success = push_to_cloudflare(api_data, WORKER_URL, API_KEY)

    if success:
        print("\nData successfully pushed to Cloudflare!")
    else:
        print("\nFailed to push data to Cloudflare")


if __name__ == '__main__':
    main()
