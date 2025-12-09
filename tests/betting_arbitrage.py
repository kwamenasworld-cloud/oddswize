#!/usr/bin/env python3
"""
Sports Betting Arbitrage Scanner
Finds guaranteed profit opportunities across multiple bookmakers
Target: $3K/month scalable
"""

import requests
import json
from datetime import datetime

class BettingArbitrage:
    """Scan multiple bookmakers for arbitrage opportunities"""

    def __init__(self):
        # Using free Odds API - get your key at the-odds-api.com
        self.api_key = 'YOUR_API_KEY'  # Free tier: 500 requests/month
        self.base_url = 'https://api.the-odds-api.com/v4'
        self.opportunities = []

    def get_sports(self):
        """Get available sports"""
        url = f'{self.base_url}/sports/'
        params = {'apiKey': self.api_key}

        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                sports = response.json()
                print(f'\nFound {len(sports)} sports available\n')
                return sports
        except Exception as e:
            print(f'Error: {e}')
        return []

    def get_odds(self, sport='soccer_epl'):
        """Get odds for a specific sport"""
        url = f'{self.base_url}/sports/{sport}/odds/'
        params = {
            'apiKey': self.api_key,
            'regions': 'us,uk,eu',  # Multiple regions for more bookmakers
            'markets': 'h2h',  # Head to head (moneyline)
            'oddsFormat': 'decimal'
        }

        try:
            print(f'Fetching odds for {sport}...')
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                print(f'Found {len(data)} games\n')
                return data
            else:
                print(f'API Error: {response.status_code}')
                if response.status_code == 401:
                    print('Invalid API key - get one at the-odds-api.com')
        except Exception as e:
            print(f'Error: {e}')

        return []

    def calculate_arbitrage(self, game):
        """Calculate if arbitrage exists for a game"""
        if not game.get('bookmakers'):
            return None

        home_team = game['home_team']
        away_team = game['away_team']

        # Find best odds for each outcome across all bookmakers
        best_home = {'odds': 0, 'bookmaker': ''}
        best_away = {'odds': 0, 'bookmaker': ''}

        for bookmaker in game['bookmakers']:
            for market in bookmaker.get('markets', []):
                if market['key'] == 'h2h':
                    for outcome in market['outcomes']:
                        odds = outcome['price']

                        if outcome['name'] == home_team and odds > best_home['odds']:
                            best_home = {'odds': odds, 'bookmaker': bookmaker['title']}

                        if outcome['name'] == away_team and odds > best_away['odds']:
                            best_away = {'odds': odds, 'bookmaker': bookmaker['title']}

        # Calculate arbitrage
        if best_home['odds'] > 0 and best_away['odds'] > 0:
            # Arbitrage percentage
            arb_pct = (1 / best_home['odds'] + 1 / best_away['odds']) * 100

            if arb_pct < 100:  # Arbitrage exists!
                profit_pct = 100 - arb_pct

                return {
                    'game': f"{home_team} vs {away_team}",
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_odds': best_home['odds'],
                    'away_odds': best_away['odds'],
                    'home_bookmaker': best_home['bookmaker'],
                    'away_bookmaker': best_away['bookmaker'],
                    'profit_pct': profit_pct,
                    'arb_pct': arb_pct,
                    'commence_time': game.get('commence_time', '')
                }

        return None

    def calculate_stakes(self, arb, bankroll=100):
        """Calculate optimal bet sizes"""
        # Stake on home = bankroll / (1 + (home_odds / away_odds))
        # Stake on away = bankroll - stake_home

        home_odds = arb['home_odds']
        away_odds = arb['away_odds']

        stake_home = bankroll / (1 + (home_odds / away_odds))
        stake_away = bankroll - stake_home

        # Calculate guaranteed profit
        profit_home = (stake_home * home_odds) - bankroll
        profit_away = (stake_away * away_odds) - bankroll

        return {
            'bankroll': bankroll,
            'stake_home': stake_home,
            'stake_away': stake_away,
            'profit': profit_home,  # Should be same as profit_away
            'roi': (profit_home / bankroll) * 100
        }

    def scan_all(self, sports=['soccer_epl', 'basketball_nba', 'americanfootball_nfl', 'tennis_atp']):
        """Scan multiple sports for arbitrage"""
        print('='*70)
        print('  SPORTS BETTING ARBITRAGE SCANNER')
        print('='*70)

        all_opportunities = []

        for sport in sports:
            games = self.get_odds(sport)

            for game in games:
                arb = self.calculate_arbitrage(game)
                if arb:
                    all_opportunities.append(arb)

        # Sort by profit %
        all_opportunities.sort(key=lambda x: x['profit_pct'], reverse=True)

        return all_opportunities

    def display_opportunities(self, opportunities):
        """Display found arbitrage opportunities"""
        print('\n' + '='*70)
        print(f'  ARBITRAGE OPPORTUNITIES FOUND: {len(opportunities)}')
        print('='*70 + '\n')

        if not opportunities:
            print('No arbitrage found. This is normal - opportunities are rare.\n')
            print('Tips:')
            print('- Check more sports')
            print('- Scan more frequently (odds change constantly)')
            print('- Use more bookmakers')
            return

        for i, opp in enumerate(opportunities, 1):
            print(f'{i}. {opp["game"]}')
            print(f'   {opp["home_team"]}: {opp["home_odds"]:.2f} ({opp["home_bookmaker"]})')
            print(f'   {opp["away_team"]}: {opp["away_odds"]:.2f} ({opp["away_bookmaker"]})')
            print(f'   Profit: {opp["profit_pct"]:.2f}%')

            # Calculate stakes for $100
            stakes = self.calculate_stakes(opp, 100)
            print(f'   Bet ${stakes["stake_home"]:.2f} on {opp["home_team"]}')
            print(f'   Bet ${stakes["stake_away"]:.2f} on {opp["away_team"]}')
            print(f'   Guaranteed profit: ${stakes["profit"]:.2f}')
            print()

    def monthly_projection(self, avg_profit_pct, trades_per_day, bankroll):
        """Calculate monthly earnings projection"""
        print('\n' + '='*70)
        print('  MONTHLY PROJECTION')
        print('='*70 + '\n')

        profit_per_trade = bankroll * (avg_profit_pct / 100)
        daily_profit = profit_per_trade * trades_per_day
        monthly_profit = daily_profit * 30

        print(f'Bankroll: ${bankroll}')
        print(f'Avg profit per trade: {avg_profit_pct:.2f}% = ${profit_per_trade:.2f}')
        print(f'Trades per day: {trades_per_day}')
        print(f'Daily profit: ${daily_profit:.2f}')
        print(f'Monthly profit: ${monthly_profit:.2f}')

        if monthly_profit >= 3000:
            print(f'\n>> TARGET MET! ${monthly_profit:.2f}/month >= $3,000')
        else:
            needed_bankroll = (3000 / 30 / trades_per_day) / (avg_profit_pct / 100)
            print(f'\n>> Need ${needed_bankroll:.2f} bankroll to reach $3K/month')
            print(f'   OR increase trades/day to {3000/30/profit_per_trade:.1f}')

if __name__ == '__main__':
    print('\nSports Betting Arbitrage Scanner')
    print('Get free API key at: https://the-odds-api.com\n')

    scanner = BettingArbitrage()

    # Example without API key - showing structure
    print('To use:')
    print('1. Get free API key from the-odds-api.com (500 requests/month)')
    print('2. Set api_key in the code')
    print('3. Run: python betting_arbitrage.py\n')

    # Sports to scan (popular ones)
    sports = [
        'soccer_epl',           # English Premier League
        'basketball_nba',       # NBA
        'americanfootball_nfl', # NFL
        'tennis_atp',           # ATP Tennis
        'icehockey_nhl',        # NHL
        'baseball_mlb'          # MLB
    ]

    # Scan for opportunities
    # opportunities = scanner.scan_all(sports)
    # scanner.display_opportunities(opportunities)

    # Projection for $3K/month
    print('EXAMPLE PROJECTION:')
    scanner.monthly_projection(
        avg_profit_pct=2.0,     # 2% profit per arbitrage
        trades_per_day=3,       # 3 opportunities found/day
        bankroll=500            # $500 per trade
    )
