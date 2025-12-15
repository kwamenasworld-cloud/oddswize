#!/usr/bin/env python3
"""
GitHub Actions Odds Scraper

Lightweight scraper for running in GitHub Actions.
Uses requests library instead of curl/subprocess for better compatibility.
Scrapes odds from API-based bookmakers and pushes to Cloudflare Worker.
"""

import json
import os
import re
import time
import requests
from datetime import datetime
from typing import Dict, List, Set, Optional
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
CLOUDFLARE_WORKER_URL = os.getenv('CLOUDFLARE_WORKER_URL', '')
CLOUDFLARE_API_KEY = os.getenv('CLOUDFLARE_API_KEY', '')
MAX_MATCHES = 500  # Full coverage
MAX_CHAMPIONSHIPS = 50  # Top leagues by match count
TIMEOUT = 15  # Reduced timeout for faster failures
BATCH_SIZE = 100  # Larger batches = fewer requests

# Common headers for API requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
}

# ============================================================================
# SportyBet Ghana Scraper
# ============================================================================

SPORTYBET_API = "https://www.sportybet.com/api/gh/factsCenter/pcUpcomingEvents"

def scrape_sportybet() -> List[Dict]:
    """Scrape SportyBet Ghana via API."""
    print("Scraping SportyBet Ghana...")
    matches = []
    seen_ids = set()
    session = requests.Session()

    headers = {
        **HEADERS,
        'Referer': 'https://www.sportybet.com/gh/sport/football',
        'clientid': 'web',
        'operid': '3',
        'platform': 'web',
    }

    for page in range(1, 10):  # Max 9 pages
        if len(matches) >= MAX_MATCHES:
            break

        try:
            url = f"{SPORTYBET_API}?sportId=sr%3Asport%3A1&marketId=1%2C18%2C10&pageSize=100&pageNum={page}&option=1"
            resp = session.get(url, headers=headers, timeout=TIMEOUT)
            data = resp.json()

            if data.get('bizCode') != 10000:
                break

            tournaments = data.get('data', {}).get('tournaments', [])
            if not tournaments:
                break

            for tournament in tournaments:
                for event in tournament.get('events', []):
                    event_id = event.get('eventId')
                    if not event_id or event_id in seen_ids:
                        continue

                    home = event.get('homeTeamName')
                    away = event.get('awayTeamName')
                    if not home or not away:
                        continue

                    # Extract 1X2 odds
                    home_odds = draw_odds = away_odds = None
                    for market in event.get('markets', []):
                        if market.get('id') == '1' or market.get('name') in ['1X2', '1x2', 'Match Result']:
                            for outcome in market.get('outcomes', []):
                                desc = outcome.get('desc', '').lower()
                                odds = outcome.get('odds')
                                if odds:
                                    odds_val = float(odds) / 100 if float(odds) > 100 else float(odds)
                                    if desc in ['1', 'home', 'w1']:
                                        home_odds = odds_val
                                    elif desc in ['x', 'draw']:
                                        draw_odds = odds_val
                                    elif desc in ['2', 'away', 'w2']:
                                        away_odds = odds_val
                            break

                    if not home_odds or not away_odds:
                        continue

                    # Get league name
                    sport = event.get('sport', {})
                    category = sport.get('category', {})
                    tourn = category.get('tournament', {})
                    league = tourn.get('name', '')

                    # Get start time
                    start_time = event.get('estimateStartTime', 0)
                    if start_time > 1000000000000:
                        start_time = start_time // 1000

                    seen_ids.add(event_id)
                    matches.append({
                        'bookmaker': 'SportyBet Ghana',
                        'event_id': str(event_id),
                        'home_team': home,
                        'away_team': away,
                        'home_odds': home_odds,
                        'draw_odds': draw_odds or 0.0,
                        'away_odds': away_odds,
                        'league': league,
                        'start_time': start_time,
                    })

            print(f"  Page {page}: {len(matches)} matches")

        except Exception as e:
            print(f"  Page {page} error: {e}")
            break

    print(f"  Total: {len(matches)} matches from SportyBet")
    return matches[:MAX_MATCHES]


# ============================================================================
# 1xBet Ghana Scraper
# ============================================================================

