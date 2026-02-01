import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
import math
import time
from typing import Iterable, Optional
from datetime import datetime, timedelta, timezone

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    import numpy as np
    import pandas as pd
    import plotly.express as px
    import streamlit as st
except ImportError as exc:
    raise SystemExit(
        "Missing analytics dependencies. Install with: "
        "pip install -r requirements.analytics.txt"
    ) from exc

from tools.arb_lab import (
    add_slippage_adjustment,
    attach_results,
    build_best_lines,
    compute_arbitrage_opportunities,
    compute_consensus_edges,
    load_snapshot_rows,
    load_snapshot_rows_from_jsonl,
    load_results_rows,
    resolve_db_path,
    resolve_history_jsonl,
    resolve_results_db_path,
    rows_from_odds_payload,
    append_snapshot_to_history_db,
    append_snapshot_to_history_jsonl,
    simulate_daily_compounding,
    summarize_arbitrage,
    outcome_from_scores,
)


st.set_page_config(page_title="Arbitrage Strategy Terminal", layout="wide")

st.title("Arbitrage Strategy Terminal")
st.caption(
    "Local research workspace for odds history. Analysis-only; execution risk and limits apply."
)

today = datetime.utcnow().date()
default_start = today - timedelta(days=14)


def _apply_widget_overrides():
    for key in ("max_snapshot_age_minutes", "min_minutes_to_kickoff"):
        override_key = f"override_{key}"
        if override_key in st.session_state:
            st.session_state[key] = st.session_state.pop(override_key)


_apply_widget_overrides()


SEARCH_BASE_URL = os.getenv("SEARCH_BASE_URL", "https://www.google.com/search?q=")
BOOKMAKER_EVENT_TEMPLATES = {
    "SportyBet Ghana": "https://www.sportybet.com/gh/sport/football/{league_path}/{home_vs_away}/{event_id_url}",
    "Betway Ghana": "https://www.betway.com.gh/sport/soccer/event/{event_id}",
    "22Bet Ghana": "https://22bet.com.gh/prematch/football/{league_id}-{league_slug}/{event_id}-{home_slug}-{away_slug}",
    "1xBet Ghana": "https://1xbet.com.gh/en/line/football/{league_id}-{league_slug}/{event_id}-{home_slug}-{away_slug}",
    "SoccaBet Ghana": "https://www.soccabet.com/sports/match?id={event_id}&t={league_id}&cs=77",
    "Betfox Ghana": "https://www.betfox.com.gh/sportsbook/#/event/{event_id}",
}
BOOKMAKER_EVENT_TEMPLATES.update(
    json.loads(os.getenv("BOOKMAKER_EVENT_TEMPLATES", "{}") or "{}")
)
DEFAULT_RESEARCH_DB_PATH = os.getenv("RESEARCH_DB_PATH", os.path.join("data", "research.db"))
CLV_TIME_BINS = [-float("inf"), 2, 6, 12, 24, 48, float("inf")]
CLV_TIME_LABELS = ["<2h", "2-6h", "6-12h", "12-24h", "24-48h", "48h+"]


def _build_search_url(*parts: object) -> str:
    query = " ".join(str(part).strip() for part in parts if part and str(part).strip())
    if not query:
        return ""
    return f"{SEARCH_BASE_URL}{urllib.parse.quote_plus(query)}"


