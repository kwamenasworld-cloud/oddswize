#!/usr/bin/env python3
"""
Process and Push Script
Processes already-scraped odds data and pushes to Cloudflare.
This allows testing filtering/normalization without re-scraping.
"""

import json
import os
import re
import requests
from typing import Dict, List
from difflib import SequenceMatcher

# ============================================================================
# Configuration
# ============================================================================

CLOUDFLARE_WORKER_URL = os.environ.get('CLOUDFLARE_WORKER_URL', '')
CLOUDFLARE_API_KEY = os.environ.get('CLOUDFLARE_API_KEY', '')
INPUT_FILE = 'odds_data.json'

# ============================================================================
# Team Validation Data (copied from scrape_odds_github.py)
# ============================================================================

LEAGUE_TEAMS = {
    'Premier League': {
        'arsenal', 'aston villa', 'bournemouth', 'brentford', 'brighton',
        'brighton hove', 'brighton hove albion',
        'burnley',
        'chelsea', 'crystal palace', 'everton', 'fulham', 'ipswich', 'ipswich town',
        'leeds', 'leeds united',
        'leicester', 'leicester city', 'liverpool', 'manchester city', 'manchester united',
        'newcastle', 'newcastle united', 'nottingham forest', 'southampton',
        'sunderland', 'sunderland afc',
        'tottenham', 'west ham', 'wolves', 'wolverhampton', 'wolverhampton wanderers'
    },
    'La Liga': {
        'athletic bilbao', 'athletic club', 'atletico madrid', 'barcelona', 'celta vigo',
        'espanyol', 'getafe', 'girona', 'las palmas', 'leganes',
        'mallorca', 'osasuna', 'rayo vallecano', 'real betis', 'real madrid',
        'real sociedad', 'real valladolid', 'sevilla', 'valencia', 'villarreal'
    },
    'Serie A': {
        'atalanta', 'bologna', 'cagliari', 'como', 'empoli',
        'fiorentina', 'genoa', 'inter', 'inter milan', 'internazionale',
        'juventus', 'lazio', 'lecce', 'milan', 'ac milan',
        'monza', 'napoli', 'parma', 'roma', 'torino',
        'udinese', 'venezia', 'verona', 'hellas verona'
    },
    'Bundesliga': {
        'augsburg', 'bayer leverkusen', 'leverkusen', 'bayern', 'bayern munich',
        'bochum', 'borussia dortmund', 'dortmund', 'eintracht frankfurt', 'frankfurt',
        'freiburg', 'heidenheim', 'hoffenheim', 'holstein kiel',
        'mainz', 'rb leipzig', 'leipzig', 'st pauli', 'union berlin',
        'werder bremen', 'bremen', 'wolfsburg'
    },
    'Ligue 1': {
        'angers', 'auxerre', 'brest', 'le havre', 'lens',
        'lille', 'lyon', 'marseille', 'monaco', 'montpellier',
        'nantes', 'nice', 'psg', 'paris', 'paris saint germain',
        'rennais', 'stade rennais',
        'reims', 'rennes', 'saint etienne', 'strasbourg', 'toulouse'
    },
    'Championship': {
        'barnsley', 'birmingham', 'blackburn', 'bristol city', 'burnley',
        'cardiff', 'charlton', 'charlton athletic', 'coventry', 'derby', 'derby county', 'hull', 'hull city',
        'ipswich', 'ipswich town',
        'leeds', 'leeds united', 'luton', 'luton town', 'middlesbrough',
        'millwall', 'norwich', 'norwich city', 'plymouth', 'portsmouth',
        'preston', 'qpr', 'queens park rangers', 'raith rovers', 'raith rovers fc',
        'sheffield united', 'sheffield wednesday',
        'southampton', 'southampton fc',
        'stoke', 'stoke city', 'sunderland', 'swansea', 'watford', 'west brom',
        'wrexham', 'wrexham afc'
    }
}

# ============================================================================
# Helper Functions (copied from scrape_odds_github.py)
# ============================================================================

def normalize_name(name: str) -> str:
    """Normalize team name for matching."""
    name = name.lower().strip()
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name)

    removals = ['fc', 'cf', 'sc', 'ac', 'afc', 'ssc', 'bc', 'fk', 'sk', 'nk',
                'united', 'utd', 'city', 'town', 'athletic', 'sporting']
    words = name.split()
    words = [w for w in words if w not in removals]
    return ' '.join(words) if words else name

def is_team_in_league(team_name: str, league: str) -> bool:
    """Check if a team belongs to a specific league."""
    if league not in LEAGUE_TEAMS:
        return True  # No validation data for this league, allow it

    known_teams = LEAGUE_TEAMS[league]
    normalized = normalize_name(team_name).lower()

    # Check if normalized name is in the known teams set
    if normalized in known_teams:
        return True

    # Also check if any known team name is contained in the team name
    for known_team in known_teams:
        if known_team in normalized or normalized in known_team:
            return True

    return False

