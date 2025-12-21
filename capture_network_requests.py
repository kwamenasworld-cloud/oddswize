#!/usr/bin/env python3
"""
Use Selenium to capture actual network requests made by 22Bet.
"""

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import json
    import time

    def capture_requests():
        print("=" * 60)
        print("CAPTURING 22BET NETWORK REQUESTS")
        print("=" * 60)

        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')

        # Enable performance logging to capture network requests
        chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

        driver = webdriver.Chrome(options=chrome_options)

        try:
            print("\n1. Loading 22Bet football page...")
            driver.get('https://22bet.com.gh/line/football')

            # Wait for page to load
            time.sleep(5)

            print("\n2. Extracting network requests...")
            logs = driver.get_log('performance')

            api_requests = []

            for entry in logs:
                log = json.loads(entry['message'])['message']

                if log['method'] == 'Network.requestWillBeSent':
                    url = log['params']['request']['url']

                    # Filter for API requests
                    if any(keyword in url.lower() for keyword in ['api', 'platform', 'sports', 'line', 'feed', 'championship']):
                        method = log['params']['request']['method']
                        headers = log['params']['request'].get('headers', {})

                        api_requests.append({
                            'method': method,
                            'url': url,
                            'headers': dict(headers)
                        })

            print(f"\nFound {len(api_requests)} API requests:")

            seen_urls = set()
            for req in api_requests:
                url = req['url']
                if url not in seen_urls:
                    seen_urls.add(url)
                    print(f"\n{req['method']} {url}")

                    # Show relevant headers
                    if 'authorization' in str(req['headers']).lower():
                        print("  [!] Has Authorization header")
                    if 'x-api-key' in str(req['headers']).lower():
                        print("  [!] Has API Key header")

            # Save to file
            with open('22bet_network_requests.json', 'w') as f:
                json.dumps(api_requests, f, indent=2)

            print(f"\nSaved all requests to 22bet_network_requests.json")

        finally:
            driver.quit()

    if __name__ == '__main__':
        capture_requests()

except ImportError:
    print("Selenium not installed. Install with: pip install selenium")
    print("\nAlternative: Use browser DevTools to manually inspect network requests")
    print("1. Open https://22bet.com.gh/line/football in Chrome")
    print("2. Open DevTools (F12) -> Network tab")
    print("3. Filter by 'Fetch/XHR'")
    print("4. Look for API calls containing sports/championship data")
