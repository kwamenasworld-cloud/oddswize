import argparse
import base64
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


CREATE_URLS = [
    'https://www.instagram.com/',
    'https://www.instagram.com/create/select/',
    'https://www.instagram.com/create/reels/',
    'https://www.instagram.com/reels/create/',
    'https://www.instagram.com/create/select/?__coig_restricted=1',
]
MOBILE_CREATE_URLS = [
    'https://m.instagram.com/',
    'https://m.instagram.com/reels/create/',
    'https://m.instagram.com/create/select/',
]
FILE_INPUT_SELECTORS = [
    'input[type="file"][accept*="video/"]',
    'input[type="file"][accept*="video"]',
    'input[type="file"][accept*="mp4"]',
    'input[type="file"][accept*="image/*,video/*"]',
    'input[type="file"][accept*="image"]',
    'input[type="file"]',
]
CREATE_LEFT_NAV_SELECTORS = [
    'nav a[href="/create/"]',
    'nav a[href="/create/select/"]',
    'nav a[href="/create/reels/"]',
    'nav a[href="/reels/create/"]',
    'nav [aria-label="Create"]',
    'nav [aria-label="Create new post"]',
    'nav [aria-label="New post"]',
    'nav [aria-label="Create new reel"]',
    'nav [aria-label="New reel"]',
]
CREATE_SELECTORS = [
    'div[role="button"]:has(svg[aria-label="New post"])',
    'button:has(svg[aria-label="New post"])',
    'a:has(svg[aria-label="New post"])',
    '[aria-label="Create"]',
    '[aria-label="Create new post"]',
    '[aria-label="New post"]',
    '[aria-label="Create new reel"]',
    '[aria-label="New reel"]',
    'div[role="button"][aria-label="Create"]',
    'nav a[href="/create/"]',
    'a[href="/create/select/"]',
    'a[href="/create/reels/"]',
    'a[href="/reels/create/"]',
    'a[href="/create/style/"]',
    'a[href^="/reels/create"]',
    'nav a:has-text("Create")',
    'nav button:has-text("Create")',
    'nav div[role="button"]:has-text("Create")',
]
CREATE_MENU_SELECTORS = [
    'text=Post',
    'text=Reel',
    'text=Reels',
    'text=Story',
    'text=Live video',
    'div[role="menuitem"]:has-text("Post")',
    'div[role="menuitem"]:has-text("Reel")',
]
POST_SELECTORS = [
    'div[role="menuitem"]:has-text("Post")',
    'div[role="menuitemradio"]:has-text("Post")',
    'text=Post',
    'div[role="button"]:has-text("Post")',
    'button:has-text("Post")',
    'a:has-text("Post")',
]
REEL_SELECTORS = [
    'div[role="menuitem"]:has-text("Reel")',
    'div[role="menuitem"]:has-text("Reels")',
    'div[role="menuitemradio"]:has-text("Reel")',
    'text=Reel',
    'text=Reels',
    'button:has-text("Reel")',
    'button:has-text("Reels")',
    '[role="tab"]:has-text("Reel")',
    '[role="tab"]:has-text("Reels")',
]
SELECT_FROM_COMPUTER_SELECTORS = [
    'text=Select from computer',
    'button:has-text("Select from computer")',
    'div[role="button"]:has-text("Select from computer")',
    'text=Choose from computer',
    'button:has-text("Choose from computer")',
    'div[role="button"]:has-text("Choose from computer")',
    'text=Select files',
    'button:has-text("Select files")',
    'div[role="button"]:has-text("Select files")',
    'text=Choose files',
    'button:has-text("Choose files")',
    'div[role="button"]:has-text("Choose files")',
    'text=Select photos or videos',
    'button:has-text("Select photos or videos")',
    'div[role="button"]:has-text("Select photos or videos")',
    'text=Add photos or videos',
    'button:has-text("Add photos or videos")',
    'div[role="button"]:has-text("Add photos or videos")',
    'text=Select videos',
    'button:has-text("Select videos")',
    'div[role="button"]:has-text("Select videos")',
    'text=Upload',
    'button:has-text("Upload")',
    'div[role="button"]:has-text("Upload")',
    'text=Upload from computer',
    'button:has-text("Upload from computer")',
    'div[role="button"]:has-text("Upload from computer")',
    'text=Add from computer',
    'button:has-text("Add from computer")',
    'div[role="button"]:has-text("Add from computer")',
    'button[aria-label*="select" i]',
    'button[aria-label*="upload" i]',
    'div[role="button"][aria-label*="select" i]',
    'div[role="button"][aria-label*="upload" i]',
    'text=/select|choose|upload/i',
]
NEXT_SELECTORS = [
    'button:has-text("Next")',
    'div[role="button"]:has-text("Next")',
    '[role="button"]:has-text("Next")',
    '[aria-label="Next"]',
]
CAPTION_SELECTORS = [
    'textarea[aria-label*="Write a caption" i]',
    'textarea[aria-label*="caption" i]',
    'div[contenteditable="true"][role="textbox"]',
]
SHARE_SELECTORS = [
    'button:has-text("Share")',
    'button:has-text("Post")',
    'button:has-text("Publish")',
    'div[role="button"]:has-text("Share")',
    'div[role="button"]:has-text("Post")',
    'div[role="button"]:has-text("Publish")',
    '[aria-label="Share"]',
]
MAX_CAPTION_LEN = 2200


