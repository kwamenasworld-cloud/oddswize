#!/usr/bin/env python3
"""Debug Betfox network calls"""
import asyncio
from playwright.async_api import async_playwright

async def debug_betfox():
    async def handle_response(response):
        url = response.url
        if 'betfox' in url and ('api' in url or 'json' in url):
            print(f"API Call: {response.status} {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        page = await context.new_page()
        page.on('response', handle_response)

        print("Loading page...")
        await page.goto('https://www.betfox.com.gh/sportsbook', wait_until='networkidle', timeout=60000)
        print("Page loaded")
        await asyncio.sleep(5)

        print("\nPage title:", await page.title())
        await browser.close()

asyncio.run(debug_betfox())
