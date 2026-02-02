#!/usr/bin/env python3
"""
Betfair Exchange odds scraper using the official Betting API (free tier).

Setup required:
1. Create a free Betfair account at betfair.com
2. Get a free Application Key at https://developer.betfair.com/
3. Set environment variables:
   - BETFAIR_USERNAME
   - BETFAIR_PASSWORD
   - BETFAIR_APP_KEY

The free (delayed) tier gives up to 20 req/sec with no charge.
Exchange odds are back-prices (best available to back at).
"""
import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

BETFAIR_LOGIN_URL = "https://identitysso.betfair.com/api/login"
BETFAIR_API_URL = "https://api.betfair.com/exchange/betting/rest/v1.0"
SOCCER_EVENT_TYPE_ID = "1"
MATCH_ODDS_MARKET = "MATCH_ODDS"
DEFAULT_MAX_MATCHES = 1200


def _login(username: str, password: str, app_key: str) -> Optional[str]:
    """Authenticate and return session token (SSOID)."""
    try:
        import requests
        resp = requests.post(
            BETFAIR_LOGIN_URL,
            data={"username": username, "password": password},
            headers={
                "X-Application": app_key,
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=15,
        )
        data = resp.json()
        if data.get("status") == "SUCCESS":
            return data.get("token")
        print(f"  [Betfair] Login failed: {data.get('error', 'unknown')}")
        return None
    except Exception as e:
        print(f"  [Betfair] Login error: {e}")
        return None


def _api_call(endpoint: str, params: dict, app_key: str, session_token: str) -> Optional[dict]:
    """Make an authenticated Betfair API call."""
    try:
        import requests
        url = f"{BETFAIR_API_URL}/{endpoint}/"
        resp = requests.post(
            url,
            json={"filter": params.get("filter", {}), **{k: v for k, v in params.items() if k != "filter"}},
            headers={
                "X-Application": app_key,
                "X-Authentication": session_token,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=25,
        )
        if resp.status_code != 200:
            print(f"  [Betfair] API {endpoint} error {resp.status_code}: {resp.text[:200]}")
            return None
        return resp.json()
    except Exception as e:
        print(f"  [Betfair] API error: {e}")
        return None


def _get_soccer_competitions(app_key: str, session_token: str) -> List[Dict]:
    """Get soccer competitions (leagues) with upcoming events."""
    data = _api_call(
        "listCompetitions",
        {
            "filter": {
                "eventTypeIds": [SOCCER_EVENT_TYPE_ID],
                "marketStartTime": {
                    "from": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "to": (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
            }
        },
        app_key,
        session_token,
    )
    return data if isinstance(data, list) else []


def _get_events(app_key: str, session_token: str, competition_ids: List[str] = None) -> List[Dict]:
    """Get soccer events (matches)."""
    filter_params = {
        "eventTypeIds": [SOCCER_EVENT_TYPE_ID],
        "marketStartTime": {
            "from": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to": (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "marketTypeCodes": [MATCH_ODDS_MARKET],
    }
    if competition_ids:
        filter_params["competitionIds"] = competition_ids

    data = _api_call(
        "listEvents",
        {"filter": filter_params},
        app_key,
        session_token,
    )
    return data if isinstance(data, list) else []


def _get_market_catalogues(
    app_key: str, session_token: str, event_ids: List[str], batch_size: int = 50
) -> List[Dict]:
    """Get Match Odds market catalogues for events (includes runner names)."""
    all_catalogues = []
    for i in range(0, len(event_ids), batch_size):
        chunk = event_ids[i:i + batch_size]
        data = _api_call(
            "listMarketCatalogue",
            {
                "filter": {
                    "eventTypeIds": [SOCCER_EVENT_TYPE_ID],
                    "eventIds": chunk,
                    "marketTypeCodes": [MATCH_ODDS_MARKET],
                },
                "maxResults": str(batch_size),
                "marketProjection": ["RUNNER_DESCRIPTION", "EVENT", "COMPETITION"],
            },
            app_key,
            session_token,
        )
        if data and isinstance(data, list):
            all_catalogues.extend(data)
        time.sleep(0.1)
    return all_catalogues


def _get_market_books(
    app_key: str, session_token: str, market_ids: List[str], batch_size: int = 40
) -> List[Dict]:
    """Get live exchange prices for markets."""
    all_books = []
    for i in range(0, len(market_ids), batch_size):
        chunk = market_ids[i:i + batch_size]
        data = _api_call(
            "listMarketBook",
            {
                "marketIds": chunk,
                "priceProjection": {"priceData": ["EX_BEST_OFFERS"]},
            },
            app_key,
            session_token,
        )
        if data and isinstance(data, list):
            all_books.extend(data)
        time.sleep(0.1)
    return all_books


def _parse_team_names(event_name: str):
    """Parse 'Team A v Team B' into (home, away)."""
    separators = [" v ", " vs ", " - "]
    for sep in separators:
        if sep in event_name:
            parts = event_name.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    return None, None


def scrape_betfair_exchange(max_matches: int = DEFAULT_MAX_MATCHES) -> List[Dict]:
    """
    Scrape Betfair Exchange soccer odds using the official API (free tier).
    Requires BETFAIR_USERNAME, BETFAIR_PASSWORD, and BETFAIR_APP_KEY env vars.
    """
    max_matches = int(os.getenv("BETFAIR_MAX_MATCHES", max_matches))
    username = os.getenv("BETFAIR_USERNAME", "")
    password = os.getenv("BETFAIR_PASSWORD", "")
    app_key = os.getenv("BETFAIR_APP_KEY", "")

    if not all([username, password, app_key]):
        print("  [Betfair] Missing credentials (BETFAIR_USERNAME, BETFAIR_PASSWORD, BETFAIR_APP_KEY). Skipping.")
        return []

    print("Scraping Betfair Exchange (official API)...")

    # Step 1: Login
    session_token = _login(username, password, app_key)
    if not session_token:
        return []
    print("  [Betfair] Authenticated successfully")

    # Step 2: Get events
    events = _get_events(app_key, session_token)
    if not events:
        print("  [Betfair] No soccer events found")
        return []
    print(f"  [Betfair] Found {len(events)} soccer events")

    # Build event info map
    event_info: Dict[str, Dict] = {}
    event_ids = []
    for ev_data in events[:max_matches]:
        ev = ev_data.get("event", {})
        ev_id = ev.get("id")
        if not ev_id:
            continue
        home, away = _parse_team_names(ev.get("name", ""))
        if not home or not away:
            continue
        start_time_str = ev.get("openDate", "")
        start_epoch = int(time.time()) + 3600
        if start_time_str:
            try:
                normalized = start_time_str.replace("Z", "+00:00")
                start_epoch = int(datetime.fromisoformat(normalized).timestamp())
            except Exception:
                pass
        event_info[ev_id] = {
            "home_team": home,
            "away_team": away,
            "start_time": start_epoch,
        }
        event_ids.append(ev_id)

    # Step 3: Get market catalogues (runner names + competition)
    catalogues = _get_market_catalogues(app_key, session_token, event_ids)
    if not catalogues:
        print("  [Betfair] No Match Odds markets found")
        return []
    print(f"  [Betfair] Found {len(catalogues)} Match Odds markets")

    # Build market -> event mapping and runner name lookup
    market_event_map: Dict[str, str] = {}
    market_runners: Dict[str, Dict[int, str]] = {}  # market_id -> {selection_id: name}
    market_competition: Dict[str, str] = {}
    market_ids = []
    for cat in catalogues:
        market_id = cat.get("marketId")
        event = cat.get("event", {})
        ev_id = event.get("id")
        competition = cat.get("competition", {})
        if not market_id or not ev_id:
            continue
        market_event_map[market_id] = ev_id
        market_competition[market_id] = competition.get("name", "Soccer")
        runners = {}
        for runner in cat.get("runners", []):
            sel_id = runner.get("selectionId")
            name = runner.get("runnerName", "")
            if sel_id and name:
                runners[sel_id] = name
        market_runners[market_id] = runners
        market_ids.append(market_id)

    # Step 4: Get live prices
    books = _get_market_books(app_key, session_token, market_ids)
    print(f"  [Betfair] Got prices for {len(books)} markets")

    # Step 5: Assemble results
    results: List[Dict] = []
    for book in books:
        market_id = book.get("marketId")
        if not market_id or market_id not in market_event_map:
            continue
        ev_id = market_event_map[market_id]
        info = event_info.get(ev_id)
        if not info:
            continue
        runners = market_runners.get(market_id, {})

        odds = {}
        for runner in book.get("runners", []):
            sel_id = runner.get("selectionId")
            runner_name = runners.get(sel_id, "")
            # Best back price (what you can bet at)
            ex = runner.get("ex", {})
            back_prices = ex.get("availableToBack", [])
            if not back_prices:
                continue
            best_back = back_prices[0].get("price", 0)
            if not best_back or best_back < 1.01:
                continue

            name_lower = runner_name.lower().strip()
            if name_lower == "the draw" or name_lower == "draw":
                odds["draw"] = float(best_back)
            elif runner_name == info["home_team"]:
                odds["home"] = float(best_back)
            elif runner_name == info["away_team"]:
                odds["away"] = float(best_back)
            else:
                # Fuzzy: first non-draw runner = home, second = away
                if "home" not in odds and name_lower != "draw" and name_lower != "the draw":
                    odds["home"] = float(best_back)
                    # Update team name from Betfair's naming
                    info["home_team"] = runner_name
                elif "away" not in odds and name_lower != "draw" and name_lower != "the draw":
                    odds["away"] = float(best_back)
                    info["away_team"] = runner_name

        if "home" in odds and "away" in odds:
            results.append({
                "bookmaker": "Betfair Exchange",
                "home_team": info["home_team"],
                "away_team": info["away_team"],
                "home_odds": odds["home"],
                "draw_odds": odds.get("draw", 0.0),
                "away_odds": odds["away"],
                "start_time": info["start_time"],
                "league": market_competition.get(market_id, "Soccer"),
                "event_id": f"betfair_{ev_id}",
            })

    print(f"  [Betfair] Scraped {len(results)} matches with exchange odds")
    return results


if __name__ == "__main__":
    if not all([os.getenv("BETFAIR_USERNAME"), os.getenv("BETFAIR_PASSWORD"), os.getenv("BETFAIR_APP_KEY")]):
        print("Set BETFAIR_USERNAME, BETFAIR_PASSWORD, and BETFAIR_APP_KEY to test.")
    else:
        matches = scrape_betfair_exchange(max_matches=20)
        if matches:
            print(f"\n--- Betfair Exchange ({len(matches)} matches) ---")
            for m in matches[:5]:
                print(json.dumps(m, indent=2))
        else:
            print("\nNo matches returned from Betfair Exchange scraper.")
