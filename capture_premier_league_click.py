#!/usr/bin/env python3
"""
Capture API calls when clicking Premier League.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time

chrome_options = Options()
chrome_options.add_argument('--headless=new')
chrome_options.add_argument('--disable-gpu')
chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

driver = webdriver.Chrome(options=chrome_options)

try:
    print("Loading 22Bet football page...")
    driver.get('https://22bet.com.gh/line/football')
    time.sleep(5)

    # Clear previous logs
    driver.get_log('performance')

    print("Looking for Premier League link...")

    try:
        # Try different selectors for Premier League
        selectors = [
            "//a[contains(text(), 'Premier League')]",
            "//div[contains(text(), 'Premier League')]",
            "//*[contains(text(), 'Premier League')]",
        ]

        element = None
        for selector in selectors:
            try:
                element = driver.find_element(By.XPATH, selector)
                if element:
                    print(f"Found Premier League with selector: {selector}")
                    break
            except:
                continue

        if element:
            print("Clicking Premier League...")
            element.click()
            time.sleep(5)

            # Get logs after click
            logs = driver.get_log('performance')

            # Extract URLs
            urls = []
            for entry in logs:
                log = json.loads(entry['message'])['message']
                if log['method'] == 'Network.requestWillBeSent':
                    url = log['params']['request']['url']
                    if 'platform.22bet.com.gh' in url:
                        urls.append(url)

            print(f"\nAPI calls after clicking Premier League ({len(urls)} total):")
            for url in urls:
                if any(x in url for x in ['event', 'game', 'match', 'league', 'fixture']):
                    print(url)
        else:
            print("Could not find Premier League element")

    except Exception as e:
        print(f"Error: {e}")

finally:
    driver.quit()
