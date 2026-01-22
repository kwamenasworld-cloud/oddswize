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
DEFAULT_MAX_MATCHES = 1200
PAGE_SIZE = int(os.getenv("TWENTYTWOBET_PAGE_SIZE", "100"))  # max observed per request

MAJOR_LEAGUE_KEYWORDS = {
    "premier": ["premier league", "english premier league", "england premier league", "epl"],
    "laliga": ["la liga", "laliga", "primera division"],
    "seriea": ["serie a"],
    "bundesliga": ["bundesliga"],
    "ligue1": ["ligue 1"],
    "ucl": ["uefa champions league", "champions league", "ucl"],
}

MAJOR_LEAGUE_EXCLUSIONS = {
    "premier league cup",
    "premier league 2",
    "premier league u21",
    "premier league u 21",
    "premier league u-21",
}

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


def _is_major_league(name: str) -> bool:
    if not name:
        return False
    lowered = name.lower()
    if any(ex in lowered for ex in MAJOR_LEAGUE_EXCLUSIONS):
        return False
    return any(any(k in lowered for k in keywords) for keywords in MAJOR_LEAGUE_KEYWORDS.values())


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


def _fetch_league_list() -> List[Dict]:
    """Fetch the league catalog so we can target specific major leagues."""
    leagues: List[Dict] = []
    page = 1
    limit = 500
    while True:
        params = [
            ("lang", "en"),
            ("sportId_eq", 1),
            ("limit", limit),
            ("page", page),
        ]
        resp = SESSION.get(f"{API_BASE}/league/list", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        items = data.get("leagues", []) if isinstance(data, dict) else []
        if not items:
            break
        leagues.extend(items)
        if len(items) < limit:
            break
        page += 1
        if page > 5:
            break
    return leagues


def _match_major_league_ids(leagues: List[Dict]) -> Set[int]:
    ids: Set[int] = set()
    for league in leagues:
        name = (league.get("name") or "").lower()
        if not name:
            continue
        if any(ex in name for ex in MAJOR_LEAGUE_EXCLUSIONS):
            continue
        for keywords in MAJOR_LEAGUE_KEYWORDS.values():
            if any(k in name for k in keywords):
                league_id = league.get("id")
                if league_id:
                    ids.add(int(league_id))
    return ids


def _fetch_league_page(league_id: int, page: int, limit: int) -> Dict:
    params = [
        ("lang", "en"),
        ("oddsExists_eq", 1),
        ("main", 1),
        ("period", 0),
        ("sportId_eq", 1),
        ("limit", limit),
        ("status_in", 0),
        ("oddsBooster", 0),
        ("isFavorite", 0),
        ("isLive", "false"),
        ("page", page),
        ("leagueId_eq", league_id),
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

    force_major = os.getenv("TWENTYTWOBET_FORCE_LEAGUES", "1").strip().lower() not in {"0", "false", "no"}
    league_pages = int(os.getenv("TWENTYTWOBET_LEAGUE_PAGES", "6"))

    if force_major:
        try:
            leagues = _fetch_league_list()
            league_ids = _match_major_league_ids(leagues)
        except Exception:
            league_ids = set()

        for league_id in sorted(league_ids):
            page = 1
            total_pages = None
            while page <= max(1, league_pages):
                data = _fetch_league_page(league_id, page, PAGE_SIZE)
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

    major_first = [m for m in matches if _is_major_league(m.get("league", ""))]
    other = [m for m in matches if not _is_major_league(m.get("league", ""))]
    return (major_first + other)[:max_matches]


if __name__ == "__main__":
    results = scrape_22bet_ghana()
    print(f"Fetched {len(results)} matches from 22Bet Ghana")
    for m in results[:5]:
        print(f"{m['teams']}: {m['home_odds']} / {m['draw_odds']} / {m['away_odds']}")
