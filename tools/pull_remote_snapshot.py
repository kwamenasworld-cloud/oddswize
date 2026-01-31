#!/usr/bin/env python3
"""
Fetch the latest odds_data.json from a remote URL and append to local history.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tools.arb_lab import (
    append_snapshot_to_history_db,
    append_snapshot_to_history_jsonl,
    history_run_exists,
    last_jsonl_run_id,
)


DEFAULT_REMOTE_URL = "https://raw.githubusercontent.com/kwamenasworld-cloud/oddswize/data/odds_data.json"


def fetch_payload(url: str, timeout: int) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Pull remote odds_data.json and append to history.")
    parser.add_argument("--url", default=os.getenv("REMOTE_ODDS_URL", DEFAULT_REMOTE_URL))
    parser.add_argument("--db", default=os.getenv("HISTORY_DB_PATH", "data/odds_history.db"))
    parser.add_argument("--jsonl", default=os.getenv("HISTORY_MATCHED_FILE", "data/odds_history.jsonl"))
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout in seconds")
    parser.add_argument("--save-db", action="store_true", help="Append to history DB")
    parser.add_argument("--save-jsonl", action="store_true", help="Append to history JSONL")
    parser.add_argument("--dedupe", action="store_true", help="Skip if run_id already present")
    args = parser.parse_args()

    if not args.save_db and not args.save_jsonl:
        args.save_db = True

    payload = fetch_payload(args.url, args.timeout)
    if not payload:
        print("No payload found.")
        return 1

    run_id = payload.get("run_id") or payload.get("last_updated") or datetime.now(timezone.utc).isoformat()

    if args.dedupe:
        if args.save_db and history_run_exists(args.db, run_id):
            print(f"Run already exists in DB: {run_id}")
            return 0
        if args.save_jsonl:
            last_run = last_jsonl_run_id(args.jsonl)
            if last_run == run_id:
                print(f"Run already exists in JSONL: {run_id}")
                return 0

    if args.save_db:
        append_snapshot_to_history_db(payload, args.db)
        print(f"Appended to DB: {args.db}")
    if args.save_jsonl:
        append_snapshot_to_history_jsonl(payload, args.jsonl)
        print(f"Appended to JSONL: {args.jsonl}")

    print(f"Done. run_id={run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
