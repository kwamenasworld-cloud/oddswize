#!/usr/bin/env python3
"""Test different 22Bet URLs"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

urls_to_try = [
    'https://22bet.com.gh/',
    'https://22bet.com.gh/line',
    'https://22bet.com.gh/sports',
    'https://www.22bet.com.gh/line/football',
    'https://www.22bet.com.gh/',
]

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

service = Service(ChromeDriverManager().install())

for url in urls_to_try:
    print(f'\nTrying: {url}')
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        time.sleep(5)

        title = driver.title
        current_url = driver.current_url

        print(f'  Title: {title}')
        print(f'  Final URL: {current_url}')
        print(f'  Is 404: {"404" in title or "not found" in title.lower()}')

        driver.quit()
    except Exception as e:
        print(f'  Error: {e}')

print('\nDone!')
