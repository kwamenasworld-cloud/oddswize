import argparse
import json
import os
import secrets
import sys
from pathlib import Path
from urllib import request
from urllib.error import HTTPError, URLError


def load_message(args):
    if args.message:
        return args.message
    if args.file:
        return Path(args.file).read_text(encoding='utf-8').strip()
    data = sys.stdin.read().strip()
    if data:
        return data
    return ''


def post_to_telegram(token, chat_id, text, parse_mode=None, disable_preview=False):
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': text,
        'disable_web_page_preview': disable_preview,
    }
    if parse_mode:
        payload['parse_mode'] = parse_mode

    data = json.dumps(payload).encode('utf-8')
    headers = {
        'Content-Type': 'application/json',
    }
    req = request.Request(url, data=data, headers=headers, method='POST')
    try:
        with request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode('utf-8', 'ignore')
    except HTTPError as exc:
        raise SystemExit(f'Telegram error {exc.code}: {exc.read().decode("utf-8", "ignore")}')
    except URLError as exc:
        raise SystemExit(f'Telegram request failed: {exc}')

    return body


def build_multipart(fields, files):
    boundary = f'----oddswize{secrets.token_hex(12)}'
    body = bytearray()

    for name, value in fields.items():
        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        body.extend(f'Content-Disposition: form-data; name=\"{name}\"\r\n\r\n'.encode('utf-8'))
        body.extend(str(value).encode('utf-8'))
        body.extend(b'\r\n')

    for name, file_path, content_type in files:
        file_path = Path(file_path)
        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        body.extend(
            f'Content-Disposition: form-data; name=\"{name}\"; filename=\"{file_path.name}\"\r\n'.encode('utf-8')
        )
        body.extend(f'Content-Type: {content_type}\r\n\r\n'.encode('utf-8'))
        body.extend(file_path.read_bytes())
        body.extend(b'\r\n')

    body.extend(f'--{boundary}--\r\n'.encode('utf-8'))
    return body, f'multipart/form-data; boundary={boundary}'


def post_video_to_telegram(token, chat_id, video_path, caption=None, parse_mode=None):
    url = f'https://api.telegram.org/bot{token}/sendVideo'
    fields = {'chat_id': chat_id}
    if caption:
        caption = caption.strip()
        if len(caption) > 900:
            caption = caption[:897] + '...'
        fields['caption'] = caption
    if parse_mode:
        fields['parse_mode'] = parse_mode

    data, content_type = build_multipart(fields, [('video', video_path, 'video/mp4')])
    headers = {'Content-Type': content_type}
    req = request.Request(url, data=data, headers=headers, method='POST')
    try:
        with request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode('utf-8', 'ignore')
    except HTTPError as exc:
        raise SystemExit(f'Telegram error {exc.code}: {exc.read().decode(\"utf-8\", \"ignore\")}')
    except URLError as exc:
        raise SystemExit(f'Telegram request failed: {exc}')

    return body


def main():
    parser = argparse.ArgumentParser(description='Post a message to a Telegram channel or group.')
    parser.add_argument('--token', help='Telegram bot token (or TELEGRAM_BOT_TOKEN)')
    parser.add_argument('--chat-id', help='Telegram chat id or @channel (or TELEGRAM_CHAT_ID)')
    parser.add_argument('--message', help='Message text')
    parser.add_argument('--file', help='Path to message file')
    parser.add_argument('--video', help='Path to mp4 video to upload')
    parser.add_argument('--caption', help='Video caption (optional)')
    parser.add_argument('--parse-mode', choices=['Markdown', 'MarkdownV2', 'HTML'])
    parser.add_argument('--no-preview', action='store_true', help='Disable link preview')

    args = parser.parse_args()

    token = args.token or os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = args.chat_id or os.getenv('TELEGRAM_CHAT_ID')

    if not token:
        raise SystemExit('Missing Telegram bot token (set TELEGRAM_BOT_TOKEN or --token).')
    if not chat_id:
        raise SystemExit('Missing Telegram chat id (set TELEGRAM_CHAT_ID or --chat-id).')

    if args.video:
        caption = args.caption or load_message(args)
        body = post_video_to_telegram(token, chat_id, args.video, caption, args.parse_mode)
        print(body)
        return

    text = load_message(args)
    if not text:
        raise SystemExit('Provide --message, --file, or pipe content via stdin')
    body = post_to_telegram(token, chat_id, text, args.parse_mode, args.no_preview)
    print(body)


if __name__ == '__main__':
    main()
