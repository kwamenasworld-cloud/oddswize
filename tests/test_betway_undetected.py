#!/usr/bin/env python3
"""Test Betway with undetected-chromedriver"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import re

url = 'https://www.betway.com.gh/sport/football'

print('Loading Betway Ghana with undetected-chromedriver...')

options = uc.ChromeOptions()
# Don't use headless initially - it might still trigger detection
options.add_argument('--start-maximized')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = uc.Chrome(options=options, version_main=142)
driver.get(url)

print('Waiting for content to load (25 seconds)...')
time.sleep(25)

# Scroll to trigger lazy loading
print('Scrolling page...')
for i in range(5):
    driver.execute_script(f"window.scrollTo(0, {(i+1)*600});")
    time.sleep(2)

print(f'\nPage title: {driver.title}')
print(f'Current URL: {driver.current_url}')

# Get body text
body = driver.find_element(By.TAG_NAME, 'body')
body_text = body.text

print(f'Body text length: {len(body_text)} characters')
print(f'First 500 characters:\n{body_text[:500]}\n')

# Look for all divs
all_divs = driver.find_elements(By.CSS_SELECTOR, 'div')
print(f'Total divs found: {len(all_divs)}')

# Look for matches with odds patterns
matches_found = []
for div in all_divs[:500]:
    text = div.text.strip()
    if text and 30 < len(text) < 600:
        # Look for decimal odds pattern
        odds = re.findall(r'\b\d+\.\d{1,2}\b', text)
        if len(odds) >= 2:
            matches_found.append(text[:400])

print(f'\nPotential matches found: {len(matches_found)}')

if matches_found:
    print('\nFirst 5 matches:')
    for i, match in enumerate(matches_found[:5]):
        print(f'\n--- Match {i+1} ---')
        print(match)
else:
    print('\nNo matches found. Trying alternative selectors...')

    # Try specific selectors
    selectors = [
        '[class*="match"]',
        '[class*="event"]',
        '[class*="fixture"]',
        '[class*="odds"]',
        'button',
        'article',
        'li'
    ]

    for sel in selectors:
        elements = driver.find_elements(By.CSS_SELECTOR, sel)
        print(f'\n{sel}: {len(elements)} elements')
        if elements and len(elements) < 100:
            for i, elem in enumerate(elements[:3]):
                text = elem.text.strip()
                if text and len(text) > 10:
                    print(f'  {i+1}. {text[:150]}')

# Save page source for inspection
with open('betway_undetected_source.html', 'w', encoding='utf-8') as f:
    f.write(driver.page_source)
print('\nPage source saved to: betway_undetected_source.html')

# Save screenshot
driver.save_screenshot('betway_undetected.png')
print('Screenshot saved to: betway_undetected.png')

print('\nWaiting 5 seconds before closing...')
time.sleep(5)

driver.quit()
print('Done!')
