#!/usr/bin/env python3
"""Test Betway with non-headless mode"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time
import re

url = 'https://www.betway.com.gh/sport/football'

options = Options()
# DON'T use headless - let it render properly
# options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--start-maximized')

print('Loading Betway Ghana (visible browser)...')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
driver.get(url)

print('Waiting for content to load...')
time.sleep(20)  # Wait for JS to fully load

# Scroll
driver.execute_script("window.scrollTo(0, 1000);")
time.sleep(3)

# Get all divs
all_divs = driver.find_elements(By.CSS_SELECTOR, 'div')
print(f'\nTotal divs: {len(all_divs)}')

# Look for odds patterns
matches_found = []
for div in all_divs:
    text = div.text
    if text and 30 < len(text) < 500:
        odds = re.findall(r'\b\d+\.\d{2}\b', text)
        if len(odds) >= 2:
            matches_found.append(text[:300])

print(f'Potential matches: {len(matches_found)}')
for i, match in enumerate(matches_found[:5]):
    print(f'\n--- Match {i+1} ---')
    print(match)

input('\nPress Enter to close browser...')
driver.quit()