def normalize_league(league: str) -> str:
    """Normalize league name to prevent duplicates across bookmakers."""
    if not league:
        return ''

    league = league.strip()

    # First normalize periods and spaces
    league = league.replace('. ', ' ').strip()

    # Normalize specific league name variations
    league = league.replace('LaLiga', 'La Liga')
    league = league.replace('2 Bundesliga', '2nd Bundesliga')
    league = league.replace('3 Bundesliga', '3rd Bundesliga')

    # Major league mappings
    major_league_mappings = {
        'England Premier League': 'Premier League',
        'England Championship': 'Championship',
        'England League One': 'League One',
        'England League Two': 'League Two',
        'Spain La Liga': 'La Liga',
        'Spain La Liga 2': 'La Liga 2',
        'Italy Serie A': 'Serie A',
        'Italy Serie B': 'Serie B',
        'Germany Bundesliga': 'Bundesliga',
        'Germany 2nd Bundesliga': '2nd Bundesliga',
        'France Ligue 1': 'Ligue 1',
        'France Ligue 2': 'Ligue 2',
        'Portugal Primeira Liga': 'Primeira Liga',
        'Netherlands Eredivisie': 'Eredivisie',
        'Scotland Premiership': 'Scottish Premiership',
    }

    if league in major_league_mappings:
        league = major_league_mappings[league]

    return league

# ============================================================================
# Processing Functions
# ============================================================================

def load_scraped_data(filename: str) -> Dict:
    """Load scraped data from JSON file."""
    print(f"Loading data from {filename}...")
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total_matches = len(data.get('matches', []))
    print(f"  Loaded {total_matches} matches")
    return data

def process_and_filter(data: Dict) -> List[Dict]:
    """Process matches with normalization and filtering."""
    matches = data.get('matches', [])

    # Group by league
    league_groups = {}
    filtered_count = 0

    print("\nProcessing matches...")

    for match in matches:
        league = match.get('league', 'Unknown')

        # Normalize league name
        normalized_league = normalize_league(league)

        # Validate teams for specific leagues
        if normalized_league in LEAGUE_TEAMS:
            home_team = match.get('home_team', '')
            away_team = match.get('away_team', '')

            is_home_valid = is_team_in_league(home_team, normalized_league)
            is_away_valid = is_team_in_league(away_team, normalized_league)

            if not (is_home_valid or is_away_valid):
                print(f"  [FILTER] Skipping non-{normalized_league} match: {home_team} vs {away_team}")
                filtered_count += 1
                continue

        # Initialize league group if needed
        if normalized_league not in league_groups:
            league_groups[normalized_league] = {
                'league': normalized_league,
                'matches': []
            }

        # Update match league to normalized version
        match['league'] = normalized_league
        league_groups[normalized_league]['matches'].append(match)

    if filtered_count > 0:
        print(f"  [FILTER] Filtered out {filtered_count} mismatched matches from major leagues")

    # Convert to array
    output = list(league_groups.values())

    total_matches = sum(len(lg['matches']) for lg in output)
    print(f"  Processed into {len(output)} leagues with {total_matches} total matches")

    return output

def push_to_cloudflare(league_data: List[Dict]):
    """Push processed data to Cloudflare Worker."""
    if not CLOUDFLARE_WORKER_URL or not CLOUDFLARE_API_KEY:
        print("\n" + "="*60)
        print("WARNING: Cloudflare credentials not set")
        print("="*60)
        print("  Set CLOUDFLARE_WORKER_URL and CLOUDFLARE_API_KEY to push to Cloudflare")
        return

    api_url = CLOUDFLARE_WORKER_URL.rstrip('/')
    if not api_url.endswith('/api/odds/update'):
        api_url += '/api/odds/update'

    print(f"\n{'='*60}")
    print(f"Pushing to Cloudflare...")
    print(f"{'='*60}")
    print(f"  Target URL: {api_url}")
    print(f"  Leagues: {len(league_data)}")

    total_matches = sum(len(lg['matches']) for lg in league_data)
    print(f"  Matches: {total_matches}")

    try:
        resp = requests.post(
            api_url,
            json=league_data,
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': CLOUDFLARE_API_KEY
            },
            timeout=30
        )

        print(f"  [OK] Response: {resp.status_code}")

        if resp.status_code == 200:
            print(f"  [SUCCESS] Data pushed successfully!")
            print(f"  [SUCCESS] Website will update with new odds")
        else:
            print(f"  [WARNING] Unexpected status: {resp.status_code}")
            print(f"  Response: {resp.text[:200]}")

    except Exception as e:
        print(f"  [ERROR] Failed to push: {e}")

# ============================================================================
# Main
# ============================================================================

def main():
    print("="*60)
    print("ODDS DATA PROCESSOR & PUSHER")
    print("="*60)
    print()

    # Load scraped data
    data = load_scraped_data(INPUT_FILE)

    # Process and filter
    processed_data = process_and_filter(data)

    # Push to Cloudflare
    push_to_cloudflare(processed_data)

    print("\nDone!")

if __name__ == '__main__':
    main()
