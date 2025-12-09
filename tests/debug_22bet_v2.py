#!/usr/bin/env python3
"""Debug 22Bet scraper with correct URL"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time
import re

url = 'https://www.22bet.com.gh/line/football'

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

print('Loading 22Bet Ghana football...')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
driver.get(url)
time.sleep(12)

print('\nPage title:', driver.title)
print('Current URL:', driver.current_url)

# Scroll
driver.execute_script("window.scrollTo(0, 1000);")
time.sleep(2)

# Look for divs with odds
all_divs = driver.find_elements(By.CSS_SELECTOR, 'div')
print(f'\nTotal divs: {len(all_divs)}')

# Look for text with team names and odds
matches_found = []
for div in all_divs[:500]:
    text = div.text
    if text and len(text) > 30 and len(text) < 500:
        # Look for odds pattern (decimal like 1.50, 2.30)
        odds_found = re.findall(r'\b\d+\.\d+\b', text)
        if len(odds_found) >= 2:
            matches_found.append(text[:300])

print(f'\nDivs with potential matches: {len(matches_found)}')
for i, text in enumerate(matches_found[:5]):
    print(f'\n---Match {i+1}---')
    print(text)

driver.quit()
