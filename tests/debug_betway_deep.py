#!/usr/bin/env python3
"""Deep debug of Betway - check JavaScript loading"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

url = 'https://www.betway.com.gh/sport/football'

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

print('Loading Betway Ghana...')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
driver.get(url)

print('Waiting for page load...')
time.sleep(15)  # Wait longer

# Try to find any text on page
body = driver.find_element(By.TAG_NAME, 'body')
body_text = body.text

print(f'\nBody text length: {len(body_text)}')
print(f'Has "football": {"football" in body_text.lower()}')
print(f'Has numbers (odds): {any(char.isdigit() for char in body_text)}')

# Check for specific common betting site elements
selectors_to_try = [
    'button',
    'a',
    'span',
    '[class*="odd"]',
    '[class*="bet"]',
    '[class*="match"]',
    '[data-test]',
    '[data-testid]'
]

print('\nChecking selectors:')
for sel in selectors_to_try:
    elements = driver.find_elements(By.CSS_SELECTOR, sel)
    if elements:
        print(f'  {sel}: {len(elements)} elements')
        # Print first few with text
        for i, elem in enumerate(elements[:3]):
            if elem.text:
                print(f'    {i+1}. {elem.text[:80]}')

# Save screenshot
driver.save_screenshot('betway_debug.png')
print('\nScreenshot saved: betway_debug.png')

driver.quit()
