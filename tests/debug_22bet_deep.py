#!/usr/bin/env python3
"""Deep debug 22Bet - find the right selectors"""

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
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

print('Loading 22Bet Ghana...')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
driver.get(url)
time.sleep(15)  # Wait longer

print(f'Current URL: {driver.current_url}')

# Scroll to load more
for i in range(3):
    driver.execute_script(f"window.scrollTo(0, {(i+1)*1000});")
    time.sleep(2)

# Get all text
body = driver.find_element(By.TAG_NAME, 'body')
full_text = body.text

print(f'\nBody text length: {len(full_text)}')
print(f'Sample text:\n{full_text[:500]}')

# Look for team name patterns
lines = full_text.split('\n')
print(f'\nTotal lines: {len(lines)}')

# Find lines that look like team names followed by odds
potential_matches = []
for i, line in enumerate(lines):
    # Look for lines with team-like names (3-30 chars, alphabetic)
    if 5 < len(line) < 35 and any(c.isalpha() for c in line):
        # Check if next few lines have odds
        next_lines = lines[i+1:i+10] if i+10 < len(lines) else lines[i+1:]
        odds_in_next = []
        for nl in next_lines:
            odds = re.findall(r'\b\d+\.\d+\b', nl)
            odds_in_next.extend(odds)

        if len(odds_in_next) >= 2:
            context = '\n'.join([line] + lines[i+1:i+5])
            potential_matches.append(context)

print(f'\nPotential match contexts found: {len(potential_matches)}')
for i, match in enumerate(potential_matches[:5]):
    print(f'\n---Match {i+1}---')
    print(match)
    print('---')

# Try specific selectors
selectors = [
    '[class*="event"]',
    '[class*="game"]',
    '[class*="match"]',
    '[class*="c-events"]',
    '[data-id]',
    'li',
]

print('\n\nTrying selectors:')
for sel in selectors:
    elements = driver.find_elements(By.CSS_SELECTOR, sel)
    print(f'{sel}: {len(elements)} elements')
    if elements and len(elements) < 50:
        for i, elem in enumerate(elements[:2]):
            if elem.text:
                print(f'  {i+1}. {elem.text[:100]}')

driver.quit()
