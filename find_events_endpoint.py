#!/usr/bin/env python3
"""Find the endpoint that has actual events/matches"""
import asyncio
from playwright.async_api import async_playwright

async def find_endpoint():
    async def handle_response(response):
        url = response.url
        if 'betfox.com.gh/api' in url and response.status == 200:
            print(f"API: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
        """)

        page = await context.new_page()
        page.on('response', handle_response)

        print("Loading sportsbook...")
        await page.goto('https://www.betfox.com.gh/sportsbook', wait_until='networkidle', timeout=60000)

        print("\nClick on Football...")
        try:
            await page.click('text=Football', timeout=5000)
            await asyncio.sleep(2)
        except:
            pass

        print("\nClick on Premier League if found...")
        try:
            await page.click('text=Premier League', timeout=5000)
            await asyncio.sleep(3)
        except:
            pass

        await browser.close()

asyncio.run(find_endpoint())
