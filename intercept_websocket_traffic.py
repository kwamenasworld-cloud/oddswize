#!/usr/bin/env python3
"""
Intercept actual WebSocket messages from 22Bet browser to learn the protocol.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import time

chrome_options = Options()
chrome_options.add_argument('--headless=new')
chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

driver = webdriver.Chrome(options=chrome_options)

try:
    print("Loading 22Bet football page...")
    driver.get('https://22bet.com.gh/line/football')
    time.sleep(10)  # Wait for WebSocket to connect and receive data

    print("\nExtracting WebSocket messages...")

    logs = driver.get_log('performance')

    ws_messages = []

    for entry in logs:
        log = json.loads(entry['message'])['message']

        # Look for WebSocket frame events
        if log['method'] in ['Network.webSocketFrameSent', 'Network.webSocketFrameReceived']:
            frame_data = log['params'].get('response', {})

            if not frame_data:
                frame_data = log['params']

            payload = frame_data.get('payloadData', '')

            if payload:
                ws_messages.append({
                    'direction': 'SENT' if 'Sent' in log['method'] else 'RECEIVED',
                    'payload': payload
                })

    print(f"Found {len(ws_messages)} WebSocket messages\n")

    if ws_messages:
        print("=" * 60)
        print("WEBSOCKET TRAFFIC")
        print("=" * 60)

        for i, msg in enumerate(ws_messages[:20]):  # Show first 20
            print(f"\n[{msg['direction']}] Message {i+1}:")
            try:
                # Try to parse as JSON
                data = json.loads(msg['payload'])
                print(json.dumps(data, indent=2)[:500])
            except:
                print(msg['payload'][:300])

        # Save all messages
        with open('22bet_ws_messages_intercepted.json', 'w') as f:
            json.dump(ws_messages, f, indent=2)

        print(f"\n\nSaved all {len(ws_messages)} messages to 22bet_ws_messages_intercepted.json")

    else:
        print("No WebSocket messages found in logs")

finally:
    driver.quit()
