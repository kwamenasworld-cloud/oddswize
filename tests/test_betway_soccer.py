#!/usr/bin/env python3
"""Test Betway with correct soccer URL"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import re

url = 'https://www.betway.com.gh/sport/soccer'

print('Loading Betway Ghana soccer...')

options = uc.ChromeOptions()
options.add_argument('--start-maximized')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = uc.Chrome(options=options, version_main=142)
driver.get(url)

print('Waiting for content to load (20 seconds)...')
time.sleep(20)

# Scroll to trigger lazy loading
print('Scrolling...')
for i in range(8):
    driver.execute_script(f"window.scrollTo(0, {(i+1)*500});")
    time.sleep(2)

print(f'\nPage title: {driver.title}')
print(f'Current URL: {driver.current_url}')

# Get body text
body = driver.find_element(By.TAG_NAME, 'body')
body_text = body.text

print(f'\nBody text length: {len(body_text)} characters')
print(f'First 600 characters:\n{body_text[:600]}\n')

# Look for all divs
all_divs = driver.find_elements(By.CSS_SELECTOR, 'div')
print(f'Total divs: {len(all_divs)}')

# Look for matches with odds patterns
matches_found = []
for div in all_divs[:800]:
    text = div.text.strip()
    if text and 30 < len(text) < 600:
        # Look for decimal odds
        odds = re.findall(r'\b\d+\.\d{1,2}\b', text)
        if len(odds) >= 2:
            matches_found.append(text[:400])

print(f'\nPotential matches found: {len(matches_found)}')

if matches_found:
    print('\nFirst 10 matches:')
    for i, match in enumerate(matches_found[:10]):
        print(f'\n--- Match {i+1} ---')
        print(match)
else:
    print('\nNo matches found.')

# Save for inspection
with open('betway_soccer_source.html', 'w', encoding='utf-8') as f:
    f.write(driver.page_source)
driver.save_screenshot('betway_soccer.png')
print('\nPage source saved to: betway_soccer_source.html')
print('Screenshot saved to: betway_soccer.png')

time.sleep(3)
driver.quit()
print('Done!')
