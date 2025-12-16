#!/usr/bin/env python3
"""22Bet Ghana Odds Scraper (platform API).

Fetch prematch football events and odds from platform.22bet.com.gh.
"""

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

import requests

# API and scraping controls
API_BASE = os.getenv("TWENTYTWOBET_API_URL", "https://platform.22bet.com.gh/api")
DEFAULT_MAX_MATCHES = 800
PAGE_SIZE = 100  # max observed per request

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
    }
)


def _parse_start_time(time_str: Optional[str]) -> int:
    """Convert 'YYYY-MM-DD HH:MM:SS' to epoch seconds."""
    if not time_str:
        return 0
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return int(dt.replace(tzinfo=timezone.utc).timestamp())
    except Exception:
        return 0


def _find_main_market(odds_list: List[Dict]) -> Optional[Dict]:
    """Pick the main 1X2 market (vendorMarketId=1, 3 outcomes, no specifiers)."""
    for market in odds_list:
        if market.get("vendorMarketId") != 1:
            continue
        outcomes = market.get("outcomes", [])
        if len(outcomes) != 3:
            continue
        if market.get("specifiers"):
            continue
        return market
    return None


def _extract_odds(market: Dict) -> Optional[Dict]:
    """Extract home/draw/away odds from a market."""
    outcomes = market.get("outcomes", [])
    if len(outcomes) != 3:
        return None

    by_vendor = {str(o.get("vendorOutcomeId")): o for o in outcomes}
    home = by_vendor.get("1") or outcomes[0]
    draw = by_vendor.get("2") or outcomes[1]
    away = by_vendor.get("3") or outcomes[2]

    try:
        home_odds = float(home.get("odds"))
        draw_odds = float(draw.get("odds"))
        away_odds = float(away.get("odds"))
    except Exception:
        return None

    if min(home_odds, draw_odds, away_odds) < 1.01 or max(home_odds, draw_odds, away_odds) > 100:
        return None

    return {
        "home_odds": home_odds,
        "draw_odds": draw_odds,
        "away_odds": away_odds,
    }


def _fetch_page(page: int, limit: int) -> Dict:
    """Fetch a single page of football prematch events with odds."""
    params = [
        ("lang", "en"),
        ("oddsExists_eq", 1),
        ("main", 1),
        ("period", 0),  # prematch
        ("sportId_eq", 1),  # football
        ("limit", limit),
        ("status_in", 0),
        ("oddsBooster", 0),
        ("isFavorite", 0),
        ("isLive", "false"),
        ("page", page),
    ]
    for rel in ["odds", "withMarketsCount", "league", "competitors"]:
        params.append(("relations", rel))

    resp = SESSION.get(f"{API_BASE}/event/list", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("data", {})


def _parse_events(data: Dict, seen_ids: Set[int]) -> List[Dict]:
    """Parse events block into our match format."""
    items = data.get("items", [])
    relations = data.get("relations", {})
    competitors = {c["id"]: c for c in relations.get("competitors", []) if "id" in c}
    leagues = {l["id"]: l.get("name", "") for l in relations.get("league", []) if "id" in l}
    odds_map = relations.get("odds", {}) or {}

    parsed: List[Dict] = []
    for event in items:
        event_id = event.get("id")
        if not event_id or event_id in seen_ids:
            continue

        odds_list = odds_map.get(str(event_id)) or odds_map.get(event_id) or []
        main_market = _find_main_market(odds_list)
        if not main_market:
            continue

        odds = _extract_odds(main_market)
        if not odds:
            continue

        home = competitors.get(event.get("competitor1Id"), {}).get("name") or event.get("team1") or ""
        away = competitors.get(event.get("competitor2Id"), {}).get("name") or event.get("team2") or ""
        if not home or not away:
            continue

        start_time = _parse_start_time(event.get("time"))
        match = {
            "bookmaker": "22Bet Ghana",
            "event_id": event_id,
            "home_team": home,
            "away_team": away,
            "teams": f"{home} vs {away}",
            "league": leagues.get(event.get("leagueId"), ""),
            "start_time": start_time,
            **odds,
        }
        seen_ids.add(event_id)
        parsed.append(match)

    return parsed


def scrape_22bet_ghana(max_matches: int = DEFAULT_MAX_MATCHES) -> List[Dict]:
    max_matches = int(os.getenv("TWENTYTWOBET_MAX_MATCHES", max_matches))
    matches: List[Dict] = []
    seen_ids: Set[int] = set()

    page = 1
    total_pages = None

    while len(matches) < max_matches:
        data = _fetch_page(page, min(PAGE_SIZE, max_matches))
        items = data.get("items", [])
        if not items:
            break

        matches.extend(_parse_events(data, seen_ids))

        total = data.get("totalCount")
        limit = data.get("limit") or PAGE_SIZE
        if total and limit:
            total_pages = max(total_pages or 0, (total + limit - 1) // limit)

        page += 1
        if total_pages and page > total_pages:
            break

    return matches[:max_matches]


if __name__ == "__main__":
    results = scrape_22bet_ghana()
    print(f"Fetched {len(results)} matches from 22Bet Ghana")
    for m in results[:5]:
        print(f"{m['teams']}: {m['home_odds']} / {m['draw_odds']} / {m['away_odds']}")
