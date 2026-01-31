import argparse
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tools.arb_lab import (
    compute_arbitrage_opportunities,
    compute_consensus_edges,
    load_snapshot_rows,
    load_snapshot_rows_from_jsonl,
    resolve_db_path,
    resolve_history_jsonl,
    summarize_arbitrage,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backtest arbitrage and consensus-edge strategies.")
    parser.add_argument("--db", default=resolve_db_path(), help="Path to odds_history.db")
    parser.add_argument("--jsonl", default=resolve_history_jsonl(), help="Path to odds_history.jsonl")
    parser.add_argument("--use-jsonl", action="store_true", help="Use JSONL instead of SQLite")
    parser.add_argument("--run-start", default=None, help="Run start date (YYYY-MM-DD)")
    parser.add_argument("--run-end", default=None, help="Run end date (YYYY-MM-DD)")
    parser.add_argument("--match-start", default=None, help="Match start date (YYYY-MM-DD)")
    parser.add_argument("--match-end", default=None, help="Match end date (YYYY-MM-DD)")
    parser.add_argument("--bankroll", type=float, default=1000.0, help="Bankroll per opportunity")
    parser.add_argument("--min-roi", type=float, default=0.0, help="Minimum arbitrage ROI")
    parser.add_argument("--min-edge", type=float, default=0.0, help="Minimum consensus edge")
    parser.add_argument("--strategy", choices=["arb", "edge"], default="arb", help="Strategy type")
    parser.add_argument("--leagues", nargs="*", default=None, help="Filter leagues")
    parser.add_argument("--bookmakers", nargs="*", default=None, help="Filter bookmakers")
    parser.add_argument("--max-rows", type=int, default=None, help="Max rows to load")
    parser.add_argument("--output-csv", default=None, help="Export results to CSV")
    parser.add_argument("--output-json", default=None, help="Export results to JSON")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.use_jsonl:
        rows = load_snapshot_rows_from_jsonl(
            jsonl_path=args.jsonl,
            run_start=args.run_start,
            run_end=args.run_end,
        )
    else:
        rows = load_snapshot_rows(
            db_path=args.db,
            run_start=args.run_start,
            run_end=args.run_end,
            match_start=args.match_start,
            match_end=args.match_end,
            limit=args.max_rows,
        )

    if rows.empty:
        print("No data found for the requested range.")
        return 1

    if args.strategy == "arb":
        arbs, matches = compute_arbitrage_opportunities(
            rows,
            bankroll=args.bankroll,
            min_roi=args.min_roi,
            include_bookmakers=args.bookmakers,
            include_leagues=args.leagues,
        )
        summary = summarize_arbitrage(arbs, matches)
        print(f"Matches: {summary['matches']}")
        print(f"Arbs: {summary['arbs']}")
        print(f"Avg ROI: {summary['avg_roi']*100:.2f}%")
        print(f"Max ROI: {summary['max_roi']*100:.2f}%")
        if arbs.empty:
            print("No arbitrage opportunities found.")
        results = arbs
    else:
        results = compute_consensus_edges(
            rows,
            bankroll=args.bankroll,
            min_edge=args.min_edge,
            include_bookmakers=args.bookmakers,
            include_leagues=args.leagues,
        )
        if results.empty:
            print("No consensus-edge candidates found.")
        else:
            print(f"Candidates: {len(results)}")
            print(f"Avg edge: {results['pick_edge'].mean()*100:.2f}%")
            print(f"Max edge: {results['pick_edge'].max()*100:.2f}%")

    if args.output_csv and not results.empty:
        results.to_csv(args.output_csv, index=False)
        print(f"Wrote {args.output_csv}")
    if args.output_json and not results.empty:
        results.to_json(args.output_json, orient="records")
        print(f"Wrote {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
