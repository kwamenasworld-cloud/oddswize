import argparse
import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path
from urllib import request
from urllib.error import HTTPError, URLError

TEMPLATES_PATH = Path(__file__).with_name('voiceover_templates.json')


class SafeDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'


def load_templates():
    if not TEMPLATES_PATH.exists():
        return []
    return json.loads(TEMPLATES_PATH.read_text(encoding='utf-8'))


def get_script_text(args):
    if args.text:
        return args.text
    if args.text_file:
        return Path(args.text_file).read_text(encoding='utf-8').strip()
    if args.script_id:
        templates = load_templates()
        match = next((t for t in templates if t.get('id') == args.script_id), None)
        if not match:
            raise SystemExit(f'Unknown script id: {args.script_id}')
        return match.get('text', '')
    raise SystemExit('Provide --text, --text-file, or --script-id')


def fill_template(text, brand, cta_url, region):
    values = SafeDict({
        'brand': brand,
        'cta_url': cta_url,
        'region': region,
    })
    return text.format_map(values)


def ensure_ffmpeg():
    if not shutil.which('ffmpeg'):
        raise SystemExit('ffmpeg not found in PATH (required for mp3 output).')


def convert_wav_to_mp3(wav_path, out_path):
    ensure_ffmpeg()
    cmd = [
        'ffmpeg',
        '-y',
        '-i', str(wav_path),
        '-c:a', 'libmp3lame',
        '-b:a', '128k',
        str(out_path),
    ]
    subprocess.run(cmd, check=True)


def render_piper(text, out_path, model_path, speaker=None):
    if not shutil.which('piper'):
        raise SystemExit('Piper not found in PATH. Install Piper or use --provider espeak.')
    if not model_path:
        raise SystemExit('Missing --model for Piper.')

    out_path = Path(out_path)
    needs_convert = out_path.suffix.lower() != '.wav'
    wav_path = out_path if not needs_convert else out_path.with_suffix('.wav')

    cmd = ['piper', '--model', model_path, '--output_file', str(wav_path)]
    if speaker is not None:
        cmd += ['--speaker', str(speaker)]

    subprocess.run(cmd, input=text, text=True, check=True)

    if needs_convert:
        convert_wav_to_mp3(wav_path, out_path)
        wav_path.unlink(missing_ok=True)


def render_espeak(text, out_path, voice='en', rate=175):
    espeak_exe = resolve_espeak_exe()
    if not espeak_exe:
        raise SystemExit('eSpeak not found. Install eSpeak or set ESPEAK_PATH.')

    out_path = Path(out_path)
    needs_convert = out_path.suffix.lower() != '.wav'
    wav_path = out_path if not needs_convert else out_path.with_suffix('.wav')

    cmd = [espeak_exe, '-v', voice, '-s', str(rate), '-w', str(wav_path), text]
    subprocess.run(cmd, check=True)

    if needs_convert:
        convert_wav_to_mp3(wav_path, out_path)
        wav_path.unlink(missing_ok=True)