ONEXBET_API = "https://1xbet.com.gh/service-api/LineFeed"

def scrape_1xbet() -> List[Dict]:
    """Scrape 1xBet Ghana via API."""
    print("Scraping 1xBet Ghana...")
    matches = []
    seen_ids = set()
    session = requests.Session()  # Reuse connections

    try:
        # Get championships
        resp = session.get(f"{ONEXBET_API}/GetChampsZip?sport=1&lng=en", headers=HEADERS, timeout=TIMEOUT)
        champs = resp.json().get("Value", [])
        champs = sorted(champs, key=lambda x: x.get("GC", 0), reverse=True)[:MAX_CHAMPIONSHIPS]

        skip_patterns = ["alternative", "team vs player", "specials", "fantasy", "esports"]

        for champ in champs:
            if len(matches) >= MAX_MATCHES:
                break

            champ_id = champ.get("LI")
            champ_name = champ.get("L", "")

            if any(p in champ_name.lower() for p in skip_patterns):
                continue

            # Get games for championship
            try:
                resp = session.get(f"{ONEXBET_API}/GetChampZip?champ={champ_id}&lng=en", headers=HEADERS, timeout=TIMEOUT)
                value = resp.json().get("Value", {})
                games = value.get("G", []) if isinstance(value, dict) else []
            except:
                continue

            game_ids = [g.get("I") for g in games if g.get("I") and g.get("I") not in seen_ids]

            # Fetch games with odds in larger batches
            for i in range(0, len(game_ids), BATCH_SIZE):
                if len(matches) >= MAX_MATCHES:
                    break

                batch_ids = game_ids[i:i+BATCH_SIZE]
                ids_str = ",".join(str(i) for i in batch_ids)

                try:
                    resp = session.get(f"{ONEXBET_API}/GetGamesZip?ids={ids_str}&lng=en", headers=HEADERS, timeout=TIMEOUT)
                    games_data = resp.json().get("Value", [])
                except:
                    continue

                for game in games_data:
                    event_id = game.get("I")
                    if not event_id or event_id in seen_ids:
                        continue

                    home = game.get("O1") or game.get("O1E")
                    away = game.get("O2") or game.get("O2E")

                    home_odds = draw_odds = away_odds = None
                    for o in game.get("E", []):
                        if o.get("G") != 1:
                            continue
                        ot = o.get("T")
                        if ot == 1:
                            home_odds = o.get("C")
                        elif ot == 2:
                            draw_odds = o.get("C")
                        elif ot == 3:
                            away_odds = o.get("C")

                    if not (home and away and home_odds and away_odds):
                        continue

                    # Validate odds
                    try:
                        home_odds = float(home_odds)
                        away_odds = float(away_odds)
                        draw_odds = float(draw_odds) if draw_odds else 0.0

                        if home_odds < 1.01 or home_odds > 100:
                            continue
                        if away_odds < 1.01 or away_odds > 100:
                            continue
                        if draw_odds > 0 and (draw_odds < 2.0 or draw_odds > 50):
                            continue
                    except:
                        continue

                    seen_ids.add(event_id)
                    matches.append({
                        'bookmaker': '1xBet Ghana',
                        'event_id': str(event_id),
                        'home_team': home,
                        'away_team': away,
                        'home_odds': home_odds,
                        'draw_odds': draw_odds,
                        'away_odds': away_odds,
                        'league': game.get("L", ""),
                        'start_time': game.get("S", 0),
                    })

    except Exception as e:
        print(f"  1xBet error: {e}")

    print(f"  Total: {len(matches)} matches from 1xBet")
    return matches[:MAX_MATCHES]


# ============================================================================
# 22Bet Ghana Scraper
# ============================================================================

TWENTYTWOBET_API = "https://22bet.ng/LineFeed"

