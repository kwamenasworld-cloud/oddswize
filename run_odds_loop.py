#!/usr/bin/env python3
"""
Run the odds scraper in a continuous loop for near-real-time updates.

Defaults to running scrape_odds_github.py every 120 seconds with light jitter.
"""

import argparse
import os
import random
import subprocess
import sys
import time
from datetime import datetime


def log(message: str) -> None:
    timestamp = datetime.now().isoformat(timespec='seconds')
    print(f"[{timestamp}] {message}", flush=True)


def run_scraper(cmd: list[str], env: dict) -> tuple[int, float]:
    start = time.time()
    log(f"Starting: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env)
    duration = time.time() - start
    if result.returncode == 0:
        log(f"Completed in {duration:.1f}s")
    else:
        log(f"Failed (exit {result.returncode}) after {duration:.1f}s")
    return result.returncode, duration


def normalize_interval(value: int, minimum: int) -> int:
    if value < minimum:
        return minimum
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the odds scraper in a continuous loop.")
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=int(os.getenv("ODDS_LOOP_INTERVAL_SECONDS", "120")),
        help="Target interval between scrapes (seconds). Default: 120",
    )
    parser.add_argument(
        "--jitter-seconds",
        type=int,
        default=int(os.getenv("ODDS_LOOP_JITTER_SECONDS", "10")),
        help="Random jitter added to sleep time (seconds). Default: 10",
    )
    parser.add_argument(
        "--max-backoff-seconds",
        type=int,
        default=int(os.getenv("ODDS_LOOP_MAX_BACKOFF_SECONDS", "600")),
        help="Max backoff delay after failures (seconds). Default: 600",
    )
    parser.add_argument(
        "--script",
        default=os.getenv("ODDS_LOOP_SCRIPT", "scrape_odds_github.py"),
        help="Scraper script path. Default: scrape_odds_github.py",
    )
    parser.add_argument(
        "--python",
        default=os.getenv("ODDS_LOOP_PYTHON", sys.executable),
        help="Python executable to use. Default: current interpreter",
    )
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit.")
    parser.add_argument(
        "script_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed to the scraper (prefix with --).",
    )

    args = parser.parse_args()
    interval = normalize_interval(args.interval_seconds, minimum=30)
    jitter = max(0, args.jitter_seconds)
    max_backoff = normalize_interval(args.max_backoff_seconds, minimum=interval)

    script_args = args.script_args[1:] if args.script_args[:1] == ["--"] else args.script_args
    cmd = [args.python, args.script, *script_args]
    env = os.environ.copy()

    backoff = 0
    while True:
        exit_code, duration = run_scraper(cmd, env)
        if args.once:
            raise SystemExit(exit_code)

        if exit_code == 0:
            backoff = 0
            sleep_base = interval
        else:
            backoff = backoff * 2 if backoff else interval * 2
            if backoff > max_backoff:
                backoff = max_backoff
            sleep_base = backoff

        sleep_for = max(0, sleep_base - duration)
        if jitter:
            sleep_for += random.uniform(0, jitter)

        next_time = datetime.fromtimestamp(time.time() + sleep_for).isoformat(timespec='seconds')
        log(f"Sleeping {sleep_for:.1f}s (next run ~{next_time})")
        time.sleep(sleep_for)


if __name__ == "__main__":
    main()
