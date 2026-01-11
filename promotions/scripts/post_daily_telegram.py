import argparse
import os
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Generate daily promo text and post to Telegram.')
    parser.add_argument('--data', help='Path to odds_data.json')
    parser.add_argument('--min-edge', type=float, default=5)
    parser.add_argument('--count', type=int, default=5)
    parser.add_argument('--brand', default='OddsWize')
    parser.add_argument('--cta-url', default='https://oddswize.com/odds?ref=promo_auto')
    parser.add_argument('--out', default='promotions/output/daily_posts.txt')
    parser.add_argument('--token', help='Telegram bot token')
    parser.add_argument('--chat-id', help='Telegram chat id or @channel')
    parser.add_argument('--dry-run', action='store_true')

    args = parser.parse_args()

    gen_cmd = [
        'python',
        str(Path(__file__).with_name('generate_daily_posts.py')),
        '--min-edge', str(args.min_edge),
        '--count', str(args.count),
        '--brand', args.brand,
        '--cta-url', args.cta_url,
        '--out', args.out,
    ]
    if args.data:
        gen_cmd += ['--data', args.data]

    subprocess.run(gen_cmd, check=True)

    if args.dry_run:
        print(Path(args.out).read_text(encoding='utf-8'))
        return

    post_cmd = [
        'python',
        str(Path(__file__).with_name('post_to_telegram.py')),
        '--file', args.out,
    ]
    if args.token:
        post_cmd += ['--token', args.token]
    if args.chat_id:
        post_cmd += ['--chat-id', args.chat_id]

    subprocess.run(post_cmd, check=True)


if __name__ == '__main__':
    main()