def scrape_22bet() -> List[Dict]:
    """Scrape 22Bet via API."""
    print("Scraping 22Bet...")
    matches = []
    seen_ids = set()
    session = requests.Session()  # Reuse connections

    try:
        # Get championships
        resp = session.get(f"{TWENTYTWOBET_API}/GetChampsZip?sport=1&lng=en", headers=HEADERS, timeout=TIMEOUT)
        champs = resp.json().get("Value", [])
        champs = sorted(champs, key=lambda x: x.get("GC", 0), reverse=True)[:MAX_CHAMPIONSHIPS]

        skip_patterns = ["alternative", "team vs player", "specials", "fantasy", "esports"]

        for champ in champs:
            if len(matches) >= MAX_MATCHES:
                break

            champ_id = champ.get("LI")
            champ_name = champ.get("L", "")

            if any(p in champ_name.lower() for p in skip_patterns):
                continue

            # Get games for championship
            try:
                resp = session.get(f"{TWENTYTWOBET_API}/GetChampZip?champ={champ_id}&lng=en", headers=HEADERS, timeout=TIMEOUT)
                value = resp.json().get("Value", {})
                games = value.get("G", []) if isinstance(value, dict) else []
            except:
                continue

            game_ids = [g.get("I") for g in games if g.get("I") and g.get("I") not in seen_ids]

            # Fetch games with odds in larger batches
            for i in range(0, len(game_ids), BATCH_SIZE):
                if len(matches) >= MAX_MATCHES:
                    break

                batch_ids = game_ids[i:i+BATCH_SIZE]
                ids_str = ",".join(str(i) for i in batch_ids)

                try:
                    resp = session.get(f"{TWENTYTWOBET_API}/GetGamesZip?ids={ids_str}&lng=en", headers=HEADERS, timeout=TIMEOUT)
                    games_data = resp.json().get("Value", [])
                except:
                    continue

                for game in games_data:
                    event_id = game.get("I")
                    if not event_id or event_id in seen_ids:
                        continue

                    home = game.get("O1") or game.get("O1E")
                    away = game.get("O2") or game.get("O2E")

                    home_odds = draw_odds = away_odds = None
                    for o in game.get("E", []):
                        if o.get("G") != 1:
                            continue
                        ot = o.get("T")
                        if ot == 1:
                            home_odds = o.get("C")
                        elif ot == 2:
                            draw_odds = o.get("C")
                        elif ot == 3:
                            away_odds = o.get("C")

                    if not (home and away and home_odds and away_odds):
                        continue

                    # Validate odds
                    try:
                        home_odds = float(home_odds)
                        away_odds = float(away_odds)
                        draw_odds = float(draw_odds) if draw_odds else 0.0

                        if home_odds < 1.01 or home_odds > 100:
                            continue
                        if away_odds < 1.01 or away_odds > 100:
                            continue
                        if draw_odds > 0 and (draw_odds < 2.0 or draw_odds > 50):
                            continue
                    except:
                        continue

                    seen_ids.add(event_id)
                    matches.append({
                        'bookmaker': '22Bet Ghana',
                        'event_id': str(event_id),
                        'home_team': home,
                        'away_team': away,
                        'home_odds': home_odds,
                        'draw_odds': draw_odds,
                        'away_odds': away_odds,
                        'league': game.get("L", ""),
                        'start_time': game.get("S", 0),
                    })

    except Exception as e:
        print(f"  22Bet error: {e}")

    print(f"  Total: {len(matches)} matches from 22Bet")
    return matches[:MAX_MATCHES]


# ============================================================================
# Betway Ghana Scraper
# ============================================================================

BETWAY_API = "https://www.betway.com.gh/sportsapi/br/v1/BetBook/Upcoming/"

