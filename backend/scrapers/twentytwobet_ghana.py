#!/usr/bin/env python3
"""22Bet Ghana Odds Scraper (API-based)

Uses curl subprocess to bypass TLS fingerprinting.
Fetches events by championship to get 800+ matches.
"""

import json
import os
import subprocess
import time
from typing import Dict, List, Set

BASE_URL = os.getenv("TWENTYTWOBET_API_URL", "https://22bet.ng/LineFeed")
DEFAULT_MAX_MATCHES = 800


def _curl_fetch(endpoint: str, params: str) -> dict:
    """Fetch from API using curl."""
    url = f"{BASE_URL}/{endpoint}?{params}"
    cmd = [
        "curl", "-s", "--compressed",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "-H", "Accept: application/json, text/plain, */*",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    if result.returncode != 0 or not result.stdout:
        return {}
    return json.loads(result.stdout.decode('utf-8', errors='ignore'))


def _get_championships() -> List[Dict]:
    """Get list of football championships."""
    data = _curl_fetch("GetChampsZip", "sport=1&lng=en")
    return data.get("Value", [])


def _get_championship_games(champ_id: int) -> List[Dict]:
    """Get games for a championship (without odds)."""
    data = _curl_fetch("GetChampZip", f"champ={champ_id}&lng=en")
    value = data.get("Value", {})
    return value.get("G", []) if isinstance(value, dict) else []


def _get_games_with_odds(game_ids: List[int]) -> List[Dict]:
    """Fetch multiple games with odds."""
    if not game_ids:
        return []
    ids_str = ",".join(str(i) for i in game_ids[:50])  # Max 50 per request
    data = _curl_fetch("GetGamesZip", f"ids={ids_str}&lng=en")
    return data.get("Value", []) if isinstance(data.get("Value"), list) else []


def _parse_game(game: Dict, seen_ids: Set[int]) -> Dict:
    """Parse a game with odds into our match format."""
    event_id = game.get("I")
    if not event_id or event_id in seen_ids:
        return None

    home = game.get("O1") or game.get("O1E")
    away = game.get("O2") or game.get("O2E")
    odds = game.get("E", [])

    home_odds = draw_odds = away_odds = None
    for o in odds:
        ot = o.get("T")
        g = o.get("G")
        if g != 1:  # Only main 1X2 market (G=1)
            continue
        # T=1: Home (P1), T=2: Draw (X), T=3: Away (P2)
        if ot == 1:
            home_odds = o.get("C")
        elif ot == 2:
            draw_odds = o.get("C")  # T=2 is Draw, not Away!
        elif ot == 3:
            away_odds = o.get("C")  # T=3 is Away, not Draw!

    if not (home and away and home_odds and away_odds):
        return None

    # Validate odds are reasonable (detect malformed data)
    # Real 1X2 odds: home/draw/away should each be >= 1.01 and <= 50
    # Draw odds specifically should be >= 2.0 for real football matches
    home_odds = float(home_odds)
    away_odds = float(away_odds)
    draw_odds = float(draw_odds) if draw_odds else 0.0

    if home_odds < 1.01 or home_odds > 100:
        return None
    if away_odds < 1.01 or away_odds > 100:
        return None
    if draw_odds > 0 and (draw_odds < 2.0 or draw_odds > 50):
        # Draw odds < 2.0 indicates malformed data (not a real 1X2 market)
        return None

    seen_ids.add(event_id)
    return {
        "bookmaker": "22Bet Ghana",
        "event_id": event_id,
        "home_team": home,
        "away_team": away,
        "teams": f"{home} vs {away}",
        "home_odds": home_odds,
        "draw_odds": draw_odds,
        "away_odds": away_odds,
        "league": game.get("L", ""),
        "start_time": game.get("S", 0),
    }


def scrape_22bet_ghana(max_matches: int = DEFAULT_MAX_MATCHES) -> List[Dict]:
    max_matches = int(os.getenv("TWENTYTWOBET_MAX_MATCHES", max_matches))

    print("Fetching championships...")
    champs = _get_championships()
    # Sort by game count descending
    champs = sorted(champs, key=lambda x: x.get("GC", 0), reverse=True)
    print(f"Found {len(champs)} championships")

    matches: List[Dict] = []
    seen_ids: Set[int] = set()

    # Patterns that indicate fake/alternative matches (not real games)
    skip_patterns = ["alternative", "team vs player", "specials", "fantasy", "esports"]

    for champ in champs:
        if len(matches) >= max_matches:
            break

        champ_id = champ.get("LI")
        champ_name = champ.get("L", "Unknown")
        game_count = champ.get("GC", 0)

        if game_count == 0:
            continue

        # Skip fake/alternative championships
        if any(pattern in champ_name.lower() for pattern in skip_patterns):
            continue

        # Get games for this championship
        games = _get_championship_games(champ_id)
        if not games:
            continue

        # Get game IDs
        game_ids = [g.get("I") for g in games if g.get("I") and g.get("I") not in seen_ids]

        # Fetch games with odds in batches of 50
        for i in range(0, len(game_ids), 50):
            if len(matches) >= max_matches:
                break

            batch_ids = game_ids[i:i+50]
            games_with_odds = _get_games_with_odds(batch_ids)

            for game in games_with_odds:
                match = _parse_game(game, seen_ids)
                if match:
                    matches.append(match)

            time.sleep(0.02)  # Small delay between batches

        print(f"  {champ_name}: +{len([g for g in game_ids if g in seen_ids])} (total {len(matches)})")
        time.sleep(0.01)

    matches = matches[:max_matches]
    print(f"Found {len(matches)} matches on 22Bet")
    return matches


if __name__ == "__main__":
    data = scrape_22bet_ghana()
    for m in data[:5]:
        print(f"{m['teams']}: {m['home_odds']} / {m['draw_odds']} / {m['away_odds']}")
