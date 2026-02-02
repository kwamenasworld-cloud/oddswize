#!/usr/bin/env python3
"""
Direct Pinnacle odds scraper using the public guest API.
No API key required - this is the same data Pinnacle's website loads.

Base URL: https://guest.api.arcadia.pinnacle.com/0.1
Endpoints:
  - /sports/{id}/leagues?all=false  -> list active leagues
  - /leagues/{id}/matchups          -> matchups for a league
  - /leagues/{id}/markets/straight  -> odds for a league's matchups
"""
import json
import os
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Optional

PINNACLE_BASE = os.getenv(
    "PINNACLE_API_BASE",
    "https://guest.api.arcadia.pinnacle.com/0.1",
)
SPORT_ID = 29  # Soccer
DEFAULT_MAX_MATCHES = 12000

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Referer": "https://www.pinnacle.com/",
    "Origin": "https://www.pinnacle.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "X-Device-UUID": "undefined",
    "X-Api-Key": "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R",
}


def _american_to_decimal(american: float) -> float:
    """Convert American odds to decimal odds."""
    if american >= 100:
        return round((american / 100) + 1, 4)
    elif american <= -100:
        return round((100 / abs(american)) + 1, 4)
    else:
        # Edge case: odds between -100 and +100 shouldn't exist
        # but handle gracefully
        return round(abs(american / 100) + 1, 4)


def _curl_get(url: str, timeout: int = 20) -> Optional[list]:
    """Use curl subprocess for TLS fingerprint compatibility."""
    header_args = []
    for k, v in HEADERS.items():
        header_args += ["-H", f"{k}: {v}"]
    cmd = [
        "curl", "-s", "--max-time", str(timeout),
        "--compressed",
    ] + header_args + [url]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        if result.returncode != 0 or not result.stdout.strip():
            return None
        return json.loads(result.stdout)
    except Exception as e:
        print(f"  [Pinnacle] curl error: {e}")
        return None


def _requests_get(url: str, timeout: int = 20) -> Optional[list]:
    """Fallback using requests library."""
    try:
        import requests as req
        resp = req.get(url, headers=HEADERS, timeout=timeout)
        if resp.status_code == 204:
            return []  # No content = empty result
        if resp.status_code != 200:
            print(f"  [Pinnacle] HTTP {resp.status_code} for {url}")
            return None
        return resp.json()
    except Exception as e:
        print(f"  [Pinnacle] requests error: {e}")
        return None


def _fetch_json(url: str, timeout: int = 20) -> Optional[list]:
    """Try curl first, fall back to requests."""
    data = _curl_get(url, timeout)
    if data is not None:
        return data
    return _requests_get(url, timeout)


def _fetch_leagues() -> List[Dict]:
    """Get all active soccer leagues from Pinnacle."""
    url = f"{PINNACLE_BASE}/sports/{SPORT_ID}/leagues?all=false"
    data = _fetch_json(url)
    if not data or not isinstance(data, list):
        return []
    return [lg for lg in data if lg.get("id") and lg.get("matchupCount", 0) > 0]


def _fetch_league_matchups(league_id: int) -> List[Dict]:
    """Fetch matchups for a single league."""
    url = f"{PINNACLE_BASE}/leagues/{league_id}/matchups"
    data = _fetch_json(url, timeout=25)
    if data and isinstance(data, list):
        return data
    return []


def _fetch_league_odds(league_id: int) -> List[Dict]:
    """Fetch straight market odds for a single league."""
    url = f"{PINNACLE_BASE}/leagues/{league_id}/markets/straight"
    data = _fetch_json(url, timeout=25)
    if data and isinstance(data, list):
        return data
    return []


def _parse_start_time(start_time_str: str) -> int:
    """Parse ISO datetime string to epoch seconds."""
    if not start_time_str:
        return int(time.time()) + 3600
    try:
        normalized = start_time_str.replace("Z", "+00:00")
        return int(datetime.fromisoformat(normalized).timestamp())
    except Exception:
        return int(time.time()) + 3600


