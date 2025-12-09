#!/usr/bin/env python3
"""Test Betway with correct URL"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

url = 'https://sports.betway.com.gh/en/sports/cat/football'

print('Loading Betway Ghana football (correct URL)...')

options = uc.ChromeOptions()
options.add_argument('--start-maximized')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = uc.Chrome(options=options, version_main=142)
driver.get(url)

print('Initial wait (15 seconds)...')
time.sleep(15)

# Scroll progressively to trigger lazy loading
print('Scrolling to load content...')
for i in range(10):
    driver.execute_script(f"window.scrollTo(0, {(i+1)*400});")
    time.sleep(1)

# Scroll back to top
driver.execute_script("window.scrollTo(0, 0);")
time.sleep(2)

print(f'\nPage title: {driver.title}')
print(f'Current URL: {driver.current_url}')

# Get body text
body = driver.find_element(By.TAG_NAME, 'body')
body_text = body.text

print(f'\nBody text length: {len(body_text)} characters')
print(f'Sample text (first 800 chars):\n{body_text[:800]}\n')

# Count decimal numbers (potential odds)
decimals = re.findall(r'\b\d+\.\d{1,2}\b', body_text)
print(f'Decimal numbers found: {len(decimals)}')
if decimals:
    print(f'Sample decimals: {decimals[:20]}')

# Try different selectors
selectors = [
    'div',
    '[class*="match"]',
    '[class*="event"]',
    '[class*="fixture"]',
    '[class*="odds"]',
    '[data-testid]',
    'button[class*="odds"]',
    'article',
    'li'
]

print('\n\nChecking selectors:')
for sel in selectors:
    elements = driver.find_elements(By.CSS_SELECTOR, sel)
    print(f'{sel}: {len(elements)} elements')

# Look for matches in divs
print('\n\nSearching for matches in divs...')
all_divs = driver.find_elements(By.CSS_SELECTOR, 'div')
matches_found = []

for div in all_divs[:1000]:  # Check more divs
    text = div.text.strip()
    if text and 25 < len(text) < 700:
        odds = re.findall(r'\b\d+\.\d{1,2}\b', text)
        if len(odds) >= 2:
            # Check if it looks like a match (has vs, team names, etc)
            if any(keyword in text.lower() for keyword in ['vs', 'v ', ' - ', 'draw', 'home', 'away']):
                matches_found.append(text[:500])

print(f'Potential matches found: {len(matches_found)}')

if matches_found:
    print('\nFirst 5 matches:')
    for i, match in enumerate(matches_found[:5]):
        print(f'\n--- Match {i+1} ---')
        print(match)
else:
    print('\nNo matches found yet. Checking raw elements with odds...')
    for div in all_divs[:1000]:
        text = div.text.strip()
        if text and 25 < len(text) < 200:
            odds = re.findall(r'\b\d+\.\d{1,2}\b', text)
            if len(odds) >= 3:
                print(f'\nElement with {len(odds)} odds:\n{text}\n')
                if len(matches_found) >= 3:
                    break

print('\n\nSaving page source and screenshot...')
with open('betway_correct_url_source.html', 'w', encoding='utf-8') as f:
    f.write(driver.page_source)
driver.save_screenshot('betway_correct_url.png')

print('Waiting 3 seconds...')
time.sleep(3)

driver.quit()
print('Done!')