def _slugify_simple(value: object) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _sportybet_segment(value: object) -> str:
    text = str(value or "").strip()
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def _sportybet_league_path(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parts = [p.strip() for p in raw.replace("/", ".").split(".") if p.strip()]
    segments = [_sportybet_segment(p) for p in parts if p]
    return "/".join([seg for seg in segments if seg])


def _build_bookie_event_url(
    bookmaker: object,
    event_id: object,
    home: object,
    away: object,
    league: object,
    event_league_id: object = None,
) -> str:
    template = BOOKMAKER_EVENT_TEMPLATES.get(str(bookmaker or ""))
    if not template or not event_id:
        return ""
    if str(bookmaker or "") == "SportyBet Ghana":
        league_path = _sportybet_league_path(league)
        home_seg = _sportybet_segment(home)
        away_seg = _sportybet_segment(away)
        if not league_path or not home_seg or not away_seg:
            return ""
        event_id_str = str(event_id)
        return (
            "https://www.sportybet.com/gh/sport/football/"
            f"{league_path}/{home_seg}_vs_{away_seg}/{urllib.parse.quote(event_id_str, safe=':')}"
        )
    if "{league_id}" in template and not event_league_id:
        return ""
    event_id_str = str(event_id)
    values = {
        "event_id": event_id_str,
        "event_id_url": urllib.parse.quote(event_id_str, safe=""),
        "league_path": _sportybet_league_path(league),
        "home_vs_away": f"{_sportybet_segment(home)}_vs_{_sportybet_segment(away)}",
        "home": str(home or ""),
        "away": str(away or ""),
        "league": str(league or ""),
        "league_id": str(event_league_id or ""),
        "home_slug": _slugify_simple(home),
        "away_slug": _slugify_simple(away),
        "league_slug": _slugify_simple(league),
    }

    class _SafeDict(dict):
        def __missing__(self, key):
            return ""

    try:
        return template.format_map(_SafeDict(values))
    except Exception:
        return ""


def _render_link_button(label: str, url: str) -> None:
    if not url:
        return
    if hasattr(st, "link_button"):
        st.link_button(label, url)
    else:
        st.markdown(f"[{label}]({url})")


def _build_event_lookup(rows: Optional[pd.DataFrame]) -> dict:
    if rows is None or rows.empty:
        return {}
    if "event_id" not in rows.columns or "match_id" not in rows.columns:
        return {}
    cols = ["match_id", "bookmaker", "event_id"]
    if "event_league_id" in rows.columns:
        cols.append("event_league_id")
    df = rows[cols].copy()
    if "event_league_id" not in df.columns:
        df["event_league_id"] = None
    df = df[df["event_id"].notna()]
    df["event_id"] = df["event_id"].astype(str)
    df = df[df["event_id"].str.strip() != ""]
    lookup = {}
    for row in df.itertuples(index=False):
        key = (getattr(row, "match_id", None), getattr(row, "bookmaker", None))
        if key[0] is None or key[1] is None:
            continue
        lookup[key] = (getattr(row, "event_id", None), getattr(row, "event_league_id", None))
    return lookup


def _apply_event_lookup(arbs_df: pd.DataFrame, lookup: dict) -> pd.DataFrame:
    if arbs_df is None or arbs_df.empty or not lookup:
        return arbs_df
    if "match_id" not in arbs_df.columns:
        return arbs_df
    updated = arbs_df.copy()
    for side in ("home", "draw", "away"):
        bookie_col = f"best_{side}_bookie"
        event_col = f"best_{side}_event_id"
        league_col = f"best_{side}_league_id"
        if bookie_col not in updated.columns:
            continue
        if event_col not in updated.columns:
            updated[event_col] = None
        if league_col not in updated.columns:
            updated[league_col] = None
        keys = list(zip(updated["match_id"], updated[bookie_col]))
        event_vals = [lookup.get(key, (None, None))[0] for key in keys]
        league_vals = [lookup.get(key, (None, None))[1] for key in keys]
        event_series = pd.Series(event_vals, index=updated.index)
        league_series = pd.Series(league_vals, index=updated.index)
        missing_event = updated[event_col].isna() | (updated[event_col].astype(str).str.strip() == "")
        if missing_event.any():
            updated.loc[missing_event, event_col] = event_series[missing_event]
        missing_league = updated[league_col].isna() | (updated[league_col].astype(str).str.strip() == "")
        if missing_league.any():
            updated.loc[missing_league, league_col] = league_series[missing_league]
    return updated


def _compute_liquidity_score(
    bookie_count: Optional[float],
    snapshot_age_min: Optional[float],
    kickoff_minutes: Optional[float],
    target_bookies: float,
    max_age_min: float,
    target_kickoff_min: float,
) -> float:
    if target_bookies <= 0:
        target_bookies = 1.0
    if max_age_min <= 0:
        max_age_min = 1.0
    if target_kickoff_min <= 0:
        target_kickoff_min = 1.0
    bookie_val = float(bookie_count) if bookie_count is not None else 1.0
    age_val = float(snapshot_age_min) if snapshot_age_min is not None else 0.0
    kickoff_val = float(kickoff_minutes) if kickoff_minutes is not None else target_kickoff_min

    bookie_score = min(1.0, max(0.0, bookie_val / target_bookies))
    age_score = max(0.0, 1.0 - (age_val / max_age_min))
    kickoff_score = min(1.0, max(0.0, kickoff_val / target_kickoff_min))
    return max(0.0, min(1.0, bookie_score * age_score * kickoff_score))


def _filter_low_liquidity_local_leagues(
    rows: pd.DataFrame,
    keywords: Iterable[str],
    min_bookies: int,
) -> pd.DataFrame:
    if rows is None or rows.empty:
        return rows
    if "league" not in rows.columns:
        return rows
    cleaned = [kw.strip().lower() for kw in keywords if kw and kw.strip()]
    if not cleaned:
        return rows
    pattern = "|".join(re.escape(kw) for kw in cleaned)
    df = rows.copy()
    df["league_norm"] = df["league"].astype(str).str.lower()
    local_mask = df["league_norm"].str.contains(pattern, na=False)

    group_cols = []
    if "run_id" in df.columns:
        group_cols.append("run_id")
    if "match_id" in df.columns:
        group_cols.append("match_id")
    if not group_cols or "bookmaker" not in df.columns:
        return df[~local_mask].drop(columns=["league_norm"])

    counts = (
        df.groupby(group_cols, as_index=False)["bookmaker"]
        .nunique()
        .rename(columns={"bookmaker": "bookie_count"})
    )
    df = df.merge(counts, on=group_cols, how="left")
    df = df[~(local_mask & (df["bookie_count"] < int(min_bookies)))]
    return df.drop(columns=["league_norm", "bookie_count"])


def _compute_clv_table(lines: pd.DataFrame) -> pd.DataFrame:
    if lines is None or lines.empty:
        return pd.DataFrame()
    clv_base = _build_open_close(lines)
    if clv_base.empty:
        return pd.DataFrame()
    snap_counts = lines.groupby("match_id", as_index=False)["run_time"].nunique().rename(columns={"run_time": "snapshot_count"})
    clv = clv_base.merge(snap_counts, on="match_id", how="left")
    clv = clv[clv["snapshot_count"] >= 2]
    if clv.empty:
        return pd.DataFrame()
    for col in (
        "best_home_odds_open",
        "best_draw_odds_open",
        "best_away_odds_open",
        "best_home_odds_close",
        "best_draw_odds_close",
        "best_away_odds_close",
    ):
        if col in clv.columns:
            clv[col] = pd.to_numeric(clv[col], errors="coerce")
    clv = clv[
        (clv["best_home_odds_open"] > 1)
        & (clv["best_draw_odds_open"] > 1)
        & (clv["best_away_odds_open"] > 1)
        & (clv["best_home_odds_close"] > 1)
        & (clv["best_draw_odds_close"] > 1)
        & (clv["best_away_odds_close"] > 1)
    ]
    if clv.empty:
        return pd.DataFrame()
    clv["clv_home"] = clv["best_home_odds_open"] / clv["best_home_odds_close"] - 1
    clv["clv_draw"] = clv["best_draw_odds_open"] / clv["best_draw_odds_close"] - 1
    clv["clv_away"] = clv["best_away_odds_open"] / clv["best_away_odds_close"] - 1
    clv["clv_best"] = clv[["clv_home", "clv_draw", "clv_away"]].max(axis=1)
    clv["clv_outcome"] = (
        clv[["clv_home", "clv_draw", "clv_away"]]
        .idxmax(axis=1)
        .str.replace("clv_", "")
    )
    return clv


def _compute_clv_league_stats(clv: pd.DataFrame) -> pd.DataFrame:
    if clv is None or clv.empty:
        return pd.DataFrame()
    league_col = "league_open" if "league_open" in clv.columns else "league"
    stats = (
        clv.groupby(league_col, dropna=True)
        .agg(
            clv_matches=("match_id", "count"),
            clv_pos_rate=("clv_best", lambda x: (x > 0).mean()),
            clv_median=("clv_best", "median"),
            clv_avg=("clv_best", "mean"),
        )
        .reset_index()
        .rename(columns={league_col: "league"})
    )
    return stats


def _ensure_table_columns(conn: sqlite3.Connection, table: str, columns: dict) -> None:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    for name, ddl in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def _init_research_db(path: str) -> None:
    if not path:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS research_picks (
                pick_id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT,
                mode TEXT,
                strategy TEXT,
                match_id TEXT,
                league TEXT,
                start_time INTEGER,
                home_team TEXT,
                away_team TEXT,
                bookmaker TEXT,
                outcome TEXT,
                odds REAL,
                stake REAL,
                expected_roi REAL,
                expected_profit REAL,
                source_run_time TEXT,
                notes TEXT,
                status TEXT,
                settled_at TEXT,
                outcome_result TEXT,
                realized_profit REAL,
                realized_roi REAL,
                cash_return REAL
            )
            """
        )
        _ensure_table_columns(
            conn,
            "research_picks",
            {
                "status": "TEXT",
                "settled_at": "TEXT",
                "outcome_result": "TEXT",
                "realized_profit": "REAL",
                "realized_roi": "REAL",
                "cash_return": "REAL",
            },
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cash_ledger (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT,
                change REAL,
                balance REAL,
                reason TEXT,
                pick_id INTEGER,
                note TEXT
            )
            """
        )
        _ensure_table_columns(
            conn,
            "cash_ledger",
            {
                "created_at": "TEXT",
                "change": "REAL",
                "balance": "REAL",
                "reason": "TEXT",
                "pick_id": "INTEGER",
                "note": "TEXT",
            },
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_research_created ON research_picks(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_research_start ON research_picks(start_time)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cash_ledger_created ON cash_ledger(created_at)")
        conn.commit()
    finally:
        conn.close()


def _append_research_pick(path: str, record: dict) -> Optional[int]:
    if not path:
        return None
    _init_research_db(path)
    record = dict(record or {})
    record.setdefault("status", "open")
    conn = sqlite3.connect(path)
    try:
        cur = conn.execute(
            """
            INSERT INTO research_picks (
                created_at,
                mode,
                strategy,
                match_id,
                league,
                start_time,
                home_team,
                away_team,
                bookmaker,
                outcome,
                odds,
                stake,
                expected_roi,
                expected_profit,
                source_run_time,
                notes,
                status,
                settled_at,
                outcome_result,
                realized_profit,
                realized_roi,
                cash_return
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.get("created_at"),
                record.get("mode"),
                record.get("strategy"),
                record.get("match_id"),
                record.get("league"),
                record.get("start_time"),
                record.get("home_team"),
                record.get("away_team"),
                record.get("bookmaker"),
                record.get("outcome"),
                record.get("odds"),
                record.get("stake"),
                record.get("expected_roi"),
                record.get("expected_profit"),
                record.get("source_run_time"),
                record.get("notes"),
                record.get("status"),
                record.get("settled_at"),
                record.get("outcome_result"),
                record.get("realized_profit"),
                record.get("realized_roi"),
                record.get("cash_return"),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _load_research_picks(path: str, start_date=None, end_date=None) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    _init_research_db(path)
    conn = sqlite3.connect(path)
    try:
        df = pd.read_sql_query("SELECT * FROM research_picks ORDER BY created_at DESC", conn)
    finally:
        conn.close()
    if df.empty:
        return df
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df["start_time"] = pd.to_numeric(df["start_time"], errors="coerce")
    if "status" not in df.columns:
        df["status"] = "open"
    df["status"] = df["status"].fillna("open")
    if "realized_profit" not in df.columns:
        df["realized_profit"] = np.nan
    if "realized_roi" not in df.columns:
        df["realized_roi"] = np.nan
    if "cash_return" not in df.columns:
        df["cash_return"] = np.nan
    df["match_date"] = pd.to_datetime(df["start_time"], unit="s", errors="coerce").dt.date
    df["created_date"] = df["created_at"].dt.date
    use_date = df["match_date"].fillna(df["created_date"])
    if start_date:
        df = df[use_date >= start_date]
    if end_date:
        df = df[use_date <= end_date]
    return df


def _append_cash_entry(
    path: str,
    change: float,
    reason: str,
    pick_id: Optional[int] = None,
    note: Optional[str] = None,
) -> Optional[float]:
    if not path:
        return None
    _init_research_db(path)
    conn = sqlite3.connect(path)
    try:
        cur = conn.execute(
            "SELECT balance FROM cash_ledger ORDER BY created_at DESC, entry_id DESC LIMIT 1"
        )
        row = cur.fetchone()
        last_balance = float(row[0]) if row and row[0] is not None else 0.0
        new_balance = last_balance + float(change)
        conn.execute(
            """
            INSERT INTO cash_ledger (created_at, change, balance, reason, pick_id, note)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                float(change),
                float(new_balance),
                reason,
                pick_id,
                note,
            ),
        )
        conn.commit()
        return new_balance
    finally:
        conn.close()


def _set_cash_balance(path: str, new_balance: float, note: Optional[str] = None) -> Optional[float]:
    current_balance = 0.0
    if path:
        _init_research_db(path)
        conn = sqlite3.connect(path)
        try:
            cur = conn.execute(
                "SELECT balance FROM cash_ledger ORDER BY created_at DESC, entry_id DESC LIMIT 1"
            )
            row = cur.fetchone()
            if row and row[0] is not None:
                current_balance = float(row[0])
        finally:
            conn.close()
    change = float(new_balance) - float(current_balance)
    if abs(change) < 1e-9:
        return float(current_balance)
    return _append_cash_entry(path, change, "balance_set", note=note)


def _load_cash_ledger(path: str) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    _init_research_db(path)
    conn = sqlite3.connect(path)
    try:
        df = pd.read_sql_query(
            "SELECT * FROM cash_ledger ORDER BY created_at DESC, entry_id DESC", conn
        )
    finally:
        conn.close()
    if df.empty:
        return df
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df["change"] = pd.to_numeric(df["change"], errors="coerce")
    df["balance"] = pd.to_numeric(df["balance"], errors="coerce")
    return df


def _settle_research_pick(
    path: str,
    pick_id: int,
    outcome_result: str,
    realized_profit: float,
    realized_roi: float,
    cash_return: float,
) -> None:
    if not path:
        return
    _init_research_db(path)
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            UPDATE research_picks
            SET status = ?, settled_at = ?, outcome_result = ?, realized_profit = ?, realized_roi = ?, cash_return = ?
            WHERE pick_id = ?
            """,
            (
                "settled",
                datetime.now(timezone.utc).isoformat(),
                outcome_result,
                float(realized_profit),
                float(realized_roi),
                float(cash_return),
                int(pick_id),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _evaluate_research_picks(picks: pd.DataFrame, results: pd.DataFrame, tolerance_hours: float) -> pd.DataFrame:
    if picks is None or picks.empty:
        return pd.DataFrame()
    df = picks.copy()
    df["stake"] = pd.to_numeric(df["stake"], errors="coerce")
    df["odds"] = pd.to_numeric(df["odds"], errors="coerce")
    df["expected_roi"] = pd.to_numeric(df["expected_roi"], errors="coerce")
    df["expected_profit"] = pd.to_numeric(df["expected_profit"], errors="coerce")
    df["expected_profit"] = df["expected_profit"].fillna(df["expected_roi"] * df["stake"])
    if "realized_profit" not in df.columns:
        df["realized_profit"] = np.nan
    if "realized_roi" not in df.columns:
        df["realized_roi"] = np.nan
    if "status" not in df.columns:
        df["status"] = "open"
    df["status"] = df["status"].fillna("open")
    df["result_outcome"] = None
    df["result_outcome_adj"] = None
    df["result_event_date"] = None
    df["result_home_score"] = None
    df["result_away_score"] = None
    settled_mask = df["status"].str.lower() == "settled"

    arb_mask = df["strategy"].str.contains("arb", case=False, na=False)
    arb_unset = arb_mask & ~settled_mask & df["realized_profit"].isna()
    df.loc[arb_unset, "realized_profit"] = df.loc[arb_unset, "expected_profit"]
    df.loc[arb_unset, "realized_roi"] = df.loc[arb_unset, "expected_roi"]

    if results is None or results.empty:
        return df

    candidates = df[
        (~arb_mask)
        & (~settled_mask)
        & df["home_team"].notna()
        & df["away_team"].notna()
        & df["outcome"].notna()
        & df["stake"].notna()
        & df["odds"].notna()
    ].copy()
    if candidates.empty:
        return df

    matched = attach_results(candidates, results, time_tolerance_seconds=int(tolerance_hours * 3600))
    if matched.empty:
        return df
    matched["result_outcome"] = matched.apply(
        lambda row: outcome_from_scores(row.get("result_home_score"), row.get("result_away_score")),
        axis=1,
    )
    matched["result_outcome_adj"] = matched["result_outcome"]
    swapped = matched["result_swapped"] == True
    matched.loc[swapped & (matched["result_outcome"] == "home"), "result_outcome_adj"] = "away"
    matched.loc[swapped & (matched["result_outcome"] == "away"), "result_outcome_adj"] = "home"

    matched["win"] = matched["outcome"] == matched["result_outcome_adj"]
    matched["realized_profit"] = np.where(
        matched["win"],
        matched["stake"] * (matched["odds"] - 1),
        -matched["stake"],
    )
    matched["realized_roi"] = matched["realized_profit"] / matched["stake"]

    result_cols = [
        "pick_id",
        "result_outcome",
        "result_outcome_adj",
        "result_event_date",
        "result_home_score",
        "result_away_score",
        "realized_profit",
        "realized_roi",
    ]
    update = matched[result_cols].copy()
    df = df.merge(update, on="pick_id", how="left", suffixes=("", "_result"))
    df["realized_profit"] = df["realized_profit"].fillna(df.get("realized_profit_result"))
    df["realized_roi"] = df["realized_roi"].fillna(df.get("realized_roi_result"))
    df["result_outcome"] = df["result_outcome"].fillna(df.get("result_outcome_result"))
    df["result_outcome_adj"] = df["result_outcome_adj"].fillna(df.get("result_outcome_adj_result"))
    df["result_event_date"] = df["result_event_date"].fillna(df.get("result_event_date_result"))
    df["result_home_score"] = df["result_home_score"].fillna(df.get("result_home_score_result"))
    df["result_away_score"] = df["result_away_score"].fillna(df.get("result_away_score_result"))
    drop_cols = [col for col in df.columns if col.endswith("_result")]
    if drop_cols:
        df = df.drop(columns=drop_cols)
    return df


with st.sidebar:
    st.subheader("Data Source")
    db_path = st.text_input("History DB path", value=resolve_db_path())
    jsonl_path = st.text_input("History JSONL path", value=resolve_history_jsonl())
    allow_jsonl_fallback = st.checkbox("Fallback to JSONL if DB missing", value=True)
    results_db_path = st.text_input("Results DB path", value=resolve_results_db_path())
    enable_results = st.checkbox("Enable results backtest", value=True)
    results_tolerance_hours = st.number_input("Results match tolerance (hours)", min_value=1, value=6, step=1)
    st.subheader("Remote Snapshot")
    default_remote_url = os.getenv(
        "REMOTE_ODDS_URL",
        "https://raw.githubusercontent.com/kwamenasworld-cloud/oddswize/data-arb/odds_data.json",
    )
    default_use_remote = os.getenv("DEFAULT_USE_REMOTE", "1").strip().lower() in ("1", "true", "yes", "on")
    use_remote = st.checkbox("Use remote odds snapshot", value=default_use_remote)
    remote_url = st.text_input("Remote odds_data.json URL", value=default_remote_url)
    st.caption("Tip: the arb snapshot is on the data-arb branch; the Worker /api/odds feed is top-league focused.")
    remote_timeout = st.number_input("Remote timeout (seconds)", min_value=5, value=30, step=5)
    persist_remote = st.checkbox("Append remote snapshot locally", value=False)
    persist_db = st.checkbox("Write to history DB", value=True, disabled=not persist_remote)
    persist_jsonl = st.checkbox("Write to history JSONL", value=False, disabled=not persist_remote)
    st.subheader("Remote History (D1)")
    default_history_url = os.getenv(
        "REMOTE_HISTORY_URL",
        "https://oddswize-api.kwamenahb.workers.dev",
    )
    use_remote_history = st.checkbox("Use remote history API", value=False)
    remote_history_url = st.text_input("Remote history base URL", value=default_history_url)
    remote_history_timeout = st.number_input("History timeout (seconds)", min_value=5, value=20, step=5)
    remote_history_api_key = st.text_input("History API key (optional)", value="", type="password")

    st.subheader("Live Updates")
    refresh_seconds = st.number_input("Auto refresh (seconds)", min_value=0, value=0, step=5)
    auto_refresh_remote = st.checkbox("Auto refresh when using remote data", value=True)
    refresh_clicked = st.button("Refresh now")
    effective_refresh = refresh_seconds
    if effective_refresh <= 0 and auto_refresh_remote and (use_remote or use_remote_history):
        effective_refresh = 180
    if effective_refresh > 0:
        if hasattr(st, "autorefresh"):
            st.autorefresh(interval=int(effective_refresh * 1000), key="auto_refresh")
        else:
            st.info("Upgrade Streamlit for auto-refresh support; use Refresh now.")
    force_refresh = refresh_clicked or effective_refresh > 0
    if force_refresh:
        st.cache_data.clear()
        st.session_state["last_refresh_ts"] = datetime.utcnow().isoformat()
        st.session_state["effective_refresh_seconds"] = int(effective_refresh) if effective_refresh else None
        if refresh_clicked:
            rerun = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
            if rerun:
                rerun()

    st.subheader("Date Filters")
    run_range = st.date_input(
        "Snapshot run date range", value=(default_start, today)
    )
    match_filter_on = st.checkbox("Filter by match start date", value=False)
    match_range = st.date_input(
        "Match start date range",
        value=(default_start, today + timedelta(days=7)),
        disabled=not match_filter_on,
    )

    st.subheader("Strategy")
    strategy = st.selectbox(
        "Strategy",
        (
            "Arbitrage (guaranteed when executed)",
            "Consensus Edge (model-free, not guaranteed)",
            "Closing Line Value (CLV)",
            "Price Movement (Line Drift)",
            "Liquidity/Age Filters",
        ),
    )

    st.subheader("Controls")
    bankroll = st.number_input("Bankroll per opportunity", min_value=10.0, value=1000.0, step=50.0)
    min_roi = st.slider("Minimum arb ROI (raw)", min_value=0.0, max_value=0.1, value=0.0, step=0.0025)
    slippage_pct = st.slider("Slippage buffer (%)", min_value=0.0, max_value=0.05, value=0.005, step=0.0025)
    execution_lag_seconds = st.number_input("Execution lag (seconds)", min_value=0, value=20, step=5)
    slippage_per_min_pct = st.slider(
        "Slippage per minute (%)", min_value=0.0, max_value=0.02, value=0.001, step=0.0005
    )
    min_minutes_to_kickoff = st.number_input(
        "Min minutes to kickoff", min_value=0, value=5, step=1, key="min_minutes_to_kickoff"
    )
    max_snapshot_age_minutes = st.number_input(
        "Max snapshot age (minutes)", min_value=0, value=15, step=5, key="max_snapshot_age_minutes"
    )
    auto_relax_filters = st.checkbox("Auto relax filters if empty", value=True)
    show_quick_links = st.checkbox("Show quick links in tables", value=True)
    allow_search_links = st.checkbox("Include search links (fallback)", value=False)
    st.subheader("CLV Filters")
    use_clv_filter = st.checkbox("Only show picks with positive historical CLV", value=False)
    clv_min_pos_rate = st.slider(
        "Min positive CLV rate",
        min_value=0.0,
        max_value=1.0,
        value=0.55,
        step=0.05,
        disabled=not use_clv_filter,
    )
    clv_min_median_pct = st.slider(
        "Min median CLV (%)",
        min_value=-5.0,
        max_value=5.0,
        value=0.0,
        step=0.25,
        disabled=not use_clv_filter,
    )
    clv_min_matches = st.number_input(
        "Min CLV samples",
        min_value=5,
        value=20,
        step=5,
        disabled=not use_clv_filter,
    )
    st.subheader("Local League Filter")
    filter_local_leagues = st.checkbox("Auto-filter low-liquidity local leagues", value=True)
    local_league_keywords = st.text_input(
        "Local league keywords (comma-separated)",
        value="Ghana",
        disabled=not filter_local_leagues,
    )
    local_min_bookies = st.number_input(
        "Min bookies for local leagues",
        min_value=1,
        value=3,
        step=1,
        disabled=not filter_local_leagues,
    )
    st.subheader("Liquidity Weighting")
    use_liquidity_weight = st.checkbox("Liquidity-weighted staking", value=True)
    liq_target_bookies = st.number_input(
        "Target bookies for full weight",
        min_value=1,
        value=6,
        step=1,
        disabled=not use_liquidity_weight,
    )
    liq_max_age = st.number_input(
        "Max snapshot age for full weight (min)",
        min_value=1,
        value=10,
        step=1,
        disabled=not use_liquidity_weight,
    )
    liq_target_kickoff = st.number_input(
        "Minutes to kickoff for full weight",
        min_value=1,
        value=60,
        step=5,
        disabled=not use_liquidity_weight,
    )
    st.subheader("Research Log")
    research_db_path = st.text_input("Research DB path", value=DEFAULT_RESEARCH_DB_PATH)
    log_mode = st.selectbox("Log mode", ("paper", "live"), index=0)
    min_roi_adj = st.slider(
        "Minimum arb ROI (after slippage)",
        min_value=0.0,
        max_value=0.1,
        value=0.0,
        step=0.0025,
    )
    max_roi_adj = st.slider(
        "Maximum arb ROI (after slippage)",
        min_value=0.05,
        max_value=1.0,
        value=0.5,
        step=0.05,
    )
    min_edge = st.slider(
        "Minimum consensus edge",
        min_value=-0.1,
        max_value=0.2,
        value=0.0,
        step=0.005,
    )
    st.subheader("Results Backtest Settings")
    stake_per_arb = st.number_input("Stake per arb (results)", min_value=1.0, value=bankroll, step=10.0)
    fill_prob = st.slider("Leg fill probability", min_value=0.5, max_value=1.0, value=0.9, step=0.02)
    cancel_on_incomplete = st.checkbox("Cancel if any leg fails", value=False)
    stake_per_pick = st.number_input("Stake per pick (edge results)", min_value=1.0, value=bankroll, step=10.0)
    max_rows = st.number_input("Max rows to load", min_value=5000, value=200000, step=5000)

    st.subheader("Compounding Simulator")
    initial_bankroll = st.number_input("Initial bankroll", min_value=10.0, value=200.0, step=10.0)
    reserve_pct = st.slider("Reserve % (cash buffer)", min_value=0.0, max_value=0.5, value=0.1, step=0.02)
    max_daily_exposure_pct = st.slider(
        "Max daily exposure % of bankroll", min_value=0.1, max_value=1.0, value=0.7, step=0.05
    )
    per_event_cap_pct = st.slider(
        "Max exposure % per event", min_value=0.01, max_value=0.5, value=0.1, step=0.01
    )
    per_bookie_cap_pct = st.slider(
        "Max exposure % per bookmaker", min_value=0.05, max_value=1.0, value=0.25, step=0.05
    )
    max_arbs_per_day = st.number_input("Max arbs per day", min_value=1, value=20, step=1)
    pick_priority = st.selectbox("Pick order", ("ROI", "Profit"), index=0)


def _unpack_range(value):
    if isinstance(value, tuple) or isinstance(value, list):
        return value[0], value[1]
    return value, value


def _filter_rows(rows, run_start_value, run_end_value, match_start_value, match_end_value):
    if rows is None or rows.empty:
        return rows
    filtered = rows.copy()
    if run_start_value or run_end_value:
        run_time = pd.to_datetime(filtered["last_updated"], errors="coerce", utc=True)
        if run_start_value:
            start_dt = datetime.combine(run_start_value, datetime.min.time()).replace(tzinfo=timezone.utc)
            filtered = filtered[run_time >= start_dt]
        if run_end_value:
            end_dt = datetime.combine(run_end_value, datetime.max.time()).replace(tzinfo=timezone.utc)
            filtered = filtered[run_time <= end_dt]
    if match_start_value or match_end_value:
        start_time = pd.to_numeric(filtered["start_time"], errors="coerce")
        if match_start_value:
            start_epoch = int(
                datetime.combine(match_start_value, datetime.min.time()).replace(tzinfo=timezone.utc).timestamp()
            )
            filtered = filtered[start_time >= start_epoch]
        if match_end_value:
            end_epoch = int(
                datetime.combine(match_end_value, datetime.max.time()).replace(tzinfo=timezone.utc).timestamp()
            )
            filtered = filtered[start_time <= end_epoch]
    return filtered


@st.cache_data(show_spinner=False)
def _load_remote_rows(url: str, timeout_seconds: int):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "OddsWizeTerminal/1.0 (+https://oddswize.com)",
        },
    )
    last_exc = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as handle:
                payload = json.load(handle)
            rows = rows_from_odds_payload(payload)
            return rows, payload
        except Exception as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(1 + attempt)
                continue
            break
    raise last_exc


@st.cache_data(show_spinner=False)
def _load_remote_history_rows(base_url: str, params: dict, timeout_seconds: int, api_key: Optional[str]):
    base = (base_url or "").rstrip("/")
    endpoint = f"{base}/api/history/odds"
    query = urllib.parse.urlencode(params)
    url = f"{endpoint}?{query}" if query else endpoint
    headers = {
        "Accept": "application/json",
        "User-Agent": "OddsWizeTerminal/1.0 (+https://oddswize.com)",
    }
    if api_key:
        headers["X-API-Key"] = api_key
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as handle:
            payload = json.load(handle)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{exc.code} {exc.reason} for {url}") from exc
    rows = payload.get("data") or []
    return pd.DataFrame(rows), payload


def _check_history_api(base_url: str, timeout_seconds: int, api_key: Optional[str]) -> dict:
    base = (base_url or "").rstrip("/")
    endpoints = {
        "runs": f"{base}/api/history/runs?limit=1",
        "odds": f"{base}/api/history/odds?limit=1",
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": "OddsWizeTerminal/1.0 (+https://oddswize.com)",
    }
    if api_key:
        headers["X-API-Key"] = api_key
    results = {}
    for name, url in endpoints.items():
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as handle:
                payload = json.load(handle)
            results[name] = {
                "ok": True,
                "status": 200,
                "returned": len(payload.get("data") or []),
            }
        except Exception as exc:
            results[name] = {"ok": False, "error": str(exc)}
    return results


def _build_best_lines(
    rows: pd.DataFrame,
    include_bookmakers: Optional[Iterable[str]] = None,
    include_leagues: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    lines = build_best_lines(rows, include_bookmakers=include_bookmakers, include_leagues=include_leagues)
    if lines is None or lines.empty:
        return pd.DataFrame()
    lines["run_time"] = pd.to_datetime(lines["run_time"], errors="coerce", utc=True)
    lines["match_start"] = pd.to_datetime(lines["match_start"], errors="coerce", utc=True)
    return lines


def _build_open_close(lines: pd.DataFrame) -> pd.DataFrame:
    if lines is None or lines.empty:
        return pd.DataFrame()

    df = lines.copy()
    df = df.dropna(subset=["run_time"])
    if df.empty:
        return pd.DataFrame()

    df = df.sort_values("run_time")
    open_df = df.groupby("match_id", as_index=False).first()

    def pick_close(group: pd.DataFrame) -> pd.Series:
        cutoff = group["match_start"].iloc[0]
        if pd.notna(cutoff):
            pre = group[group["run_time"] <= cutoff]
            if not pre.empty:
                return pre.iloc[-1]
        return group.iloc[-1]

    close_df = df.groupby("match_id", group_keys=False).apply(pick_close).reset_index(drop=True)
    merged = open_df.merge(close_df, on="match_id", suffixes=("_open", "_close"))
    return merged


@st.cache_data(show_spinner=False)
def _load_rows_cached(
    db_path_value,
    jsonl_path_value,
    run_start_value,
    run_end_value,
    match_start_value,
    match_end_value,
    max_rows_value,
    allow_jsonl,
):
    try:
        return load_snapshot_rows(
            db_path=db_path_value,
            run_start=run_start_value,
            run_end=run_end_value,
            match_start=match_start_value,
            match_end=match_end_value,
            limit=int(max_rows_value) if max_rows_value else None,
        )
    except FileNotFoundError:
        if not allow_jsonl:
            raise
        return load_snapshot_rows_from_jsonl(
            jsonl_path=jsonl_path_value,
            run_start=run_start_value,
            run_end=run_end_value,
        )


run_start, run_end = _unpack_range(run_range)
match_start, match_end = _unpack_range(match_range) if match_filter_on else (None, None)

append_snapshot_now = False
payload_snapshot = None

with st.spinner("Loading history..."):
    rows = None
    if use_remote_history:
        params = {}
        if run_start:
            params["run_start"] = datetime.combine(run_start, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
        if run_end:
            params["run_end"] = datetime.combine(run_end, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()
        if match_start:
            params["match_start"] = int(
                datetime.combine(match_start, datetime.min.time()).replace(tzinfo=timezone.utc).timestamp()
            )
        if match_end:
            params["match_end"] = int(
                datetime.combine(match_end, datetime.max.time()).replace(tzinfo=timezone.utc).timestamp()
            )
        if max_rows:
            params["limit"] = int(max_rows)
        try:
            rows, payload_snapshot = _load_remote_history_rows(
                remote_history_url,
                params,
                int(remote_history_timeout),
                remote_history_api_key.strip() or None,
            )
        except Exception as exc:
            st.warning(f"Remote history failed: {exc}")
            rows = None

    if rows is None and use_remote:
        try:
            rows, payload_snapshot = _load_remote_rows(remote_url, int(remote_timeout))
            rows = _filter_rows(rows, run_start, run_end, match_start, match_end)
            if max_rows and rows is not None:
                rows = rows.head(int(max_rows))
        except Exception as exc:
            st.warning(f"Remote snapshot failed: {exc}")
            rows = None

if rows is None:
        try:
            rows = _load_rows_cached(
                db_path,
                jsonl_path,
                run_start,
                run_end,
                match_start,
                match_end,
                max_rows,
                allow_jsonl_fallback,
            )
        except FileNotFoundError as exc:
            st.error(str(exc))
            st.stop()

if rows is not None and filter_local_leagues:
    keyword_list = [kw.strip() for kw in (local_league_keywords or "").split(",") if kw.strip()]
    if keyword_list:
        rows = _filter_low_liquidity_local_leagues(rows, keyword_list, int(local_min_bookies))

if payload_snapshot and persist_remote and isinstance(payload_snapshot, dict) and payload_snapshot.get("matches"):
    run_id = payload_snapshot.get("run_id") or payload_snapshot.get("last_updated")
    key = f"snapshot_appended_{run_id}"
    already_appended = st.session_state.get(key, False)
    append_label = "Snapshot appended" if already_appended else "Append snapshot now"
    if st.sidebar.button(append_label, disabled=already_appended):
        if persist_db:
            append_snapshot_to_history_db(payload_snapshot, db_path)
        if persist_jsonl:
            append_snapshot_to_history_jsonl(payload_snapshot, jsonl_path)
        st.session_state[key] = True
        st.sidebar.success("Snapshot appended to local history")

with st.sidebar:
    st.subheader("History API Health")
    st.caption("Checks /api/history/runs and /api/history/odds on the remote history base URL.")
    if "history_health_status" not in st.session_state:
        st.session_state["history_health_status"] = None
    history_key = remote_history_api_key.strip() or None
    can_check = bool(remote_history_url.strip())
    if st.button("Run history health check", disabled=not can_check):
        with st.spinner("Checking history API..."):
            st.session_state["history_health_status"] = _check_history_api(
                remote_history_url,
                int(remote_history_timeout),
                history_key,
            )
    if not can_check:
        st.warning("Set a remote history base URL to run the health check.")
    results = st.session_state.get("history_health_status")
    if results:
        for name, result in results.items():
            if result.get("ok"):
                st.success(f"{name}: ok (returned {result.get('returned', 0)})")
            else:
                st.error(f"{name}: {result.get('error', 'failed')}")

if rows.empty:
    st.warning("No odds history found for the selected range.")
    st.stop()

st.subheader("Snapshot Summary")
last_updated = pd.to_datetime(rows["last_updated"], errors="coerce", utc=True)
latest_ts = last_updated.max() if not last_updated.empty else None
latest_label = latest_ts.strftime("%Y-%m-%d %H:%M UTC") if pd.notna(latest_ts) else "Unknown"
snapshot_age = None
if pd.notna(latest_ts):
    snapshot_age = (datetime.now(timezone.utc) - latest_ts).total_seconds() / 60.0

summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
summary_col1.metric("Rows", f"{len(rows):,}")
summary_col2.metric("Matches", f"{rows['match_id'].nunique():,}")
summary_col3.metric("Bookmakers", f"{rows['bookmaker'].nunique():,}")
summary_col4.metric("Latest snapshot", latest_label)
if snapshot_age is not None:
    st.caption(f"Snapshot age: {snapshot_age:.1f} min")
    if max_snapshot_age_minutes > 0 and snapshot_age > float(max_snapshot_age_minutes):
        st.warning(
            "Latest snapshot is older than your max snapshot age filter. "
            "Increase the limit or refresh data to see opportunities."
        )
        if st.button("Set max snapshot age to latest", key="set_max_snapshot_age"):
            st.session_state["override_max_snapshot_age_minutes"] = int(math.ceil(snapshot_age))
            rerun = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
            if rerun:
                rerun()
last_refresh_ts = st.session_state.get("last_refresh_ts")
if last_refresh_ts:
    st.caption(f"Last refresh: {last_refresh_ts} UTC")
effective_refresh_note = st.session_state.get("effective_refresh_seconds")
if effective_refresh_note:
    st.caption(f"Auto refresh: every {effective_refresh_note}s")

available_leagues = sorted([l for l in rows["league"].dropna().unique() if str(l).strip()])
available_bookies = sorted([b for b in rows["bookmaker"].dropna().unique() if str(b).strip()])

with st.sidebar:
    st.subheader("Filters")
    selected_leagues = st.multiselect("Leagues", available_leagues, default=available_leagues)
    selected_bookies = st.multiselect("Bookmakers", available_bookies, default=available_bookies)

clv_table_cached = None
clv_league_stats = pd.DataFrame()
if use_clv_filter:
    with st.spinner("Computing CLV filter..."):
        lines_for_clv = _build_best_lines(rows, include_bookmakers=selected_bookies, include_leagues=selected_leagues)
        clv_table_cached = _compute_clv_table(lines_for_clv)
        clv_league_stats = _compute_clv_league_stats(clv_table_cached)
    if clv_league_stats.empty:
        st.info("CLV filter enabled, but not enough history to compute CLV stats.")

st.divider()
with st.expander("Target Growth Calculator", expanded=True):
    growth_col1, growth_col2, growth_col3, growth_col4 = st.columns(4)
    with growth_col1:
        target_start = st.number_input(
            "Starting bankroll", min_value=1.0, value=200.0, step=10.0, key="target_start"
        )
    with growth_col2:
        target_goal = st.number_input(
            "Target bankroll", min_value=10.0, value=100000.0, step=1000.0, key="target_goal"
        )
    with growth_col3:
        target_days = st.number_input("Days to target", min_value=1, value=365, step=1, key="target_days")
    with growth_col4:
        target_exposure = st.slider(
            "Avg daily exposure %", min_value=0.1, max_value=1.0, value=0.7, step=0.05, key="target_exposure"
        )

if target_start > 0 and target_goal > 0 and target_days > 0:
    required_daily_growth = (target_goal / target_start) ** (1 / target_days) - 1
    required_roi_on_exposure = required_daily_growth / max(target_exposure, 0.01)
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("Required daily growth", f"{required_daily_growth*100:.2f}%")
    metric_col2.metric("Day 1 profit needed", f"{target_start*required_daily_growth:,.2f}")
    metric_col3.metric("ROI on exposed capital", f"{required_roi_on_exposure*100:.2f}%")
    st.caption(
        "This is a math target, not a guarantee. It assumes daily compounding at the required rate."
    )

if strategy.startswith("Arbitrage"):
    st.info("Market coverage: 1X2 odds only. Add totals/BTTS to the scraper to expand.")
    arbs, matches = compute_arbitrage_opportunities(
        rows,
        bankroll=bankroll,
        min_roi=min_roi,
        include_bookmakers=selected_bookies,
        include_leagues=selected_leagues,
    )
    summary = summarize_arbitrage(arbs, matches)
    effective_slippage = slippage_pct + (float(execution_lag_seconds) / 60.0) * float(slippage_per_min_pct)
    effective_slippage = max(0.0, min(0.2, effective_slippage))
    arbs_adj = add_slippage_adjustment(arbs, slippage_pct=effective_slippage)
    if not arbs_adj.empty:
        min_roi_adj_value = float(min_roi_adj or 0.0)
        max_roi_adj_value = float(max_roi_adj or 0.0)
        arbs_adj = arbs_adj[arbs_adj["arb_roi_adj"] >= min_roi_adj_value]
        if max_roi_adj_value > 0:
            arbs_adj = arbs_adj[arbs_adj["arb_roi_adj"] <= max_roi_adj_value]

    if not arbs_adj.empty:
        now_utc = datetime.now(timezone.utc)
        arbs_adj["run_time"] = pd.to_datetime(arbs_adj["run_time"], errors="coerce", utc=True)
        arbs_adj["match_start"] = pd.to_datetime(arbs_adj["match_start"], errors="coerce", utc=True)
        arbs_adj["snapshot_age_min"] = (now_utc - arbs_adj["run_time"]).dt.total_seconds() / 60.0
        arbs_adj["kickoff_minutes"] = (arbs_adj["match_start"] - now_utc).dt.total_seconds() / 60.0

    arbs_filtered = arbs_adj
    if not arbs_adj.empty:
        if max_snapshot_age_minutes > 0:
            arbs_filtered = arbs_filtered[arbs_filtered["snapshot_age_min"] <= float(max_snapshot_age_minutes)]
        if min_minutes_to_kickoff > 0:
            arbs_filtered = arbs_filtered[arbs_filtered["kickoff_minutes"] >= float(min_minutes_to_kickoff)]
        if use_clv_filter and not clv_league_stats.empty:
            clv_min_median = float(clv_min_median_pct) / 100.0
            arbs_filtered = arbs_filtered.merge(clv_league_stats, on="league", how="left")
            arbs_filtered = arbs_filtered[
                (arbs_filtered["clv_matches"] >= int(clv_min_matches))
                & (arbs_filtered["clv_pos_rate"] >= float(clv_min_pos_rate))
                & (arbs_filtered["clv_median"] >= clv_min_median)
            ]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Matches", f"{summary['matches']:,}")
    col2.metric("Arb Opportunities (raw)", f"{summary['arbs']:,}")
    col3.metric("Avg ROI (raw)", f"{summary['avg_roi']*100:.2f}%")
    col4.metric("Max ROI (raw)", f"{summary['max_roi']*100:.2f}%")

    adj_count = int(arbs_adj["match_id"].nunique()) if not arbs_adj.empty else 0
    adj_avg = float(arbs_adj["arb_roi_adj"].mean()) if not arbs_adj.empty else 0.0
    adj_max = float(arbs_adj["arb_roi_adj"].max()) if not arbs_adj.empty else 0.0
    filt_count = int(arbs_filtered["match_id"].nunique()) if not arbs_filtered.empty else 0
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Arbs after slippage", f"{adj_count:,}")
    col6.metric("Avg ROI (adj)", f"{adj_avg*100:.2f}%")
    col7.metric("Max ROI (adj)", f"{adj_max*100:.2f}%")
    col8.metric("Arbs after age/lag", f"{filt_count:,}")

    if arbs.empty:
        st.warning("No arbitrage opportunities found for this slice.")
    else:
        if arbs_filtered.empty:
            if auto_relax_filters and not st.session_state.get("auto_relax_done", False):
                adjustments = []
                max_age_value = float(max_snapshot_age_minutes)
                min_kickoff_value = float(min_minutes_to_kickoff)
                if max_age_value > 0:
                    min_age = float(arbs_adj["snapshot_age_min"].min())
                    if min_age > max_age_value:
                        new_age = int(math.ceil(min_age))
                        st.session_state["override_max_snapshot_age_minutes"] = new_age
                        adjustments.append(f"max snapshot age -> {new_age} min")
                if min_kickoff_value > 0:
                    max_kickoff = float(arbs_adj["kickoff_minutes"].max())
                    if max_kickoff < min_kickoff_value:
                        new_kickoff = max(0, int(math.floor(max_kickoff)))
                        st.session_state["override_min_minutes_to_kickoff"] = new_kickoff
                        adjustments.append(f"min kickoff -> {new_kickoff} min")
                if adjustments:
                    st.session_state["auto_relax_done"] = True
                    st.info("Auto-relaxed filters: " + ", ".join(adjustments))
                    rerun = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
                    if rerun:
                        rerun()
                        st.stop()
            st.warning(
                "No arbitrage opportunities remain after slippage + age/lag filters "
                f"(max snapshot age {max_snapshot_age_minutes} min, min kickoff {min_minutes_to_kickoff} min)."
            )
            if arbs_adj.empty:
                st.stop()
            st.info("Showing opportunities without age/lag filters so rows are visible.")
            arbs_filtered = arbs_adj.copy()
        st.session_state["auto_relax_done"] = False
        arbs_filtered["run_date"] = pd.to_datetime(arbs_filtered["run_time"], errors="coerce").dt.date
        daily = (
            arbs_filtered.groupby("run_date", dropna=True)
            .agg(count=("match_id", "count"), avg_roi=("arb_roi_adj", "mean"))
            .reset_index()
        )

        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            fig = px.bar(daily, x="run_date", y="count", title="Arbitrage Count by Run Date")
            st.plotly_chart(fig, use_container_width=True)
        with chart_col2:
            fig = px.line(daily, x="run_date", y="avg_roi", title="Average ROI by Run Date")
            st.plotly_chart(fig, use_container_width=True)

        chart_col3, chart_col4 = st.columns(2)
        with chart_col3:
            fig = px.histogram(arbs_filtered, x="arb_roi_adj", nbins=30, title="ROI Distribution (Adj)")
            st.plotly_chart(fig, use_container_width=True)
        with chart_col4:
            top_leagues = (
                arbs_filtered.groupby("league")["match_id"].count().sort_values(ascending=False).head(12).reset_index()
            )
            fig = px.bar(top_leagues, x="league", y="match_id", title="Top Leagues by Arb Count")
            st.plotly_chart(fig, use_container_width=True)

        if show_quick_links:
            event_lookup = _build_event_lookup(rows)
            if not event_lookup and remote_url:
                try:
                    snapshot_rows_for_links, _ = _load_remote_rows(remote_url, min(int(remote_timeout), 10))
                    event_lookup = _build_event_lookup(snapshot_rows_for_links)
                except Exception:
                    event_lookup = {}
            if event_lookup:
                arbs_filtered = _apply_event_lookup(arbs_filtered, event_lookup)

        st.subheader("Top Arbitrage Opportunities")
        display_cols = [
            "run_time",
            "league",
            "home_team",
            "away_team",
            "match_start",
            "snapshot_age_min",
            "kickoff_minutes",
            "home_odds_adj",
            "draw_odds_adj",
            "away_odds_adj",
            "best_home_bookie",
            "best_draw_bookie",
            "best_away_bookie",
            "arb_roi_adj",
        ]
        event_cols = [
            col
            for col in (
                "best_home_event_id",
                "best_draw_event_id",
                "best_away_event_id",
                "best_home_league_id",
                "best_draw_league_id",
                "best_away_league_id",
            )
            if col in arbs_filtered.columns
        ]
        table = arbs_filtered[display_cols + event_cols].copy()
        table["arb_roi_adj_pct"] = table["arb_roi_adj"] * 100
        link_cols = []
        column_config = None
        if show_quick_links:
            table["home_link"] = table.apply(
                lambda row: _build_bookie_event_url(
                    row.get("best_home_bookie"),
                    row.get("best_home_event_id"),
                    row.get("home_team"),
                    row.get("away_team"),
                    row.get("league"),
                    row.get("best_home_league_id"),
                ),
                axis=1,
            )
            table["draw_link"] = table.apply(
                lambda row: _build_bookie_event_url(
                    row.get("best_draw_bookie"),
                    row.get("best_draw_event_id"),
                    row.get("home_team"),
                    row.get("away_team"),
                    row.get("league"),
                    row.get("best_draw_league_id"),
                ),
                axis=1,
            )
            table["away_link"] = table.apply(
                lambda row: _build_bookie_event_url(
                    row.get("best_away_bookie"),
                    row.get("best_away_event_id"),
                    row.get("home_team"),
                    row.get("away_team"),
                    row.get("league"),
                    row.get("best_away_league_id"),
                ),
                axis=1,
            )
            link_cols = ["home_link", "draw_link", "away_link"]
            if allow_search_links:
                table["match_search"] = table.apply(
                    lambda row: _build_search_url(
                        row.get("home_team"),
                        "vs",
                        row.get("away_team"),
                        row.get("league"),
                        "odds",
                    ),
                    axis=1,
                )
                link_cols = ["match_search"] + link_cols
            if hasattr(st, "column_config"):
                column_config = {
                    "home_link": st.column_config.LinkColumn("Home bookie", display_text="Open"),
                    "draw_link": st.column_config.LinkColumn("Draw bookie", display_text="Open"),
                    "away_link": st.column_config.LinkColumn("Away bookie", display_text="Open"),
                }
                if allow_search_links:
                    column_config["match_search"] = st.column_config.LinkColumn("Match search", display_text="Open")

            if not table.empty:
                home_cov = (table["home_link"] != "").mean()
                draw_cov = (table["draw_link"] != "").mean()
                away_cov = (table["away_link"] != "").mean()
                st.caption(
                    "Direct link coverage — "
                    f"Home {home_cov*100:.0f}%, Draw {draw_cov*100:.0f}%, Away {away_cov*100:.0f}%."
                )
                if min(home_cov, draw_cov, away_cov) < 0.25:
                    st.warning(
                        "Direct links are missing for most rows. "
                        "This usually means the current data source lacks event IDs."
                    )

        display_table = table[link_cols + display_cols].copy() if link_cols else table[display_cols].copy()
        if column_config:
            st.dataframe(display_table.head(300), use_container_width=True, column_config=column_config)
        else:
            st.dataframe(display_table.head(300), use_container_width=True)

        csv_data = display_table.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv_data, file_name="arbitrage_opportunities_adjusted.csv")

        st.subheader("Stake Allocator (Arb)")
        allocator_base_cols = [
            "run_time",
            "match_id",
            "league",
            "home_team",
            "away_team",
            "match_start",
            "snapshot_age_min",
            "kickoff_minutes",
            "bookie_count",
            "home_odds_adj",
            "draw_odds_adj",
            "away_odds_adj",
            "best_home_bookie",
            "best_draw_bookie",
            "best_away_bookie",
            "arb_roi_adj",
        ]
        allocator_event_cols = [
            col
            for col in ("best_home_event_id", "best_draw_event_id", "best_away_event_id")
            if col in arbs_filtered.columns
        ]
        allocator_event_cols += [
            col
            for col in ("best_home_league_id", "best_draw_league_id", "best_away_league_id")
            if col in arbs_filtered.columns
        ]
        allocator_table = arbs_filtered[allocator_base_cols + allocator_event_cols].copy()
        allocator_cols = [
            col
            for col in allocator_base_cols
            if col not in ("match_id", "snapshot_age_min", "kickoff_minutes", "bookie_count")
        ]
        allocator_table["pick_label"] = (
            allocator_table["home_team"].fillna("")
            + " vs "
            + allocator_table["away_team"].fillna("")
            + " - "
            + allocator_table["league"].fillna("")
        )
        selected_idx = None
        try:
            selection = st.dataframe(
                allocator_table[allocator_cols].head(300),
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
            )
            if selection and selection.selection and selection.selection.rows:
                selected_idx = selection.selection.rows[0]
        except TypeError:
            st.dataframe(allocator_table[allocator_cols].head(300), use_container_width=True)

        if selected_idx is None:
            pick_label = st.selectbox("Select a pick", allocator_table["pick_label"].head(300).tolist())
            selected_row = allocator_table[allocator_table["pick_label"] == pick_label].iloc[0]
        else:
            selected_row = allocator_table.iloc[selected_idx]

        stake_total = st.number_input(
            "Total stake to allocate", min_value=1.0, value=100.0, step=10.0, key="stake_allocator_total"
        )
        liquidity_score = None
        effective_stake = float(stake_total)
        if use_liquidity_weight:
            liquidity_score = _compute_liquidity_score(
                selected_row.get("bookie_count"),
                selected_row.get("snapshot_age_min"),
                selected_row.get("kickoff_minutes"),
                float(liq_target_bookies),
                float(liq_max_age),
                float(liq_target_kickoff),
            )
            effective_stake = float(stake_total) * float(liquidity_score)
        odds_home = float(selected_row["home_odds_adj"])
        odds_draw = float(selected_row["draw_odds_adj"])
        odds_away = float(selected_row["away_odds_adj"])
        inv_sum = (1 / odds_home) + (1 / odds_draw) + (1 / odds_away)
        stake_home = effective_stake / (odds_home * inv_sum)
        stake_draw = effective_stake / (odds_draw * inv_sum)
        stake_away = effective_stake / (odds_away * inv_sum)
        payout = effective_stake / inv_sum
        profit = payout - effective_stake

        alloc_col1, alloc_col2, alloc_col3, alloc_col4 = st.columns(4)
        alloc_col1.metric("Home stake", f"{stake_home:,.2f}")
        alloc_col2.metric("Draw stake", f"{stake_draw:,.2f}")
        alloc_col3.metric("Away stake", f"{stake_away:,.2f}")
        alloc_col4.metric("Guaranteed profit", f"{profit:,.2f}")
        roi_value = (profit / effective_stake) * 100 if effective_stake else 0.0
        st.caption(
            f"Payout per outcome: {payout:,.2f} - ROI: {roi_value:.2f}%"
        )
        if use_liquidity_weight:
            liq_cols = st.columns(2)
            liq_cols[0].metric("Liquidity score", f"{float(liquidity_score or 0.0):.2f}")
            liq_cols[1].metric("Liquidity-weighted stake", f"{effective_stake:,.2f}")
        if show_quick_links:
            match_link = _build_search_url(
                selected_row.get("home_team"),
                "vs",
                selected_row.get("away_team"),
                selected_row.get("league"),
            )
            home_link = _build_bookie_event_url(
                selected_row.get("best_home_bookie"),
                selected_row.get("best_home_event_id"),
                selected_row.get("home_team"),
                selected_row.get("away_team"),
                selected_row.get("league"),
                selected_row.get("best_home_league_id"),
            )
            draw_link = _build_bookie_event_url(
                selected_row.get("best_draw_bookie"),
                selected_row.get("best_draw_event_id"),
                selected_row.get("home_team"),
                selected_row.get("away_team"),
                selected_row.get("league"),
                selected_row.get("best_draw_league_id"),
            )
            away_link = _build_bookie_event_url(
                selected_row.get("best_away_bookie"),
                selected_row.get("best_away_event_id"),
                selected_row.get("home_team"),
                selected_row.get("away_team"),
                selected_row.get("league"),
                selected_row.get("best_away_league_id"),
            )
            link_col1, link_col2, link_col3, link_col4 = st.columns(4)
            with link_col1:
                _render_link_button("Match search", match_link)
            with link_col2:
                _render_link_button("Home bookie", home_link)
            with link_col3:
                _render_link_button("Draw bookie", draw_link)
            with link_col4:
                _render_link_button("Away bookie", away_link)

        log_note = st.text_input("Research note (optional)", value="", key="arb_log_note")
        if st.button("Log arb pick", key="log_arb_pick"):
            bookie_label = (
                f"home:{selected_row.get('best_home_bookie')} | "
                f"draw:{selected_row.get('best_draw_bookie')} | "
                f"away:{selected_row.get('best_away_bookie')}"
            )
            expected_roi = float(selected_row.get("arb_roi_adj") or 0.0)
            pick_id = _append_research_pick(
                research_db_path,
                {
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "mode": log_mode,
                    "strategy": "arb",
                    "match_id": selected_row.get("match_id"),
                    "league": selected_row.get("league"),
                    "start_time": int(pd.to_datetime(selected_row.get("match_start"), errors="coerce").timestamp())
                    if pd.notna(selected_row.get("match_start")) else 0,
                    "home_team": selected_row.get("home_team"),
                    "away_team": selected_row.get("away_team"),
                    "bookmaker": bookie_label,
                    "outcome": "arb",
                    "odds": None,
                    "stake": float(stake_total),
                    "expected_roi": expected_roi,
                    "expected_profit": float(profit),
                    "source_run_time": selected_row.get("run_time"),
                    "notes": log_note.strip(),
                    "status": "open",
                },
            )
            if pick_id is not None and float(stake_total) > 0:
                _append_cash_entry(
                    research_db_path,
                    -float(stake_total),
                    "stake_locked",
                    pick_id=int(pick_id),
                    note="arb",
                )
            st.success("Arb pick logged to research database.")

        st.subheader("Daily Compounding Simulator (Arb)")
        st.caption(
            "Simulates daily compounding using adjusted odds. This is theoretical and assumes "
            "all legs are filled at the adjusted prices."
        )
        daily_sim, picks_sim = simulate_daily_compounding(
            arbs_filtered,
            initial_bankroll=initial_bankroll,
            reserve_pct=reserve_pct,
            max_daily_exposure_pct=max_daily_exposure_pct,
            per_event_cap_pct=per_event_cap_pct,
            per_bookie_cap_pct=per_bookie_cap_pct,
            max_arbs_per_day=max_arbs_per_day,
            min_roi=min_roi_adj,
            selection="roi" if pick_priority == "ROI" else "profit",
        )
        if daily_sim.empty:
            st.warning("Simulator found no opportunities under current constraints.")
        else:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Start Bankroll", f"{daily_sim['bankroll_start'].iloc[0]:,.2f}")
            col2.metric("End Bankroll", f"{daily_sim['bankroll_end'].iloc[-1]:,.2f}")
            total_return = daily_sim["bankroll_end"].iloc[-1] / daily_sim["bankroll_start"].iloc[0] - 1
            col3.metric("Total Return", f"{total_return*100:.2f}%")
            avg_daily = daily_sim["profit"].mean()
            col4.metric("Avg Daily Profit", f"{avg_daily:,.2f}")

            sim_col1, sim_col2 = st.columns(2)
            with sim_col1:
                fig = px.line(daily_sim, x="run_date", y="bankroll_end", title="Simulated Bankroll")
                st.plotly_chart(fig, use_container_width=True)
            with sim_col2:
                fig = px.bar(daily_sim, x="run_date", y="profit", title="Simulated Daily Profit")
                st.plotly_chart(fig, use_container_width=True)

            sim_col3, sim_col4 = st.columns(2)
            with sim_col3:
                fig = px.bar(daily_sim, x="run_date", y="exposure", title="Daily Exposure")
                st.plotly_chart(fig, use_container_width=True)
            with sim_col4:
                fig = px.line(daily_sim, x="run_date", y="roi_day", title="ROI per Day (Exposure)")
                st.plotly_chart(fig, use_container_width=True)

            st.subheader("Simulated Picks")
            pick_cols = [
                "run_date",
                "league",
                "home_team",
                "away_team",
                "match_start",
                "snapshot_age_min",
                "kickoff_minutes",
                "best_home_bookie",
                "best_draw_bookie",
                "best_away_bookie",
                "arb_roi_adj",
                "stake_total",
                "stake_home",
                "stake_draw",
                "stake_away",
                "profit",
            ]
            available_cols = [col for col in pick_cols if col in picks_sim.columns]
            if not available_cols:
                st.warning("Simulated picks are available but no display columns were found.")
            else:
                st.dataframe(picks_sim[available_cols].head(300), use_container_width=True)

        st.subheader("Results Backtest (Arb Execution Risk)")
        if not enable_results:
            st.info("Enable results backtest in the sidebar to see settlement performance.")
        else:
            results_start = match_start if match_filter_on else run_start
            results_end = match_end if match_filter_on else run_end
            try:
                results_rows = load_results_rows(
                    db_path=results_db_path,
                    start_date=results_start,
                    end_date=results_end,
                    completed_only=True,
                )
            except FileNotFoundError as exc:
                st.warning(str(exc))
                results_rows = pd.DataFrame()

            if results_rows.empty:
                st.warning("No results found for the selected window.")
            else:
                matched = attach_results(arbs_adj, results_rows, time_tolerance_seconds=int(results_tolerance_hours * 3600))
                matched["result_outcome"] = matched.apply(
                    lambda row: outcome_from_scores(row.get("result_home_score"), row.get("result_away_score")),
                    axis=1,
                )
                matched["result_outcome_adj"] = matched["result_outcome"]
                swapped = matched["result_swapped"] == True
                matched.loc[swapped & (matched["result_outcome"] == "home"), "result_outcome_adj"] = "away"
                matched.loc[swapped & (matched["result_outcome"] == "away"), "result_outcome_adj"] = "home"

                settled = matched[matched["result_outcome_adj"].notna()].copy()
                if settled.empty:
                    st.warning("No settled results matched to the arbitrage candidates.")
                else:
                    settled["stake_total"] = float(stake_per_arb)
                    settled["stake_home"] = settled["stake_total"] * settled["w_home"]
                    settled["stake_draw"] = settled["stake_total"] * settled["w_draw"]
                    settled["stake_away"] = settled["stake_total"] * settled["w_away"]

                    settled["profit_home_leg"] = np.where(
                        settled["result_outcome_adj"] == "home",
                        settled["stake_home"] * (settled["home_odds_adj"] - 1),
                        -settled["stake_home"],
                    )
                    settled["profit_draw_leg"] = np.where(
                        settled["result_outcome_adj"] == "draw",
                        settled["stake_draw"] * (settled["draw_odds_adj"] - 1),
                        -settled["stake_draw"],
                    )
                    settled["profit_away_leg"] = np.where(
                        settled["result_outcome_adj"] == "away",
                        settled["stake_away"] * (settled["away_odds_adj"] - 1),
                        -settled["stake_away"],
                    )

                    if cancel_on_incomplete:
                        settled["expected_profit"] = (fill_prob ** 3) * settled["stake_total"] * settled["arb_roi_adj"]
                        expected_exposure = (fill_prob ** 3) * settled["stake_total"].sum()
                    else:
                        settled["expected_profit"] = fill_prob * (
                            settled["profit_home_leg"] + settled["profit_draw_leg"] + settled["profit_away_leg"]
                        )
                        expected_exposure = fill_prob * settled["stake_total"].sum()

                    total_expected_profit = settled["expected_profit"].sum()
                    roi_expected = total_expected_profit / expected_exposure if expected_exposure else 0.0
                    coverage = len(settled) / len(arbs_adj) if len(arbs_adj) else 0.0

                    res_col1, res_col2, res_col3, res_col4 = st.columns(4)
                    res_col1.metric("Settled Arbs", f"{len(settled):,}")
                    res_col2.metric("Coverage", f"{coverage*100:.2f}%")
                    res_col3.metric("Expected Profit", f"{total_expected_profit:,.2f}")
                    res_col4.metric("Expected ROI (exposure)", f"{roi_expected*100:.2f}%")

                    settled["result_date"] = pd.to_datetime(
                        settled["result_event_date"], errors="coerce"
                    ).dt.date
                    daily = (
                        settled.groupby("result_date", dropna=True)
                        .agg(count=("match_id", "count"), expected_profit=("expected_profit", "sum"))
                        .reset_index()
                    )
                    daily["cum_profit"] = daily["expected_profit"].cumsum()

                    chart_col1, chart_col2 = st.columns(2)
                    with chart_col1:
                        fig = px.bar(daily, x="result_date", y="expected_profit", title="Expected Profit by Result Date")
                        st.plotly_chart(fig, use_container_width=True)
                    with chart_col2:
                        fig = px.line(daily, x="result_date", y="cum_profit", title="Cumulative Expected Profit")
                        st.plotly_chart(fig, use_container_width=True)

                    st.subheader("Settled Arbs (Expected Execution)")
                    settled_cols = [
                        "result_event_date",
                        "league",
                        "home_team",
                        "away_team",
                        "result_outcome_adj",
                        "home_odds_adj",
                        "draw_odds_adj",
                        "away_odds_adj",
                        "arb_roi_adj",
                        "expected_profit",
                    ]
                    st.dataframe(settled[settled_cols].head(300), use_container_width=True)
elif strategy.startswith("Consensus"):
    edges = compute_consensus_edges(
        rows,
        bankroll=bankroll,
        min_edge=min_edge,
        include_bookmakers=selected_bookies,
        include_leagues=selected_leagues,
    )
    if use_clv_filter and not clv_league_stats.empty and not edges.empty:
        clv_min_median = float(clv_min_median_pct) / 100.0
        edges = edges.merge(clv_league_stats, on="league", how="left")
        edges = edges[
            (edges["clv_matches"] >= int(clv_min_matches))
            & (edges["clv_pos_rate"] >= float(clv_min_pos_rate))
            & (edges["clv_median"] >= clv_min_median)
        ]
    if edges.empty:
        st.warning("No consensus-edge candidates found for this slice.")
        st.stop()

    col1, col2, col3 = st.columns(3)
    col1.metric("Candidates", f"{len(edges):,}")
    col2.metric("Avg Edge", f"{edges['pick_edge'].mean()*100:.2f}%")
    col3.metric("Max Edge", f"{edges['pick_edge'].max()*100:.2f}%")

    edges["run_date"] = pd.to_datetime(edges["run_time"], errors="coerce").dt.date
    daily = (
        edges.groupby("run_date", dropna=True)
        .agg(count=("match_id", "count"), avg_edge=("pick_edge", "mean"))
        .reset_index()
    )
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        fig = px.bar(daily, x="run_date", y="count", title="Value Candidate Count by Run Date")
        st.plotly_chart(fig, use_container_width=True)
    with chart_col2:
        fig = px.line(daily, x="run_date", y="avg_edge", title="Average Consensus Edge by Run Date")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top Consensus-Edge Candidates")
    display_cols = [
        "run_time",
        "league",
        "home_team",
        "away_team",
        "match_start",
        "pick_outcome",
        "pick_odds",
        "pick_bookie",
        "pick_edge_pct",
        "expected_profit",
    ]
    table = edges[display_cols].copy()
    st.dataframe(table.head(300), use_container_width=True)

    csv_data = table.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv_data, file_name="consensus_edge_candidates.csv")

    st.subheader("Log Consensus Pick (Research)")
    log_candidates = edges.head(300).copy()
    log_candidates["pick_label"] = (
        log_candidates["home_team"].fillna("")
        + " vs "
        + log_candidates["away_team"].fillna("")
        + " - "
        + log_candidates["pick_outcome"].fillna("")
        + " @ "
        + log_candidates["pick_odds"].round(2).astype(str)
    )
    pick_label = st.selectbox(
        "Select candidate",
        log_candidates["pick_label"].tolist(),
        key="consensus_log_pick",
    )
    picked_row = log_candidates[log_candidates["pick_label"] == pick_label].iloc[0]
    note = st.text_input("Research note (optional)", value="", key="consensus_log_note")
    if st.button("Log consensus pick", key="log_consensus_pick"):
        pick_id = _append_research_pick(
            research_db_path,
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "mode": log_mode,
                "strategy": "consensus",
                "match_id": picked_row.get("match_id"),
                "league": picked_row.get("league"),
                "start_time": int(pd.to_datetime(picked_row.get("match_start"), errors="coerce").timestamp())
                if pd.notna(picked_row.get("match_start")) else 0,
                "home_team": picked_row.get("home_team"),
                "away_team": picked_row.get("away_team"),
                "bookmaker": picked_row.get("pick_bookie"),
                "outcome": picked_row.get("pick_outcome"),
                "odds": float(picked_row.get("pick_odds") or 0.0),
                "stake": float(stake_per_pick),
                "expected_roi": float(picked_row.get("pick_edge") or 0.0),
                "expected_profit": float(picked_row.get("expected_profit") or 0.0),
                "source_run_time": picked_row.get("run_time"),
                "notes": note.strip(),
                "status": "open",
            },
        )
        if pick_id is not None and float(stake_per_pick) > 0:
            _append_cash_entry(
                research_db_path,
                -float(stake_per_pick),
                "stake_locked",
                pick_id=int(pick_id),
                note="consensus",
            )
        st.success("Consensus pick logged to research database.")

    st.subheader("Results Backtest (Consensus Edge)")
    if not enable_results:
        st.info("Enable results backtest in the sidebar to see settlement performance.")
    else:
        results_start = match_start if match_filter_on else run_start
        results_end = match_end if match_filter_on else run_end
        try:
            results_rows = load_results_rows(
                db_path=results_db_path,
                start_date=results_start,
                end_date=results_end,
                completed_only=True,
            )
        except FileNotFoundError as exc:
            st.warning(str(exc))
            results_rows = pd.DataFrame()

        if results_rows.empty:
            st.warning("No results found for the selected window.")
        else:
            matched = attach_results(edges, results_rows, time_tolerance_seconds=int(results_tolerance_hours * 3600))
            matched["result_outcome"] = matched.apply(
                lambda row: outcome_from_scores(row.get("result_home_score"), row.get("result_away_score")),
                axis=1,
            )
            matched["result_outcome_adj"] = matched["result_outcome"]
            swapped = matched["result_swapped"] == True
            matched.loc[swapped & (matched["result_outcome"] == "home"), "result_outcome_adj"] = "away"
            matched.loc[swapped & (matched["result_outcome"] == "away"), "result_outcome_adj"] = "home"

            settled = matched[matched["result_outcome_adj"].notna()].copy()
            if settled.empty:
                st.warning("No settled results matched to the edge candidates.")
            else:
                settled["stake"] = float(stake_per_pick)
                settled["win"] = settled["pick_outcome"] == settled["result_outcome_adj"]
                settled["profit"] = np.where(
                    settled["win"],
                    settled["stake"] * (settled["pick_odds"] - 1),
                    -settled["stake"],
                )
                settled["result_date"] = pd.to_datetime(
                    settled["result_event_date"], errors="coerce"
                ).dt.date

                total_stake = settled["stake"].sum()
                total_profit = settled["profit"].sum()
                hit_rate = settled["win"].mean() if len(settled) else 0.0
                roi = total_profit / total_stake if total_stake else 0.0

                res_col1, res_col2, res_col3, res_col4 = st.columns(4)
                res_col1.metric("Settled Picks", f"{len(settled):,}")
                res_col2.metric("Hit Rate", f"{hit_rate*100:.2f}%")
                res_col3.metric("Total Profit", f"{total_profit:,.2f}")
                res_col4.metric("ROI", f"{roi*100:.2f}%")

                daily = (
                    settled.groupby("result_date", dropna=True)
                    .agg(count=("match_id", "count"), profit=("profit", "sum"))
                    .reset_index()
                )
                daily["cum_profit"] = daily["profit"].cumsum()

                chart_col1, chart_col2 = st.columns(2)
                with chart_col1:
                    fig = px.bar(daily, x="result_date", y="profit", title="Daily Profit (Settled)")
                    st.plotly_chart(fig, use_container_width=True)
                with chart_col2:
                    fig = px.line(daily, x="result_date", y="cum_profit", title="Cumulative Profit")
                    st.plotly_chart(fig, use_container_width=True)

                st.subheader("Settled Picks")
                settled_cols = [
                    "result_event_date",
                    "league",
                    "home_team",
                    "away_team",
                    "pick_outcome",
                    "pick_odds",
                    "result_home_score",
                    "result_away_score",
                    "result_outcome_adj",
                    "win",
                    "profit",
                ]
                st.dataframe(settled[settled_cols].head(300), use_container_width=True)
elif strategy.startswith("Closing Line Value"):
    st.caption(
        "CLV compares early prices to the last pre-kickoff snapshot. "
        "Positive CLV means the early price was better than the close. Analysis only."
    )
    lines = _build_best_lines(rows, include_bookmakers=selected_bookies, include_leagues=selected_leagues)
    if lines.empty:
        st.warning("Not enough data to compute CLV for this slice.")
        st.stop()

    run_clv = st.button("Run CLV backtest")
    if run_clv or "clv_table" not in st.session_state:
        clv_data = clv_table_cached if clv_table_cached is not None and not clv_table_cached.empty else _compute_clv_table(lines)
        st.session_state["clv_table"] = clv_data
    clv_table = st.session_state.get("clv_table")

    if clv_table is None or clv_table.empty:
        st.info("Click 'Run CLV backtest' to compute results.")
        st.stop()

    pos_rate = (clv_table["clv_best"] > 0).mean()
    clv_col1, clv_col2, clv_col3, clv_col4 = st.columns(4)
    clv_col1.metric("Matches w/ CLV", f"{len(clv_table):,}")
    clv_col2.metric("Positive CLV %", f"{pos_rate*100:.2f}%")
    clv_col3.metric("Median CLV", f"{clv_table['clv_best'].median()*100:.2f}%")
    clv_col4.metric("Max CLV", f"{clv_table['clv_best'].max()*100:.2f}%")

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        fig = px.histogram(clv_table, x="clv_best", nbins=30, title="CLV Distribution (Best Outcome)")
        st.plotly_chart(fig, use_container_width=True)
    with chart_col2:
        top_leagues = (
            clv_table.groupby("league_open")["match_id"].count().sort_values(ascending=False).head(12).reset_index()
        )
        fig = px.bar(top_leagues, x="league_open", y="match_id", title="Top Leagues by CLV Coverage")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("CLV Scoreboards")
    league_stats = _compute_clv_league_stats(clv_table)
    if not league_stats.empty:
        league_stats["clv_pos_rate_pct"] = league_stats["clv_pos_rate"] * 100
        league_stats["clv_median_pct"] = league_stats["clv_median"] * 100
        st.dataframe(
            league_stats.sort_values("clv_pos_rate", ascending=False).head(20),
            use_container_width=True,
        )
    else:
        st.info("Not enough data for league-level CLV stats.")

    if "run_time_open" in clv_table.columns and "match_start_open" in clv_table.columns:
        clv_table["kickoff_hours_open"] = (
            (pd.to_datetime(clv_table["match_start_open"], errors="coerce") - pd.to_datetime(clv_table["run_time_open"], errors="coerce"))
            .dt.total_seconds()
            / 3600.0
        )
        clv_table["time_window"] = pd.cut(
            clv_table["kickoff_hours_open"],
            bins=CLV_TIME_BINS,
            labels=CLV_TIME_LABELS,
        )
        window_stats = (
            clv_table.groupby("time_window", dropna=True)
            .agg(
                matches=("match_id", "count"),
                pos_rate=("clv_best", lambda x: (x > 0).mean()),
                median_clv=("clv_best", "median"),
            )
            .reset_index()
        )
        if not window_stats.empty:
            window_stats["pos_rate_pct"] = window_stats["pos_rate"] * 100
            window_stats["median_clv_pct"] = window_stats["median_clv"] * 100
            st.dataframe(window_stats, use_container_width=True)

    if "best_home_bookie_open" in clv_table.columns:
        clv_table["clv_bookie_open"] = np.select(
            [
                clv_table["clv_outcome"] == "home",
                clv_table["clv_outcome"] == "draw",
                clv_table["clv_outcome"] == "away",
            ],
            [
                clv_table.get("best_home_bookie_open"),
                clv_table.get("best_draw_bookie_open"),
                clv_table.get("best_away_bookie_open"),
            ],
            default=None,
        )
        bookie_stats = (
            clv_table.dropna(subset=["clv_bookie_open"])
            .groupby("clv_bookie_open", dropna=True)
            .agg(
                matches=("match_id", "count"),
                pos_rate=("clv_best", lambda x: (x > 0).mean()),
                median_clv=("clv_best", "median"),
            )
            .reset_index()
            .rename(columns={"clv_bookie_open": "bookmaker"})
        )
        if not bookie_stats.empty:
            bookie_stats["pos_rate_pct"] = bookie_stats["pos_rate"] * 100
            bookie_stats["median_clv_pct"] = bookie_stats["median_clv"] * 100
            st.dataframe(bookie_stats.sort_values("pos_rate", ascending=False).head(15), use_container_width=True)

    st.subheader("Top CLV Signals (Research)")
    display_cols = [
        "run_time_open",
        "run_time_close",
        "league_open",
        "home_team_open",
        "away_team_open",
        "match_start_open",
        "clv_outcome",
        "clv_best",
        "best_home_odds_open",
        "best_draw_odds_open",
        "best_away_odds_open",
        "best_home_odds_close",
        "best_draw_odds_close",
        "best_away_odds_close",
        "snapshot_count",
    ]
    table = clv_table.sort_values("clv_best", ascending=False)[display_cols].copy()
    table["clv_best_pct"] = table["clv_best"] * 100
    st.dataframe(table.head(300), use_container_width=True)

    csv_data = table.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv_data, file_name="clv_signals.csv")
elif strategy.startswith("Price Movement"):
    st.caption(
        "Price movement tracks line drift between the opening snapshot and the last pre-kickoff snapshot."
    )
    lines = _build_best_lines(rows, include_bookmakers=selected_bookies, include_leagues=selected_leagues)
    if lines.empty:
        st.warning("Not enough data to compute price movement for this slice.")
        st.stop()

    movement_base = _build_open_close(lines)
    if movement_base.empty:
        st.warning("No open/close snapshots found for this slice.")
        st.stop()

    snap_counts = lines.groupby("match_id", as_index=False)["run_id"].nunique().rename(
        columns={"run_id": "snapshot_count"}
    )
    movement = movement_base.merge(snap_counts, on="match_id", how="left")
    movement = movement[movement["snapshot_count"] >= 2]
    if movement.empty:
        st.warning("Price movement requires at least 2 snapshots per match.")
        st.stop()

    movement["move_home_pct"] = (movement["best_home_odds_close"] - movement["best_home_odds_open"]) / movement["best_home_odds_open"]
    movement["move_draw_pct"] = (movement["best_draw_odds_close"] - movement["best_draw_odds_open"]) / movement["best_draw_odds_open"]
    movement["move_away_pct"] = (movement["best_away_odds_close"] - movement["best_away_odds_open"]) / movement["best_away_odds_open"]
    movement["move_abs"] = movement[["move_home_pct", "move_draw_pct", "move_away_pct"]].abs().max(axis=1)
    movement["move_outcome"] = movement[["move_home_pct", "move_draw_pct", "move_away_pct"]].abs().idxmax(axis=1)
    movement["move_outcome"] = movement["move_outcome"].str.replace("move_", "").str.replace("_pct", "")

    run_move = st.button("Run movement backtest")
    if run_move or "movement_table" not in st.session_state:
        st.session_state["movement_table"] = movement
    movement_table = st.session_state.get("movement_table")

    if movement_table is None or movement_table.empty:
        st.info("Click 'Run movement backtest' to compute results.")
        st.stop()

    mv_col1, mv_col2, mv_col3, mv_col4 = st.columns(4)
    mv_col1.metric("Matches w/ Movement", f"{len(movement_table):,}")
    mv_col2.metric("Median Move", f"{movement_table['move_abs'].median()*100:.2f}%")
    mv_col3.metric("Max Move", f"{movement_table['move_abs'].max()*100:.2f}%")
    mv_col4.metric("Avg Move", f"{movement_table['move_abs'].mean()*100:.2f}%")

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        fig = px.histogram(movement_table, x="move_abs", nbins=30, title="Price Movement (Abs %)")
        st.plotly_chart(fig, use_container_width=True)
    with chart_col2:
        top_leagues = (
            movement_table.groupby("league_open")["match_id"].count().sort_values(ascending=False).head(12).reset_index()
        )
        fig = px.bar(top_leagues, x="league_open", y="match_id", title="Top Leagues by Movement Coverage")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top Movers (Research)")
    display_cols = [
        "run_time_open",
        "run_time_close",
        "league_open",
        "home_team_open",
        "away_team_open",
        "match_start_open",
        "move_outcome",
        "move_abs",
        "move_home_pct",
        "move_draw_pct",
        "move_away_pct",
        "snapshot_count",
    ]
    table = movement_table.sort_values("move_abs", ascending=False)[display_cols].copy()
    table["move_abs_pct"] = table["move_abs"] * 100
    st.dataframe(table.head(300), use_container_width=True)

    csv_data = table.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv_data, file_name="price_movement_signals.csv")
elif strategy.startswith("Liquidity"):
    st.caption("Liquidity and age filters help you focus on matches with more bookies and fresher snapshots.")
    lines = _build_best_lines(rows, include_bookmakers=selected_bookies, include_leagues=selected_leagues)
    if lines.empty:
        st.warning("Not enough data to compute liquidity for this slice.")
        st.stop()

    latest = lines.sort_values("run_time").groupby("match_id", as_index=False).tail(1)
    now_utc = datetime.now(timezone.utc)
    latest["snapshot_age_min"] = (now_utc - latest["run_time"]).dt.total_seconds() / 60.0
    latest["kickoff_minutes"] = (latest["match_start"] - now_utc).dt.total_seconds() / 60.0

    st.subheader("Liquidity & Age Controls")
    liq_col1, liq_col2, liq_col3 = st.columns(3)
    with liq_col1:
        min_bookies = st.number_input("Min bookies per match", min_value=1, value=3, step=1)
    with liq_col2:
        max_age = st.number_input("Max snapshot age (minutes)", min_value=0, value=15, step=5)
    with liq_col3:
        min_kickoff = st.number_input("Min minutes to kickoff", min_value=0, value=10, step=5)

    filtered = latest.copy()
    if min_bookies:
        filtered = filtered[filtered["bookie_count"] >= int(min_bookies)]
    if max_age:
        filtered = filtered[filtered["snapshot_age_min"] <= float(max_age)]
    if min_kickoff:
        filtered = filtered[filtered["kickoff_minutes"] >= float(min_kickoff)]

    liq_col1, liq_col2, liq_col3, liq_col4 = st.columns(4)
    liq_col1.metric("Matches (filtered)", f"{len(filtered):,}")
    liq_col2.metric("Median Bookies", f"{filtered['bookie_count'].median():.0f}" if not filtered.empty else "0")
    liq_col3.metric("Median Snapshot Age", f"{filtered['snapshot_age_min'].median():.1f} min" if not filtered.empty else "0")
    liq_col4.metric("Median Minutes to KO", f"{filtered['kickoff_minutes'].median():.1f}" if not filtered.empty else "0")

    st.subheader("Filtered Matches")
    display_cols = [
        "run_time",
        "league",
        "home_team",
        "away_team",
        "match_start",
        "bookie_count",
        "snapshot_age_min",
        "kickoff_minutes",
        "best_home_odds",
        "best_draw_odds",
        "best_away_odds",
    ]
    st.dataframe(filtered[display_cols].head(300), use_container_width=True)

st.markdown("---")
st.subheader("Research Log")
log_start = match_start if match_filter_on else run_start
log_end = match_end if match_filter_on else run_end
cash_ledger = _load_cash_ledger(research_db_path)
cash_balance = float(cash_ledger.iloc[0]["balance"]) if not cash_ledger.empty else 0.0
cash_updated = cash_ledger.iloc[0]["created_at"] if not cash_ledger.empty else None
cash_col1, cash_col2, cash_col3 = st.columns(3)
cash_col1.metric("Liquid Cash", f"{cash_balance:,.2f}")
cash_col2.metric("Cash Entries", f"{len(cash_ledger):,}")
cash_col3.metric(
    "Last Update",
    cash_updated.strftime("%Y-%m-%d %H:%M")
    if cash_updated is not None and not pd.isna(cash_updated)
    else "—",
)
balance_input = st.number_input(
    "Set liquid cash balance",
    min_value=0.0,
    value=float(cash_balance),
    step=10.0,
    key="liquid_cash_balance",
)
if st.button("Update liquid cash", key="update_liquid_cash"):
    new_balance = _set_cash_balance(research_db_path, float(balance_input))
    st.success(f"Liquid cash updated: {new_balance:,.2f}")
    rerun = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if rerun:
        rerun()
with st.expander("Cash ledger (latest 200)", expanded=False):
    if cash_ledger.empty:
        st.info("No cash entries yet.")
    else:
        st.dataframe(cash_ledger.head(200), use_container_width=True, hide_index=True)
research_picks = _load_research_picks(research_db_path, log_start, log_end)
if research_picks.empty:
    st.info("No research picks logged yet.")
else:
    try:
        results_rows = load_results_rows(
            db_path=results_db_path,
            start_date=log_start,
            end_date=log_end,
            completed_only=True,
        )
    except FileNotFoundError:
        results_rows = pd.DataFrame()

    evaluated = _evaluate_research_picks(research_picks, results_rows, results_tolerance_hours)
    settled = evaluated[evaluated["realized_profit"].notna()].copy()
    open_picks = evaluated[evaluated["status"].str.lower().fillna("open") != "settled"].copy()

    total_picks = len(evaluated)
    settled_picks = len(settled)
    avg_expected_roi = evaluated["expected_roi"].mean() if total_picks else 0.0
    avg_realized_roi = settled["realized_roi"].mean() if settled_picks else 0.0
    roi_std = settled["realized_roi"].std() if settled_picks else 0.0
    total_realized_profit = settled["realized_profit"].sum() if settled_picks else 0.0

    res_col1, res_col2, res_col3, res_col4, res_col5 = st.columns(5)
    res_col1.metric("Logged Picks", f"{total_picks:,}")
    res_col2.metric("Settled Picks", f"{settled_picks:,}")
    res_col3.metric("Avg Expected ROI", f"{avg_expected_roi*100:.2f}%")
    res_col4.metric("Avg Realized ROI", f"{avg_realized_roi*100:.2f}%")
    res_col5.metric("ROI Std Dev", f"{roi_std*100:.2f}%")

    st.metric("Total Realized Profit", f"{total_realized_profit:,.2f}")

    if not open_picks.empty:
        st.subheader("Settle Pick")
        open_picks["pick_label"] = (
            "[" + open_picks["pick_id"].astype(str) + "] "
            + open_picks["home_team"].fillna("")
            + " vs "
            + open_picks["away_team"].fillna("")
            + " - "
            + open_picks["strategy"].fillna("")
        )
        pick_label = st.selectbox(
            "Open pick",
            open_picks["pick_label"].tolist(),
            key="settle_pick_select",
        )
        selected_pick = open_picks[open_picks["pick_label"] == pick_label].iloc[0]
        stake = float(selected_pick.get("stake") or 0.0)
        odds = selected_pick.get("odds")
        expected_profit = float(selected_pick.get("expected_profit") or 0.0)
        strategy_name = str(selected_pick.get("strategy") or "")
        default_outcome = "arb" if "arb" in strategy_name.lower() else "win"
        outcome_options = ("win", "loss", "push", "void", "arb", "custom")
        outcome_result = st.selectbox(
            "Outcome",
            outcome_options,
            index=outcome_options.index(default_outcome) if default_outcome in outcome_options else 0,
            key="settle_pick_outcome",
        )

        if outcome_result == "arb":
            realized_profit = expected_profit
        elif outcome_result == "win":
            if odds and float(odds) > 0:
                realized_profit = stake * (float(odds) - 1.0)
            else:
                realized_profit = expected_profit
        elif outcome_result == "loss":
            realized_profit = -stake
        elif outcome_result in ("push", "void"):
            realized_profit = 0.0
        else:
            realized_profit = expected_profit

        if outcome_result == "custom":
            realized_profit = st.number_input(
                "Realized profit",
                value=float(realized_profit),
                step=1.0,
                key=f"settle_profit_{int(selected_pick.get('pick_id') or 0)}",
            )
            cash_return = st.number_input(
                "Cash returned to liquid",
                min_value=0.0,
                value=max(0.0, stake + float(realized_profit)),
                step=1.0,
                key=f"settle_return_{int(selected_pick.get('pick_id') or 0)}",
            )
        else:
            cash_return = max(0.0, stake + float(realized_profit))
            settle_col1, settle_col2, settle_col3 = st.columns(3)
            settle_col1.metric("Stake", f"{stake:,.2f}")
            settle_col2.metric("Realized profit", f"{float(realized_profit):,.2f}")
            settle_col3.metric("Cash returned", f"{float(cash_return):,.2f}")

        if st.button("Confirm outcome", key="confirm_pick_outcome"):
            realized_roi = float(realized_profit) / stake if stake else 0.0
            _settle_research_pick(
                research_db_path,
                int(selected_pick.get("pick_id")),
                str(outcome_result),
                float(realized_profit),
                float(realized_roi),
                float(cash_return),
            )
            _append_cash_entry(
                research_db_path,
                float(cash_return),
                "pick_settled",
                pick_id=int(selected_pick.get("pick_id")),
                note=str(outcome_result),
            )
            st.success("Pick settled and liquid cash updated.")
            rerun = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
            if rerun:
                rerun()

    show_cols = [
        "created_at",
        "mode",
        "strategy",
        "league",
        "home_team",
        "away_team",
        "outcome",
        "bookmaker",
        "odds",
        "stake",
        "expected_roi",
        "expected_profit",
        "status",
        "settled_at",
        "outcome_result",
        "realized_roi",
        "realized_profit",
        "cash_return",
        "result_outcome_adj",
        "result_event_date",
        "notes",
    ]
    display = evaluated[show_cols].copy()
    display["expected_roi"] = display["expected_roi"] * 100
    display["realized_roi"] = display["realized_roi"] * 100
    st.dataframe(display.head(300), use_container_width=True)
    st.download_button(
        "Download research log CSV",
        display.to_csv(index=False).encode("utf-8"),
        file_name="research_log.csv",
    )
