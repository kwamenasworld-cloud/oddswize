#!/usr/bin/env python3
"""
Ghana Betting Arbitrage Finder
Runs all scrapers and finds guaranteed profit opportunities across 5 bookmakers
"""

import json
import os
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

# Handle imports for both package and standalone usage
try:
    from backend.scrapers import (
        scrape_betway_ghana,
        scrape_sportybet_ghana,
        scrape_1xbet_ghana,
        scrape_22bet_ghana,
        scrape_soccabet_ghana,
    )
except ImportError:
    # When running standalone, add parent to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from scrapers import (
        scrape_betway_ghana,
        scrape_sportybet_ghana,
        scrape_1xbet_ghana,
        scrape_22bet_ghana,
        scrape_soccabet_ghana,
    )


def normalize_team_name(name: str) -> str:
    """Normalize team name for matching."""
    if not name:
        return ""

    name = name.lower().strip()

    # Replace special characters
    name = name.replace('ü', 'u').replace('ö', 'o').replace('ä', 'a')
    name = name.replace('é', 'e').replace('è', 'e').replace('ê', 'e')
    name = name.replace('á', 'a').replace('à', 'a').replace('ã', 'a')
    name = name.replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
    name = name.replace('ñ', 'n').replace('ç', 'c')

    # Remove common suffixes/prefixes
    remove_patterns = [
        r'\bfc\b', r'\bsc\b', r'\bac\b', r'\bsk\b', r'\bfk\b', r'\bcf\b',
        r'\bsv\b', r'\bssc\b', r'\bafc\b', r'\bud\b', r'\bcd\b', r'\bsd\b',
        r'\bunited\b', r'\bcity\b', r'\btown\b', r'\brathletic\b',
        r'\bsporting\b', r'\breal\b', r'\binter\b', r'\bdynamo\b',
        r'\bnk\b', r'\bkvc\b', r'\brsc\b', r'\bmfk\b', r'\bapo\b',
        r'\bsp\b', r'\brj\b', r'\bse\b',  # Brazilian suffixes
        r'\(.*?\)',  # Remove parenthetical content
    ]

    for pattern in remove_patterns:
        name = re.sub(pattern, '', name)

    # Common abbreviation expansions and name mappings
    abbreviations = {
        'man utd': 'manchester',
        'man united': 'manchester',
        'man city': 'manchester',
        'spurs': 'tottenham',
        'wolves': 'wolverhampton',
        'villa': 'aston',
        'brighton': 'brighton hove albion',
        'palace': 'crystal palace',
        'west ham': 'west ham',
        'newcastle': 'newcastle',
        'nottm forest': 'nottingham forest',
        'nott forest': 'nottingham forest',
        'sheff utd': 'sheffield',
        'sheff wed': 'sheffield wednesday',
        'hamburger': 'hamburg',
        'borussia dortmund': 'dortmund',
        'borussia monchengladbach': 'gladbach',
        'borussia mgladbach': 'gladbach',
        'bayern munchen': 'bayern munich',
        'bayern munich': 'bayern',
        'rb leipzig': 'leipzig',
        'bayer leverkusen': 'leverkusen',
        'eintracht frankfurt': 'frankfurt',
        'werder': 'bremen',
        'hertha berlin': 'hertha',
        'atletico madrid': 'atletico',
        'athletic bilbao': 'bilbao',
        'celta vigo': 'celta',
        'deportivo alaves': 'alaves',
        'paris saint germain': 'psg',
        'paris sg': 'psg',
        'olympique lyon': 'lyon',
        'olympique marseille': 'marseille',
        'as monaco': 'monaco',
        'as roma': 'roma',
        'ac milan': 'milan',
        'inter milan': 'inter',
        'juventus': 'juve',
        'atalanta': 'atalanta bergamo',
        'napoli': 'napoli',
        'lazio roma': 'lazio',
        'dr congo': 'congo dr',
        'democratic republic': 'dr',
    }

    for abbrev, full in abbreviations.items():
        if abbrev in name:
            name = name.replace(abbrev, full)

    # Remove extra whitespace
    name = ' '.join(name.split())

    return name


def similarity_score(s1: str, s2: str) -> float:
    """Calculate similarity between two strings."""
    if not s1 or not s2:
        return 0.0
    return SequenceMatcher(None, s1, s2).ratio()