def scrape_pinnacle(max_matches: int = DEFAULT_MAX_MATCHES) -> List[Dict]:
    """
    Scrape Pinnacle soccer odds directly from their public guest API.
    No API key required.
    """
    max_matches = int(os.getenv("PINNACLE_MAX_MATCHES", max_matches))
    print("Scraping Pinnacle (direct guest API)...")

    # Step 1: Get leagues
    leagues = _fetch_leagues()
    if not leagues:
        print("  [Pinnacle] No leagues found")
        return []
    print(f"  [Pinnacle] Found {len(leagues)} active soccer leagues")

    # Step 2 + 3: For each league, fetch matchups and odds together
    # Build matchup info and odds in one pass per league
    matchup_info: Dict[int, Dict] = {}
    odds_map: Dict[int, Dict] = {}

    for lg in leagues:
        league_id = lg["id"]
        league_name = lg.get("name", "Soccer")

        # Fetch matchups
        matchups = _fetch_league_matchups(league_id)
        if not matchups:
            continue

        for mu in matchups:
            mu_id = mu.get("id")
            participants = mu.get("participants", [])
            if not mu_id or len(participants) < 2:
                continue
            if mu.get("type") != "matchup":
                continue
            # Skip live matches
            if mu.get("isLive"):
                continue

            home = next((p for p in participants if p.get("alignment") == "home"), None)
            away = next((p for p in participants if p.get("alignment") == "away"), None)
            if not home or not away:
                continue

            matchup_info[mu_id] = {
                "home_team": home.get("name", ""),
                "away_team": away.get("name", ""),
                "start_time": _parse_start_time(mu.get("startTime", "")),
                "league": league_name,
            }

        # Fetch odds for this league
        markets = _fetch_league_odds(league_id)
        for market in markets:
            matchup_id = market.get("matchupId")
            if not matchup_id:
                continue
            # Only full-match moneyline (period=0, type=moneyline, not alternate)
            if market.get("type") != "moneyline" or market.get("period") != 0:
                continue
            if market.get("isAlternate"):
                continue
            prices = market.get("prices", [])
            if not prices:
                continue

            parsed = {}
            for price in prices:
                designation = price.get("designation")  # home, away, draw
                american_price = price.get("price")
                if designation and american_price is not None:
                    decimal = _american_to_decimal(float(american_price))
                    parsed[designation] = decimal

            # Validate odds are in sane range
            home_ok = 1.01 <= parsed.get("home", 0) <= 100
            away_ok = 1.01 <= parsed.get("away", 0) <= 100
            draw_val = parsed.get("draw", 0)
            draw_ok = draw_val == 0 or 1.5 <= draw_val <= 50

            if home_ok and away_ok and draw_ok:
                odds_map[matchup_id] = parsed

        time.sleep(0.02)

        if len(matchup_info) >= max_matches:
            break

    print(f"  [Pinnacle] Found {len(matchup_info)} matchups, {len(odds_map)} with odds")

    # Step 4: Combine matchup info with odds
    results: List[Dict] = []
    for mu_id, info in matchup_info.items():
        odds = odds_map.get(mu_id)
        if not odds:
            continue
        results.append({
            "bookmaker": "Pinnacle",
            "home_team": info["home_team"],
            "away_team": info["away_team"],
            "home_odds": odds.get("home", 0.0),
            "draw_odds": odds.get("draw", 0.0),
            "away_odds": odds.get("away", 0.0),
            "start_time": info["start_time"],
            "league": info["league"],
            "event_id": f"pinnacle_{mu_id}",
        })

    print(f"  [Pinnacle] Scraped {len(results)} matches with odds")
    return results


if __name__ == "__main__":
    matches = scrape_pinnacle(max_matches=20)
    if matches:
        print(f"\n--- Pinnacle Direct Scrape ({len(matches)} matches) ---")
        for m in matches[:5]:
            print(json.dumps(m, indent=2))
    else:
        print("\nNo matches returned from Pinnacle scraper.")
