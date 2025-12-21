#!/usr/bin/env python3
"""Capture actual Betfox API response"""
import asyncio
import json
from playwright.async_api import async_playwright

async def capture_data():
    api_data = None

    async def handle_response(response):
        nonlocal api_data
        url = response.url
        if '/api/offer/v4/competitions' in url and 'enriched=2' in url and response.status == 200:
            try:
                api_data = await response.json()
                print(f"Captured competition data from: {url[:100]}...")
            except Exception as e:
                print(f"Error: {e}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        )

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """)

        page = await context.new_page()
        page.on('response', handle_response)

        await page.goto('https://www.betfox.com.gh/sportsbook', wait_until='networkidle', timeout=60000)
        await asyncio.sleep(2)

        # Click on Premier League to trigger the enriched API call
        try:
            await page.click('text=Premier League', timeout=10000)
            await asyncio.sleep(3)
        except Exception as e:
            print(f"Click error: {e}")

        await browser.close()

    if api_data:
        # Save to file
        with open('betfox_response.json', 'w') as f:
            json.dump(api_data, f, indent=2)
        print("Saved to betfox_response.json")

        # Show structure
        if isinstance(api_data, list):
            print(f"\nResponse is a list with {len(api_data)} items")
            if api_data:
                print(f"First item keys: {list(api_data[0].keys()) if isinstance(api_data[0], dict) else type(api_data[0])}")
        else:
            print(f"\nResponse keys: {list(api_data.keys())}")

asyncio.run(capture_data())
