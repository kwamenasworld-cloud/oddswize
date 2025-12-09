#!/usr/bin/env python3
"""
Automated Odds Scanner
Runs the Ghana betting odds scanner every 5 minutes automatically.
"""

import json
import os
import sys
import time
import logging
from datetime import datetime
from threading import Thread

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scanner.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.core.arbitrage import GhanaBettingArbitrage, calculate_stakes


# Configuration
SCAN_INTERVAL_MINUTES = 5
MAX_MATCHES = 800
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'frontend', 'public', 'data')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'odds_data.json')


def ensure_output_dir():
    """Create output directory if it doesn't exist."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        logger.info(f"Created output directory: {OUTPUT_DIR}")


def run_scan():
    """Run a single odds scan and save results."""
    scan_start = datetime.now()
    logger.info("=" * 60)
    logger.info(f"Starting odds scan at {scan_start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    try:
        # Initialize scanner
        scanner = GhanaBettingArbitrage()

        # Run all scrapers
        scanner.scrape_all(max_matches=MAX_MATCHES)

        # Match events across bookmakers
        scanner.match_events()

        # Find arbitrage opportunities
        opportunities = scanner.find_arbitrage()

        # Prepare data for frontend
        matches_data = []
        for event in scanner.matched_events:
            if len(event) < 2:
                continue

            match_data = {
                'home_team': event[0].get('home_team', ''),
                'away_team': event[0].get('away_team', ''),
                'league': event[0].get('league', ''),
                'start_time': event[0].get('start_time'),
                'odds': []
            }

            for m in event:
                match_data['odds'].append({
                    'bookmaker': m.get('bookmaker', ''),
                    'home_odds': m.get('home_odds', 0),
                    'draw_odds': m.get('draw_odds', 0),
                    'away_odds': m.get('away_odds', 0)
                })

            matches_data.append(match_data)

        # Prepare arbitrage data
        arb_data = []
        for opp in opportunities:
            stakes = calculate_stakes(opp, 100)
            arb_data.append({
                'home_team': opp['home_team'],
                'away_team': opp['away_team'],
                'profit_pct': round(opp['profit_pct'], 2),
                'home_odds': opp['home_odds'],
                'home_bookmaker': opp['home_bookmaker'],
                'draw_odds': opp['draw_odds'],
                'draw_bookmaker': opp['draw_bookmaker'],
                'away_odds': opp['away_odds'],
                'away_bookmaker': opp['away_bookmaker'],
                'stakes': stakes
            })

        # Save to JSON file for frontend
        ensure_output_dir()
        output_data = {
            'last_updated': datetime.now().isoformat(),
            'next_update': (datetime.now().timestamp() + SCAN_INTERVAL_MINUTES * 60),
            'stats': {
                'total_matches': sum(len(m) for m in scanner.all_matches.values()),
                'matched_events': len(scanner.matched_events),
                'arbitrage_count': len(opportunities),
                'bookmakers': list(scanner.all_matches.keys())
            },
            'matches': matches_data[:200],  # Limit to 200 matches for performance
            'arbitrage': arb_data
        }

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)

        # Also save to root for API
        root_file = os.path.join(os.path.dirname(__file__), 'ghana_arb_results.json')
        scanner.save_results(opportunities, root_file)

        scan_duration = (datetime.now() - scan_start).total_seconds()
        logger.info(f"Scan completed in {scan_duration:.1f} seconds")
        logger.info(f"Found {len(matches_data)} matched events, {len(arb_data)} arbitrage opportunities")
        logger.info(f"Data saved to: {OUTPUT_FILE}")

        return True

    except Exception as e:
        logger.error(f"Scan failed: {e}", exc_info=True)
        return False


def scheduler_loop():
    """Main scheduler loop - runs scans every SCAN_INTERVAL_MINUTES."""
    logger.info("=" * 60)
    logger.info("  AUTOMATED ODDS SCANNER STARTED")
    logger.info(f"  Scan interval: {SCAN_INTERVAL_MINUTES} minutes")
    logger.info("=" * 60)

    scan_count = 0

    while True:
        scan_count += 1
        logger.info(f"\n[Scan #{scan_count}]")

        # Run the scan
        success = run_scan()

        if success:
            logger.info(f"Next scan in {SCAN_INTERVAL_MINUTES} minutes...")
        else:
            logger.warning(f"Scan failed. Retrying in {SCAN_INTERVAL_MINUTES} minutes...")

        # Wait for next scan
        time.sleep(SCAN_INTERVAL_MINUTES * 60)


def run_api_server():
    """Run the FastAPI server in a separate thread."""
    try:
        import uvicorn
        from backend.api.main import app

        logger.info("Starting API server on http://0.0.0.0:8000")
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
    except Exception as e:
        logger.error(f"API server failed: {e}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Automated Ghana Odds Scanner')
    parser.add_argument('--once', action='store_true', help='Run scan once and exit')
    parser.add_argument('--interval', type=int, default=5, help='Scan interval in minutes (default: 5)')
    parser.add_argument('--with-api', action='store_true', help='Also start the API server')
    args = parser.parse_args()

    global SCAN_INTERVAL_MINUTES
    SCAN_INTERVAL_MINUTES = args.interval

    if args.once:
        # Run single scan and exit
        logger.info("Running single scan...")
        run_scan()
        return

    if args.with_api:
        # Start API server in background thread
        api_thread = Thread(target=run_api_server, daemon=True)
        api_thread.start()
        time.sleep(2)  # Give API time to start

    # Run the scheduler loop
    try:
        scheduler_loop()
    except KeyboardInterrupt:
        logger.info("\nScanner stopped by user.")
        sys.exit(0)


if __name__ == '__main__':
    main()
