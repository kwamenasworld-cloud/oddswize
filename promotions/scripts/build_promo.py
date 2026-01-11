import argparse
import os
import re
import subprocess
from pathlib import Path

from render_voiceover import (
    load_templates,
    fill_template,
    render_elevenlabs,
    render_espeak,
    render_piper,
)


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
    return ''


def ffprobe_duration(path):
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def format_timestamp(seconds):
    millis = int(round(seconds * 1000))
    hours = millis // 3600000
    millis -= hours * 3600000
    minutes = millis // 60000
    millis -= minutes * 60000
    secs = millis // 1000
    millis -= secs * 1000
    return f'{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}'


def split_sentences(text, max_words=12):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks = []
    for sentence in sentences:
        words = sentence.split()
        while len(words) > max_words:
            chunks.append(' '.join(words[:max_words]))
            words = words[max_words:]
        if words:
            chunks.append(' '.join(words))
    return [chunk for chunk in chunks if chunk]


def write_srt(text, duration, out_path):
    chunks = split_sentences(text)
    if not chunks:
        return
    total_words = sum(len(chunk.split()) for chunk in chunks)
    if total_words == 0:
        return
    start = 0.0
    lines = []
    for idx, chunk in enumerate(chunks, 1):
        word_count = len(chunk.split())
        share = word_count / total_words
        seg_duration = max(1.2, duration * share)
        end = min(duration, start + seg_duration)
        lines.append(str(idx))
        lines.append(f'{format_timestamp(start)} --> {format_timestamp(end)}')
        lines.append(chunk)
        lines.append('')
        start = end
    Path(out_path).write_text('\n'.join(lines), encoding='utf-8')


def escape_drawtext(text):
    return (text.replace('\\', '\\\\')
                .replace(':', '\\:')
                .replace("'", "\\'")
                .replace('%', '\\%'))


def build_video_filter(args, captions_path=None):
    width, height = args.size.split('x')
    filters = [
        f'scale={width}:{height}:force_original_aspect_ratio=increase',
        f'crop={width}:{height}',
    ]
    if captions_path and args.burn_captions:
        subtitle_path = str(Path(captions_path).resolve()).replace('\\', '/')
        filters.append(
            f"subtitles='{subtitle_path}':force_style='FontSize=36,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,Outline=2'"
        )
    if args.title:
        title_text = escape_drawtext(args.title)
        font = f":fontfile='{args.font_file}'" if args.font_file else ''
        filters.append(
            f"drawtext=text='{title_text}'{font}:fontcolor=white:fontsize=64:box=1:boxcolor=black@0.35:boxborderw=18:x=(w-text_w)/2:y=80"
        )
    if args.cta:
        cta_text = escape_drawtext(args.cta)
        font = f":fontfile='{args.font_file}'" if args.font_file else ''
        filters.append(
            f"drawtext=text='{cta_text}'{font}:fontcolor=white:fontsize=54:box=1:boxcolor=black@0.45:boxborderw=18:x=(w-text_w)/2:y=h-160"
        )
    return ','.join(filters)


