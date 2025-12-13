#!/usr/bin/env python3
"""
GitHub Actions Odds Scraper

Lightweight scraper for running in GitHub Actions.
Uses requests library instead of curl/subprocess for better compatibility.
Scrapes odds from API-based bookmakers and pushes to Cloudflare Worker.
"""

import json
import os
import re
import time
import requests
from datetime import datetime
from typing import Dict, List, Set, Optional
from difflib import SequenceMatcher

# Configuration
CLOUDFLARE_WORKER_URL = os.getenv('CLOUDFLARE_WORKER_URL', '')
CLOUDFLARE_API_KEY = os.getenv('CLOUDFLARE_API_KEY', '')
MAX_MATCHES = 500

# Common headers for API requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
}

# ============================================================================
# SportyBet Ghana Scraper
# ============================================================================

SPORTYBET_API = "https://www.sportybet.com/api/gh/factsCenter/pcUpcomingEvents"

def scrape_sportybet() -> List[Dict]:
    """Scrape SportyBet Ghana via API."""
    print("Scraping SportyBet Ghana...")
    matches = []
    seen_ids = set()

    headers = {
        **HEADERS,
        'Referer': 'https://www.sportybet.com/gh/sport/football',
        'clientid': 'web',
        'operid': '3',
        'platform': 'web',
    }

    for page in range(1, 10):  # Max 10 pages
        if len(matches) >= MAX_MATCHES:
            break

        try:
            url = f"{SPORTYBET_API}?sportId=sr%3Asport%3A1&marketId=1%2C18%2C10&pageSize=100&pageNum={page}&option=1"
            resp = requests.get(url, headers=headers, timeout=30)
            data = resp.json()

            if data.get('bizCode') != 10000:
                break

            tournaments = data.get('data', {}).get('tournaments', [])
            if not tournaments:
                break

            for tournament in tournaments:
                for event in tournament.get('events', []):
                    event_id = event.get('eventId')
                    if not event_id or event_id in seen_ids:
                        continue

                    home = event.get('homeTeamName')
                    away = event.get('awayTeamName')
                    if not home or not away:
                        continue

                    # Extract 1X2 odds
                    home_odds = draw_odds = away_odds = None
                    for market in event.get('markets', []):
                        if market.get('id') == '1' or market.get('name') in ['1X2', '1x2', 'Match Result']:
                            for outcome in market.get('outcomes', []):
                                desc = outcome.get('desc', '').lower()
                                odds = outcome.get('odds')
                                if odds:
                                    odds_val = float(odds) / 100 if float(odds) > 100 else float(odds)
                                    if desc in ['1', 'home', 'w1']:
                                        home_odds = odds_val
                                    elif desc in ['x', 'draw']:
                                        draw_odds = odds_val
                                    elif desc in ['2', 'away', 'w2']:
                                        away_odds = odds_val
                            break

                    if not home_odds or not away_odds:
                        continue

                    # Get league name
                    sport = event.get('sport', {})
                    category = sport.get('category', {})
                    tourn = category.get('tournament', {})
                    league = tourn.get('name', '')

                    # Get start time
                    start_time = event.get('estimateStartTime', 0)
                    if start_time > 1000000000000:
                        start_time = start_time // 1000

                    seen_ids.add(event_id)
                    matches.append({
                        'bookmaker': 'SportyBet Ghana',
                        'event_id': str(event_id),
                        'home_team': home,
                        'away_team': away,
                        'home_odds': home_odds,
                        'draw_odds': draw_odds or 0.0,
                        'away_odds': away_odds,
                        'league': league,
                        'start_time': start_time,
                    })

            print(f"  Page {page}: {len(matches)} matches")
            time.sleep(0.1)

        except Exception as e:
            print(f"  Page {page} error: {e}")
            break

    print(f"  Total: {len(matches)} matches from SportyBet")
    return matches[:MAX_MATCHES]


# ============================================================================
# 1xBet Ghana Scraper
# ============================================================================

ONEXBET_API = "https://1xbet.com.gh/service-api/LineFeed"