def parse_args():
    parser = argparse.ArgumentParser(description='Upload a video to Instagram Reels via Playwright.')
    parser.add_argument('--video', required=True, help='Path to the mp4 file to upload.')
    parser.add_argument('--caption', default='', help='Caption text for the video.')
    parser.add_argument('--caption-file', help='Path to a file containing the caption text.')
    parser.add_argument('--storage-state', help='Path to Playwright storage_state.json.')
    parser.add_argument('--storage-state-b64', help='Base64 storage state (or env INSTAGRAM_STORAGE_STATE_B64).')
    parser.add_argument('--temp-dir', default='promotions/tmp', help='Temp dir for decoded storage state.')
    parser.add_argument('--timeout', type=int, default=900, help='Timeout in seconds for upload readiness.')
    parser.add_argument('--dry-run', action='store_true', help='Do not click Share.')
    parser.add_argument('--debug', action='store_true', help='Capture debug screenshots on failures.')
    parser.add_argument('--debug-dir', default='promotions/tmp', help='Directory for debug screenshots.')
    parser.add_argument('--mobile', action='store_true',
                        help='Use mobile emulation for a more reliable upload flow.')
    parser.add_argument('--headless', dest='headless', action='store_true', help='Run Chromium in headless mode.')
    parser.add_argument('--headed', dest='headless', action='store_false', help='Run Chromium with a UI.')
    parser.set_defaults(headless=None)
    return parser.parse_args()


