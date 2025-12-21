#!/usr/bin/env python3
"""Debug the Betfox scraper"""
import asyncio
from playwright.async_api import async_playwright
from dateutil import parser

async def debug_scraper():
    competitions_data = []
    api_calls_seen = []

    async def handle_response(response):
        nonlocal competitions_data, api_calls_seen
        url = response.url

        # Log all API calls
        if 'betfox.com.gh/api' in url:
            api_calls_seen.append(f"{response.status} {url}")

        # Capture competition enriched data
        if '/api/offer/v4/competitions' in url and 'enriched=2' in url and response.status == 200:
            try:
                comp_data = await response.json()
                competitions_data.append(comp_data)
                print(f"✓ Captured competition data: {len(comp_data.get('enriched', []))} events")
            except Exception as e:
                print(f"✗ Error parsing competition data: {e}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        page = await context.new_page()
        page.on('response', handle_response)

        print("Loading sportsbook...")
        await page.goto('https://www.betfox.com.gh/sportsbook', wait_until='networkidle', timeout=60000)
        await asyncio.sleep(3)

        print(f"Page title: {await page.title()}")

        # Click on competitions
        competitions_to_fetch = ['Premier League', 'LaLiga', 'Serie A']

        for comp_name in competitions_to_fetch:
            print(f"Clicking {comp_name}...")
            try:
                await page.click(f'text={comp_name}', timeout=5000)
                await asyncio.sleep(2)
            except Exception as e:
                print(f"  Failed to click {comp_name}: {e}")

        await asyncio.sleep(3)
        await browser.close()

    print(f"\n{'='*60}")
    print(f"API calls seen: {len(api_calls_seen)}")
    for call in api_calls_seen[:10]:
        print(f"  {call}")
    if len(api_calls_seen) > 10:
        print(f"  ... and {len(api_calls_seen) - 10} more")

    print(f"\nCompetition data captured: {len(competitions_data)}")

    if competitions_data:
        print("\nProcessing matches...")
        total_matches = 0
        for comp in competitions_data:
            events = comp.get('enriched', [])
            print(f"  Competition has {len(events)} enriched events")
            total_matches += len(events)

        print(f"\nTotal events available: {total_matches}")
    else:
        print("\n✗ No competition data captured!")

asyncio.run(debug_scraper())
