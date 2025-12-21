#!/usr/bin/env python3
"""
Capture real network requests from 22Bet using selenium to see what APIs they actually call.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json

def capture_api_calls():
    print("=" * 60)
    print("CAPTURING 22BET NETWORK REQUESTS")
    print("=" * 60)

    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    # Enable performance logging to capture network requests
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    print("\nStarting Chrome...")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        # Visit the Premier League page
        url = 'https://22bet.com.gh/line/football/england/premier-league'
        print(f"Loading: {url}")

        driver.get(url)

        # Wait for content to load
        print("Waiting for page to load...")
        time.sleep(10)  # Give it time to make API calls

        # Get performance logs
        print("\nAnalyzing network requests...")
        logs = driver.get_log('performance')

        api_calls = []

        for entry in logs:
            try:
                log = json.loads(entry['message'])
                message = log.get('message', {})
                method = message.get('method', '')

                # Look for network requests
                if method == 'Network.requestWillBeSent':
                    params = message.get('params', {})
                    request = params.get('request', {})
                    url = request.get('url', '')

                    # Filter for API calls
                    if any(keyword in url.lower() for keyword in ['api', 'feed', 'line', 'sport', 'match', 'event', 'game', 'championship']):
                        if '22bet' in url:
                            api_calls.append({
                                'url': url,
                                'method': request.get('method', 'GET'),
                                'headers': request.get('headers', {})
                            })

            except Exception as e:
                continue

        # Print unique API calls
        unique_urls = set(call['url'] for call in api_calls)

        print(f"\nFound {len(unique_urls)} unique API calls:")
        for url in sorted(unique_urls):
            print(f"  {url}")

        # Save full details
        if api_calls:
            with open('22bet_api_calls.json', 'w') as f:
                json.dump(api_calls, f, indent=2)
            print(f"\nSaved full details to 22bet_api_calls.json")

        return list(unique_urls)

    finally:
        driver.quit()

if __name__ == '__main__':
    api_urls = capture_api_calls()

    print(f"\n{'='*60}")
    if api_urls:
        print(f"[SUCCESS] Found {len(api_urls)} API endpoints!")
        print("Test these endpoints to find the working one")
    else:
        print("[FAILED] No API calls captured")
        print("The page might use WebSockets or load data differently")
    print('='*60)