def scrape_1xbet() -> List[Dict]:
    """Scrape 1xBet Ghana via API."""
    print("Scraping 1xBet Ghana...")
    matches = []
    seen_ids = set()

    try:
        # Get championships
        resp = requests.get(f"{ONEXBET_API}/GetChampsZip?sport=1&lng=en", headers=HEADERS, timeout=30)
        champs = resp.json().get("Value", [])
        champs = sorted(champs, key=lambda x: x.get("GC", 0), reverse=True)

        skip_patterns = ["alternative", "team vs player", "specials", "fantasy", "esports"]

        for champ in champs:
            if len(matches) >= MAX_MATCHES:
                break

            champ_id = champ.get("LI")
            champ_name = champ.get("L", "")

            if any(p in champ_name.lower() for p in skip_patterns):
                continue

            # Get games for championship
            try:
                resp = requests.get(f"{ONEXBET_API}/GetChampZip?champ={champ_id}&lng=en", headers=HEADERS, timeout=30)
                value = resp.json().get("Value", {})
                games = value.get("G", []) if isinstance(value, dict) else []
            except:
                continue

            game_ids = [g.get("I") for g in games if g.get("I") and g.get("I") not in seen_ids]

            # Fetch games with odds in batches
            for i in range(0, len(game_ids), 50):
                if len(matches) >= MAX_MATCHES:
                    break

                batch_ids = game_ids[i:i+50]
                ids_str = ",".join(str(i) for i in batch_ids)

                try:
                    resp = requests.get(f"{ONEXBET_API}/GetGamesZip?ids={ids_str}&lng=en", headers=HEADERS, timeout=30)
                    games_data = resp.json().get("Value", [])
                except:
                    continue

                for game in games_data:
                    event_id = game.get("I")
                    if not event_id or event_id in seen_ids:
                        continue

                    home = game.get("O1") or game.get("O1E")
                    away = game.get("O2") or game.get("O2E")

                    home_odds = draw_odds = away_odds = None
                    for o in game.get("E", []):
                        if o.get("G") != 1:
                            continue
                        ot = o.get("T")
                        if ot == 1:
                            home_odds = o.get("C")
                        elif ot == 2:
                            draw_odds = o.get("C")
                        elif ot == 3:
                            away_odds = o.get("C")

                    if not (home and away and home_odds and away_odds):
                        continue

                    # Validate odds
                    try:
                        home_odds = float(home_odds)
                        away_odds = float(away_odds)
                        draw_odds = float(draw_odds) if draw_odds else 0.0

                        if home_odds < 1.01 or home_odds > 100:
                            continue
                        if away_odds < 1.01 or away_odds > 100:
                            continue
                        if draw_odds > 0 and (draw_odds < 2.0 or draw_odds > 50):
                            continue
                    except:
                        continue

                    seen_ids.add(event_id)
                    matches.append({
                        'bookmaker': '1xBet Ghana',
                        'event_id': str(event_id),
                        'home_team': home,
                        'away_team': away,
                        'home_odds': home_odds,
                        'draw_odds': draw_odds,
                        'away_odds': away_odds,
                        'league': game.get("L", ""),
                        'start_time': game.get("S", 0),
                    })

                time.sleep(0.05)

            time.sleep(0.02)

    except Exception as e:
        print(f"  1xBet error: {e}")

    print(f"  Total: {len(matches)} matches from 1xBet")
    return matches[:MAX_MATCHES]


# ============================================================================
# 22Bet Ghana Scraper
# ============================================================================

TWENTYTWOBET_API = "https://22bet.ng/LineFeed"

