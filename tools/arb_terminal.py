import json
import os
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


def _build_search_url(*parts: object) -> str:
    query = " ".join(str(part).strip() for part in parts if part and str(part).strip())
    if not query:
        return ""
    return f"{SEARCH_BASE_URL}{urllib.parse.quote_plus(query)}"


def _render_link_button(label: str, url: str) -> None:
    if not url:
        return
    if hasattr(st, "link_button"):
        st.link_button(label, url)
    else:
        st.markdown(f"[{label}]({url})")


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
        "https://oddswize-api.kwamenahb.workers.dev/api/odds",
    )
    default_use_remote = os.getenv("DEFAULT_USE_REMOTE", "1").strip().lower() in ("1", "true", "yes", "on")
    use_remote = st.checkbox("Use remote odds snapshot", value=default_use_remote)
    remote_url = st.text_input("Remote odds_data.json URL", value=default_remote_url)
    st.caption("Tip: use the Worker /api/odds endpoint for the freshest snapshot.")
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
    min_roi_adj = st.slider(
        "Minimum arb ROI (after slippage)",
        min_value=0.0,
        max_value=0.1,
        value=0.0,
        step=0.0025,
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
            st.warning(
                "No arbitrage opportunities remain after slippage + age/lag filters "
                f"(max snapshot age {max_snapshot_age_minutes} min, min kickoff {min_minutes_to_kickoff} min)."
            )
            st.stop()
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
        table = arbs_filtered[display_cols].copy()
        table["arb_roi_adj_pct"] = table["arb_roi_adj"] * 100
        link_cols = []
        column_config = None
        if show_quick_links:
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
            table["home_search"] = table.apply(
                lambda row: _build_search_url(
                    row.get("best_home_bookie"),
                    row.get("home_team"),
                    "vs",
                    row.get("away_team"),
                ),
                axis=1,
            )
            table["draw_search"] = table.apply(
                lambda row: _build_search_url(
                    row.get("best_draw_bookie"),
                    row.get("home_team"),
                    "vs",
                    row.get("away_team"),
                ),
                axis=1,
            )
            table["away_search"] = table.apply(
                lambda row: _build_search_url(
                    row.get("best_away_bookie"),
                    row.get("home_team"),
                    "vs",
                    row.get("away_team"),
                ),
                axis=1,
            )
            link_cols = ["match_search", "home_search", "draw_search", "away_search"]
            if hasattr(st, "column_config"):
                column_config = {
                    "match_search": st.column_config.LinkColumn("Match search", display_text="Open"),
                    "home_search": st.column_config.LinkColumn("Home bookie", display_text="Open"),
                    "draw_search": st.column_config.LinkColumn("Draw bookie", display_text="Open"),
                    "away_search": st.column_config.LinkColumn("Away bookie", display_text="Open"),
                }

        display_table = table[display_cols + link_cols].copy()
        if column_config:
            st.dataframe(display_table.head(300), use_container_width=True, column_config=column_config)
        else:
            st.dataframe(display_table.head(300), use_container_width=True)

        csv_data = display_table.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv_data, file_name="arbitrage_opportunities_adjusted.csv")

        st.subheader("Stake Allocator (Arb)")
        allocator_cols = [
            "run_time",
            "league",
            "home_team",
            "away_team",
            "match_start",
            "home_odds_adj",
            "draw_odds_adj",
            "away_odds_adj",
            "best_home_bookie",
            "best_draw_bookie",
            "best_away_bookie",
            "arb_roi_adj",
        ]
        allocator_table = arbs_filtered[allocator_cols].copy()
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
        odds_home = float(selected_row["home_odds_adj"])
        odds_draw = float(selected_row["draw_odds_adj"])
        odds_away = float(selected_row["away_odds_adj"])
        inv_sum = (1 / odds_home) + (1 / odds_draw) + (1 / odds_away)
        stake_home = stake_total / (odds_home * inv_sum)
        stake_draw = stake_total / (odds_draw * inv_sum)
        stake_away = stake_total / (odds_away * inv_sum)
        payout = stake_total / inv_sum
        profit = payout - stake_total

        alloc_col1, alloc_col2, alloc_col3, alloc_col4 = st.columns(4)
        alloc_col1.metric("Home stake", f"{stake_home:,.2f}")
        alloc_col2.metric("Draw stake", f"{stake_draw:,.2f}")
        alloc_col3.metric("Away stake", f"{stake_away:,.2f}")
        alloc_col4.metric("Guaranteed profit", f"{profit:,.2f}")
        st.caption(
            f"Payout per outcome: {payout:,.2f} - ROI: {(profit / stake_total) * 100:.2f}%"
        )
        if show_quick_links:
            match_link = _build_search_url(
                selected_row.get("home_team"),
                "vs",
                selected_row.get("away_team"),
                selected_row.get("league"),
            )
            home_link = _build_search_url(
                selected_row.get("best_home_bookie"),
                selected_row.get("home_team"),
                "vs",
                selected_row.get("away_team"),
            )
            draw_link = _build_search_url(
                selected_row.get("best_draw_bookie"),
                selected_row.get("home_team"),
                "vs",
                selected_row.get("away_team"),
            )
            away_link = _build_search_url(
                selected_row.get("best_away_bookie"),
                selected_row.get("home_team"),
                "vs",
                selected_row.get("away_team"),
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

    clv_base = _build_open_close(lines)
    if clv_base.empty:
        st.warning("No open/close snapshots found for this slice.")
        st.stop()

    snap_counts = lines.groupby("match_id", as_index=False)["run_id"].nunique().rename(
        columns={"run_id": "snapshot_count"}
    )
    clv = clv_base.merge(snap_counts, on="match_id", how="left")
    clv = clv[clv["snapshot_count"] >= 2]
    if clv.empty:
        st.warning("CLV requires at least 2 snapshots per match.")
        st.stop()

    clv["clv_home"] = clv["best_home_odds_open"] / clv["best_home_odds_close"] - 1
    clv["clv_draw"] = clv["best_draw_odds_open"] / clv["best_draw_odds_close"] - 1
    clv["clv_away"] = clv["best_away_odds_open"] / clv["best_away_odds_close"] - 1

    clv["clv_best"] = clv[["clv_home", "clv_draw", "clv_away"]].max(axis=1)
    clv["clv_outcome"] = clv[["clv_home", "clv_draw", "clv_away"]].idxmax(axis=1).str.replace("clv_", "")

    run_clv = st.button("Run CLV backtest")
    if run_clv or "clv_table" not in st.session_state:
        st.session_state["clv_table"] = clv
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