def scrape_betway() -> List[Dict]:
    """Scrape Betway Ghana via API."""
    print("Scraping Betway Ghana...")
    matches = []
    seen_ids = set()
    session = requests.Session()

    headers = {
        **HEADERS,
        'Referer': 'https://www.betway.com.gh/sport/soccer/upcoming',
    }

    skip = 0
    page_size = 500

    for _ in range(10):  # Max 10 pages
        if len(matches) >= MAX_MATCHES:
            break

        try:
            url = (
                f"{BETWAY_API}?countryCode=GH"
                f"&sportId=soccer"
                f"&cultureCode=en-US"
                f"&marketTypes=%5BWin%2FDraw%2FWin%5D"
                f"&isEsport=false"
                f"&Skip={skip}"
                f"&Take={page_size}"
            )
            resp = session.get(url, headers=headers, timeout=TIMEOUT*2)  # Betway slower
            data = resp.json()

            events = data.get('events', [])
            if not events:
                break

            markets = data.get('markets', [])
            outcomes = data.get('outcomes', [])
            prices = data.get('prices', [])

            # Build lookup maps
            market_by_event = {}
            for m in markets:
                if m.get('name') == '[Win/Draw/Win]' or m.get('displayName') == '1X2':
                    market_by_event[m.get('eventId')] = m

            outcomes_by_market = {}
            for o in outcomes:
                mid = o.get('marketId')
                if mid not in outcomes_by_market:
                    outcomes_by_market[mid] = []
                outcomes_by_market[mid].append(o)

            price_by_outcome = {p.get('outcomeId'): p.get('priceDecimal') for p in prices}

            for event in events:
                event_id = event.get('eventId')
                if not event_id or event_id in seen_ids:
                    continue

                home = event.get('homeTeam')
                away = event.get('awayTeam')
                if not home or not away:
                    continue

                market = market_by_event.get(event_id)
                if not market:
                    continue

                market_id = market.get('marketId')
                market_outcomes = outcomes_by_market.get(market_id, [])

                home_odds = draw_odds = away_odds = None

                for outcome in market_outcomes:
                    outcome_id = outcome.get('outcomeId')
                    outcome_name = outcome.get('name', '').lower()
                    price = price_by_outcome.get(outcome_id)

                    if not price:
                        continue

                    if outcome_name == home.lower() or outcome.get('displayName', '').lower() == home.lower():
                        home_odds = price
                    elif outcome_name == away.lower() or outcome.get('displayName', '').lower() == away.lower():
                        away_odds = price
                    elif 'draw' in outcome_name or outcome_name == 'x':
                        draw_odds = price

                if not home_odds or not away_odds:
                    continue

                seen_ids.add(event_id)
                matches.append({
                    'bookmaker': 'Betway Ghana',
                    'event_id': str(event_id),
                    'home_team': home,
                    'away_team': away,
                    'home_odds': home_odds,
                    'draw_odds': draw_odds or 0.0,
                    'away_odds': away_odds,
                    'league': event.get('league', ''),
                    'start_time': event.get('expectedStartEpoch', 0),
                })

            print(f"  Skip {skip}: {len(matches)} matches")

            if data.get('isFinalPage', False):
                break

            skip += page_size

        except Exception as e:
            print(f"  Betway error: {e}")
            break

    print(f"  Total: {len(matches)} matches from Betway")
    return matches[:MAX_MATCHES]


# ============================================================================
# SoccaBet Ghana Scraper
# ============================================================================

SOCCABET_API = "https://www.soccabet.com/bet/odds.js"

def iter_dict_or_list(data):
    """Helper to iterate over dict items or list elements."""
    if isinstance(data, dict):
        return data.items()
    elif isinstance(data, list):
        return enumerate(data)
    return []

