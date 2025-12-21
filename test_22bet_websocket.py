#!/usr/bin/env python3
"""
Connect to 22Bet WebSocket to get odds data.
"""

import websocket
import json
import time

def test_websocket():
    print("=" * 60)
    print("CONNECTING TO 22BET WEBSOCKET")
    print("=" * 60)

    ws_url = "wss://centrifugo.22bet.com.gh/connection/websocket"
    print(f"\nConnecting to: {ws_url}")

    messages_received = []

    def on_message(ws, message):
        print(f"\n[MESSAGE RECEIVED]")
        try:
            data = json.loads(message)
            print(json.dumps(data, indent=2)[:500])
            messages_received.append(data)

            # Save all messages
            with open('22bet_ws_messages.json', 'w') as f:
                json.dump(messages_received, f, indent=2)

        except Exception as e:
            print(f"Raw message: {message[:200]}")

    def on_error(ws, error):
        print(f"\n[ERROR] {error}")

    def on_close(ws, close_status_code, close_msg):
        print(f"\n[CLOSED] Status: {close_status_code}, Message: {close_msg}")

    def on_open(ws):
        print("\n[CONNECTED] WebSocket opened")

        # Centrifugo connection protocol - send connect command
        connect_msg = {
            "id": 1,
            "method": 1,  # Connect method
            "params": {}
        }

        print(f"\nSending connect message...")
        ws.send(json.dumps(connect_msg))

        # Subscribe to football/sports channels
        time.sleep(1)

        subscribe_messages = [
            {
                "id": 2,
                "method": 2,  # Subscribe method
                "params": {
                    "channel": "sport:1"  # Sport ID 1 = Football
                }
            },
            {
                "id": 3,
                "method": 2,
                "params": {
                    "channel": "prematch"
                }
            },
            {
                "id": 4,
                "method": 2,
                "params": {
                    "channel": "line:football"
                }
            }
        ]

        for msg in subscribe_messages:
            print(f"Subscribing to channel: {msg['params']['channel']}")
            ws.send(json.dumps(msg))
            time.sleep(0.5)

    try:
        ws = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )

        # Run for 15 seconds to capture messages
        print("\nListening for messages (15 seconds)...")
        ws.run_forever(ping_interval=10, ping_timeout=5)

    except KeyboardInterrupt:
        print("\n\nStopped by user")
    except Exception as e:
        print(f"\nException: {e}")

    print(f"\n\nTotal messages received: {len(messages_received)}")

    if messages_received:
        print("\nSample of received data:")
        print(json.dumps(messages_received[0], indent=2)[:1000])

    return len(messages_received) > 0

if __name__ == '__main__':
    success = test_websocket()

    print(f"\n{'='*60}")
    if success:
        print("[SUCCESS] WebSocket connection worked!")
        print("Check 22bet_ws_messages.json for full data")
    else:
        print("[FAILED] No messages received from WebSocket")
    print('='*60)