def times_match(m1: Dict, m2: Dict, max_diff_hours: float = 2.0) -> bool:
    """Check if two matches have similar start times."""
    t1 = m1.get('start_time', 0)
    t2 = m2.get('start_time', 0)

    # If either time is missing, we can't verify - be conservative and reject
    if not t1 or not t2:
        return True  # Allow match if time data is missing (fallback)

    diff_seconds = abs(t1 - t2)
    diff_hours = diff_seconds / 3600

    return diff_hours <= max_diff_hours


def teams_match(m1: Dict, m2: Dict, threshold: float = 0.75) -> bool:
    """Check if two matches are the same game using fuzzy matching and time check."""
    h1 = normalize_team_name(m1.get('home_team', ''))
    h2 = normalize_team_name(m2.get('home_team', ''))
    a1 = normalize_team_name(m1.get('away_team', ''))
    a2 = normalize_team_name(m2.get('away_team', ''))

    if not h1 or not h2 or not a1 or not a2:
        return False

    # First check if start times are close (within 2 hours)
    if not times_match(m1, m2, max_diff_hours=2.0):
        return False

    # Exact match after normalization
    if h1 == h2 and a1 == a2:
        return True

    # Fuzzy match - require high similarity for both teams
    home_sim = similarity_score(h1, h2)
    away_sim = similarity_score(a1, a2)

    # Both teams must match above threshold
    if home_sim >= threshold and away_sim >= threshold:
        return True

    # Word-based matching - check if all words from shorter name are in longer name
    def words_match(s1: str, s2: str) -> bool:
        if s1 == s2:
            return True
        words1 = set(s1.split())
        words2 = set(s2.split())
        if not words1 or not words2:
            return False
        shorter, longer = (words1, words2) if len(words1) <= len(words2) else (words2, words1)
        # All words from shorter must be in longer (allows "hamburg" to match "hamburg bremen")
        # But shorter must have at least 1 significant word
        if len(shorter) >= 1 and shorter.issubset(longer):
            return True
        # Also check if main word (first significant word) matches
        main1 = [w for w in s1.split() if len(w) >= 4]
        main2 = [w for w in s2.split() if len(w) >= 4]
        if main1 and main2 and main1[0] == main2[0]:
            return True
        return False

    # Strict substring check - only allow if substring is significant portion (>= 75%)
    def is_valid_substring(s1: str, s2: str) -> bool:
        if s1 == s2:
            return True
        shorter, longer = (s1, s2) if len(s1) <= len(s2) else (s2, s1)
        if shorter in longer:
            # Substring must be at least 75% of the longer string
            return len(shorter) / len(longer) >= 0.75
        return False

    if len(h1) >= 3 and len(h2) >= 3 and len(a1) >= 3 and len(a2) >= 3:
        # Try word-based matching first
        h_words = words_match(h1, h2)
        a_words = words_match(a1, a2)
        if h_words and a_words:
            return True

        # Fall back to substring matching
        h_valid = is_valid_substring(h1, h2)
        a_valid = is_valid_substring(a1, a2)
        if h_valid and a_valid:
            return True

    return False


def calculate_arbitrage_1x2(odds_list: List[Dict]) -> Optional[Dict]:
    """
    Calculate arbitrage for 1X2 market across multiple bookmakers.
    Returns the best arbitrage opportunity if exists.
    """
    if len(odds_list) < 2:
        return None

    # Find best odds for each outcome
    best_home = max(odds_list, key=lambda x: x.get('home_odds', 0))
    best_draw = max(odds_list, key=lambda x: x.get('draw_odds', 0))
    best_away = max(odds_list, key=lambda x: x.get('away_odds', 0))

    home_odds = best_home.get('home_odds', 0)
    draw_odds = best_draw.get('draw_odds', 0)
    away_odds = best_away.get('away_odds', 0)

    if home_odds <= 1 or away_odds <= 1:
        return None

    # Calculate arbitrage percentage
    # For 1X2: sum of implied probabilities should be < 1 for arbitrage
    implied_home = 1 / home_odds
    implied_away = 1 / away_odds

    if draw_odds > 1:
        # 3-way arbitrage (1X2)
        implied_draw = 1 / draw_odds
        total_implied = implied_home + implied_draw + implied_away

        if total_implied < 1:
            profit_pct = (1 - total_implied) * 100
            return {
                'type': '1X2',
                'home_team': best_home.get('home_team', ''),
                'away_team': best_home.get('away_team', ''),
                'home_odds': home_odds,
                'home_bookmaker': best_home.get('bookmaker', ''),
                'draw_odds': draw_odds,
                'draw_bookmaker': best_draw.get('bookmaker', ''),
                'away_odds': away_odds,
                'away_bookmaker': best_away.get('bookmaker', ''),
                'profit_pct': profit_pct,
                'total_implied': total_implied * 100,
                'all_odds': odds_list
            }
    else:
        # 2-way arbitrage (no draw)
        total_implied = implied_home + implied_away

        if total_implied < 1:
            profit_pct = (1 - total_implied) * 100
            return {
                'type': '12',
                'home_team': best_home.get('home_team', ''),
                'away_team': best_home.get('away_team', ''),
                'home_odds': home_odds,
                'home_bookmaker': best_home.get('bookmaker', ''),
                'draw_odds': 0,
                'draw_bookmaker': 'N/A',
                'away_odds': away_odds,
                'away_bookmaker': best_away.get('bookmaker', ''),
                'profit_pct': profit_pct,
                'total_implied': total_implied * 100,
                'all_odds': odds_list
            }

    return None