def scrape_soccabet() -> List[Dict]:
    """Scrape SoccaBet Ghana via API."""
    print("Scraping SoccaBet Ghana...")
    matches = []

    headers = {
        **HEADERS,
        'Referer': 'https://www.soccabet.com/',
    }

    try:
        session = requests.Session()
        session.get('https://www.soccabet.com/', headers=headers, timeout=TIMEOUT)

        resp = session.get(SOCCABET_API, headers=headers, timeout=TIMEOUT*2)
        if resp.status_code != 200:
            print(f"  Error: HTTP {resp.status_code}")
            return []

        data = resp.json()

        # Get soccer sport data (ID: 77 or key 'soccer')
        sports = data.get('sports', {})
        soccer = sports.get('77', sports.get('soccer', {}))

        if not soccer:
            # Try to find soccer in list format
            if isinstance(sports, list):
                for sport in sports:
                    if sport.get('id') == 77 or sport.get('name', '').lower() == 'soccer':
                        soccer = sport
                        break

        if not soccer:
            print("  Error: No soccer data found")
            return []

        categories = soccer.get('categories', soccer.get('regions', []))

        skip_patterns = ['esoccer', 'ebasketball', 'esports', '(thomas)', '(nathan)',
                         '(iron)', '(jason)', '(panther)', '(felix)', '(odin)', '(cleo)']

        for cat_id, category in iter_dict_or_list(categories):
            if len(matches) >= MAX_MATCHES:
                break

            if isinstance(category, dict):
                cat_name = category.get('name', 'Unknown')
                tournaments = category.get('tournaments', category.get('competitions', []))
            else:
                continue

            for tourn_id, tournament in iter_dict_or_list(tournaments):
                if len(matches) >= MAX_MATCHES:
                    break

                if isinstance(tournament, dict):
                    tourn_name = tournament.get('name', 'Unknown')
                    league = f"{cat_name}. {tourn_name}"
                    raw_matches = tournament.get('matches', tournament.get('events', []))
                else:
                    continue

                for match_id, match in iter_dict_or_list(raw_matches):
                    if len(matches) >= MAX_MATCHES:
                        break

                    if not isinstance(match, dict):
                        continue

                    # Skip live matches
                    if match.get('live'):
                        continue

                    name = match.get('name', '')
                    if not name or ' v ' not in name:
                        # Try alternative format
                        home = match.get('home', match.get('homeTeam', ''))
                        away = match.get('away', match.get('awayTeam', ''))
                        if home and away:
                            name = f"{home} v {away}"
                        else:
                            continue

                    if ' v ' in name:
                        parts = name.split(' v ')
                    elif ' vs ' in name:
                        parts = name.split(' vs ')
                    else:
                        continue

                    if len(parts) != 2:
                        continue

                    home_team = parts[0].strip()
                    away_team = parts[1].strip()

                    # Skip eSports
                    full_name = f"{home_team} {away_team}".lower()
                    if any(p in full_name for p in skip_patterns):
                        continue

                    start_ts = match.get('ts', match.get('startTime', 0))
                    match_id_str = str(match.get('id', match_id))

                    # Find 1x2 market
                    markets_data = match.get('markets', match.get('odds', []))
                    home_odds = draw_odds = away_odds = 0

                    for mkt_id, mkt in iter_dict_or_list(markets_data):
                        if not isinstance(mkt, dict):
                            continue

                        type_id = str(mkt.get('typeid', mkt.get('typeId', mkt.get('marketType', ''))))
                        mkt_name = mkt.get('name', '').lower()

                        # Match 1X2 market by type ID or name
                        if type_id in ['4102', '4720', '1'] or '1x2' in mkt_name or 'match result' in mkt_name:
                            selections = mkt.get('selections', mkt.get('outcomes', []))

                            for sel_id, sel in iter_dict_or_list(selections):
                                if not isinstance(sel, dict):
                                    continue

                                outcome = str(sel.get('n', sel.get('name', sel.get('outcome', ''))))
                                odds_str = sel.get('o', sel.get('odds', sel.get('price', '0')))

                                try:
                                    odds = float(odds_str)
                                except:
                                    continue

                                if outcome in ['1', 'home', 'Home']:
                                    home_odds = odds
                                elif outcome in ['X', 'x', 'draw', 'Draw']:
                                    draw_odds = odds
                                elif outcome in ['2', 'away', 'Away']:
                                    away_odds = odds

                            if home_odds > 0 and away_odds > 0:
                                break

                    # Validate odds
                    if home_odds <= 1 or away_odds <= 1:
                        continue
                    if draw_odds > 0 and draw_odds < 2.0:
                        continue

                    matches.append({
                        'bookmaker': 'SoccaBet Ghana',
                        'event_id': match_id_str,
                        'home_team': home_team,
                        'away_team': away_team,
                        'home_odds': home_odds,
                        'draw_odds': draw_odds,
                        'away_odds': away_odds,
                        'league': league,
                        'start_time': start_ts,
                    })

        print(f"  Total: {len(matches)} matches from SoccaBet")

    except Exception as e:
        print(f"  SoccaBet error: {e}")
        import traceback
        traceback.print_exc()

    return matches[:MAX_MATCHES]


# ============================================================================
# Betfox Ghana Scraper (uses Playwright due to Cloudflare protection)
# ============================================================================

