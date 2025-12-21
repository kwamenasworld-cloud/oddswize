#!/usr/bin/env python3
"""
Capture actual event data from 22Bet WebSocket by waiting longer.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import time
import base64

chrome_options = Options()
chrome_options.add_argument('--headless=new')
chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

driver = webdriver.Chrome(options=chrome_options)

try:
    print("Loading 22Bet Premier League page...")
    driver.get('https://22bet.com.gh/line/football/england/premier-league')

    print("Waiting for event data to load (20 seconds)...")
    time.sleep(20)  # Wait longer for actual event data

    print("\nExtracting WebSocket messages...")

    logs = driver.get_log('performance')

    ws_messages = []

    for entry in logs:
        log = json.loads(entry['message'])['message']

        if log['method'] in ['Network.webSocketFrameSent', 'Network.webSocketFrameReceived']:
            frame_data = log['params'].get('response', log['params'])
            payload = frame_data.get('payloadData', '')

            if payload:
                # Decode to check size
                try:
                    binary = base64.b64decode(payload)
                    ws_messages.append({
                        'direction': 'SENT' if 'Sent' in log['method'] else 'RECEIVED',
                        'payload': payload,
                        'size': len(binary)
                    })
                except:
                    pass

    print(f"Found {len(ws_messages)} WebSocket messages\n")

    # Filter for large messages (likely contain event data)
    large_messages = [m for m in ws_messages if m['size'] > 500]

    print(f"Large messages (>500 bytes): {len(large_messages)}")

    if large_messages:
        print("\n" + "="*60)
        print("LARGE MESSAGES (Likely event data)")
        print("="*60)

        for i, msg in enumerate(large_messages[:5]):
            binary = base64.b64decode(msg['payload'])

            print(f"\n[{msg['direction']}] Message {i+1} - {msg['size']} bytes")

            # Extract readable strings
            strings = []
            current = []
            for byte in binary:
                if 32 <= byte <= 126:
                    current.append(chr(byte))
                else:
                    if len(current) >= 4:
                        strings.append(''.join(current))
                    current = []
            if len(current) >= 4:
                strings.append(''.join(current))

            # Look for event-related keywords
            event_strings = [s for s in strings if any(keyword in s.lower() for keyword in
                ['premier', 'chelsea', 'newcastle', 'event', 'match', 'team', 'odds', 'league'])]

            if event_strings:
                print("Event-related strings:")
                for s in event_strings[:20]:
                    print(f"  - {s}")
            else:
                print("Sample strings:")
                for s in strings[:15]:
                    print(f"  - {s}")

        # Save large messages
        with open('22bet_large_messages.json', 'w') as f:
            json.dump(large_messages, f, indent=2)

        print(f"\n\nSaved {len(large_messages)} large messages to 22bet_large_messages.json")
    else:
        print("No large messages found - event data may use different delivery method")

finally:
    driver.quit()
