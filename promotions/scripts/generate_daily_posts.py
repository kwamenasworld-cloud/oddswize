import argparse
import json
from pathlib import Path


def load_data(path_hint=None):
    candidates = []
    if path_hint:
        candidates.append(Path(path_hint))
    candidates.append(Path('frontend/public/data/odds_data.json'))
    candidates.append(Path('odds_data.json'))

    for path in candidates:
        if path.exists():
            data = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                return data
    raise SystemExit('Could not find odds_data.json')


def best_edges(matches, min_edge, max_picks):
    picks = []
    for match in matches:
        odds_list = match.get('odds') or []
        if not odds_list:
            continue
        for field, outcome in [
            ('home_odds', 'Home'),
            ('draw_odds', 'Draw'),
            ('away_odds', 'Away'),
        ]:
            values = []
            for bookie in odds_list:
                value = bookie.get(field)
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    continue
                if value <= 1:
                    continue
                values.append(value)
            if len(values) < 2:
                continue
            avg = sum(values) / len(values)
            for bookie in odds_list:
                value = bookie.get(field)
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    continue
                if value <= 1:
                    continue
                edge = (value / avg - 1) * 100
                if edge < min_edge:
                    continue
                picks.append({
                    'match': match,
                    'outcome': outcome,
                    'bookmaker': bookie.get('bookmaker', 'Bookmaker'),
                    'odds': value,
                    'edge': edge,
                })
    picks.sort(key=lambda x: x['edge'], reverse=True)
    return picks[:max_picks]


def render_posts(picks, cta_url):
    lines = ['Top value picks today on OddsWize:']
    for idx, pick in enumerate(picks, 1):
        match = pick['match']
        home = match.get('home_team', 'Home')
        away = match.get('away_team', 'Away')
        lines.append(
            f"{idx}) {home} vs {away} - {pick['outcome']} {pick['odds']:.2f} at {pick['bookmaker']} (+{pick['edge']:.0f}%)"
        )
    lines.append(f'Compare all odds: {cta_url}')
    return '\n'.join(lines)


def render_voiceover(picks, brand, cta_url):
    parts = [
        f"Here are today's top value picks on {brand}.",
    ]
    for pick in picks:
        match = pick['match']
        home = match.get('home_team', 'Home')
        away = match.get('away_team', 'Away')
        parts.append(
            f"{home} versus {away}, {pick['outcome']} at {pick['bookmaker']} with odds {pick['odds']:.2f}."
        )
    parts.append(f"Compare all odds now at {cta_url}.")
    return ' '.join(parts)


def main():
    parser = argparse.ArgumentParser(description='Generate daily promo text from odds data.')
    parser.add_argument('--data', help='Path to odds_data.json')
    parser.add_argument('--min-edge', type=float, default=5)
    parser.add_argument('--count', type=int, default=5)
    parser.add_argument('--brand', default='OddsWize')
    parser.add_argument('--cta-url', default='https://oddswize.com/odds?ref=promo_auto')
    parser.add_argument('--out', default='promotions/output/daily_posts.txt')
    parser.add_argument('--voiceover-out', default='promotions/output/daily_voiceover.txt')

    args = parser.parse_args()

    data = load_data(args.data)
    matches = data.get('matches') or []
    picks = best_edges(matches, args.min_edge, args.count)
    if not picks:
        raise SystemExit('No value picks found for the given edge threshold.')

    post_text = render_posts(picks, args.cta_url)
    voiceover_text = render_voiceover(picks, args.brand, args.cta_url)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(post_text, encoding='utf-8')
    Path(args.voiceover_out).write_text(voiceover_text, encoding='utf-8')

    print(f'Wrote posts to {args.out}')
    print(f'Wrote voiceover script to {args.voiceover_out}')


if __name__ == '__main__':
    main()