def resolve_espeak_exe():
    candidates = [
        os.getenv('ESPEAK_PATH'),
        shutil.which('espeak'),
        r'C:\Program Files (x86)\eSpeak\command_line\espeak.exe',
        r'C:\Program Files\eSpeak\command_line\espeak.exe',
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def render_elevenlabs(text, out_path, voice_id, model_id, api_key):
    if not api_key:
        raise SystemExit('Missing ElevenLabs API key. Set ELEVENLABS_API_KEY or use --api-key.')
    if not voice_id:
        raise SystemExit('Missing --voice-id for ElevenLabs')

    url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
    payload = {
        'text': text,
        'model_id': model_id,
        'voice_settings': {
            'stability': 0.45,
            'similarity_boost': 0.75,
            'style': 0.25,
            'use_speaker_boost': True,
        },
    }
    data = json.dumps(payload).encode('utf-8')
    headers = {
        'Accept': 'audio/mpeg',
        'Content-Type': 'application/json',
        'xi-api-key': api_key,
    }
    req = request.Request(url, data=data, headers=headers, method='POST')
    try:
        with request.urlopen(req, timeout=60) as resp:
            audio = resp.read()
    except HTTPError as exc:
        raise SystemExit(f'ElevenLabs error {exc.code}: {exc.read().decode("utf-8", "ignore")}')
    except URLError as exc:
        raise SystemExit(f'ElevenLabs request failed: {exc}')

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(audio)


def convert_mp3_to_wav(mp3_path, out_path):
    ensure_ffmpeg()
    cmd = [
        'ffmpeg',
        '-y',
        '-i', str(mp3_path),
        str(out_path),
    ]
    subprocess.run(cmd, check=True)


def render_edge_tts(text, out_path, voice='en-NG-AbeoNeural', rate='0%', pitch='0Hz'):
    try:
        import edge_tts
    except ImportError:
        raise SystemExit('edge-tts not installed. Run: python -m pip install edge-tts')

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    needs_wav = out_path.suffix.lower() == '.wav'
    mp3_path = out_path if not needs_wav else out_path.with_suffix('.mp3')

    async def _run():
        communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
        await communicate.save(str(mp3_path))

    asyncio.run(_run())

    if needs_wav:
        convert_mp3_to_wav(mp3_path, out_path)
        mp3_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description='Render AI voiceover for promo videos.')
    parser.add_argument('--provider', default='piper', choices=['piper', 'espeak', 'elevenlabs', 'edge'])
    parser.add_argument('--model', help='Piper model path (onnx)')
    parser.add_argument('--speaker', type=int, help='Piper speaker id (optional)')
    parser.add_argument('--espeak-voice', default='en', help='eSpeak voice (e.g., en, en-us)')
    parser.add_argument('--espeak-rate', type=int, default=175, help='eSpeak rate (words per minute)')
    parser.add_argument('--voice-id', help='ElevenLabs voice id')
    parser.add_argument('--model-id', default='eleven_multilingual_v2')
    parser.add_argument('--api-key', help='ElevenLabs API key')
    parser.add_argument('--edge-voice', default='en-NG-AbeoNeural', help='edge-tts voice (e.g., en-NG-AbeoNeural)')
    parser.add_argument('--edge-rate', default='+0%', help='edge-tts rate (e.g., -10%%, +0%%, +10%%)')
    parser.add_argument('--edge-pitch', default='+0Hz', help='edge-tts pitch (e.g., -2Hz, +0Hz, +2Hz)')
    parser.add_argument('--text', help='Voiceover text')
    parser.add_argument('--text-file', help='Path to text file')
    parser.add_argument('--script-id', help='Template id from voiceover_templates.json')
    parser.add_argument('--brand', default='OddsWize')
    parser.add_argument('--cta-url', default='https://oddswize.com')
    parser.add_argument('--region', default='Ghana and Nigeria')
    parser.add_argument('--out', required=True, help='Output audio file path (wav/mp3)')
    parser.add_argument('--list-templates', action='store_true')

    args = parser.parse_args()

    if args.list_templates:
        for template in load_templates():
            print(f"{template.get('id')}: {template.get('title')}")
        return

    script_text = get_script_text(args)
    script_text = fill_template(script_text, args.brand, args.cta_url, args.region)

    if args.provider == 'piper':
        render_piper(script_text, args.out, args.model, args.speaker)
    elif args.provider == 'espeak':
        render_espeak(script_text, args.out, args.espeak_voice, args.espeak_rate)
    elif args.provider == 'elevenlabs':
        api_key = args.api_key or os.getenv('ELEVENLABS_API_KEY') or os.getenv('PROMO_ELEVENLABS_API_KEY')
        render_elevenlabs(script_text, args.out, args.voice_id, args.model_id, api_key)
    elif args.provider == 'edge':
        render_edge_tts(script_text, args.out, args.edge_voice, args.edge_rate, args.edge_pitch)
    else:
        raise SystemExit(f'Unsupported provider: {args.provider}')

    print(f'Wrote voiceover to {args.out}')


if __name__ == '__main__':
    main()
