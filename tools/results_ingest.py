#!/usr/bin/env python3
"""
Ingest final soccer results from ESPN scoreboard into a local SQLite DB.
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional

import requests
from dateutil.parser import isoparse

from tools.team_normalization import normalize_team

ESPN_SCOREBOARD_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"

LEAGUE_CONFIG = {
    "premier": {"id": "eng.1", "name": "Premier League"},
    "laliga": {"id": "esp.1", "name": "La Liga"},
    "seriea": {"id": "ita.1", "name": "Serie A"},
    "bundesliga": {"id": "ger.1", "name": "Bundesliga"},
    "ligue1": {"id": "fra.1", "name": "Ligue 1"},
    "ucl": {"id": "uefa.champions", "name": "UEFA Champions League"},
}


def resolve_db_path(path: Optional[str]) -> str:
    return path or "data/results.db"


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS results (
            event_id TEXT PRIMARY KEY,
            league_key TEXT,
            league_id TEXT,
            league_name TEXT,
            start_time INTEGER,
            event_date TEXT,
            home_team_raw TEXT,
            away_team_raw TEXT,
            home_team_norm TEXT,
            away_team_norm TEXT,
            home_score INTEGER,
            away_score INTEGER,
            status TEXT,
            completed INTEGER,
            updated_at TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_results_event_date ON results(event_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_results_start ON results(start_time)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_results_norm ON results(home_team_norm, away_team_norm)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_results_completed ON results(completed)")


def fetch_scoreboard(league_id: str, start: datetime, end: datetime) -> Dict:
    params = {"dates": f"{start:%Y%m%d}-{end:%Y%m%d}"}
    url = f"{ESPN_SCOREBOARD_BASE}/{league_id}/scoreboard"
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def parse_events(payload: Dict, league_key: str, league_meta: Dict) -> List[Dict]:
    events = []
    for event in payload.get("events", []) or []:
        competitions = event.get("competitions") or []
        competition = competitions[0] if competitions else {}
        competitors = competition.get("competitors") or []
        if len(competitors) < 2:
            continue

        status = competition.get("status") or event.get("status") or {}
        status_type = status.get("type") or {}
        state = status_type.get("state") or status_type.get("name") or ""
        completed = bool(status_type.get("completed") or state == "post")

        home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[-1])

        home_team = (home.get("team") or {}).get("displayName") or (home.get("team") or {}).get("name") or ""
        away_team = (away.get("team") or {}).get("displayName") or (away.get("team") or {}).get("name") or ""
        start_time_str = competition.get("date") or event.get("date")
        if not start_time_str:
            continue
        start_dt = isoparse(start_time_str)
        start_time = int(start_dt.timestamp())
        event_date = start_dt.date().isoformat()

        home_score = home.get("score")
        away_score = away.get("score")
        try:
            home_score = int(float(home_score)) if home_score is not None else None
        except (TypeError, ValueError):
            home_score = None
        try:
            away_score = int(float(away_score)) if away_score is not None else None
        except (TypeError, ValueError):
            away_score = None

        events.append(
            {
                "event_id": event.get("id"),
                "league_key": league_key,
                "league_id": league_meta["id"],
                "league_name": league_meta["name"],
                "start_time": start_time,
                "event_date": event_date,
                "home_team_raw": home_team,
                "away_team_raw": away_team,
                "home_team_norm": normalize_team(home_team),
                "away_team_norm": normalize_team(away_team),
                "home_score": home_score,
                "away_score": away_score,
                "status": state,
                "completed": 1 if completed else 0,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    return events


def insert_results(conn: sqlite3.Connection, rows: Iterable[Dict]) -> int:
    rows = list(rows)
    if not rows:
        return 0
    conn.executemany(
        """
        INSERT OR REPLACE INTO results (
            event_id,
            league_key,
            league_id,
            league_name,
            start_time,
            event_date,
            home_team_raw,
            away_team_raw,
            home_team_norm,
            away_team_norm,
            home_score,
            away_score,
            status,
            completed,
            updated_at
        ) VALUES (
            :event_id,
            :league_key,
            :league_id,
            :league_name,
            :start_time,
            :event_date,
            :home_team_raw,
            :away_team_raw,
            :home_team_norm,
            :away_team_norm,
            :home_score,
            :away_score,
            :status,
            :completed,
            :updated_at
        )
        """,
        rows,
    )
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest ESPN final scores into SQLite.")
    parser.add_argument("--db", default=None, help="SQLite DB path (default: data/results.db)")
    parser.add_argument("--days-back", type=int, default=14, help="Days back from today to fetch")
    parser.add_argument("--days-forward", type=int, default=1, help="Days forward to include (0 for none)")
    parser.add_argument("--league", action="append", help="Limit to league key(s), e.g. premier")
    args = parser.parse_args()

    db_path = resolve_db_path(args.db)
    start = datetime.now(timezone.utc).date() - timedelta(days=args.days_back)
    end = datetime.now(timezone.utc).date() + timedelta(days=args.days_forward)

    leagues = LEAGUE_CONFIG
    if args.league:
        leagues = {k: v for k, v in LEAGUE_CONFIG.items() if k in set(args.league)}

    conn = sqlite3.connect(db_path)
    try:
        init_db(conn)
        total = 0
        for league_key, meta in leagues.items():
            payload = fetch_scoreboard(meta["id"], start, end)
            rows = parse_events(payload, league_key, meta)
            inserted = insert_results(conn, rows)
            total += inserted
            print(f"{meta['name']}: {inserted} events ingested")
        conn.commit()
    finally:
        conn.close()

    print(f"Done. Stored {total} events in {db_path}")


if __name__ == "__main__":
    main()
