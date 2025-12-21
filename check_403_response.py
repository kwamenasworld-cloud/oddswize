#!/usr/bin/env python3
"""Check what's actually blocking us"""
import asyncio
from playwright.async_api import async_playwright

async def check_headless_vs_nonheadless():
    print("=" * 60)
    print("TEST 1: HEADLESS MODE")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            response = await page.goto('https://www.betfox.com.gh/api/offer/v3/sports?live=false', timeout=30000)
            print(f"Status: {response.status}")
            print(f"Headers: {response.headers}")

            if response.status == 403:
                body = await response.text()
                print(f"\nResponse body (first 500 chars):\n{body[:500]}")

                # Save full response
                with open('headless_403_response.html', 'w', encoding='utf-8') as f:
                    f.write(body)
                print("\nSaved full response to headless_403_response.html")
        except Exception as e:
            print(f"Error: {e}")

        await browser.close()

    print("\n" + "=" * 60)
    print("TEST 2: NON-HEADLESS MODE")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context()

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
        """)

        page = await context.new_page()

        try:
            # First visit main page to get cookies
            await page.goto('https://www.betfox.com.gh/sportsbook', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)

            # Now try API
            response = await page.goto('https://www.betfox.com.gh/api/offer/v3/sports?live=false', timeout=30000)
            print(f"Status: {response.status}")

            if response.status == 200:
                print("SUCCESS! Non-headless works!")
                body = await response.text()
                print(f"Response preview: {body[:200]}")
        except Exception as e:
            print(f"Error: {e}")

        await browser.close()

asyncio.run(check_headless_vs_nonheadless())
