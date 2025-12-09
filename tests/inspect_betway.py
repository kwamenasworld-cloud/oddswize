#!/usr/bin/env python3
"""Inspect Betway page structure in detail"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time

url = 'https://www.betway.com.gh/sport/football'

options = Options()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--start-maximized')
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

print('Loading Betway Ghana...')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
driver.get(url)

print('Waiting 20 seconds for content...')
time.sleep(20)

# Scroll multiple times
for i in range(5):
    driver.execute_script(f"window.scrollTo(0, {(i+1)*500});")
    time.sleep(2)

print(f'\nPage title: {driver.title}')
print(f'Current URL: {driver.current_url}')

# Save page source
with open('betway_page_source.html', 'w', encoding='utf-8') as f:
    f.write(driver.page_source)
print('\nPage source saved to: betway_page_source.html')

# Save screenshot
driver.save_screenshot('betway_screenshot.png')
print('Screenshot saved to: betway_screenshot.png')

# Get all text
body = driver.find_element(By.TAG_NAME, 'body')
body_text = body.text
print(f'\nBody text length: {len(body_text)} characters')
print(f'First 500 characters:\n{body_text[:500]}')

# Try various selectors
selectors_to_check = [
    'div[class*="match"]',
    'div[class*="event"]',
    'div[class*="game"]',
    'div[class*="fixture"]',
    'div[class*="odds"]',
    'button[class*="odds"]',
    'span[class*="odds"]',
    '[data-testid]',
    '[data-test]',
    'article',
    'li[class*="match"]',
    'li[class*="event"]',
]

print('\n\nChecking selectors:')
for sel in selectors_to_check:
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, sel)
        if elements:
            print(f'\n{sel}: {len(elements)} elements found')
            for i, elem in enumerate(elements[:3]):
                text = elem.text.strip()
                if text:
                    print(f'  Element {i+1}: {text[:100]}')
    except Exception as e:
        print(f'{sel}: Error - {e}')

# Look for any numbers that might be odds
print('\n\nSearching for all elements with decimal numbers:')
all_elements = driver.find_elements(By.CSS_SELECTOR, '*')
elements_with_decimals = []

for elem in all_elements[:500]:
    text = elem.text.strip()
    if text and len(text) < 100:
        # Check if contains decimal numbers
        import re
        decimals = re.findall(r'\b\d+\.\d+\b', text)
        if decimals:
            elements_with_decimals.append((elem.tag_name, elem.get_attribute('class'), text))

print(f'Elements with decimal numbers: {len(elements_with_decimals)}')
for i, (tag, cls, text) in enumerate(elements_with_decimals[:10]):
    print(f'{i+1}. <{tag} class="{cls}">: {text}')

input('\nPress Enter to close browser...')
driver.quit()
