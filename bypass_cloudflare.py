#!/usr/bin/env python3
"""Try advanced Cloudflare bypass techniques"""
import asyncio
from playwright.async_api import async_playwright

async def test_stealth_techniques():
    async with async_playwright() as p:
        # Use more aggressive stealth settings
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
        )

        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='Africa/Accra',
            geolocation={'longitude': -0.1870, 'latitude': 5.6037},  # Accra, Ghana
            permissions=['geolocation'],
        )

        # More comprehensive stealth script
        await context.add_init_script("""
            // Overwrite the `plugins` property to use a custom getter
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

            // Overwrite the `plugins` property
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Overwrite the `languages` property
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });

            // Chrome runtime
            window.chrome = {
                runtime: {}
            };

            // Permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({state: Notification.permission}) :
                    originalQuery(parameters)
            );
        """)

        page = await context.new_page()

        api_data = None

        async def handle_response(response):
            nonlocal api_data
            url = response.url
            if '/api/offer/v3/sports' in url and 'live=false' in url:
                print(f"API Response: {response.status} {url}")
                if response.status == 200:
                    try:
                        api_data = await response.json()
                        print(f"SUCCESS! Got {len(api_data) if isinstance(api_data, list) else 'data'}")
                    except Exception as e:
                        print(f"Parse error: {e}")
                elif response.status == 403:
                    text = await response.text()
                    if 'cloudflare' in text.lower():
                        print("Still blocked by Cloudflare")
                    else:
                        print(f"403 but not Cloudflare: {text[:200]}")

        page.on('response', handle_response)

        print("Loading page with stealth mode...")
        try:
            await page.goto('https://www.betfox.com.gh/sportsbook', wait_until='domcontentloaded', timeout=60000)

            # Wait for potential Cloudflare challenge
            await asyncio.sleep(10)

            print(f"Page title: {await page.title()}")

            # Check if we got through
            title = await page.title()
            if 'cloudflare' in title.lower() or 'attention' in title.lower():
                print("❌ Still blocked by Cloudflare")
            else:
                print("✓ Got past Cloudflare!")
                await asyncio.sleep(5)  # Wait for API calls

        except Exception as e:
            print(f"Error: {e}")

        await browser.close()

        return api_data is not None

result = asyncio.run(test_stealth_techniques())
print(f"\n{'SUCCESS' if result else 'FAILED'}")