def resolve_headless(args):
    if args.headless is not None:
        return args.headless
    env_value = os.getenv('INSTAGRAM_HEADLESS', '').strip().lower()
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

    env_path = os.getenv('INSTAGRAM_STORAGE_STATE_PATH')
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path
        raise SystemExit(f'Storage state not found: {path}')

    b64_value = args.storage_state_b64 or os.getenv('INSTAGRAM_STORAGE_STATE_B64')
    if b64_value:
        try:
            data = base64.b64decode(b64_value)
        except ValueError as exc:
            raise SystemExit(f'Invalid base64 storage state: {exc}')
        temp_dir = Path(args.temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        out_path = temp_dir / 'instagram_storage_state.json'
        out_path.write_bytes(data)
        return out_path

    raise SystemExit('Provide --storage-state or set INSTAGRAM_STORAGE_STATE_PATH/B64.')


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


def is_visible(page, selectors):
    return find_visible(page, selectors) is not None


def wait_for_any(page, selectors, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        locator = find_any(page, selectors)
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


def try_click(page, selectors, timeout=20, force=False):
    locator = wait_for_visible(page, selectors, timeout)
    if locator:
        try:
            locator.click()
            return True
        except Exception:
            if force:
                try:
                    locator.click(force=True)
                    return True
                except Exception:
                    return False
            return False
    return False


def click_when_enabled(page, selectors, timeout=20):
    locator = wait_for_visible(page, selectors, timeout)
    if not locator:
        return False
    if not wait_until_enabled(locator, timeout):
        return False
    locator.click()
    return True


def advance_flow(page, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_visible(page, CAPTION_SELECTORS) or is_visible(page, SHARE_SELECTORS):
            return True
        if click_when_enabled(page, NEXT_SELECTORS, timeout=5):
            print('Clicked Next.')
            time.sleep(2)
            continue
        time.sleep(2)
    return False


def dismiss_popups(page):
    popup_selectors = [
        'button:has-text("Allow all cookies")',
        'button:has-text("Only allow essential cookies")',
        'button:has-text("Accept all")',
        'button:has-text("Decline optional cookies")',
        'button:has-text("Continue without accepting")',
        'button:has-text("Not Now")',
        'button:has-text("Not now")',
        'button:has-text("Cancel")',
        'button:has-text("Close")',
        'button:has-text("Continue in browser")',
        'button:has-text("Continue on web")',
        'button:has-text("Use the web")',
        'div[role="button"]:has-text("Not Now")',
        'div[role="button"]:has-text("Not now")',
        'div[role="button"]:has-text("Close")',
        'svg[aria-label="Close"]',
    ]
    for _ in range(3):
        if not try_click(page, popup_selectors, timeout=3):
            break
    try:
        page.evaluate("""
        () => {
          const selectors = [
            'div[role="dialog"] [aria-label="Close"]',
            'div[role="dialog"] button[aria-label="Close"]',
            'div[role="dialog"] svg[aria-label="Close"]',
          ];
          for (const selector of selectors) {
            const el = document.querySelector(selector);
            if (!el) continue;
            const target = el.closest('button,div[role="button"]') || el;
            target.click();
            return true;
          }
          return false;
        }
        """)
    except Exception:
        pass


def detect_login_required(page):
    if 'accounts/login' in page.url:
        return True
    if wait_for_visible(page, ['input[name="username"]', 'input[name="password"]'], timeout=3):
        return True
    if wait_for_visible(page, ['text=Log in', 'text=Log In'], timeout=3):
        return True
    return False


def pick_create_page(context, fallback):
    for candidate in context.pages:
        try:
            url = candidate.url
        except Exception:
            continue
        if is_create_url(url):
            return candidate
    return fallback


def is_create_url(url):
    if not url:
        return False
    if '/reels/create' in url:
        return True
    if '/create/select' in url or '/create/reels' in url or '/create/style' in url:
        return True
    return False


def open_create_and_find_input(page, create_urls):
    context = page.context
    for url in create_urls:
        print(f'Opening Instagram create page: {url}')
        page.goto(url, wait_until='domcontentloaded')
        try:
            page.wait_for_load_state('networkidle', timeout=10_000)
        except PlaywrightTimeoutError:
            pass
        page.wait_for_timeout(2000)
        dismiss_popups(page)
        page = pick_create_page(context, page)

        if detect_login_required(page):
            raise SystemExit('Instagram login required. Storage state may be invalid.')

        if page.url.rstrip('/') in {'https://www.instagram.com/create', 'https://m.instagram.com/create'}:
            forced_url = 'https://m.instagram.com/create/select/' if 'm.instagram.com' in page.url else 'https://www.instagram.com/create/select/'
            try:
                page.goto(forced_url, wait_until='domcontentloaded')
                page.wait_for_timeout(1500)
            except PlaywrightTimeoutError:
                pass
            page = pick_create_page(context, page)

        if not is_create_url(page.url):
            create_link = find_visible(page, CREATE_LEFT_NAV_SELECTORS) or find_visible(page, CREATE_SELECTORS)
            if create_link:
                try:
                    create_link.click()
                except Exception:
                    try:
                        create_link.click(force=True)
                    except Exception:
                        try_js_click_create(page)
                page.wait_for_timeout(1500)
                page = pick_create_page(context, page)
            else:
                try:
                    page.goto('https://www.instagram.com/create/select/', wait_until='domcontentloaded')
                    page.wait_for_timeout(1500)
                    page = pick_create_page(context, page)
                except PlaywrightTimeoutError:
                    pass

        file_input = wait_for_any(page, FILE_INPUT_SELECTORS, timeout=10)
        if file_input:
            return page, file_input

        create_clicked = try_click(page, CREATE_SELECTORS, timeout=10, force=True)
        if not create_clicked:
            create_clicked = try_js_click_create(page)
            if create_clicked:
                print('Clicked Create (js).')
        if create_clicked:
            print('Clicked Create.')
            dismiss_popups(page)
            page.wait_for_timeout(1500)
            page = pick_create_page(context, page)
            if wait_for_visible(page, CREATE_MENU_SELECTORS, timeout=5):
                if try_click(page, POST_SELECTORS, timeout=5, force=True):
                    print('Selected Post.')
                elif try_js_click_menu_item(page, 'Post'):
                    print('Selected Post (js).')
                elif try_js_click_menu_item(page, 'Reel'):
                    print('Selected Reel (js).')
                page.wait_for_timeout(1500)
        else:
            print('Create button not found.')
        file_input = wait_for_any(page, FILE_INPUT_SELECTORS, timeout=20)
        if file_input:
            return page, file_input

    if try_click(page, CREATE_SELECTORS, timeout=10, force=True) or try_js_click_create(page):
        print('Clicked Create (fallback).')
        dismiss_popups(page)
        page.wait_for_timeout(1500)
        page = pick_create_page(context, page)
        if wait_for_visible(page, CREATE_MENU_SELECTORS, timeout=5):
            if try_click(page, POST_SELECTORS, timeout=5, force=True):
                print('Selected Post (fallback).')
            elif try_js_click_menu_item(page, 'Post'):
                print('Selected Post (js fallback).')
            elif try_js_click_menu_item(page, 'Reel'):
                print('Selected Reel (js fallback).')
            page.wait_for_timeout(1500)
        file_input = wait_for_any(page, FILE_INPUT_SELECTORS, timeout=20)
        if file_input:
            return page, file_input

    return page, None


def try_file_chooser(page, selectors, video_path):
    for selector in selectors:
        for force in (False, True):
            try:
                with page.expect_file_chooser(timeout=5_000) as chooser_info:
                    page.locator(selector).first.click(force=force)
                chooser_info.value.set_files(str(video_path))
                return True
            except PlaywrightTimeoutError:
                continue
            except Exception:
                continue
    return False


def try_js_file_chooser(page, video_path):
    script = """
    () => {
      const labels = [
        'Select from computer',
        'Select files',
        'Choose files',
        'Select photos or videos',
        'Add photos or videos',
        'Select videos',
        'Upload',
        'Upload from computer',
        'Add from computer',
      ];
      const nodes = Array.from(document.querySelectorAll('button,div[role="button"],a,span'));
      const match = nodes.find(el => {
        const text = (el.innerText || '').trim();
        if (!text) return false;
        return labels.some(label => text.toLowerCase().includes(label.toLowerCase()));
      });
      if (!match) return false;
      const target = match.closest('button,div[role="button"],a') || match;
      target.click();
      return true;
    }
    """
    try:
        with page.expect_file_chooser(timeout=5_000) as chooser_info:
            page.evaluate(script)
        chooser_info.value.set_files(str(video_path))
        return True
    except PlaywrightTimeoutError:
        return False
    except Exception:
        return False


def try_set_files_direct(page, video_path):
    for target in iter_targets(page):
        try:
            inputs = target.locator('input[type="file"]')
            count = inputs.count()
        except Exception:
            continue
        for idx in range(count):
            try:
                inputs.nth(idx).set_input_files(str(video_path))
                return True
            except Exception:
                continue
    return False


def try_js_click_create(page):
    script = """
    () => {
      const tryOpen = (el) => {
        const target = el.closest('a,button,div[role="button"]') || el;
        target.click();
        return true;
      };
      const createLeft = document.querySelector(
        'nav a[href="/create/"], nav a[href="/create/reels/"], nav a[href="/create/select/"], nav a[href="/create/style/"], ' +
        'a[href^="/reels/create"]'
      );
      if (createLeft) {
        return tryOpen(createLeft);
      }
      const pick = (el) => el && (el.closest('a,button,div[role="button"]') || el);
      const icon = document.querySelector(
        'svg[aria-label="New post"], svg[aria-label="Create"], svg[aria-label="New reel"], ' +
        'svg[aria-label="New Post"], svg[aria-label="Create new post"]'
      );
      if (icon) {
        const target = pick(icon);
        if (target) {
          target.click();
          return true;
        }
      }
      const textTargets = Array.from(document.querySelectorAll('a,button,div[role="button"]'));
      const nav = document.querySelector('nav');
      const scopedTargets = nav ? Array.from(nav.querySelectorAll('a,button,div[role="button"]')) : textTargets;
      const createTarget = scopedTargets.find(el => {
        const text = (el.innerText || '').trim();
        if (text !== 'Create') return false;
        const anchor = el.closest('a');
        if (anchor && anchor.getAttribute('href') === '/create/' && !anchor.closest('nav')) return false;
        return true;
      });
      if (createTarget) {
        createTarget.click();
        return true;
      }
      return false;
    }
    """
    try:
        return bool(page.evaluate(script))
    except Exception:
        return False


def try_js_click_menu_item(page, label):
    script = """
    (label) => {
      const menu = document.querySelector('[role="menu"]') || document.body;
      const nodes = Array.from(menu.querySelectorAll('a,button,div[role="button"],div[role="menuitem"],span,div'));
      const match = nodes.find(el => (el.innerText || '').trim().includes(label));
      if (!match) return false;
      const target = match.closest('a,button,div[role="button"],div[role="menuitem"]') || match;
      target.click();
      return true;
    }
    """
    try:
        return bool(page.evaluate(script, label))
    except Exception:
        return False


def debug_snapshot(page, out_dir, label):
    try:
        out_path = Path(out_dir) / f'instagram_debug_{label}.png'
        out_path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(out_path), full_page=True)
        print(f'Debug screenshot saved: {out_path}')
    except Exception:
        pass


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
        if args.mobile:
            device = p.devices.get('iPhone 14')
            if not device:
                raise SystemExit('Mobile device profile not available.')
            context = browser.new_context(storage_state=str(storage_state), **device)
            create_urls = MOBILE_CREATE_URLS
        else:
            context = browser.new_context(storage_state=str(storage_state))
            create_urls = CREATE_URLS
        page = context.new_page()
        page.set_default_timeout(30_000)

        page, file_input = open_create_and_find_input(page, create_urls)
        if not file_input:
            print('Upload input not found; trying file chooser...')
            if args.debug:
                debug_snapshot(page, args.debug_dir, 'input_missing')

        if file_input:
            print('Uploading video...')
            try:
                file_input.set_input_files(str(video_path))
            except PlaywrightTimeoutError as exc:
                raise SystemExit(f'Upload input timed out: {exc}')
            except Exception:
                if not try_file_chooser(page, SELECT_FROM_COMPUTER_SELECTORS, video_path):
                    if not try_js_file_chooser(page, video_path):
                        if not try_set_files_direct(page, video_path):
                            raise
        else:
            if not try_file_chooser(page, SELECT_FROM_COMPUTER_SELECTORS, video_path):
                if not try_js_file_chooser(page, video_path):
                    if not try_set_files_direct(page, video_path):
                        if args.debug:
                            debug_snapshot(page, args.debug_dir, 'file_chooser_missing')
                        raise SystemExit('Could not trigger the upload dialog on Instagram.')
        page.wait_for_timeout(2000)

        if try_click(page, REEL_SELECTORS, timeout=10):
            print('Selected Reel mode.')
        else:
            print('Reel tab not found; continuing.')

        print('Advancing upload flow...')
        if not advance_flow(page, timeout=args.timeout):
            print('Upload flow did not reach caption/share in time.')
            if args.debug:
                debug_snapshot(page, args.debug_dir, 'advance_timeout')

        caption_field = wait_for_visible(page, CAPTION_SELECTORS, timeout=60)
        if caption_field and caption:
            print('Filling caption...')
            fill_caption(page, caption_field, caption)
        elif caption:
            print('Caption field not found; skipping.')
            if args.debug:
                debug_snapshot(page, args.debug_dir, 'caption_missing')

        share_button = wait_for_visible(page, SHARE_SELECTORS, timeout=args.timeout)
        if not share_button:
            if args.debug:
                debug_snapshot(page, args.debug_dir, 'share_missing')
            raise SystemExit('Could not find the Share button.')

        if not wait_until_enabled(share_button, timeout=args.timeout):
            raise SystemExit('Share button did not become enabled in time.')

        if args.dry_run:
            print('Dry run enabled; skipping Share click.')
            return

        print('Sharing...')
        share_button.click()

        success = wait_for_visible(
            page,
            [
                'text=Your post has been shared',
                'text=Reel shared',
                'text=Post shared',
            ],
            timeout=60,
        )
        if success:
            print('Upload submitted.')
        else:
            print('Share clicked; verify the upload in Instagram.')

        context.close()
        browser.close()


if __name__ == '__main__':
    main()
