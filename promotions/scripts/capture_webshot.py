import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description='Capture a website screenshot for promo overlays.')
    parser.add_argument('--url', required=True, help='Website URL to capture')
    parser.add_argument('--out', default='promotions/assets/oddswize_screenshot.png')
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=720)
    parser.add_argument('--full-page', action='store_true')
    parser.add_argument('--wait', type=float, default=2.0, help='Extra wait time in seconds')
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': args.width, 'height': args.height})
        page.goto(args.url, wait_until='networkidle', timeout=60000)
        if args.wait:
            page.wait_for_timeout(int(args.wait * 1000))
        page.screenshot(path=str(out_path), full_page=args.full_page)
        browser.close()

    print(f'Webshot written to {out_path}')


if __name__ == '__main__':
    main()
