#!/usr/bin/env python3
"""Find the correct Betway Ghana football URL"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import re

# Try different potential URLs
urls_to_try = [
    'https://www.betway.com.gh/',
    'https://www.betway.com.gh/sports',
    'https://www.betway.com.gh/sportsbook',
    'https://www.betway.com.gh/en/sports',
    'https://sports.betway.com.gh/',
    'https://sports.betway.com.gh/en/sports/cat/football'
]

options = uc.ChromeOptions()
options.add_argument('--start-maximized')
options.add_argument('--no-sandbox')

driver = uc.Chrome(options=options, version_main=142)

for url in urls_to_try:
    print(f'\nTrying: {url}')
    try:
        driver.get(url)
        time.sleep(8)

        # Check if page loaded successfully
        if "can't seem to find" in driver.page_source.lower() or "404" in driver.page_source:
            print('  [X] Page not found')
            continue

        print(f'  [OK] Loaded: {driver.title}')
        print(f'  Current URL: {driver.current_url}')

        # Look for football links
        links = driver.find_elements(By.TAG_NAME, 'a')
        football_links = []
        for link in links[:200]:
            href = link.get_attribute('href')
            text = link.text.strip().lower()
            if href and ('football' in href.lower() or 'football' in text or 'soccer' in text):
                football_links.append((text, href))

        if football_links:
            print(f'  Found {len(football_links)} football links:')
            for text, href in football_links[:5]:
                print(f'    - {text}: {href}')

        # Check for odds on current page
        body_text = driver.find_element(By.TAG_NAME, 'body').text
        odds_count = len(re.findall(r'\b\d+\.\d{1,2}\b', body_text))
        print(f'  Decimal numbers found: {odds_count}')

        if odds_count > 50:
            print(f'  [***] THIS PAGE LIKELY HAS ODDS!')
            break

    except Exception as e:
        print(f'  [X] Error: {e}')

print('\n\nFinal URL:', driver.current_url)
print('Waiting 3 seconds...')
time.sleep(3)

driver.quit()
