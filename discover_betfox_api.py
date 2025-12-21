#!/usr/bin/env python3
"""
Discover Betfox API using browser automation
"""
import asyncio
from playwright.async_api import async_playwright
import json

async def discover_api():
    """Use Playwright to discover API endpoints"""
    api_calls = []

    async with async_playwright() as p:
        # Launch browser with mobile viewport
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 375, 'height': 667},
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
        )
        page = await context.new_page()

        # Capture all network requests
        async def handle_request(request):
            url = request.url
            if 'api' in url or 'graphql' in url or '.json' in url:
                api_calls.append({
                    'url': url,
                    'method': request.method,
                    'headers': request.headers,
                })
                print(f"📡 API Call: {request.method} {url}")

        async def handle_response(response):
            url = response.url
            if 'api' in url or 'graphql' in url or '.json' in url:
                try:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '')
                        if 'json' in content_type:
                            print(f"✓ Success: {url} -> {response.status}")
                            data = await response.json()
                            print(f"  Data preview: {str(data)[:200]}")
                except Exception as e:
                    print(f"  Error reading response: {e}")

        page.on('request', handle_request)
        page.on('response', handle_response)

        print("Loading Betfox website...")
        try:
            await page.goto('https://www.betfox.com.gh/', wait_until='networkidle', timeout=30000)
            print("Page loaded! Waiting for API calls...")

            # Wait a bit for lazy-loaded content
            await asyncio.sleep(5)

            # Try to click on sports/soccer if available
            try:
                await page.click('text=Football', timeout=5000)
                print("Clicked on Football...")
                await asyncio.sleep(3)
            except:
                print("No Football button found")

            try:
                await page.click('text=Sports', timeout=5000)
                print("Clicked on Sports...")
                await asyncio.sleep(3)
            except:
                print("No Sports button found")

        except Exception as e:
            print(f"Error loading page: {e}")

        await browser.close()

    print(f"\n\nDiscovered {len(api_calls)} API calls:")
    for call in api_calls:
        print(f"  {call['method']} {call['url']}")

    # Save to file
    with open('betfox_api_calls.json', 'w') as f:
        json.dump(api_calls, f, indent=2)
    print(f"\nSaved to betfox_api_calls.json")

if __name__ == '__main__':
    asyncio.run(discover_api())
