import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


LOGIN_URL = 'https://www.instagram.com/accounts/login/'


def main():
    parser = argparse.ArgumentParser(description='Capture Instagram Playwright storage state.')
    parser.add_argument('--out', default='promotions/tmp/instagram_storage_state.json')
    parser.add_argument('--headless', action='store_true', help='Run Chromium in headless mode.')
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context()
        page = context.new_page()
        page.goto(LOGIN_URL, wait_until='domcontentloaded')

        print('Log in to Instagram in the opened browser window.')
        input('Press Enter after login completes...')

        context.storage_state(path=str(out_path))
        print(f'Storage state saved to {out_path}')
        context.close()
        browser.close()


if __name__ == '__main__':
    main()
