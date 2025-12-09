#!/usr/bin/env python3
"""Test Betway with very long wait for dynamic content"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import re

url = 'https://www.betway.com.gh/sport/soccer'

print('Loading Betway Ghana soccer...')

options = uc.ChromeOptions()
options.add_argument('--start-maximized')
options.add_argument('--no-sandbox')

driver = uc.Chrome(options=options, version_main=142)
driver.get(url)

# Wait much longer for JavaScript to load all content
print('Waiting 30 seconds for JavaScript content...')
time.sleep(30)

# Scroll progressively
print('Scrolling through page...')
for i in range(15):
    driver.execute_script(f"window.scrollTo(0, {(i+1)*600});")
    time.sleep(3)

print('\nSearching for matches...')

# Get all text elements
all_elements = driver.find_elements(By.CSS_SELECTOR, '*')
print(f'Total elements: {len(all_elements)}')

# Look for any elements containing decimal numbers (odds)
elements_with_odds = []
for elem in all_elements[:2000]:
    text = elem.text.strip()
    if text and 20 < len(text) < 500:
        decimals = re.findall(r'\b\d+\.\d{1,2}\b', text)
        if len(decimals) >= 2:
            elements_with_odds.append(text[:400])

print(f'\nElements with potential odds: {len(elements_with_odds)}')

if elements_with_odds:
    print('\nFirst 10 potential matches:')
    for i, text in enumerate(elements_with_odds[:10]):
        print(f'\n--- Element {i+1} ---')
        print(text)
else:
    print('\nNo odds found. Checking page structure...')

    # Check for specific Betway elements
    betbook_elements = driver.find_elements(By.CSS_SELECTOR, '[class*="betbook"]')
    print(f'Betbook elements: {len(betbook_elements)}')

    sport_elements = driver.find_elements(By.CSS_SELECTOR, '[class*="sport"]')
    print(f'Sport elements: {len(sport_elements)}')

    # Check if there are any iframes
    iframes = driver.find_elements(By.TAG_NAME, 'iframe')
    print(f'Iframes found: {len(iframes)}')

    if iframes:
        print('\nSwitching to first iframe...')
        driver.switch_to.frame(iframes[0])
        iframe_body = driver.find_element(By.TAG_NAME, 'body').text
        print(f'Iframe text length: {len(iframe_body)}')
        print(f'Sample: {iframe_body[:500]}')

driver.quit()
print('\nDone!')
