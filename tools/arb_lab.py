import json
import os
import re
import sqlite3
from datetime import date, datetime, timezone
from typing import Dict, Iterable, Optional, Tuple

try:
    import numpy as np
    import pandas as pd
except ImportError as exc:
    raise SystemExit(
        "Missing analytics dependencies. Install with: "
        "pip install -r requirements.analytics.txt"
    ) from exc


DEFAULT_DB_PATH = os.getenv("HISTORY_DB_PATH", os.path.join("data", "odds_history.db"))
DEFAULT_HISTORY_JSONL = os.getenv("HISTORY_MATCHED_FILE", os.path.join("data", "odds_history.jsonl"))
DEFAULT_RESULTS_DB_PATH = os.getenv("RESULTS_DB_PATH", os.path.join("data", "results.db"))


def _slugify_simple(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def _build_fixture_id(match: Dict) -> str:
    home = _slugify_simple(match.get("home_team", ""))
    away = _slugify_simple(match.get("away_team", ""))
    start = int(match.get("start_time") or 0)
    if home and away:
        return f"{home}-vs-{away}-{start}"
    return f"match-{start}"


def resolve_db_path(path: Optional[str] = None) -> str:
    candidate = path or DEFAULT_DB_PATH
    return os.path.abspath(candidate) if candidate else ""


def resolve_history_jsonl(path: Optional[str] = None) -> str:
    candidate = path or DEFAULT_HISTORY_JSONL
    return os.path.abspath(candidate) if candidate else ""


def resolve_results_db_path(path: Optional[str] = None) -> str:
    candidate = path or DEFAULT_RESULTS_DB_PATH
    return os.path.abspath(candidate) if candidate else ""


def init_history_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            last_updated TEXT,
            total_scraped INTEGER,
            matched_events INTEGER,
            scrape_time_seconds REAL,
            fast_mode INTEGER,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS matches (
            run_id TEXT,
            match_id TEXT,
            league TEXT,
            start_time INTEGER,
            home_team TEXT,
            away_team TEXT,
            PRIMARY KEY (run_id, match_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS odds (
            run_id TEXT,
            match_id TEXT,
            bookmaker TEXT,
            home_odds REAL,
            draw_odds REAL,
            away_odds REAL,
            event_id TEXT,
            event_league_id TEXT,
            PRIMARY KEY (run_id, match_id, bookmaker)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_league ON matches(league)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_start ON matches(start_time)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_odds_bookie ON odds(bookmaker)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_updated ON runs(last_updated)")

    cols = {row[1] for row in conn.execute("PRAGMA table_info(odds)").fetchall()}
    if "event_id" not in cols:
        conn.execute("ALTER TABLE odds ADD COLUMN event_id TEXT")
    if "event_league_id" not in cols:
        conn.execute("ALTER TABLE odds ADD COLUMN event_league_id TEXT")


def rows_from_odds_payload(payload: Dict) -> pd.DataFrame:
    if not payload:
        return pd.DataFrame()

    def _coerce_start_time(value: Optional[object]) -> int:
        if value is None:
            return 0
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return 0
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return int(parsed.timestamp())
        return 0

    meta = payload.get("meta") or {}
    last_updated = (
        payload.get("last_updated")
        or meta.get("last_updated")
        or datetime.now(timezone.utc).isoformat()
    )
    run_id = payload.get("run_id") or last_updated
    rows = []

    if payload.get("matches"):
        for match in payload.get("matches", []) or []:
            start_time = _coerce_start_time(match.get("start_time") or match.get("kickoff"))
            match_id = match.get("match_id") or match.get("id") or _build_fixture_id({
                "home_team": match.get("home_team"),
                "away_team": match.get("away_team"),
                "start_time": start_time,
            })
            for odds in match.get("odds", []) or []:
                rows.append({
                    "run_id": run_id,
                    "last_updated": last_updated,
                    "match_id": match_id,
                    "league": match.get("league"),
                    "start_time": start_time,
                    "home_team": match.get("home_team"),
                    "away_team": match.get("away_team"),
                    "bookmaker": odds.get("bookmaker"),
                    "event_id": odds.get("event_id"),
                    "event_league_id": odds.get("event_league_id") or odds.get("league_id"),
                    "home_odds": odds.get("home_odds"),
                    "draw_odds": odds.get("draw_odds"),
                    "away_odds": odds.get("away_odds"),
                })
        return pd.DataFrame(rows)

    for league in payload.get("data", []) or []:
        league_name = league.get("league") or league.get("name") or ""
        for match in league.get("matches", []) or []:
            start_time = _coerce_start_time(match.get("start_time") or match.get("kickoff"))
            match_id = match.get("match_id") or match.get("id") or _build_fixture_id({
                "home_team": match.get("home_team"),
                "away_team": match.get("away_team"),
                "start_time": start_time,
            })
            for odds in match.get("odds", []) or []:
                rows.append({
                    "run_id": run_id,
                    "last_updated": last_updated,
                    "match_id": match_id,
                    "league": match.get("league") or league_name,
                    "start_time": start_time,
                    "home_team": match.get("home_team"),
                    "away_team": match.get("away_team"),
                    "bookmaker": odds.get("bookmaker"),
                    "event_id": odds.get("event_id"),
                    "event_league_id": odds.get("event_league_id") or odds.get("league_id"),
                    "home_odds": odds.get("home_odds"),
                    "draw_odds": odds.get("draw_odds"),
                    "away_odds": odds.get("away_odds"),
                })

    return pd.DataFrame(rows)


def append_snapshot_to_history_jsonl(payload: Dict, path: Optional[str] = None) -> None:
    if not payload:
        return
    target = os.path.abspath(path or DEFAULT_HISTORY_JSONL)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    record = dict(payload)
    if not record.get("run_id"):
        record["run_id"] = record.get("last_updated") or datetime.now(timezone.utc).isoformat()
    with open(target, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def append_snapshot_to_history_db(payload: Dict, db_path: Optional[str] = None) -> None:
    if not payload:
        return
    path = resolve_db_path(db_path)
    if not path:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    run_id = payload.get("run_id") or payload.get("last_updated") or datetime.now(timezone.utc).isoformat()
    stats = payload.get("stats", {}) or {}

    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        init_history_db(conn)
        conn.execute(
            """
            INSERT OR REPLACE INTO runs (
                run_id, last_updated, total_scraped, matched_events, scrape_time_seconds,
                fast_mode, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                payload.get("last_updated"),
                stats.get("total_scraped"),
                stats.get("matched_events"),
                stats.get("scrape_time_seconds"),
                0,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        match_rows = []
        odds_rows = []
        for match in payload.get("matches", []) or []:
            match_id = match.get("match_id") or _build_fixture_id(match)
            match_rows.append((
                run_id,
                match_id,
                match.get("league", ""),
                int(match.get("start_time") or 0),
                match.get("home_team", ""),
                match.get("away_team", ""),
            ))
            for odds in match.get("odds", []) or []:
                odds_rows.append((
                    run_id,
                    match_id,
                    odds.get("bookmaker", ""),
                    odds.get("home_odds"),
                    odds.get("draw_odds"),
                    odds.get("away_odds"),
                    odds.get("event_id"),
                    odds.get("event_league_id") or odds.get("league_id"),
                ))

        if match_rows:
            conn.executemany(
                "INSERT OR REPLACE INTO matches (run_id, match_id, league, start_time, home_team, away_team)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                match_rows,
            )
        if odds_rows:
            conn.executemany(
                "INSERT OR REPLACE INTO odds "
                "(run_id, match_id, bookmaker, home_odds, draw_odds, away_odds, event_id, event_league_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                odds_rows,
            )
        conn.commit()
    finally:
        conn.close()


def history_run_exists(db_path: Optional[str], run_id: str) -> bool:
    if not run_id:
        return False
    path = resolve_db_path(db_path)
    if not path or not os.path.exists(path):
        return False
    conn = sqlite3.connect(path)
    try:
        init_history_db(conn)
        row = conn.execute("SELECT 1 FROM runs WHERE run_id = ? LIMIT 1", (run_id,)).fetchone()
        return row is not None
    finally:
        conn.close()


def last_jsonl_run_id(path: Optional[str]) -> Optional[str]:
    target = os.path.abspath(path or DEFAULT_HISTORY_JSONL)
    if not target or not os.path.exists(target):
        return None
    last_line = None
    with open(target, "rb") as handle:
        try:
            handle.seek(-2, os.SEEK_END)
            while handle.read(1) != b"\n":
                handle.seek(-2, os.SEEK_CUR)
        except OSError:
            handle.seek(0)
        last_line = handle.readline().decode("utf-8", errors="ignore").strip()
    if not last_line:
        return None
    try:
        record = json.loads(last_line)
    except json.JSONDecodeError:
        return None
    return record.get("run_id") or record.get("last_updated")


def _to_iso(value: Optional[object], end_of_day: bool = False) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime.combine(value, datetime.max.time() if end_of_day else datetime.min.time())
    elif isinstance(value, str):
        if "T" in value or " " in value:
            return value
        return f"{value}T23:59:59" if end_of_day else f"{value}T00:00:00"
    else:
        return None
    if end_of_day:
        dt = dt.replace(hour=23, minute=59, second=59, microsecond=0)
    else:
        dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return dt.isoformat()


def _to_epoch(value: Optional[object], end_of_day: bool = False) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime.combine(value, datetime.max.time() if end_of_day else datetime.min.time())
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            return None
    else:
        return None
    if end_of_day:
        dt = dt.replace(hour=23, minute=59, second=59, microsecond=0)
    else:
        dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(dt.timestamp())


def load_snapshot_rows(
    db_path: Optional[str] = None,
    run_start: Optional[object] = None,
    run_end: Optional[object] = None,
    match_start: Optional[object] = None,
    match_end: Optional[object] = None,
    limit: Optional[int] = None,
) -> pd.DataFrame:
    path = resolve_db_path(db_path)
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"History DB not found: {path or '<empty>'}")

    run_start_iso = _to_iso(run_start, end_of_day=False)
    run_end_iso = _to_iso(run_end, end_of_day=True)
    match_start_ts = _to_epoch(match_start, end_of_day=False)
    match_end_ts = _to_epoch(match_end, end_of_day=True)

    clauses = []
    params = []
    if run_start_iso:
        clauses.append("r.last_updated >= ?")
        params.append(run_start_iso)
    if run_end_iso:
        clauses.append("r.last_updated <= ?")
        params.append(run_end_iso)
    if match_start_ts is not None:
        clauses.append("m.start_time >= ?")
        params.append(match_start_ts)
    if match_end_ts is not None:
        clauses.append("m.start_time <= ?")
        params.append(match_end_ts)

    query = """
        SELECT
            r.run_id,
            r.last_updated,
            m.match_id,
            m.league,
            m.start_time,
            m.home_team,
            m.away_team,
            o.bookmaker,
            o.home_odds,
            o.draw_odds,
            o.away_odds,
            o.event_id,
            o.event_league_id
        FROM odds o
        JOIN matches m ON o.run_id = m.run_id AND o.match_id = m.match_id
        JOIN runs r ON o.run_id = r.run_id
    """
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY r.last_updated DESC, m.start_time DESC"
    if limit:
        query += " LIMIT ?"
        params.append(int(limit))

    conn = sqlite3.connect(path)
    try:
        init_history_db(conn)
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


def load_snapshot_rows_from_jsonl(
    jsonl_path: Optional[str] = None,
    run_start: Optional[object] = None,
    run_end: Optional[object] = None,
) -> pd.DataFrame:
    path = resolve_history_jsonl(jsonl_path)
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"History JSONL not found: {path or '<empty>'}")

    run_start_iso = _to_iso(run_start, end_of_day=False)
    run_end_iso = _to_iso(run_end, end_of_day=True)

    rows = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            run_id = record.get("run_id") or record.get("last_updated")
            last_updated = record.get("last_updated")
            if run_start_iso and last_updated and last_updated < run_start_iso:
                continue
            if run_end_iso and last_updated and last_updated > run_end_iso:
                continue
            for match in record.get("matches", []) or []:
                home_team = match.get("home_team") or ""
                away_team = match.get("away_team") or ""
                start_time = match.get("start_time") or 0
                match_id = match.get("match_id") or f"{home_team}-{away_team}-{start_time}"
                for odds in match.get("odds", []) or []:
                    rows.append({
                        "run_id": run_id,
                        "last_updated": last_updated,
                        "match_id": match_id,
                        "league": match.get("league"),
                        "start_time": start_time,
                        "home_team": home_team,
                        "away_team": away_team,
                        "bookmaker": odds.get("bookmaker"),
                        "event_id": odds.get("event_id"),
                        "event_league_id": odds.get("event_league_id") or odds.get("league_id"),
                        "home_odds": odds.get("home_odds"),
                        "draw_odds": odds.get("draw_odds"),
                        "away_odds": odds.get("away_odds"),
                    })

    return pd.DataFrame(rows)


def _prepare_odds_frame(rows: pd.DataFrame) -> pd.DataFrame:
    df = rows.copy()
    odds_cols = ["home_odds", "draw_odds", "away_odds"]
    for col in odds_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df[odds_cols] = df[odds_cols].replace({0: np.nan})
    df["run_time"] = pd.to_datetime(df["last_updated"], errors="coerce")
    df["match_start"] = pd.to_datetime(df["start_time"], unit="s", errors="coerce")
    df["implied_sum"] = (
        1 / df["home_odds"] + 1 / df["draw_odds"] + 1 / df["away_odds"]
    )
    df = _dedupe_bookmaker_lines(df)
    df = _align_home_away_to_consensus(df)
    return df


def _dedupe_bookmaker_lines(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "bookmaker" not in df.columns:
        return df
    group_cols = []
    if "run_id" in df.columns:
        group_cols.append("run_id")
    if "match_id" in df.columns and df["match_id"].notna().any():
        group_cols.extend(["match_id", "bookmaker"])
    else:
        fallback_cols = [col for col in ("league", "home_team", "away_team", "start_time") if col in df.columns]
        if fallback_cols:
            group_cols.extend(["bookmaker"] + fallback_cols)
    if not group_cols:
        return df
    return (
        df.sort_values("implied_sum", na_position="last")
        .drop_duplicates(subset=group_cols, keep="first")
        .reset_index(drop=True)
    )


def _align_home_away_to_consensus(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    group_cols = []
    if "run_id" in df.columns:
        group_cols.append("run_id")
    if "match_id" in df.columns and df["match_id"].notna().any():
        group_cols.append("match_id")
    else:
        fallback_cols = [col for col in ("league", "home_team", "away_team", "start_time") if col in df.columns]
        if fallback_cols:
            group_cols.extend(fallback_cols)
    if not group_cols:
        return df

    medians = (
        df.groupby(group_cols, as_index=False)
        .agg(med_home=("home_odds", "median"), med_away=("away_odds", "median"))
    )
    df = df.merge(medians, on=group_cols, how="left")

    valid = (
        df["home_odds"].notna()
        & df["away_odds"].notna()
        & (df["home_odds"] > 0)
        & (df["away_odds"] > 0)
        & df["med_home"].notna()
        & df["med_away"].notna()
        & (df["med_home"] > 0)
        & (df["med_away"] > 0)
    )
    dist_as_is = (
        np.log(df["home_odds"] / df["med_home"]).abs()
        + np.log(df["away_odds"] / df["med_away"]).abs()
    )
    dist_swapped = (
        np.log(df["away_odds"] / df["med_home"]).abs()
        + np.log(df["home_odds"] / df["med_away"]).abs()
    )
    swap_mask = valid & (dist_swapped + 1e-9 < dist_as_is)
    if swap_mask.any():
        df.loc[swap_mask, ["home_odds", "away_odds"]] = df.loc[
            swap_mask, ["away_odds", "home_odds"]
        ].to_numpy()

    return df.drop(columns=["med_home", "med_away"])


def _best_by_outcome(
    df: pd.DataFrame,
    outcome_col: str,
    odds_label: str,
    bookie_label: str,
    event_label: Optional[str] = None,
    extra_labels: Optional[dict] = None,
) -> pd.DataFrame:
    keys = ["run_id", "match_id"]
    eligible = df[df[outcome_col].notna() & (df[outcome_col] > 0)].copy()
    if eligible.empty:
        return pd.DataFrame(columns=keys + [bookie_label, odds_label])
    idx = eligible.groupby(keys)[outcome_col].idxmax()
    cols = ["bookmaker", outcome_col]
    rename_map = {"bookmaker": bookie_label, outcome_col: odds_label}
    if event_label and "event_id" in eligible.columns:
        cols.append("event_id")
        rename_map["event_id"] = event_label
    if extra_labels:
        for src, dest in extra_labels.items():
            if src in eligible.columns and dest:
                cols.append(src)
                rename_map[src] = dest
    best = eligible.loc[idx, keys + cols]
    return best.rename(columns=rename_map)


def build_best_lines(
    rows: pd.DataFrame,
    include_bookmakers: Optional[Iterable[str]] = None,
    include_leagues: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    if rows is None or rows.empty:
        return pd.DataFrame()

    df = _prepare_odds_frame(rows)
    if include_bookmakers:
        df = df[df["bookmaker"].isin(list(include_bookmakers))]
    if include_leagues:
        df = df[df["league"].isin(list(include_leagues))]
    if df.empty:
        return pd.DataFrame()

    keys = ["run_id", "match_id"]
    match_info = df.groupby(keys, as_index=False).agg({
        "league": "first",
        "start_time": "first",
        "home_team": "first",
        "away_team": "first",
        "last_updated": "first",
    })
    match_info["run_time"] = pd.to_datetime(match_info["last_updated"], errors="coerce")
    match_info["match_start"] = pd.to_datetime(match_info["start_time"], unit="s", errors="coerce")

    best_home = _best_by_outcome(
        df,
        "home_odds",
        "best_home_odds",
        "best_home_bookie",
        "best_home_event_id",
        extra_labels={"event_league_id": "best_home_league_id"},
    )
    best_draw = _best_by_outcome(
        df,
        "draw_odds",
        "best_draw_odds",
        "best_draw_bookie",
        "best_draw_event_id",
        extra_labels={"event_league_id": "best_draw_league_id"},
    )
    best_away = _best_by_outcome(
        df,
        "away_odds",
        "best_away_odds",
        "best_away_bookie",
        "best_away_event_id",
        extra_labels={"event_league_id": "best_away_league_id"},
    )

    merged = match_info.merge(best_home, on=keys, how="left")
    merged = merged.merge(best_draw, on=keys, how="left")
    merged = merged.merge(best_away, on=keys, how="left")

    bookie_counts = df.groupby(keys, as_index=False)["bookmaker"].nunique().rename(columns={"bookmaker": "bookie_count"})
    merged = merged.merge(bookie_counts, on=keys, how="left")

    merged = merged.dropna(subset=["best_home_odds", "best_draw_odds", "best_away_odds"])
    return merged


def compute_arbitrage_opportunities(
    rows: pd.DataFrame,
    bankroll: float = 1000.0,
    min_roi: float = 0.0,
    include_bookmakers: Optional[Iterable[str]] = None,
    include_leagues: Optional[Iterable[str]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if rows is None or rows.empty:
        return pd.DataFrame(), pd.DataFrame()

    df = _prepare_odds_frame(rows)
    if include_bookmakers:
        df = df[df["bookmaker"].isin(list(include_bookmakers))]
    if include_leagues:
        df = df[df["league"].isin(list(include_leagues))]
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    keys = ["run_id", "match_id"]
    match_info = df.groupby(keys, as_index=False).agg({
        "league": "first",
        "start_time": "first",
        "home_team": "first",
        "away_team": "first",
        "last_updated": "first",
    })
    match_info["run_time"] = pd.to_datetime(match_info["last_updated"], errors="coerce")
    match_info["match_start"] = pd.to_datetime(match_info["start_time"], unit="s", errors="coerce")

    best_home = _best_by_outcome(
        df,
        "home_odds",
        "best_home_odds",
        "best_home_bookie",
        "best_home_event_id",
        extra_labels={"event_league_id": "best_home_league_id"},
    )
    best_draw = _best_by_outcome(
        df,
        "draw_odds",
        "best_draw_odds",
        "best_draw_bookie",
        "best_draw_event_id",
        extra_labels={"event_league_id": "best_draw_league_id"},
    )
    best_away = _best_by_outcome(
        df,
        "away_odds",
        "best_away_odds",
        "best_away_bookie",
        "best_away_event_id",
        extra_labels={"event_league_id": "best_away_league_id"},
    )

    merged = match_info.merge(best_home, on=keys, how="left")
    merged = merged.merge(best_draw, on=keys, how="left")
    merged = merged.merge(best_away, on=keys, how="left")
    bookie_counts = (
        df.groupby(keys, as_index=False)["bookmaker"]
        .nunique()
        .rename(columns={"bookmaker": "bookie_count"})
    )
    merged = merged.merge(bookie_counts, on=keys, how="left")
    merged = merged.dropna(subset=["best_home_odds", "best_draw_odds", "best_away_odds"])
    if merged.empty:
        return pd.DataFrame(), match_info

    merged["implied_sum"] = (
        1 / merged["best_home_odds"]
        + 1 / merged["best_draw_odds"]
        + 1 / merged["best_away_odds"]
    )
    merged = merged[merged["implied_sum"] > 0]
    merged["arb_roi"] = 1 / merged["implied_sum"] - 1
    if min_roi is not None:
        merged = merged[merged["arb_roi"] >= min_roi]
    if merged.empty:
        return pd.DataFrame(), match_info

    merged["stake_home"] = bankroll / (merged["implied_sum"] * merged["best_home_odds"])
    merged["stake_draw"] = bankroll / (merged["implied_sum"] * merged["best_draw_odds"])
    merged["stake_away"] = bankroll / (merged["implied_sum"] * merged["best_away_odds"])
    merged["arb_profit"] = bankroll * merged["arb_roi"]
    merged["arb_roi_pct"] = merged["arb_roi"] * 100
    return merged.sort_values("arb_roi", ascending=False), match_info


def compute_consensus_edges(
    rows: pd.DataFrame,
    bankroll: float = 1000.0,
    min_edge: float = 0.0,
    include_bookmakers: Optional[Iterable[str]] = None,
    include_leagues: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    if rows is None or rows.empty:
        return pd.DataFrame()

    df = _prepare_odds_frame(rows)
    if include_bookmakers:
        df = df[df["bookmaker"].isin(list(include_bookmakers))]
    if include_leagues:
        df = df[df["league"].isin(list(include_leagues))]
    if df.empty:
        return pd.DataFrame()

    keys = ["run_id", "match_id"]
    avg_odds = df.groupby(keys, as_index=False).agg({
        "league": "first",
        "start_time": "first",
        "home_team": "first",
        "away_team": "first",
        "last_updated": "first",
        "home_odds": "mean",
        "draw_odds": "mean",
        "away_odds": "mean",
    })
    avg_odds = avg_odds.dropna(subset=["home_odds", "draw_odds", "away_odds"])
    if avg_odds.empty:
        return pd.DataFrame()

    avg_odds["run_time"] = pd.to_datetime(avg_odds["last_updated"], errors="coerce")
    avg_odds["match_start"] = pd.to_datetime(avg_odds["start_time"], unit="s", errors="coerce")

    best_home = _best_by_outcome(df, "home_odds", "best_home_odds", "best_home_bookie")
    best_draw = _best_by_outcome(df, "draw_odds", "best_draw_odds", "best_draw_bookie")
    best_away = _best_by_outcome(df, "away_odds", "best_away_odds", "best_away_bookie")

    merged = avg_odds.merge(best_home, on=keys, how="left")
    merged = merged.merge(best_draw, on=keys, how="left")
    merged = merged.merge(best_away, on=keys, how="left")
    merged = merged.dropna(subset=["best_home_odds", "best_draw_odds", "best_away_odds"])
    if merged.empty:
        return pd.DataFrame()

    prob_home = 1 / merged["home_odds"]
    prob_draw = 1 / merged["draw_odds"]
    prob_away = 1 / merged["away_odds"]
    prob_sum = prob_home + prob_draw + prob_away
    merged["cons_prob_home"] = prob_home / prob_sum
    merged["cons_prob_draw"] = prob_draw / prob_sum
    merged["cons_prob_away"] = prob_away / prob_sum

    merged["edge_home"] = merged["best_home_odds"] * merged["cons_prob_home"] - 1
    merged["edge_draw"] = merged["best_draw_odds"] * merged["cons_prob_draw"] - 1
    merged["edge_away"] = merged["best_away_odds"] * merged["cons_prob_away"] - 1

    edges = merged[["edge_home", "edge_draw", "edge_away"]]
    merged["pick_outcome"] = edges.idxmax(axis=1).str.replace("edge_", "", regex=False)
    merged["pick_edge"] = edges.max(axis=1)

    merged["pick_odds"] = np.select(
        [
            merged["pick_outcome"] == "home",
            merged["pick_outcome"] == "draw",
            merged["pick_outcome"] == "away",
        ],
        [
            merged["best_home_odds"],
            merged["best_draw_odds"],
            merged["best_away_odds"],
        ],
        default=np.nan,
    )
    merged["pick_bookie"] = np.select(
        [
            merged["pick_outcome"] == "home",
            merged["pick_outcome"] == "draw",
            merged["pick_outcome"] == "away",
        ],
        [
            merged["best_home_bookie"],
            merged["best_draw_bookie"],
            merged["best_away_bookie"],
        ],
        default="",
    )
    merged["pick_prob"] = np.select(
        [
            merged["pick_outcome"] == "home",
            merged["pick_outcome"] == "draw",
            merged["pick_outcome"] == "away",
        ],
        [
            merged["cons_prob_home"],
            merged["cons_prob_draw"],
            merged["cons_prob_away"],
        ],
        default=np.nan,
    )
    merged["expected_profit"] = bankroll * merged["pick_edge"]
    if min_edge is not None:
        merged = merged[merged["pick_edge"] >= min_edge]
    if merged.empty:
        return pd.DataFrame()
    merged["pick_edge_pct"] = merged["pick_edge"] * 100
    return merged.sort_values("pick_edge", ascending=False)


def summarize_arbitrage(arbs: pd.DataFrame, matches: Optional[pd.DataFrame] = None) -> dict:
    summary = {
        "matches": int(matches["match_id"].nunique()) if matches is not None and not matches.empty else 0,
        "arbs": int(arbs["match_id"].nunique()) if arbs is not None and not arbs.empty else 0,
        "avg_roi": float(arbs["arb_roi"].mean()) if arbs is not None and not arbs.empty else 0.0,
        "max_roi": float(arbs["arb_roi"].max()) if arbs is not None and not arbs.empty else 0.0,
        "median_roi": float(arbs["arb_roi"].median()) if arbs is not None and not arbs.empty else 0.0,
    }
    return summary


def load_results_rows(
    db_path: Optional[str] = None,
    start_date: Optional[object] = None,
    end_date: Optional[object] = None,
    completed_only: bool = True,
) -> pd.DataFrame:
    path = resolve_results_db_path(db_path)
    if not path:
        return pd.DataFrame()
    if not os.path.exists(path):
        _init_results_db(path)
        return pd.DataFrame()

    start_iso = _to_iso(start_date, end_of_day=False)
    end_iso = _to_iso(end_date, end_of_day=True)

    clauses = []
    params = []
    if completed_only:
        clauses.append("completed = 1")
    if start_iso:
        clauses.append("event_date >= ?")
        params.append(start_iso.split("T")[0])
    if end_iso:
        clauses.append("event_date <= ?")
        params.append(end_iso.split("T")[0])

    query = "SELECT * FROM results"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    conn = sqlite3.connect(path)
    try:
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


def _init_results_db(path: str) -> None:
    base_dir = os.path.dirname(path)
    if base_dir:
        os.makedirs(base_dir, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
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
        conn.commit()
    finally:
        conn.close()


def _normalize_team_value(value: str) -> str:
    try:
        from tools.team_normalization import normalize_team
        return normalize_team(value or "")
    except Exception:
        return str(value or "").strip().lower()


def attach_results(
    matches: pd.DataFrame,
    results: pd.DataFrame,
    time_tolerance_seconds: int = 6 * 3600,
) -> pd.DataFrame:
    if matches is None or matches.empty or results is None or results.empty:
        return pd.DataFrame()

    frame = matches.copy().reset_index(drop=False).rename(columns={"index": "_row_id"})
    frame["home_norm"] = frame["home_team"].map(_normalize_team_value)
    frame["away_norm"] = frame["away_team"].map(_normalize_team_value)

    if "start_time" in frame.columns and frame["start_time"].notna().any():
        frame["match_epoch"] = pd.to_numeric(frame["start_time"], errors="coerce")
        frame["match_date"] = pd.to_datetime(frame["match_epoch"], unit="s", errors="coerce").dt.date
    else:
        frame["match_date"] = pd.to_datetime(frame.get("match_start"), errors="coerce").dt.date
        frame["match_epoch"] = pd.to_datetime(frame.get("match_start"), errors="coerce").astype("int64") // 10**9

    frame["key_direct"] = (
        frame["home_norm"].fillna("") + "|" + frame["away_norm"].fillna("") + "|" + frame["match_date"].astype(str)
    )
    frame["key_reverse"] = (
        frame["away_norm"].fillna("") + "|" + frame["home_norm"].fillna("") + "|" + frame["match_date"].astype(str)
    )

    results_frame = results.copy()
    results_frame["home_team_norm"] = results_frame["home_team_norm"].map(_normalize_team_value)
    results_frame["away_team_norm"] = results_frame["away_team_norm"].map(_normalize_team_value)
    results_frame["event_date"] = results_frame["event_date"].astype(str)
    results_frame["key"] = (
        results_frame["home_team_norm"].fillna("")
        + "|"
        + results_frame["away_team_norm"].fillna("")
        + "|"
        + results_frame["event_date"].fillna("")
    )

    direct = frame.merge(results_frame, left_on="key_direct", right_on="key", how="left", suffixes=("", "_result"))
    direct["result_swapped"] = False

    matched_ids = set(direct.loc[direct["event_id"].notna(), "_row_id"])
    unmatched = frame.loc[~frame["_row_id"].isin(matched_ids), ["_row_id", "key_reverse", "match_epoch"]]
    if not unmatched.empty:
        reverse = unmatched.merge(results_frame, left_on="key_reverse", right_on="key", how="left")
        reverse["result_swapped"] = True
        combined = pd.concat([direct, reverse], ignore_index=True, sort=False)
    else:
        combined = direct

    if "start_time_result" in combined.columns and "start_time" in combined.columns:
        combined["result_start_time"] = combined["start_time_result"].fillna(combined["start_time"])
    elif "start_time_result" in combined.columns:
        combined["result_start_time"] = combined["start_time_result"]
    else:
        combined["result_start_time"] = combined.get("start_time")

    combined["time_diff"] = (
        pd.to_numeric(combined["match_epoch"], errors="coerce")
        - pd.to_numeric(combined["result_start_time"], errors="coerce")
    ).abs()
    combined["time_diff"] = combined["time_diff"].fillna(time_tolerance_seconds + 1)
    combined = combined[combined["time_diff"] <= time_tolerance_seconds]
    combined = combined.sort_values(["_row_id", "time_diff"])
    best = combined.drop_duplicates(subset=["_row_id"], keep="first")

    result_cols = {
        "event_id": "result_event_id",
        "result_start_time": "result_start_time",
        "event_date": "result_event_date",
        "home_team_raw": "result_home_team",
        "away_team_raw": "result_away_team",
        "home_score": "result_home_score",
        "away_score": "result_away_score",
        "status": "result_status",
        "completed": "result_completed",
    }
    for col, new_col in result_cols.items():
        if col in best.columns:
            best[new_col] = best[col]

    best["result_time_diff"] = best["time_diff"]
    best = best[["_row_id", "result_event_id", "result_start_time", "result_event_date",
                "result_home_team", "result_away_team", "result_home_score", "result_away_score",
                "result_status", "result_completed", "result_swapped", "result_time_diff"]]

    merged = frame.merge(best, on="_row_id", how="left")
    return merged


def outcome_from_scores(home_score: Optional[float], away_score: Optional[float]) -> Optional[str]:
    if home_score is None or away_score is None:
        return None
    try:
        home_val = float(home_score)
        away_val = float(away_score)
    except (TypeError, ValueError):
        return None
    if home_val > away_val:
        return "home"
    if away_val > home_val:
        return "away"
    return "draw"


def add_slippage_adjustment(arbs: pd.DataFrame, slippage_pct: float = 0.0) -> pd.DataFrame:
    if arbs is None or arbs.empty:
        return pd.DataFrame()
    df = arbs.copy()
    for col in ("best_home_odds", "best_draw_odds", "best_away_odds"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    slippage_pct = max(0.0, float(slippage_pct or 0.0))
    factor = max(0.0, 1.0 - slippage_pct)
    df["home_odds_adj"] = df["best_home_odds"] * factor
    df["draw_odds_adj"] = df["best_draw_odds"] * factor
    df["away_odds_adj"] = df["best_away_odds"] * factor
    df = df.dropna(subset=["home_odds_adj", "draw_odds_adj", "away_odds_adj"])
    df = df[(df["home_odds_adj"] > 1) & (df["draw_odds_adj"] > 1) & (df["away_odds_adj"] > 1)]
    df["implied_sum_adj"] = (
        1 / df["home_odds_adj"] + 1 / df["draw_odds_adj"] + 1 / df["away_odds_adj"]
    )
    df = df[df["implied_sum_adj"] > 0]
    df["arb_roi_adj"] = 1 / df["implied_sum_adj"] - 1
    df["w_home"] = 1 / (df["home_odds_adj"] * df["implied_sum_adj"])
    df["w_draw"] = 1 / (df["draw_odds_adj"] * df["implied_sum_adj"])
    df["w_away"] = 1 / (df["away_odds_adj"] * df["implied_sum_adj"])
    return df


def simulate_daily_compounding(
    arbs: pd.DataFrame,
    initial_bankroll: float,
    reserve_pct: float = 0.1,
    max_daily_exposure: Optional[float] = None,
    max_daily_exposure_pct: Optional[float] = None,
    per_event_cap: Optional[float] = None,
    per_event_cap_pct: Optional[float] = None,
    per_bookie_cap: Optional[float] = None,
    per_bookie_cap_pct: Optional[float] = None,
    max_arbs_per_day: Optional[int] = None,
    min_roi: float = 0.0,
    selection: str = "roi",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if arbs is None or arbs.empty:
        return pd.DataFrame(), pd.DataFrame()

    df = arbs.copy()
    df["run_date"] = pd.to_datetime(df["run_time"], errors="coerce").dt.date
    df = df.dropna(subset=["run_date", "arb_roi_adj"])
    df = df[df["arb_roi_adj"] >= float(min_roi or 0.0)]
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    sort_col = "arb_roi_adj" if selection == "roi" else "arb_roi_adj"
    df = df.sort_values(["run_date", sort_col], ascending=[True, False])
    df = df.drop_duplicates(subset=["run_date", "match_id"], keep="first")

    bankroll = float(initial_bankroll)
    daily_rows = []
    pick_rows = []

    for run_date, group in df.groupby("run_date"):
        day_start = bankroll
        reserve_pct = max(0.0, min(0.95, float(reserve_pct or 0.0)))
        reserve = day_start * reserve_pct
        available = max(day_start - reserve, 0.0)

        day_cap = available
        if max_daily_exposure is not None:
            day_cap = min(day_cap, float(max_daily_exposure))
        if max_daily_exposure_pct is not None:
            day_cap = min(day_cap, day_start * float(max_daily_exposure_pct))

        event_cap = float(per_event_cap) if per_event_cap is not None else None
        if per_event_cap_pct is not None:
            pct_cap = day_start * float(per_event_cap_pct)
            event_cap = pct_cap if event_cap is None else min(event_cap, pct_cap)

        bookie_cap = float(per_bookie_cap) if per_bookie_cap is not None else None
        if per_bookie_cap_pct is not None:
            pct_cap = day_start * float(per_bookie_cap_pct)
            bookie_cap = pct_cap if bookie_cap is None else min(bookie_cap, pct_cap)

        exposure_used = 0.0
        profit_total = 0.0
        picks_count = 0
        bookie_exposure = {}

        for _, row in group.iterrows():
            if max_arbs_per_day and picks_count >= int(max_arbs_per_day):
                break

            remaining = day_cap - exposure_used
            if remaining <= 0:
                break

            stake_total = remaining
            if event_cap is not None:
                stake_total = min(stake_total, event_cap)
            if stake_total <= 0:
                continue

            stake_home = stake_total * row["w_home"]
            stake_draw = stake_total * row["w_draw"]
            stake_away = stake_total * row["w_away"]

            if bookie_cap is not None:
                factor = 1.0
                for bookie, stake in (
                    (row["best_home_bookie"], stake_home),
                    (row["best_draw_bookie"], stake_draw),
                    (row["best_away_bookie"], stake_away),
                ):
                    if not bookie:
                        continue
                    cap_left = bookie_cap - bookie_exposure.get(bookie, 0.0)
                    if cap_left <= 0 or stake <= 0:
                        factor = 0.0
                        break
                    factor = min(factor, cap_left / stake)

                if factor <= 0:
                    continue
                if factor < 1.0:
                    stake_total *= factor
                    stake_home = stake_total * row["w_home"]
                    stake_draw = stake_total * row["w_draw"]
                    stake_away = stake_total * row["w_away"]

            exposure_used += stake_total
            profit = stake_total * row["arb_roi_adj"]
            profit_total += profit
            picks_count += 1

            for bookie, stake in (
                (row["best_home_bookie"], stake_home),
                (row["best_draw_bookie"], stake_draw),
                (row["best_away_bookie"], stake_away),
            ):
                if not bookie:
                    continue
                bookie_exposure[bookie] = bookie_exposure.get(bookie, 0.0) + stake

            pick_rows.append({
                "run_date": run_date,
                "run_time": row.get("run_time"),
                "league": row.get("league"),
                "home_team": row.get("home_team"),
                "away_team": row.get("away_team"),
                "match_start": row.get("match_start"),
                "snapshot_age_min": row.get("snapshot_age_min"),
                "kickoff_minutes": row.get("kickoff_minutes"),
                "best_home_bookie": row.get("best_home_bookie"),
                "best_draw_bookie": row.get("best_draw_bookie"),
                "best_away_bookie": row.get("best_away_bookie"),
                "home_odds_adj": row.get("home_odds_adj"),
                "draw_odds_adj": row.get("draw_odds_adj"),
                "away_odds_adj": row.get("away_odds_adj"),
                "arb_roi_adj": row.get("arb_roi_adj"),
                "stake_total": stake_total,
                "stake_home": stake_home,
                "stake_draw": stake_draw,
                "stake_away": stake_away,
                "profit": profit,
            })

        day_end = day_start + profit_total
        bankroll = day_end
        daily_rows.append({
            "run_date": run_date,
            "bankroll_start": day_start,
            "bankroll_end": day_end,
            "profit": profit_total,
            "exposure": exposure_used,
            "roi_day": (profit_total / exposure_used) if exposure_used > 0 else 0.0,
            "picks": picks_count,
            "reserve": reserve,
        })

    return pd.DataFrame(daily_rows), pd.DataFrame(pick_rows)
