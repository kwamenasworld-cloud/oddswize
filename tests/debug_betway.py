#!/usr/bin/env python3
"""Debug Betway scraper"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time

url = 'https://www.betway.com.gh/sport/football'

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

print('Loading Betway Ghana...')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
driver.get(url)
time.sleep(10)

print('\nPage title:', driver.title)
print('Current URL:', driver.current_url)

# Try different selectors
selectors = [
    '[class*="event"]',
    '[class*="match"]',
    '[class*="game"]',
    '[class*="odds"]',
    'div',
    'span'
]

for sel in selectors:
    elements = driver.find_elements(By.CSS_SELECTOR, sel)
    print(f'\n{sel}: Found {len(elements)} elements')
    if len(elements) > 0 and len(elements) < 20:
        for i, elem in enumerate(elements[:3]):
            text = elem.text[:100] if elem.text else '(no text)'
            print(f'  {i+1}. {text}')

# Save page source to file for inspection
with open('betway_page.html', 'w', encoding='utf-8') as f:
    f.write(driver.page_source)
print('\nPage source saved to betway_page.html')

driver.quit()
