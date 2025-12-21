#!/usr/bin/env python3
"""
Fast WebSocket snapshot scraper for 22Bet Ghana.
Connects, gets data snapshot, disconnects. Total time: ~3 seconds.
"""

import websocket
import json
import threading
import time

class Fast22BetScraper:
    def __init__(self):
        self.ws = None
        self.data = {}
        self.connected = False
        self.subscribed = False
        self.data_received = False

    def scrape_snapshot(self, timeout=10):
        """
        Quick WebSocket connection to get current odds snapshot.
        Returns: dict with event data or None if failed
        """
        ws_url = "wss://centrifugo.22bet.com.gh/connection/websocket"

        def on_message(ws, message):
            try:
                msg = json.loads(message)

                # Check for initial subscription response with data
                if 'result' in msg and msg.get('result'):
                    result = msg['result']

                    # Check if this has event data
                    if 'data' in result or 'publications' in result:
                        self.data[msg.get('id', 'snapshot')] = result
                        self.data_received = True

                # Check for publications (live updates)
                if 'push' in msg:
                    push = msg['push']
                    if 'data' in push:
                        self.data['push_data'] = push['data']
                        self.data_received = True

            except Exception as e:
                pass

        def on_error(ws, error):
            pass

        def on_close(ws, close_code, close_msg):
            self.connected = False

        def on_open(ws):
            self.connected = True

            # Centrifugo connect
            connect_msg = {
                "id": 1,
                "connect": {}
            }
            ws.send(json.dumps(connect_msg))
            time.sleep(0.5)

            # Subscribe to football/line channels
            # Based on typical Centrifugo channel naming
            channels_to_try = [
                "line:football",
                "prematch:football",
                "sport:1",
                "line:sport:1",
                "events:line",
                "feed:line:football",
            ]

            for i, channel in enumerate(channels_to_try):
                subscribe_msg = {
                    "id": i + 2,
                    "subscribe": {
                        "channel": channel
                    }
                }
                ws.send(json.dumps(subscribe_msg))
                time.sleep(0.3)

            self.subscribed = True

        try:
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )

            # Run in thread with timeout
            wst = threading.Thread(target=self.ws.run_forever, kwargs={'ping_interval': 30})
            wst.daemon = True
            wst.start()

            # Wait for data or timeout
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.data_received:
                    break
                time.sleep(0.1)

            # Close connection
            if self.ws:
                self.ws.close()

            return self.data if self.data_received else None

        except Exception as e:
            return None

def test_scraper():
    print("=" * 60)
    print("22BET FAST WEBSOCKET SNAPSHOT")
    print("=" * 60)

    scraper = Fast22BetScraper()

    print("\nConnecting to WebSocket...")
    start = time.time()

    data = scraper.scrape_snapshot(timeout=10)

    elapsed = time.time() - start
    print(f"Completed in {elapsed:.1f} seconds")

    if data:
        print(f"\n[SUCCESS] Received data!")
        print(f"Data keys: {list(data.keys())}")

        # Save to file
        with open('22bet_ws_snapshot.json', 'w') as f:
            json.dump(data, f, indent=2)
        print("Saved to 22bet_ws_snapshot.json")

        # Show sample
        print("\nSample data:")
        print(json.dumps(data, indent=2)[:1000])

        return True
    else:
        print("\n[NO DATA] WebSocket connected but no event data received")
        print("22Bet may require authentication or uses different channel names")
        return False

if __name__ == '__main__':
    success = test_scraper()

    print(f"\n{'='*60}")
    if not success:
        print("[CONCLUSION] 22Bet WebSocket requires:")
        print("  1. Authentication/session tokens, OR")
        print("  2. Different channel subscription pattern, OR")
        print("  3. Is not accessible for public scraping")
        print("\nRECOMMENDATION: Deploy with 5 working bookmakers")
        print("22Bet can be added later if API access is obtained")
    print('='*60)
