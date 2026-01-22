import argparse
import base64
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


UPLOAD_URL = 'https://www.tiktok.com/upload?lang=en'
MAX_CAPTION_LEN = 2200


def parse_args():
    parser = argparse.ArgumentParser(description='Upload a video to TikTok via Playwright.')
    parser.add_argument('--video', required=True, help='Path to the mp4 file to upload.')
    parser.add_argument('--caption', default='', help='Caption text for the video.')
    parser.add_argument('--caption-file', help='Path to a file containing the caption text.')
    parser.add_argument('--storage-state', help='Path to Playwright storage_state.json.')
    parser.add_argument('--storage-state-b64', help='Base64 storage state (or env TIKTOK_STORAGE_STATE_B64).')
    parser.add_argument('--temp-dir', default='promotions/tmp', help='Temp dir for decoded storage state.')
    parser.add_argument('--timeout', type=int, default=900, help='Timeout in seconds for upload readiness.')
    parser.add_argument('--dry-run', action='store_true', help='Do not click Post.')
    parser.add_argument('--headless', dest='headless', action='store_true', help='Run Chromium in headless mode.')
    parser.add_argument('--headed', dest='headless', action='store_false', help='Run Chromium with a UI.')
    parser.set_defaults(headless=None)
    return parser.parse_args()


def resolve_headless(args):
    if args.headless is not None:
        return args.headless
    env_value = os.getenv('TIKTOK_HEADLESS', '').strip().lower()
    if not env_value:
        return False
    return env_value in {'1', 'true', 'yes', 'y'}


def read_caption(args):
    caption = args.caption or ''
    if not caption and args.caption_file:
        caption = Path(args.caption_file).read_text(encoding='utf-8').strip()
    if len(caption) > MAX_CAPTION_LEN:
        caption = caption[:MAX_CAPTION_LEN - 3] + '...'
    return caption


def resolve_storage_state(args):
    if args.storage_state:
        path = Path(args.storage_state)
        if path.exists():
            return path
        raise SystemExit(f'Storage state not found: {path}')

    env_path = os.getenv('TIKTOK_STORAGE_STATE_PATH')
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path
        raise SystemExit(f'Storage state not found: {path}')

    b64_value = args.storage_state_b64 or os.getenv('TIKTOK_STORAGE_STATE_B64')
    if b64_value:
        try:
            data = base64.b64decode(b64_value)
        except ValueError as exc:
            raise SystemExit(f'Invalid base64 storage state: {exc}')
        temp_dir = Path(args.temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        out_path = temp_dir / 'tiktok_storage_state.json'
        out_path.write_bytes(data)
        return out_path

    raise SystemExit('Provide --storage-state or set TIKTOK_STORAGE_STATE_PATH/B64.')


def iter_targets(page):
    yield page
    for frame in page.frames:
        yield frame


def find_any(page, selectors):
    for target in iter_targets(page):
        for selector in selectors:
            try:
                locator = target.locator(selector)
                if locator.count() > 0:
                    return locator.first
            except Exception:
                continue
    return None


def find_visible(page, selectors):
    for target in iter_targets(page):
        for selector in selectors:
            try:
                locator = target.locator(selector)
                if locator.count() == 0:
                    continue
                candidate = locator.first
                if candidate.is_visible():
                    return candidate
            except Exception:
                continue
    return None


def wait_for_visible(page, selectors, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        locator = find_visible(page, selectors)
        if locator:
            return locator
        time.sleep(0.5)
    return None


def wait_until_enabled(locator, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if locator.is_enabled():
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def fill_caption(page, locator, caption):
    if not caption:
        return
    try:
        tag = locator.evaluate("el => el.tagName.toLowerCase()")
    except Exception:
        tag = ''

    if tag in {'input', 'textarea'}:
        locator.fill(caption)
        return

    modifier = 'Meta' if sys.platform == 'darwin' else 'Control'
    locator.click()
    page.keyboard.press(f'{modifier}+A')
    page.keyboard.type(caption)


def main():
    args = parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        raise SystemExit(f'Video not found: {video_path}')

    storage_state = resolve_storage_state(args)
    caption = read_caption(args)
    headless = resolve_headless(args)

    print('Launching browser...')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(storage_state=str(storage_state))
        page = context.new_page()
        page.set_default_timeout(30_000)

        print('Opening TikTok upload page...')
        page.goto(UPLOAD_URL, wait_until='domcontentloaded')

        file_selectors = [
            'input[type="file"][accept*="video"]',
            'input[type="file"]',
        ]
        file_input = None
        for _ in range(120):
            file_input = find_any(page, file_selectors)
            if file_input:
                break
            time.sleep(0.5)
        if not file_input:
            raise SystemExit('Could not find the video upload input.')

        print('Uploading video...')
        try:
            file_input.set_input_files(str(video_path))
        except PlaywrightTimeoutError as exc:
            raise SystemExit(f'Upload input timed out: {exc}')

        caption_selectors = [
            'textarea[placeholder*="caption" i]',
            'textarea[placeholder*="Describe" i]',
            'div[contenteditable="true"][role="textbox"]',
            'div[contenteditable="true"]',
        ]
        caption_field = wait_for_visible(page, caption_selectors, timeout=60)
        if caption_field and caption:
            print('Filling caption...')
            fill_caption(page, caption_field, caption)
        elif caption:
            print('Caption field not found; skipping.')

        post_selectors = [
            'button:has-text("Post")',
            'button:has-text("Upload")',
            'button[data-e2e*="post"]',
        ]
        post_button = wait_for_visible(page, post_selectors, timeout=args.timeout)
        if not post_button:
            raise SystemExit('Could not find the Post button.')

        print('Waiting for upload to finish...')
        if not wait_until_enabled(post_button, timeout=args.timeout):
            raise SystemExit('Post button did not become enabled in time.')

        if args.dry_run:
            print('Dry run enabled; skipping Post click.')
            return

        print('Posting...')
        post_button.click()

        success_selectors = [
            'text=Your video is being uploaded',
            'text=Video posted',
            'text=Upload another video',
        ]
        success = wait_for_visible(page, success_selectors, timeout=60)
        if success:
            print('Upload submitted.')
        else:
            print('Post clicked; verify the upload in TikTok.')

        context.close()
        browser.close()


if __name__ == '__main__':
    main()
