#!/usr/bin/env python3
"""
Fast HTML scraper for 22Bet Ghana using Selenium.
Loads page once, extracts all match data, closes. Total time: ~8 seconds.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import re

def scrape_22bet_matches():
    """
    Scrape 22Bet matches using Selenium.
    Returns: list of match dictionaries
    """
    print("[22BET] Starting HTML scraper...")
    start_time = time.time()

    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=chrome_options)

    matches = []

    try:
        # Load football main page
        driver.get('https://22bet.com.gh/line/football')

        # Wait for content to load
        time.sleep(8)  # Give time for WebSocket to populate data

        # Get page HTML
        html = driver.page_source

        # Save for debugging
        with open('22bet_page_scraped.html', 'w', encoding='utf-8') as f:
            f.write(html)

        # Look for embedded JSON data in scripts
        json_pattern = r'window\.__[A-Z_]+__\s*=\s*({.*?});'
        json_matches = re.finditer(json_pattern, html, re.DOTALL)

        for match in json_matches:
            try:
                data = json.loads(match.group(1))

                # Recursively find event objects
                def find_events(obj, events_list):
                    if isinstance(obj, dict):
                        # Check if this looks like a match/event
                        keys = set(obj.keys())
                        if ('homeTeam' in keys and 'awayTeam' in keys) or \
                           ('home' in keys and 'away' in keys and 'odds' in keys):
                            events_list.append(obj)

                        # Recurse
                        for value in obj.values():
                            find_events(value, events_list)
                    elif isinstance(obj, list):
                        for item in obj:
                            find_events(item, events_list)

                embedded_events = []
                find_events(data, embedded_events)

                # Parse events
                for event in embedded_events:
                    home = event.get('homeTeam', {}).get('name') or event.get('home', '')
                    away = event.get('awayTeam', {}).get('name') or event.get('away', '')

                    if not home or not away:
                        continue

                    # Extract 1X2 odds
                    odds_data = event.get('odds', {}) or event.get('markets', [])

                    home_odds = draw_odds = away_odds = None

                    if isinstance(odds_data, dict):
                        # Try common keys
                        home_odds = odds_data.get('1') or odds_data.get('home')
                        draw_odds = odds_data.get('X') or odds_data.get('draw')
                        away_odds = odds_data.get('2') or odds_data.get('away')
                    elif isinstance(odds_data, list):
                        # Find 1x2 market
                        for market in odds_data:
                            if market.get('name') == '1x2' or market.get('id') == 621:
                                outcomes = market.get('outcomes', [])
                                if len(outcomes) >= 3:
                                    home_odds = outcomes[0].get('odds')
                                    draw_odds = outcomes[1].get('odds')
                                    away_odds = outcomes[2].get('odds')
                                break

                    league = event.get('tournament', {}).get('name', '') or event.get('league', '')

                    matches.append({
                        'home': str(home),
                        'away': str(away),
                        'league': str(league),
                        'home_odds': home_odds,
                        'draw_odds': draw_odds,
                        'away_odds': away_odds
                    })

            except Exception as e:
                continue

    finally:
        driver.quit()

    elapsed = time.time() - start_time
    print(f"[22BET] Completed in {elapsed:.1f}s, found {len(matches)} matches")

    return matches

if __name__ == '__main__':
    print("=" * 60)
    print("22BET HTML SCRAPER TEST")
    print("=" * 60)

    matches = scrape_22bet_matches()

    if matches:
        print(f"\n✓ SUCCESS: Scraped {len(matches)} matches")

        # Show first 5
        print("\nFirst 5 matches:")
        for i, match in enumerate(matches[:5]):
            print(f"{i+1}. {match['home']} vs {match['away']}")
            if match['home_odds']:
                print(f"   Odds: {match['home_odds']} / {match['draw_odds']} / {match['away_odds']}")

        # Save to file
        with open('22bet_scraped_matches.json', 'w') as f:
            json.dump(matches, f, indent=2)
        print(f"\nSaved to 22bet_scraped_matches.json")

    else:
        print("\n✗ FAILED: No matches found")
        print("Check 22bet_page_scraped.html for page structure")