def scrape_22bet() -> List[Dict]:
    """Scrape 22Bet via API."""
    print("Scraping 22Bet...")
    matches = []
    seen_ids = set()

    try:
        # Get championships
        resp = requests.get(f"{TWENTYTWOBET_API}/GetChampsZip?sport=1&lng=en", headers=HEADERS, timeout=30)
        champs = resp.json().get("Value", [])
        champs = sorted(champs, key=lambda x: x.get("GC", 0), reverse=True)

        skip_patterns = ["alternative", "team vs player", "specials", "fantasy", "esports"]

        for champ in champs:
            if len(matches) >= MAX_MATCHES:
                break

            champ_id = champ.get("LI")
            champ_name = champ.get("L", "")

            if any(p in champ_name.lower() for p in skip_patterns):
                continue

            # Get games for championship
            try:
                resp = requests.get(f"{TWENTYTWOBET_API}/GetChampZip?champ={champ_id}&lng=en", headers=HEADERS, timeout=30)
                value = resp.json().get("Value", {})
                games = value.get("G", []) if isinstance(value, dict) else []
            except:
                continue

            game_ids = [g.get("I") for g in games if g.get("I") and g.get("I") not in seen_ids]

            # Fetch games with odds in batches
            for i in range(0, len(game_ids), 50):
                if len(matches) >= MAX_MATCHES:
                    break

                batch_ids = game_ids[i:i+50]
                ids_str = ",".join(str(i) for i in batch_ids)

                try:
                    resp = requests.get(f"{TWENTYTWOBET_API}/GetGamesZip?ids={ids_str}&lng=en", headers=HEADERS, timeout=30)
                    games_data = resp.json().get("Value", [])
                except:
                    continue

                for game in games_data:
                    event_id = game.get("I")
                    if not event_id or event_id in seen_ids:
                        continue

                    home = game.get("O1") or game.get("O1E")
                    away = game.get("O2") or game.get("O2E")

                    home_odds = draw_odds = away_odds = None
                    for o in game.get("E", []):
                        if o.get("G") != 1:
                            continue
                        ot = o.get("T")
                        if ot == 1:
                            home_odds = o.get("C")
                        elif ot == 2:
                            draw_odds = o.get("C")
                        elif ot == 3:
                            away_odds = o.get("C")

                    if not (home and away and home_odds and away_odds):
                        continue

                    # Validate odds
                    try:
                        home_odds = float(home_odds)
                        away_odds = float(away_odds)
                        draw_odds = float(draw_odds) if draw_odds else 0.0

                        if home_odds < 1.01 or home_odds > 100:
                            continue
                        if away_odds < 1.01 or away_odds > 100:
                            continue
                        if draw_odds > 0 and (draw_odds < 2.0 or draw_odds > 50):
                            continue
                    except:
                        continue

                    seen_ids.add(event_id)
                    matches.append({
                        'bookmaker': '22Bet',
                        'event_id': str(event_id),
                        'home_team': home,
                        'away_team': away,
                        'home_odds': home_odds,
                        'draw_odds': draw_odds,
                        'away_odds': away_odds,
                        'league': game.get("L", ""),
                        'start_time': game.get("S", 0),
                    })

                time.sleep(0.05)

            time.sleep(0.02)

    except Exception as e:
        print(f"  22Bet error: {e}")

    print(f"  Total: {len(matches)} matches from 22Bet")
    return matches[:MAX_MATCHES]


# ============================================================================
# Event Matching
# ============================================================================

def normalize_team_name(name: str) -> str:
    """Normalize team name for matching."""
    name = name.lower().strip()
    # Remove common suffixes
    suffixes = [' fc', ' sc', ' cf', ' afc', ' united', ' city', ' town', ' sporting']
    for suffix in suffixes:
        name = name.replace(suffix, '')
    # Remove special characters
    name = re.sub(r'[^a-z0-9\s]', '', name)
    return name.strip()


def teams_match(team1: str, team2: str) -> bool:
    """Check if two team names match."""
    n1 = normalize_team_name(team1)
    n2 = normalize_team_name(team2)

    if n1 == n2:
        return True

    # Fuzzy match
    ratio = SequenceMatcher(None, n1, n2).ratio()
    return ratio > 0.75