def main():
    parser = argparse.ArgumentParser(description='Build a promo video with football clips and voiceover.')
    parser.add_argument('--clip', required=True, help='Path to background clip (mp4)')
    parser.add_argument('--audio', help='Path to voiceover audio (mp3/wav). If omitted, TTS will be used.')
    parser.add_argument('--tts-provider', default='none', choices=['none', 'piper', 'espeak', 'elevenlabs'])
    parser.add_argument('--model', help='Piper model path (onnx)')
    parser.add_argument('--speaker', type=int, help='Piper speaker id (optional)')
    parser.add_argument('--espeak-voice', default='en', help='eSpeak voice (e.g., en, en-us)')
    parser.add_argument('--espeak-rate', type=int, default=175, help='eSpeak rate (words per minute)')
    parser.add_argument('--voice-id', help='ElevenLabs voice id')
    parser.add_argument('--model-id', default='eleven_multilingual_v2')
    parser.add_argument('--api-key', help='ElevenLabs API key')
    parser.add_argument('--text', help='Voiceover text')
    parser.add_argument('--text-file', help='Text file with voiceover')
    parser.add_argument('--script-id', help='Template id from voiceover_templates.json')
    parser.add_argument('--brand', default='OddsWize')
    parser.add_argument('--cta-url', default='https://oddswize.com')
    parser.add_argument('--region', default='Ghana and Nigeria')
    parser.add_argument('--out', default='promotions/output/promo.mp4')
    parser.add_argument('--size', default='1080x1920')
    parser.add_argument('--fps', type=int, default=30)
    parser.add_argument('--music', help='Optional background music path')
    parser.add_argument('--music-volume', type=float, default=0.15)
    parser.add_argument('--captions', action='store_true', help='Generate an SRT captions file')
    parser.add_argument('--burn-captions', action='store_true', help='Burn captions into video (requires libass)')
    parser.add_argument('--title', help='Overlay title text')
    parser.add_argument('--cta', help='Overlay CTA text')
    parser.add_argument('--font-file', help='Optional font file path for drawtext')
    parser.add_argument('--no-loop', action='store_true', help='Do not loop the clip to match audio length')

    args = parser.parse_args()

    clip_path = Path(args.clip)
    if not clip_path.exists():
        raise SystemExit(f'Clip not found: {clip_path}')

    script_text = get_script_text(args)
    if script_text:
        script_text = fill_template(script_text, args.brand, args.cta_url, args.region)

    audio_path = Path(args.audio) if args.audio else None
    temp_audio = None
    if audio_path is None:
        if args.tts_provider == 'none':
            raise SystemExit('Provide --audio or select a TTS provider')
        if not script_text:
            raise SystemExit('Provide voiceover text or a template when using TTS')
        temp_audio = Path(args.out).with_suffix('.voiceover.mp3')
        if args.tts_provider == 'piper':
            render_piper(script_text, temp_audio, args.model, args.speaker)
        elif args.tts_provider == 'espeak':
            render_espeak(script_text, temp_audio, args.espeak_voice, args.espeak_rate)
        elif args.tts_provider == 'elevenlabs':
            api_key = args.api_key or os.getenv('ELEVENLABS_API_KEY')
            render_elevenlabs(script_text, temp_audio, args.voice_id, args.model_id, api_key)
        else:
            raise SystemExit(f'Unsupported TTS provider: {args.tts_provider}')
        audio_path = temp_audio

    if not audio_path.exists():
        raise SystemExit(f'Audio not found: {audio_path}')

    duration = ffprobe_duration(audio_path)

    captions_path = None
    if args.captions or args.burn_captions:
        if not script_text:
            raise SystemExit('Captions need --text, --text-file, or --script-id')
        captions_path = Path(args.out).with_suffix('.srt')
        write_srt(script_text, duration, captions_path)

    video_filter = build_video_filter(args, captions_path)

    cmd = ['ffmpeg', '-y']
    if not args.no_loop:
        cmd += ['-stream_loop', '-1']
    cmd += ['-i', str(clip_path), '-i', str(audio_path)]

    if args.music:
        cmd += ['-i', str(args.music)]
        filter_complex = (
            f"[0:v]{video_filter}[v];"
            f"[2:a]volume={args.music_volume}[bg];"
            "[1:a][bg]sidechaincompress=threshold=0.02:ratio=5:attack=20:release=250[duck];"
            "[1:a][duck]amix=inputs=2:duration=first:dropout_transition=3[a]"
        )
        cmd += ['-filter_complex', filter_complex, '-map', '[v]', '-map', '[a]']
    else:
        cmd += ['-vf', video_filter, '-map', '0:v', '-map', '1:a']

    cmd += [
        '-r', str(args.fps),
        '-c:v', 'libx264',
        '-preset', 'veryfast',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        '-shortest',
        str(args.out),
    ]

    subprocess.run(cmd, check=True)

    if temp_audio and temp_audio.exists():
        print(f'Voiceover written to {temp_audio}')

    if captions_path:
        print(f'Captions written to {captions_path}')

    print(f'Promo video written to {args.out}')


if __name__ == '__main__':
    main()
