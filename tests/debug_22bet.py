#!/usr/bin/env python3
"""Debug 22Bet scraper"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time

url = 'https://22bet.com.gh/en/line/Football'

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

print('Loading 22Bet Ghana...')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
driver.get(url)
time.sleep(12)

print('\nPage title:', driver.title)
print('Current URL:', driver.current_url)

# Scroll
driver.execute_script("window.scrollTo(0, 1000);")
time.sleep(2)

# Check for common elements
all_divs = driver.find_elements(By.CSS_SELECTOR, 'div')
print(f'\nTotal divs: {len(all_divs)}')

# Look for text with odds patterns
import re
divs_with_odds = []
for div in all_divs[:300]:
    text = div.text
    if text and len(text) > 20:
        # Look for odds pattern
        if re.search(r'\b\d+\.\d+\b', text):
            divs_with_odds.append(text[:200])

print(f'Divs with odds-like numbers: {len(divs_with_odds)}')
for i, text in enumerate(divs_with_odds[:5]):
    print(f'\n{i+1}. {text}')

driver.quit()