def match_events(all_matches: Dict[str, List[Dict]]) -> List[List[Dict]]:
    """Match events across bookmakers."""
    print("\nMatching events across bookmakers...")

    matched = []
    used_ids = {bookie: set() for bookie in all_matches}

    # Use first bookmaker as base
    bookies = list(all_matches.keys())
    if not bookies:
        return []

    base_bookie = bookies[0]
    other_bookies = bookies[1:]

    for base_match in all_matches[base_bookie]:
        event_group = [base_match]
        base_home = base_match['home_team']
        base_away = base_match['away_team']

        for other_bookie in other_bookies:
            for other_match in all_matches[other_bookie]:
                other_id = other_match['event_id']
                if other_id in used_ids[other_bookie]:
                    continue

                if (teams_match(base_home, other_match['home_team']) and
                    teams_match(base_away, other_match['away_team'])):
                    event_group.append(other_match)
                    used_ids[other_bookie].add(other_id)
                    break

        if len(event_group) >= 2:
            matched.append(event_group)

    print(f"  Matched {len(matched)} events across bookmakers")
    return matched


# ============================================================================
# Cloudflare Push
# ============================================================================

def push_to_cloudflare(matched_events: List[List[Dict]]) -> bool:
    """Push matched events to Cloudflare Worker."""
    if not CLOUDFLARE_WORKER_URL:
        print("CLOUDFLARE_WORKER_URL not configured - skipping push")
        return False

    print(f"\nPushing {len(matched_events)} events to Cloudflare...")

    # Group by league
    leagues = {}
    for event_group in matched_events:
        base = event_group[0]
        league = base.get('league', 'Unknown')

        if league not in leagues:
            leagues[league] = []

        match_data = {
            'id': f"match_{hash(base['home_team'] + base['away_team'])}",
            'home_team': base['home_team'],
            'away_team': base['away_team'],
            'league': league,
            'kickoff': datetime.fromtimestamp(base.get('start_time', 0)).isoformat() if base.get('start_time') else datetime.now().isoformat(),
            'odds': [
                {
                    'bookmaker': m['bookmaker'],
                    'home_odds': m['home_odds'],
                    'draw_odds': m['draw_odds'],
                    'away_odds': m['away_odds'],
                    'last_updated': datetime.now().isoformat()
                }
                for m in event_group
            ]
        }
        leagues[league].append(match_data)

    # Format for API
    api_data = [{'league': league, 'matches': matches} for league, matches in leagues.items()]

    # Push to Cloudflare
    url = f"{CLOUDFLARE_WORKER_URL}/api/odds/update"
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': CLOUDFLARE_API_KEY
    }

    try:
        resp = requests.post(url, json=api_data, headers=headers, timeout=30)
        if resp.status_code == 200:
            print(f"  Success: {resp.json().get('message', 'OK')}")
            return True
        else:
            print(f"  Failed: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


# ============================================================================
# Main
# ============================================================================

def main():
    print("=" * 60)
    print("OddsWize GitHub Actions Scraper")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)

    # Scrape all bookmakers
    all_matches = {}

    sportybet = scrape_sportybet()
    if sportybet:
        all_matches['SportyBet Ghana'] = sportybet

    onexbet = scrape_1xbet()
    if onexbet:
        all_matches['1xBet Ghana'] = onexbet

    twentytwobet = scrape_22bet()
    if twentytwobet:
        all_matches['22Bet'] = twentytwobet

    total = sum(len(m) for m in all_matches.values())
    print(f"\nTotal scraped: {total} matches from {len(all_matches)} bookmakers")

    if not all_matches:
        print("No matches scraped - exiting")
        return

    # Match events
    matched = match_events(all_matches)

    if not matched:
        print("No matched events - exiting")
        return

    # Save to file (for artifact upload)
    output = {
        'last_updated': datetime.now().isoformat(),
        'stats': {
            'total_scraped': total,
            'matched_events': len(matched),
            'bookmakers': list(all_matches.keys())
        },
        'matches': [
            {
                'home_team': e[0]['home_team'],
                'away_team': e[0]['away_team'],
                'league': e[0].get('league', ''),
                'odds': [
                    {
                        'bookmaker': m['bookmaker'],
                        'home_odds': m['home_odds'],
                        'draw_odds': m['draw_odds'],
                        'away_odds': m['away_odds']
                    }
                    for m in e
                ]
            }
            for e in matched[:200]
        ]
    }

    with open('odds_data.json', 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to odds_data.json")

    # Push to Cloudflare
    push_to_cloudflare(matched)

    print("\nDone!")


if __name__ == '__main__':
    main()
