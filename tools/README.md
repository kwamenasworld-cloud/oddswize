# Tools

## Arbitrage Strategy Terminal

Local analysis workspace for odds history. Uses `data/odds_history.db` by default.
Results backtests use `data/results.db` when available.

Setup:
```
pip install -r requirements.analytics.txt
```

Run the terminal (from repo root):
```
streamlit run tools/arb_terminal.py
```

Ingest results (ESPN scoreboard) for backtests:
```
python tools/results_ingest.py --days-back 30
```

Append remote GitHub snapshot into local history (for rolling history):
```
python tools/pull_remote_snapshot.py --dedupe --save-db
```

Schedule the puller (Windows Task Scheduler, every 15 minutes):
```
powershell -ExecutionPolicy Bypass -File tools/schedule_pull_remote_snapshot.ps1
```

CLI backtest example:
```
python tools/arb_backtest.py --strategy arb --run-start 2026-01-01 --run-end 2026-01-31 --output-csv data/analysis/arbs_jan.csv
```

Notes:
- Set `HISTORY_DB_PATH` to point at a different database.
- JSONL fallback uses `data/odds_history.jsonl` unless `HISTORY_MATCHED_FILE` is set.
- Set `RESULTS_DB_PATH` to point at a different results database.
- To load from the GitHub scraper directly, toggle "Use remote odds snapshot" in the terminal
  and paste the raw `odds_data.json` URL.
- To load from the Cloudflare D1 history API, toggle "Use remote history API" and set the
  base worker URL (e.g. `https://oddswize-api.kwamenahb.workers.dev`).
- Execution lag is modeled with a slippage buffer + minimum minutes to kickoff filter in the terminal controls.