def scrape_betfox() -> List[Dict]:
    """Scrape Betfox Ghana via API using Playwright to bypass Cloudflare."""
    print("Scraping Betfox Ghana...")
    matches = []

    try:
        import asyncio
        from playwright.async_api import async_playwright
        from dateutil import parser

        async def fetch_betfox_data():
            """Async function to fetch Betfox data with Playwright"""
            async with async_playwright() as p:
                # Launch with non-headless mode (works with Xvfb in GitHub Actions)
                browser = await p.chromium.launch(
                    headless=False,  # Non-headless to bypass Cloudflare
                    args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
                )
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='en-US',
                    timezone_id='Africa/Accra',
                )

                # Add stealth script to avoid detection
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                """)

                page = await context.new_page()

                try:
                    # Navigate to sportsbook
                    await page.goto('https://www.betfox.com.gh/sportsbook', wait_until='networkidle', timeout=60000)
                    await asyncio.sleep(5)

                    # Fetch categories to get all competition IDs
                    print("  Fetching all competitions...")
                    categories = await page.evaluate('''async () => {
                        const response = await fetch('https://www.betfox.com.gh/api/offer/v3/categories?sport=Football', {
                            headers: {
                                'Accept': 'application/json',
                                'x-betr-operator': 'bf-group',
                                'x-betr-brand': 'betfox.com.gh',
                                'x-locale': 'en',
                            }
                        });
                        return await response.json();
                    }''')

                    # Extract all competition IDs
                    competition_ids = []
                    for category_group in ['popularCompetitions', 'popularCategories', 'remainingCategories']:
                        items = categories.get(category_group, [])
                        if category_group == 'popularCompetitions':
                            for comp in items:
                                competition_ids.append(comp.get('id'))
                        else:
                            for category in items:
                                for comp in category.get('competitions', []):
                                    competition_ids.append(comp.get('id'))

                    # Remove duplicates and take top competitions by fixture count
                    competition_ids = list(set(competition_ids))
                    print(f"  Found {len(competition_ids)} unique competitions")

                    # Fetch enriched data for ALL competitions in batches
                    all_data = []
                    batch_size = 15  # Larger batches

                    for i in range(0, len(competition_ids), batch_size):  # Get ALL competitions
                        batch = competition_ids[i:i+batch_size]
                        ids_param = ','.join(batch)

                        try:
                            batch_data = await page.evaluate(f'''async () => {{
                                const response = await fetch('https://www.betfox.com.gh/api/offer/v4/competitions?ids={ids_param}&enriched=2&sport=Football', {{
                                    headers: {{
                                        'Accept': 'application/json',
                                        'x-betr-operator': 'bf-group',
                                        'x-betr-brand': 'betfox.com.gh',
                                        'x-locale': 'en',
                                    }}
                                }});
                                return await response.json();
                            }}''')
                            all_data.append(batch_data)
                            print(f"  Batch {i//batch_size + 1}/{(len(competition_ids) + batch_size - 1) // batch_size} done")
                            await asyncio.sleep(0.5)  # Faster rate limiting
                        except Exception as e:
                            print(f"  Batch {i//batch_size + 1} failed: {e}")

                    await browser.close()
                    print(f"  Fetched {len(all_data)} batches of enriched data")
                    return all_data if all_data else None

                except Exception as e:
                    print(f"  Browser error: {e}")
                    await browser.close()
                    return None

        # Run the async function
        data = asyncio.run(fetch_betfox_data())
        if not data:
            print("  Failed to fetch Betfox data")
            return []

        # Process the enriched competition data
        skip_patterns = ['esoccer', 'ebasketball', 'esports', 'virtual']

        for comp_response in data:
            enriched_comps = comp_response.get('enriched', [])

            for comp in enriched_comps:
                # Get league info from competition
                league = comp.get('name', 'Unknown')
                category = comp.get('category', {}).get('name', '')
                if category:
                    league = f"{category}. {league}"

                # Process fixtures (matches) in this competition
                fixtures = comp.get('fixtures', [])

                for fixture in fixtures:
                    if len(matches) >= MAX_MATCHES:
                        break

                    # Skip live events
                    if fixture.get('live'):
                        continue

                    # Get team names from competitors
                    competitors = fixture.get('competitors', [])
                    if len(competitors) < 2:
                        continue

                    home_team = competitors[0].get('name', '')
                    away_team = competitors[1].get('name', '')

                    if not home_team or not away_team:
                        continue

                    # Skip eSports
                    full_name = f"{home_team} {away_team}".lower()
                    if any(p in full_name for p in skip_patterns):
                        continue

                    # Extract 1X2 odds from FOOTBALL_WINNER market
                    home_odds = draw_odds = away_odds = None

                    for market in fixture.get('markets', []):
                        if market.get('type') == 'FOOTBALL_WINNER':
                            outcomes = market.get('outcomes', [])
                            for outcome in outcomes:
                                value = outcome.get('value')
                                odds = outcome.get('odds')

                                if odds and value:
                                    if value == 'HOME':
                                        home_odds = float(odds)
                                    elif value == 'DRAW':
                                        draw_odds = float(odds)
                                    elif value == 'AWAY':
                                        away_odds = float(odds)
                            break

                    if not home_odds or not away_odds:
                        continue

                    # Get match start time
                    start_ts = None
                    start_time = fixture.get('startTime')
                    if start_time:
                        try:
                            dt = parser.parse(start_time)
                            start_ts = int(dt.timestamp())
                        except:
                            pass

                    event_id = str(fixture.get('id', f"{home_team}_{away_team}"))

                    matches.append({
                        'bookmaker': 'Betfox Ghana',
                        'event_id': event_id,
                        'home_team': home_team,
                        'away_team': away_team,
                        'home_odds': home_odds,
                        'draw_odds': draw_odds if draw_odds else 0,
                        'away_odds': away_odds,
                        'league': league,
                        'start_time': start_ts,
                    })

        print(f"  Total: {len(matches)} matches from Betfox")

    except ImportError:
        print("  Playwright not installed. Skipping Betfox.")
        return []
    except Exception as e:
        print(f"  Betfox error: {e}")
        import traceback
        traceback.print_exc()

    return matches[:MAX_MATCHES]


# ============================================================================
# Event Matching
# ============================================================================

def normalize_team_name(name: str) -> str:
    """Normalize team name for matching."""
    name = name.lower().strip()
    # Remove common suffixes
    suffixes = [' fc', ' sc', ' cf', ' afc', ' united', ' city', ' town', ' sporting']
    for suffix in suffixes:
        name = name.replace(suffix, '')
    # Remove special characters
    name = re.sub(r'[^a-z0-9\s]', '', name)
    return name.strip()


def teams_match(team1: str, team2: str) -> bool:
    """Check if two team names match."""
    n1 = normalize_team_name(team1)
    n2 = normalize_team_name(team2)

    if n1 == n2:
        return True

    # Fuzzy match
    ratio = SequenceMatcher(None, n1, n2).ratio()
    return ratio > 0.75


def match_events(all_matches: Dict[str, List[Dict]]) -> List[List[Dict]]:
    """Match events across bookmakers."""
    print("\nMatching events across bookmakers...")

    matched = []
    used_ids = {bookie: set() for bookie in all_matches}

    # Use first bookmaker as base
    bookies = list(all_matches.keys())
    if not bookies:
        return []

    base_bookie = bookies[0]
    other_bookies = bookies[1:]

    for base_match in all_matches[base_bookie]:
        event_group = [base_match]
        base_home = base_match['home_team']
        base_away = base_match['away_team']

        for other_bookie in other_bookies:
            for other_match in all_matches[other_bookie]:
                other_id = other_match['event_id']
                if other_id in used_ids[other_bookie]:
                    continue

                if (teams_match(base_home, other_match['home_team']) and
                    teams_match(base_away, other_match['away_team'])):
                    event_group.append(other_match)
                    used_ids[other_bookie].add(other_id)
                    break

        if len(event_group) >= 2:
            matched.append(event_group)

    print(f"  Matched {len(matched)} events across bookmakers")
    return matched


# ============================================================================
# Cloudflare Push
# ============================================================================

def push_to_cloudflare(matched_events: List[List[Dict]]) -> bool:
    """Push matched events to Cloudflare Worker."""
    if not CLOUDFLARE_WORKER_URL:
        print("CLOUDFLARE_WORKER_URL not configured - skipping push")
        return False

    print(f"\nPushing {len(matched_events)} events to Cloudflare...")

    # Group by league
    leagues = {}
    for event_group in matched_events:
        base = event_group[0]
        league = base.get('league', 'Unknown')

        if league not in leagues:
            leagues[league] = []

        match_data = {
            'id': f"match_{hash(base['home_team'] + base['away_team'])}",
            'home_team': base['home_team'],
            'away_team': base['away_team'],
            'league': league,
            'kickoff': datetime.fromtimestamp(base.get('start_time', 0)).isoformat() if base.get('start_time') else datetime.now().isoformat(),
            'odds': [
                {
                    'bookmaker': m['bookmaker'],
                    'home_odds': m['home_odds'],
                    'draw_odds': m['draw_odds'],
                    'away_odds': m['away_odds'],
                    'last_updated': datetime.now().isoformat()
                }
                for m in event_group
            ]
        }
        leagues[league].append(match_data)

    # Format for API
    api_data = [{'league': league, 'matches': matches} for league, matches in leagues.items()]

    # Push to Cloudflare with retry logic
    url = f"{CLOUDFLARE_WORKER_URL}/api/odds/update"
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': CLOUDFLARE_API_KEY
    }

    # Retry up to 3 times with increasing timeout
    for attempt in range(3):
        timeout = 60 + (attempt * 30)  # 60s, 90s, 120s
        try:
            print(f"  Attempt {attempt + 1}/3 (timeout: {timeout}s)...")
            resp = requests.post(url, json=api_data, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                print(f"  Success: {resp.json().get('message', 'OK')}")
                return True
            else:
                print(f"  Failed: {resp.status_code} - {resp.text}")
                if resp.status_code < 500:  # Don't retry client errors
                    return False
        except requests.exceptions.Timeout:
            print(f"  Timeout on attempt {attempt + 1}")
        except Exception as e:
            print(f"  Error: {e}")

        if attempt < 2:
            time.sleep(2)  # Brief pause before retry

    print("  All attempts failed")
    return False


# ============================================================================
# Main
# ============================================================================

def main():
    print("=" * 60)
    print("OddsWize GitHub Actions Scraper")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)

    # Scrape all bookmakers in parallel for speed
    all_matches = {}
    scrapers = {
        'SportyBet Ghana': scrape_sportybet,
        '1xBet Ghana': scrape_1xbet,
        '22Bet Ghana': scrape_22bet,
        'Betway Ghana': scrape_betway,
        'SoccaBet Ghana': scrape_soccabet,
        'Betfox Ghana': scrape_betfox,
    }

    print("\nRunning scrapers in parallel...")
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_bookie = {
            executor.submit(scraper): bookie
            for bookie, scraper in scrapers.items()
        }
        for future in as_completed(future_to_bookie):
            bookie = future_to_bookie[future]
            try:
                matches = future.result()
                if matches:
                    all_matches[bookie] = matches
            except Exception as e:
                print(f"  {bookie} failed: {e}")

    total = sum(len(m) for m in all_matches.values())
    print(f"\nTotal scraped: {total} matches from {len(all_matches)} bookmakers")

    if not all_matches:
        print("No matches scraped - exiting")
        return

    # Match events
    matched = match_events(all_matches)

    if not matched:
        print("No matched events - exiting")
        return

    # Save to file (for artifact upload)
    output = {
        'last_updated': datetime.now().isoformat(),
        'stats': {
            'total_scraped': total,
            'matched_events': len(matched),
            'bookmakers': list(all_matches.keys())
        },
        'matches': [
            {
                'home_team': e[0]['home_team'],
                'away_team': e[0]['away_team'],
                'league': e[0].get('league', ''),
                'odds': [
                    {
                        'bookmaker': m['bookmaker'],
                        'home_odds': m['home_odds'],
                        'draw_odds': m['draw_odds'],
                        'away_odds': m['away_odds']
                    }
                    for m in e
                ]
            }
            for e in matched[:200]
        ]
    }

    with open('odds_data.json', 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to odds_data.json")

    # Push to Cloudflare
    push_to_cloudflare(matched)

    print("\nDone!")


if __name__ == '__main__':
    main()