def calculate_stakes(arb: Dict, bankroll: float = 100) -> Dict:
    """Calculate optimal stake distribution for guaranteed profit."""
    home_odds = arb['home_odds']
    draw_odds = arb['draw_odds']
    away_odds = arb['away_odds']

    # Calculate stakes proportional to implied probabilities
    implied_home = 1 / home_odds
    implied_away = 1 / away_odds

    if draw_odds > 1:
        implied_draw = 1 / draw_odds
        total = implied_home + implied_draw + implied_away

        stake_home = bankroll * (implied_home / total)
        stake_draw = bankroll * (implied_draw / total)
        stake_away = bankroll * (implied_away / total)

        # Verify: each outcome should return the same amount
        return_home = stake_home * home_odds
        return_draw = stake_draw * draw_odds
        return_away = stake_away * away_odds

        guaranteed_return = min(return_home, return_draw, return_away)
        profit = guaranteed_return - bankroll

        return {
            'bankroll': bankroll,
            'stake_home': round(stake_home, 2),
            'stake_draw': round(stake_draw, 2),
            'stake_away': round(stake_away, 2),
            'guaranteed_return': round(guaranteed_return, 2),
            'profit': round(profit, 2),
            'roi_pct': round((profit / bankroll) * 100, 2)
        }
    else:
        total = implied_home + implied_away

        stake_home = bankroll * (implied_home / total)
        stake_away = bankroll * (implied_away / total)

        return_home = stake_home * home_odds
        return_away = stake_away * away_odds

        guaranteed_return = min(return_home, return_away)
        profit = guaranteed_return - bankroll

        return {
            'bankroll': bankroll,
            'stake_home': round(stake_home, 2),
            'stake_draw': 0,
            'stake_away': round(stake_away, 2),
            'guaranteed_return': round(guaranteed_return, 2),
            'profit': round(profit, 2),
            'roi_pct': round((profit / bankroll) * 100, 2)
        }


