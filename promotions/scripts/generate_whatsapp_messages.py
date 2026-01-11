import argparse
import csv
import urllib.parse
from pathlib import Path

from generate_daily_posts import load_data, best_edges


def format_pick_line(index, pick):
    match = pick['match']
    home = match.get('home_team', 'Home')
    away = match.get('away_team', 'Away')
    outcome = pick['outcome']
    bookmaker = pick['bookmaker']
    odds = pick['odds']
    edge = pick['edge']
    return f"{index}) {home} vs {away} - {outcome} {odds:.2f} at {bookmaker} (+{edge:.0f}%)"


def build_daily_message(picks, cta_url, brand):
    lines = [f"Top value picks today on {brand}:"]
    for idx, pick in enumerate(picks, 1):
        lines.append(format_pick_line(idx, pick))
    lines.append(f"Compare all odds: {cta_url}")
    return '\n'.join(lines)


def build_pick_message(pick, cta_url, brand):
    match = pick['match']
    home = match.get('home_team', 'Home')
    away = match.get('away_team', 'Away')
    outcome = pick['outcome']
    bookmaker = pick['bookmaker']
    odds = pick['odds']
    edge = pick['edge']
    return (
        f"Value pick on {brand}: {home} vs {away}. "
        f"{outcome} at {bookmaker} {odds:.2f} (+{edge:.0f}%). "
        f"Compare odds: {cta_url}"
    )


def build_whatsapp_link(message):
    return 'https://wa.me/?text=' + urllib.parse.quote(message)


def main():
    parser = argparse.ArgumentParser(description='Generate WhatsApp-ready promo messages from odds data.')
    parser.add_argument('--data', help='Path to odds_data.json')
    parser.add_argument('--min-edge', type=float, default=5)
    parser.add_argument('--count', type=int, default=5)
    parser.add_argument('--brand', default='OddsWize')
    parser.add_argument('--cta-url', default='https://oddswize.com/odds?ref=wa_share')
    parser.add_argument('--out', default='promotions/output/whatsapp_messages.txt')
    parser.add_argument('--out-links', default='promotions/output/whatsapp_links.csv')

    args = parser.parse_args()

    data = load_data(args.data)
    matches = data.get('matches') or []
    picks = best_edges(matches, args.min_edge, args.count)
    if not picks:
        raise SystemExit('No value picks found for the given edge threshold.')

    daily_message = build_daily_message(picks, args.cta_url, args.brand)
    pick_messages = [build_pick_message(pick, args.cta_url, args.brand) for pick in picks]

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text('\n\n'.join([daily_message] + pick_messages), encoding='utf-8')

    with Path(args.out_links).open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['type', 'message', 'whatsapp_link'])
        writer.writerow(['daily', daily_message, build_whatsapp_link(daily_message)])
        for idx, message in enumerate(pick_messages, 1):
            writer.writerow([f'pick_{idx}', message, build_whatsapp_link(message)])

    print(f'Wrote WhatsApp messages to {args.out}')
    print(f'Wrote WhatsApp links to {args.out_links}')


if __name__ == '__main__':
    main()
