#!/usr/bin/env python3
"""Betfox Ghana Odds Scraper (API-based).

Uses the fixtures/home/upcoming endpoint with embedded markets.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

import cloudscraper

API_URL = os.getenv(
    "BETFOX_API_URL",
    "https://www.betfox.com.gh/api/offer/v4/fixtures/home/upcoming",
)
DEFAULT_MAX_MATCHES = 800
DEFAULT_FIRST = 1000
TIMEOUT_SECONDS = 20


def _build_scraper() -> cloudscraper.CloudScraper:
    scraper = cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "windows",
            "desktop": True,
        }
    )
    scraper.headers.update(
        {
            "Accept": "application/json",
            "Referer": "https://www.betfox.com.gh/sportsbook",
            "x-betr-brand": "betfox.com.gh",
            "x-locale": "en",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        }
    )
    return scraper


def _parse_start_time(value: Optional[str]) -> int:
    if not value:
        return 0
    try:
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
    except Exception:
        return 0


def _extract_teams(fixture: Dict) -> Tuple[str, str]:
    competitors = fixture.get("competitors") or fixture.get("participants") or []
    if len(competitors) >= 2:
        home = competitors[0].get("name", "") or ""
        away = competitors[1].get("name", "") or ""
        return home, away

    home = (
        fixture.get("home", {}).get("name")
        or fixture.get("homeTeam", {}).get("name")
        or ""
    )
    away = (
        fixture.get("away", {}).get("name")
        or fixture.get("awayTeam", {}).get("name")
        or ""
    )
    return home, away


def _extract_odds(markets: List[Dict]) -> Optional[Dict]:
    winner_market = None
    for market in markets:
        if market.get("type") == "FOOTBALL_WINNER":
            winner_market = market
            break
    if not winner_market:
        return None

    home_odds = draw_odds = away_odds = None
    for outcome in winner_market.get("outcomes", []):
        odds_value = outcome.get("odds")
        outcome_type = (outcome.get("value") or "").upper()
        if not odds_value:
            continue
        try:
            odds = float(odds_value)
        except (ValueError, TypeError):
            continue

        if outcome_type == "HOME":
            home_odds = odds
        elif outcome_type == "DRAW":
            draw_odds = odds
        elif outcome_type == "AWAY":
            away_odds = odds

    if not home_odds or not away_odds:
        return None

    if home_odds < 1.01 or home_odds > 100:
        return None
    if away_odds < 1.01 or away_odds > 100:
        return None
    if draw_odds and (draw_odds < 2.0 or draw_odds > 100):
        return None

    return {
        "home_odds": home_odds,
        "draw_odds": draw_odds or 0.0,
        "away_odds": away_odds,
    }


def scrape_betfox_ghana(max_matches: int = DEFAULT_MAX_MATCHES) -> List[Dict]:
    max_matches = int(os.getenv("BETFOX_MAX_MATCHES", max_matches))

    print("Scraping Betfox Ghana API...")
    scraper = _build_scraper()

    first = min(max_matches, DEFAULT_FIRST)
    url = f"{API_URL}?first={first}&sport=Football"

    try:
        resp = scraper.get(url, timeout=TIMEOUT_SECONDS)
        if resp.status_code != 200:
            print(f"  Error: HTTP {resp.status_code}")
            return []

        data = resp.json()
        fixtures = data.get("data", []) if isinstance(data, dict) else []
    except Exception as e:
        print(f"  Error: {e}")
        return []

    matches: List[Dict] = []
    seen_ids: Set[str] = set()

    for fixture in fixtures:
        if len(matches) >= max_matches:
            break

        try:
            event_id = fixture.get("id")
            if not event_id or event_id in seen_ids:
                continue

            home, away = _extract_teams(fixture)
            if not home or not away:
                continue

            odds = _extract_odds(fixture.get("markets", []))
            if not odds:
                continue

            competition = fixture.get("competition", {}) or {}
            category = fixture.get("category", {}) or {}
            league_name = (competition.get("name") or "").strip()
            country_name = (category.get("name") or "").strip()
            if league_name and country_name:
                league = f"{country_name}. {league_name}"
            else:
                league = league_name or country_name

            match = {
                "bookmaker": "Betfox Ghana",
                "event_id": event_id,
                "home_team": home,
                "away_team": away,
                "teams": f"{home} vs {away}",
                "league": league,
                "start_time": _parse_start_time(fixture.get("startTime")),
                **odds,
            }

            seen_ids.add(event_id)
            matches.append(match)
        except Exception:
            continue

    print(f"Found {len(matches)} matches on Betfox")
    return matches[:max_matches]


if __name__ == "__main__":
    data = scrape_betfox_ghana()
    for m in data[:5]:
        print(f"{m['teams']}: {m['home_odds']} / {m['draw_odds']} / {m['away_odds']}")
