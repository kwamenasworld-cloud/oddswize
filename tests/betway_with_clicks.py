#!/usr/bin/env python3
"""Try clicking through Betway navigation"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

url = 'https://www.betway.com.gh/'

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

print('Loading Betway Ghana homepage...')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
driver.get(url)
time.sleep(5)

# Try to click Sport link
try:
    print('Looking for Sport navigation...')
    wait = WebDriverWait(driver, 10)

    # Try different ways to find sport link
    sport_link = None
    try:
        sport_link = driver.find_element(By.LINK_TEXT, 'sport')
    except:
        pass

    if not sport_link:
        try:
            sport_link = driver.find_element(By.PARTIAL_LINK_TEXT, 'Sport')
        except:
            pass

    if sport_link:
        print('Clicking Sport...')
        sport_link.click()
        time.sleep(8)

        # Now look for football
        try:
            football_link = driver.find_element(By.PARTIAL_LINK_TEXT, 'Football')
            print('Clicking Football...')
            football_link.click()
            time.sleep(8)
        except:
            print('Football link not found')

    # Check what we have now
    body_text = driver.find_element(By.TAG_NAME, 'body').text
    print(f'\nCurrent URL: {driver.current_url}')
    print(f'Body text length: {len(body_text)}')
    print(f'Has odds-like numbers: {len(re.findall(r"\\b\\d+\\.\\d+\\b", body_text))} found')

    # Look for any divs with odds
    all_text = []
    for elem in driver.find_elements(By.CSS_SELECTOR, 'div')[:300]:
        text = elem.text
        if text and 20 < len(text) < 300:
            odds = re.findall(r'\\b\\d+\\.\\d+\\b', text)
            if len(odds) >= 2:
                all_text.append(text[:200])

    print(f'Elements with potential odds: {len(all_text)}')
    for i, text in enumerate(all_text[:3]):
        print(f'\n{i+1}. {text}')

except Exception as e:
    print(f'Error: {e}')

driver.quit()