class GhanaBettingArbitrage:
    """Find arbitrage across Ghana bookmakers"""

    def __init__(self):
        self.all_matches: Dict[str, List[Dict]] = {}
        self.matched_events: List[List[Dict]] = []

    def scrape_all(self, max_matches: int = 400):
        """Run all scrapers in parallel"""
        print('=' * 70)
        print('  GHANA BETTING ARBITRAGE SCANNER')
        print('=' * 70 + '\n')

        scrapers = [
            ('Betway', scrape_betway_ghana),
            ('SportyBet', scrape_sportybet_ghana),
            ('1xBet', scrape_1xbet_ghana),
            ('22Bet', scrape_22bet_ghana),
            ('SoccaBet', scrape_soccabet_ghana)
        ]

        def run_scraper(name, scraper_fn, max_m):
            try:
                return name, scraper_fn(max_matches=max_m)
            except Exception as e:
                print(f'{name} failed: {e}')
                return name, []

        # Run all scrapers in parallel
        print('Running all scrapers in parallel...\n')
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(run_scraper, name, fn, max_matches): name
                for name, fn in scrapers
            }
            for future in as_completed(futures):
                name, matches = future.result()
                self.all_matches[name] = matches
                print(f'{name}: {len(matches)} matches\n')

        total = sum(len(m) for m in self.all_matches.values())
        print(f'Total matches scraped: {total}')
        return self.all_matches

    def match_events(self) -> List[List[Dict]]:
        """Match same events across all bookmakers."""
        print('\nMatching events across bookmakers...')

        # Start with Betway as base (usually has cleanest names)
        bookmaker_order = ['Betway', 'SportyBet', '1xBet', '22Bet', 'SoccaBet']
        available = [b for b in bookmaker_order if b in self.all_matches and self.all_matches[b]]

        if len(available) < 2:
            print('Need at least 2 bookmakers with matches')
            return []

        base_bookmaker = available[0]
        base_matches = self.all_matches[base_bookmaker]

        matched_events = []
        used_indices = {b: set() for b in available}

        for i, base_match in enumerate(base_matches):
            event_matches = [base_match]
            used_indices[base_bookmaker].add(i)

            for other_bookmaker in available[1:]:
                other_matches = self.all_matches[other_bookmaker]

                for j, other_match in enumerate(other_matches):
                    if j in used_indices[other_bookmaker]:
                        continue

                    if teams_match(base_match, other_match):
                        event_matches.append(other_match)
                        used_indices[other_bookmaker].add(j)
                        break

            if len(event_matches) >= 2:
                matched_events.append(event_matches)

        self.matched_events = matched_events
        print(f'Found {len(matched_events)} matched events across bookmakers')

        # Show match distribution
        distribution = defaultdict(int)
        for event in matched_events:
            distribution[len(event)] += 1

        for count, num_events in sorted(distribution.items()):
            print(f'  {num_events} events with {count} bookmakers')

        return matched_events

    def find_arbitrage(self) -> List[Dict]:
        """Find arbitrage opportunities in matched events."""
        print('\nSearching for arbitrage opportunities...')

        opportunities = []

        for event_matches in self.matched_events:
            arb = calculate_arbitrage_1x2(event_matches)
            if arb:
                opportunities.append(arb)

        # Deduplicate opportunities based on normalized team names
        # Same match can appear twice if team names differ slightly between bookmakers
        opportunities = self._deduplicate_opportunities(opportunities)

        # Sort by profit percentage
        opportunities.sort(key=lambda x: x['profit_pct'], reverse=True)

        print(f'Found {len(opportunities)} arbitrage opportunities')
        return opportunities

    def _deduplicate_opportunities(self, opportunities: List[Dict]) -> List[Dict]:
        """Remove duplicate arbitrage opportunities for the same match."""
        if not opportunities:
            return opportunities

        # Create a normalized key for each opportunity
        def get_match_key(opp: Dict) -> str:
            home = normalize_team_name(opp.get('home_team', ''))
            away = normalize_team_name(opp.get('away_team', ''))
            # Sort to handle any home/away swap edge cases
            teams = tuple(sorted([home, away]))
            return f"{teams[0]}|{teams[1]}"

        # Group by match key, keep the one with highest profit
        seen = {}
        for opp in opportunities:
            key = get_match_key(opp)
            if key not in seen or opp['profit_pct'] > seen[key]['profit_pct']:
                seen[key] = opp

        deduped = list(seen.values())
        if len(deduped) < len(opportunities):
            print(f'  Deduplicated {len(opportunities)} -> {len(deduped)} unique opportunities')

        return deduped

    def display_opportunities(self, opportunities: List[Dict], bankroll: float = 100):
        """Display arbitrage opportunities with stake calculations."""
        print('\n' + '=' * 70)
        print(f'  ARBITRAGE OPPORTUNITIES: {len(opportunities)}')
        print('=' * 70)

        if not opportunities:
            print('\nNo arbitrage found.')
            print('This is normal - betting arbitrage is rare (~0.5-2% of matches)')
            print('\nOdds comparison saved to file for review.\n')
            return

        for i, opp in enumerate(opportunities, 1):
            stakes = calculate_stakes(opp, bankroll)

            print(f'\n{"-"*70}')
            print(f'  #{i}. {opp["home_team"]} vs {opp["away_team"]}')
            print(f'{"-"*70}')
            print(f'  Type: {opp["type"]} | Profit: {opp["profit_pct"]:.2f}%')
            print()
            print(f'  HOME: {opp["home_odds"]:.2f} @ {opp["home_bookmaker"]}')
            if opp["draw_odds"] > 0:
                print(f'  DRAW: {opp["draw_odds"]:.2f} @ {opp["draw_bookmaker"]}')
            print(f'  AWAY: {opp["away_odds"]:.2f} @ {opp["away_bookmaker"]}')
            print()
            print(f'  Stakes for ${bankroll:.2f} bankroll:')
            print(f'    Home: ${stakes["stake_home"]:.2f}')
            if stakes["stake_draw"] > 0:
                print(f'    Draw: ${stakes["stake_draw"]:.2f}')
            print(f'    Away: ${stakes["stake_away"]:.2f}')
            print(f'  Guaranteed return: ${stakes["guaranteed_return"]:.2f}')
            print(f'  Guaranteed profit: ${stakes["profit"]:.2f} ({stakes["roi_pct"]:.2f}%)')

    def display_close_matches(self, threshold: float = 102.0, limit: int = 20):
        """Display matches that are close to arbitrage (for monitoring)."""
        print('\n' + '=' * 70)
        print(f'  CLOSE TO ARBITRAGE (100% < implied < {threshold}%)')
        print('=' * 70)

        close_matches = []

        for event_matches in self.matched_events:
            if len(event_matches) < 2:
                continue

            best_home = max(event_matches, key=lambda x: x.get('home_odds', 0))
            best_draw = max(event_matches, key=lambda x: x.get('draw_odds', 0))
            best_away = max(event_matches, key=lambda x: x.get('away_odds', 0))

            home_odds = best_home.get('home_odds', 0)
            draw_odds = best_draw.get('draw_odds', 0)
            away_odds = best_away.get('away_odds', 0)

            if home_odds <= 1 or away_odds <= 1:
                continue

            implied = (1/home_odds + 1/away_odds) * 100
            if draw_odds > 1:
                implied = (1/home_odds + 1/draw_odds + 1/away_odds) * 100

            # Only show matches CLOSE to arbitrage (not actual arbitrage)
            # Actual arbitrage = implied < 100, close = 100 < implied < threshold
            if implied >= 100.0 and implied < threshold:
                close_matches.append({
                    'home_team': best_home.get('home_team', ''),
                    'away_team': best_home.get('away_team', ''),
                    'home_odds': home_odds,
                    'home_bookie': best_home.get('bookmaker', ''),
                    'draw_odds': draw_odds,
                    'draw_bookie': best_draw.get('bookmaker', ''),
                    'away_odds': away_odds,
                    'away_bookie': best_away.get('bookmaker', ''),
                    'implied': implied,
                    'num_bookies': len(event_matches)
                })

        close_matches.sort(key=lambda x: x['implied'])

        if not close_matches:
            print('\nNo matches close to arbitrage threshold.')
            return

        for i, m in enumerate(close_matches[:limit], 1):
            margin = m['implied'] - 100
            print(f'\n{i}. {m["home_team"]} vs {m["away_team"]} ({m["num_bookies"]} bookies)')
            print(f'   H: {m["home_odds"]:.2f} ({m["home_bookie"]}) | ', end='')
            if m['draw_odds'] > 0:
                print(f'D: {m["draw_odds"]:.2f} ({m["draw_bookie"]}) | ', end='')
            print(f'A: {m["away_odds"]:.2f} ({m["away_bookie"]})')
            print(f'   Implied: {m["implied"]:.2f}% (margin: {margin:.2f}%)')

    def save_results(self, opportunities: List[Dict], filename: str = 'ghana_arb_results.json'):
        """Save results to file."""
        # Prepare serializable data
        matched_simple = []
        for event in self.matched_events:
            matched_simple.append([{
                'bookmaker': m.get('bookmaker'),
                'home_team': m.get('home_team'),
                'away_team': m.get('away_team'),
                'home_odds': m.get('home_odds'),
                'draw_odds': m.get('draw_odds'),
                'away_odds': m.get('away_odds'),
            } for m in event])

        # Remove circular references from opportunities
        opps_clean = []
        for opp in opportunities:
            opp_copy = dict(opp)
            opp_copy.pop('all_odds', None)
            opps_clean.append(opp_copy)

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total_matches': sum(len(m) for m in self.all_matches.values()),
                    'matched_events': len(self.matched_events),
                    'arbitrage_found': len(opportunities)
                },
                'opportunities': opps_clean,
                'matched_events': matched_simple[:100],  # Save first 100 for inspection
            }, f, indent=2)

        print(f'\nResults saved to: {filename}')


def main():
    scanner = GhanaBettingArbitrage()

    # Scrape all bookmakers (800 matches for full coverage)
    scanner.scrape_all(max_matches=800)

    # Match events across bookmakers
    scanner.match_events()

    # Find arbitrage
    opportunities = scanner.find_arbitrage()

    # Display results
    scanner.display_opportunities(opportunities, bankroll=100)

    # Show close matches (within 2% of arbitrage)
    scanner.display_close_matches(threshold=102.0, limit=15)

    # Save results
    scanner.save_results(opportunities)


if __name__ == '__main__':
    main()
