#!/usr/bin/env python3
"""
Decode 22Bet Protocol Buffer messages to understand the schema.
"""

import base64
import json
from google.protobuf import descriptor_pb2
from google.protobuf.json_format import MessageToDict

def decode_protobuf_unknown(data):
    """
    Try to decode protobuf without schema using wire format parsing.
    """
    result = {}
    i = 0

    while i < len(data):
        if i >= len(data):
            break

        # Read field tag
        tag_byte = data[i]
        i += 1

        field_number = tag_byte >> 3
        wire_type = tag_byte & 0x07

        # Wire types:
        # 0 = Varint
        # 1 = 64-bit
        # 2 = Length-delimited (string, bytes, embedded message)
        # 3 = Start group (deprecated)
        # 4 = End group (deprecated)
        # 5 = 32-bit

        if wire_type == 0:  # Varint
            value = 0
            shift = 0
            while i < len(data):
                byte = data[i]
                i += 1
                value |= (byte & 0x7F) << shift
                if not (byte & 0x80):
                    break
                shift += 7
            result[f"field_{field_number}_varint"] = value

        elif wire_type == 1:  # 64-bit
            if i + 8 <= len(data):
                value = int.from_bytes(data[i:i+8], 'little')
                result[f"field_{field_number}_64bit"] = value
                i += 8

        elif wire_type == 2:  # Length-delimited
            # Read length
            length = 0
            shift = 0
            while i < len(data):
                byte = data[i]
                i += 1
                length |= (byte & 0x7F) << shift
                if not (byte & 0x80):
                    break
                shift += 7

            if i + length <= len(data):
                value_bytes = data[i:i+length]
                i += length

                # Try to decode as UTF-8 string
                try:
                    value_str = value_bytes.decode('utf-8')
                    result[f"field_{field_number}_string"] = value_str
                except:
                    # Try to decode as nested message
                    try:
                        nested = decode_protobuf_unknown(value_bytes)
                        result[f"field_{field_number}_message"] = nested
                    except:
                        result[f"field_{field_number}_bytes"] = value_bytes.hex()[:100]

        elif wire_type == 5:  # 32-bit
            if i + 4 <= len(data):
                value = int.from_bytes(data[i:i+4], 'little')
                result[f"field_{field_number}_32bit"] = value
                i += 4

    return result

def analyze_messages():
    print("=" * 60)
    print("DECODING 22BET PROTOBUF MESSAGES")
    print("=" * 60)

    # Load intercepted messages
    try:
        with open('22bet_ws_messages_intercepted.json', 'r') as f:
            messages = json.load(f)
    except FileNotFoundError:
        print("Error: 22bet_ws_messages_intercepted.json not found")
        print("Run intercept_websocket_traffic.py first")
        return

    print(f"\nAnalyzing {len(messages)} messages...\n")

    decoded_messages = []

    for i, msg in enumerate(messages):
        direction = msg['direction']
        payload = msg['payload']

        print(f"{'='*60}")
        print(f"Message {i+1} [{direction}]")
        print(f"{'='*60}")

        try:
            # Decode from base64
            binary_data = base64.b64decode(payload)
            print(f"Binary length: {len(binary_data)} bytes")

            # Try to find readable strings
            strings = []
            current = []
            for byte in binary_data:
                if 32 <= byte <= 126:  # Printable ASCII
                    current.append(chr(byte))
                else:
                    if len(current) >= 4:  # Minimum string length
                        strings.append(''.join(current))
                    current = []
            if len(current) >= 4:
                strings.append(''.join(current))

            if strings:
                print(f"Readable strings found:")
                for s in strings[:10]:
                    print(f"  - {s}")

            # Try to decode structure
            decoded = decode_protobuf_unknown(binary_data)
            if decoded:
                print(f"\nDecoded fields:")
                print(json.dumps(decoded, indent=2)[:1000])

            decoded_messages.append({
                'direction': direction,
                'binary_length': len(binary_data),
                'strings': strings,
                'decoded': decoded
            })

            print()

        except Exception as e:
            print(f"Error decoding: {e}")
            print()

    # Save decoded messages
    with open('22bet_decoded_messages.json', 'w') as f:
        json.dump(decoded_messages, f, indent=2)

    print(f"\nSaved decoded messages to 22bet_decoded_messages.json")

    # Analyze patterns
    print("\n" + "="*60)
    print("ANALYSIS")
    print("="*60)

    received = [m for m in decoded_messages if m['direction'] == 'RECEIVED']
    sent = [m for m in decoded_messages if m['direction'] == 'SENT']

    print(f"\nMessages sent: {len(sent)}")
    print(f"Messages received: {len(received)}")

    # Find channel subscriptions from sent message
    if sent:
        all_strings = []
        for m in sent:
            all_strings.extend(m['strings'])

        channels = [s for s in all_strings if ':' in s and ('proto' in s or 'public' in s)]
        if channels:
            print(f"\nChannels subscribed to:")
            for ch in set(channels):
                print(f"  - {ch}")

    # Find message types from received
    if received:
        all_strings = []
        for m in received:
            all_strings.extend(m['strings'])

        message_types = [s for s in all_strings if 'Message' in s or 'State' in s or 'type.googleapis.com' in s]
        if message_types:
            print(f"\nMessage types received:")
            for mt in set(message_types):
                print(f"  - {mt}")

if __name__ == '__main__':
    analyze_messages()
