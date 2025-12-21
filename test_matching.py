#!/usr/bin/env python3
"""
Test matching logic without re-scraping.
Simulates the match_events() function to debug why Newcastle vs Chelsea isn't matching across all bookmakers.
"""

import re
from difflib import SequenceMatcher
from typing import Dict, List

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

def match_events(all_matches: Dict[str, List[Dict]]) -> List[List[Dict]]:
    """Match events across bookmakers."""
    print("\nMatching events...")

    groups = {}

    # Generic team names to filter out
    generic_names = {'home', 'away', 'team 1', 'team 2', 'team1', 'team2', 'home team', 'away team'}

    for bookie, matches in all_matches.items():
        for match in matches:
            home = normalize_name(match['home_team'])
            away = normalize_name(match['away_team'])

            print(f"  {bookie}: '{match['home_team']}' -> '{home}' | '{match['away_team']}' -> '{away}'")

            # Skip generic names
            if (home in generic_names or away in generic_names or
                not home or not away or
                home.startswith('home') or away.startswith('away') or
                home.startswith('team') or away.startswith('team')):
                print(f"    -> SKIPPED (generic name)")
                continue

            # Try exact match first
            key = f"{home}|{away}"
            if key in groups:
                groups[key].append(match)
                print(f"    -> EXACT MATCH to existing group '{key}'")
                continue

            # Fuzzy matching
            matched = False
            for existing_key in list(groups.keys()):
                eh, ea = existing_key.split('|')
                home_sim = SequenceMatcher(None, home, eh).ratio()
                away_sim = SequenceMatcher(None, away, ea).ratio()

                if home_sim > 0.8 and away_sim > 0.8:
                    groups[existing_key].append(match)
                    print(f"    -> FUZZY MATCH to '{existing_key}' (H:{home_sim:.2f}, A:{away_sim:.2f})")
                    matched = True
                    break

            if not matched:
                groups[key] = [match]
                print(f"    -> NEW GROUP '{key}'")

    # Only return events with 2+ bookmakers
    matched = [g for g in groups.values() if len(g) >= 2]

    print(f"\n  Total groups: {len(groups)}")
    print(f"  Groups with 2+ bookmakers: {len(matched)}")

    return matched

# ============================================================================
# Test Data - Newcastle vs Chelsea from different bookmakers
# ============================================================================

test_matches = {
    'Betway Ghana': [
        {
            'bookmaker': 'Betway Ghana',
            'home_team': 'Newcastle United',
            'away_team': 'Chelsea',
            'league': 'Premier League',
            'home_odds': 2.65,
            'draw_odds': 3.55,
            'away_odds': 2.55,
        }
    ],
    'SoccaBet Ghana': [
        {
            'bookmaker': 'SoccaBet Ghana',
            'home_team': 'Newcastle Utd.',
            'away_team': 'Chelsea',
            'league': 'England. Premier League',
            'home_odds': 2.65,
            'draw_odds': 3.55,
            'away_odds': 2.55,
        }
    ],
    'SportyBet Ghana': [
        {
            'bookmaker': 'SportyBet Ghana',
            'home_team': 'Newcastle',
            'away_team': 'Chelsea',
            'league': 'England Premier League',
            'home_odds': 2.66,
            'draw_odds': 3.60,
            'away_odds': 2.59,
        }
    ],
    '1xBet Ghana': [
        {
            'bookmaker': '1xBet Ghana',
            'home_team': 'Newcastle United',
            'away_team': 'Chelsea',
            'league': 'England. Premier League',
            'home_odds': 2.753,
            'draw_odds': 3.695,
            'away_odds': 2.621,
        }
    ],
    '22Bet Ghana': [
        {
            'bookmaker': '22Bet Ghana',
            'home_team': 'Newcastle United',
            'away_team': 'Chelsea',
            'league': 'England. Premier League',
            'home_odds': 2.753,
            'draw_odds': 3.695,
            'away_odds': 2.621,
        }
    ],
    'Betfox Ghana': [
        {
            'bookmaker': 'Betfox Ghana',
            'home_team': 'Newcastle United',
            'away_team': 'Chelsea',
            'league': 'England. Premier League',
            'home_odds': 2.70,
            'draw_odds': 3.60,
            'away_odds': 2.60,
        }
    ],
}

if __name__ == '__main__':
    print("="*60)
    print("TESTING MATCH LOGIC - Newcastle vs Chelsea")
    print("="*60)

    matched_groups = match_events(test_matches)

    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)

    for i, group in enumerate(matched_groups):
        print(f"\nGroup {i+1}: {len(group)} bookmakers")
        for match in group:
            print(f"  - {match['bookmaker']}: {match['home_team']} vs {match['away_team']}")

    if matched_groups and len(matched_groups[0]) == 6:
        print("\n✓ SUCCESS: All 6 bookmakers matched!")
    else:
        print(f"\n✗ FAILED: Expected 1 group with 6 bookmakers, got {len(matched_groups)} groups")
        if matched_groups:
            print(f"  Largest group has {len(matched_groups[0])} bookmakers")
