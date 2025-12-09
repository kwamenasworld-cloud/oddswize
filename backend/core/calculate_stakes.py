#!/usr/bin/env python3
"""Calculate exact betting stakes for arbitrage"""

def calculate_stakes(bankroll, home_odds, away_odds):
    """Calculate optimal stakes for 2-way arbitrage"""

    # Total implied probability
    total_prob = (1/home_odds) + (1/away_odds)

    # This is arbitrage if total_prob < 1
    if total_prob >= 1:
        print("NOT ARBITRAGE - total probability >= 100%")
        return

    # Calculate stakes
    stake_home = bankroll / total_prob / home_odds
    stake_away = bankroll / total_prob / away_odds

    # Calculate returns
    return_home = stake_home * home_odds
    return_away = stake_away * away_odds

    # Profit (should be same for both)
    profit = return_home - bankroll

    print(f"=== ARBITRAGE CALCULATION ===")
    print(f"Bankroll: ${bankroll:.2f}")
    print(f"Home odds: {home_odds}")
    print(f"Away odds: {away_odds}")
    print()
    print(f"STAKE ON HOME: ${stake_home:.2f}")
    print(f"STAKE ON AWAY: ${stake_away:.2f}")
    print(f"Total staked: ${stake_home + stake_away:.2f}")
    print()
    print(f"If HOME wins: ${return_home:.2f} (profit: ${profit:.2f})")
    print(f"If AWAY wins: ${return_away:.2f} (profit: ${profit:.2f})")
    print()
    print(f"GUARANTEED PROFIT: ${profit:.2f} ({profit/bankroll*100:.2f}%)")

if __name__ == '__main__':
    # Copenhagen vs Kairat example
    calculate_stakes(100, 1.38, 9.50)
    print()
    print("=" * 50)
    print()
    # For $1000 bankroll
    calculate_stakes(1000, 1.38, 9.50)
