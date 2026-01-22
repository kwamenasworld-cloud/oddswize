import argparse
import math
import os
import random
import re
import shutil
import subprocess
from pathlib import Path

from render_voiceover import (
    load_templates,
    fill_template,
    render_edge_tts,
    render_elevenlabs,
    render_espeak,
    render_piper,
)


CAPTION_LINE_CHARS = 42
CAPTION_CHUNK_CHARS = CAPTION_LINE_CHARS * 2 + 4
LABEL_PATTERN = re.compile(r'^(Safe play|Bold pick|Value watch)\s*[:-]\s+', re.IGNORECASE)
LABEL_SHORT_FOR_CAPTIONS = {
    'SAFE PLAY': 'SAFE',
    'BOLD PICK': 'BOLD',
    'VALUE WATCH': 'VALUE',
}
CAPTION_ABBREVIATIONS = [
    (re.compile(r'\bManchester\b', re.IGNORECASE), 'Man'),
    (re.compile(r'\bUnited\b', re.IGNORECASE), 'Utd'),
    (re.compile(r'\bSaint\b', re.IGNORECASE), 'St'),
    (re.compile(r'\bAtletico\b', re.IGNORECASE), 'Atleti'),
]
CTA_CHUNK_PREFIXES = ('visit ',)
CTA_CHUNK_KEYWORDS = ('oddswize.com', 'http', 'www.')


def is_cta_chunk(chunk):
    if not chunk:
        return False
    lower = chunk.strip().lower()
    if lower.startswith(CTA_CHUNK_PREFIXES):
        return True
    return any(keyword in lower for keyword in CTA_CHUNK_KEYWORDS)


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


def build_clip_montage(clip_path, out_path, total_duration, segment_length, seed=None):
    if total_duration <= 0:
        return None
    clip_duration = ffprobe_duration(clip_path)
    if clip_duration <= 0:
        return None
    segment_length = max(1.0, segment_length)
    if clip_duration <= segment_length:
        return None

    rng = random.Random(seed)
    segments = []
    remaining = total_duration
    while remaining > 0:
        duration = min(segment_length, remaining)
        remaining -= duration
        segments.append(duration)
    if segments and segments[-1] < 0.5:
        if len(segments) == 1:
            segments[-1] = max(1.0, segments[-1])
        else:
            segments[-2] += segments[-1]
            segments.pop()

    cmd = [
        'ffmpeg', '-y',
        '-fflags', '+genpts+discardcorrupt',
        '-err_detect', 'ignore_err',
        '-i', str(clip_path),
    ]
    filter_parts = []
    for idx, duration in enumerate(segments):
        max_start = max(0.0, clip_duration - duration)
        start = 0.0 if max_start == 0 else rng.uniform(0, max_start)
        filter_parts.append(
            f"[0:v]trim=start={start:.2f}:duration={duration:.2f},setpts=PTS-STARTPTS[v{idx}]"
        )
    concat_inputs = ''.join([f'[v{idx}]' for idx in range(len(segments))])
    filter_parts.append(f'{concat_inputs}concat=n={len(segments)}:v=1:a=0[v]')
    cmd += [
        '-filter_complex', ';'.join(filter_parts),
        '-map', '[v]',
        '-an',
        '-c:v', 'libx264',
        '-preset', 'veryfast',
        '-crf', '23',
        str(out_path),
    ]
    subprocess.run(cmd, check=True)
    return out_path


def format_timestamp(seconds):
    millis = int(round(seconds * 1000))
    hours = millis // 3600000
    millis -= hours * 3600000
    minutes = millis // 60000
    millis -= minutes * 60000
    secs = millis // 1000
    millis -= secs * 1000
    return f'{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}'


def format_spoken_url(url):
    if not url:
        return ''
    spoken = url.replace('https://', '').replace('http://', '')
    spoken = spoken.split('?', 1)[0]
    return spoken.rstrip('/')


def find_webshot_timing(chunks, durations, gap, cta_url, brand):
    if not chunks or not durations:
        return None, None
    keywords = []
    spoken = format_spoken_url(cta_url)
    if spoken:
        keywords.append(spoken.lower())
    if cta_url:
        keywords.append(cta_url.lower())
    if brand:
        keywords.append(brand.lower())

    start = 0.0
    for chunk, duration in zip(chunks, durations):
        lower = chunk.lower()
        if any(keyword in lower for keyword in keywords):
            return start, duration
        start += duration + max(0.0, gap)
    return None, None


def merge_short_chunks(chunks, max_words, max_chars, min_words):
    if not chunks:
        return []
    merged = []
    idx = 0
    while idx < len(chunks):
        chunk = chunks[idx]
        idx += 1
        while idx < len(chunks):
            next_chunk = chunks[idx]
            if is_cta_chunk(next_chunk):
                break
            if LABEL_PATTERN.match(chunk) and next_chunk.lower().startswith('because '):
                break
            words = chunk.split()
            needs_merge = (
                len(words) < min_words
                or chunk.endswith((':', ';', ','))
                or next_chunk.lower().startswith('because ')
            )
            if not needs_merge:
                break
            candidate = f'{chunk} {next_chunk}'.strip()
            if len(candidate.split()) <= max_words and len(candidate) <= max_chars:
                chunk = candidate
                idx += 1
                continue
            break
        merged.append(chunk)
    if len(merged) >= 2:
        last = merged[-1]
        last_words = last.split()
        if len(last_words) < min_words and not is_cta_chunk(last):
            candidate = f'{merged[-2]} {last}'.strip()
            if len(candidate.split()) <= max_words and len(candidate) <= max_chars:
                merged = merged[:-2] + [candidate]
    return merged


def abbreviate_caption_text(text):
    if not text:
        return text
    if ' vs ' not in text.lower():
        return text
    for pattern, replacement in CAPTION_ABBREVIATIONS:
        text = pattern.sub(replacement, text)
    return text


def split_sentences(text, max_words=12, max_chars=68, min_words=3):
    text = ' '.join(text.strip().split())
    if not text:
        return []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        clauses = re.split(r'(?<=[,;:])\s+', sentence)
        for clause in clauses:
            words = clause.split()
            if not words:
                continue
            current = []
            for word in words:
                candidate = ' '.join(current + [word]).strip()
                if current and (len(current) + 1 > max_words or len(candidate) > max_chars):
                    chunks.append(' '.join(current))
                    current = [word]
                else:
                    current.append(word)
            if current:
                chunks.append(' '.join(current))
    return merge_short_chunks(chunks, max_words, max_chars, min_words)


def wrap_caption(chunk, max_chars_per_line=CAPTION_LINE_CHARS, verbatim=False):
    chunk = ' '.join(chunk.strip().split())
    if not chunk:
        return chunk
    if not verbatim:
        if chunk.lower().startswith('because '):
            chunk = f"Reason: {chunk[8:].strip()}"
        label_match = LABEL_PATTERN.match(chunk)
        if label_match:
            label = label_match.group(1).upper()
            label = LABEL_SHORT_FOR_CAPTIONS.get(label, label)
            rest = chunk[label_match.end():].strip()
            chunk = f'{label}: {rest}'
        chunk = chunk.rstrip(',')
        if ' because ' in chunk:
            left, right = chunk.split(' because ', 1)
            left = left.strip().rstrip(',')
            right = f'Reason: {right.strip()}'
            if len(left) <= max_chars_per_line and len(right) <= max_chars_per_line:
                return f'{left}\n{right}'

    words = chunk.split()
    if not words:
        return chunk
    if len(chunk) <= max_chars_per_line or len(words) == 1:
        return chunk
    if any(len(word) > max_chars_per_line for word in words):
        return chunk

    best_idx = None
    best_score = None
    for idx in range(1, len(words)):
        left = ' '.join(words[:idx])
        right = ' '.join(words[idx:])
        if len(left) <= max_chars_per_line and len(right) <= max_chars_per_line:
            score = abs(len(left) - len(right))
            if best_score is None or score < best_score:
                best_score = score
                best_idx = idx

    if best_idx is not None:
        left = ' '.join(words[:best_idx])
        right = ' '.join(words[best_idx:])
        return f'{left}\n{right}'

    lines = []
    current = []
    for word in words:
        candidate = ' '.join(current + [word]).strip()
        if len(candidate) <= max_chars_per_line or not current:
            current.append(word)
        else:
            lines.append(' '.join(current))
            current = [word]
    if current:
        lines.append(' '.join(current))
    if len(lines) <= 1:
        return chunk
    if len(lines) > 2:
        lines = [lines[0], ' '.join(lines[1:])]
    return '\n'.join(lines)


def write_srt(text, duration, out_path, verbatim=False):
    max_chunk_chars = CAPTION_CHUNK_CHARS
    if not verbatim:
        text = abbreviate_caption_text(text)
    chunks = split_sentences(text, max_words=12, max_chars=max_chunk_chars, min_words=3)
    if not chunks:
        return
    total_words = sum(len(chunk.split()) for chunk in chunks)
    if total_words == 0:
        return

    words_per_second = 2.7
    min_duration = 1.2
    max_duration = 4.5

    raw_durations = []
    for chunk in chunks:
        word_count = len(chunk.split())
        raw_durations.append(word_count / words_per_second)

    total_raw = sum(raw_durations)
    if total_raw <= 0:
        return
    scale = duration / total_raw if duration > 0 else 1.0

    start = 0.0
    lines = []
    for idx, (chunk, raw) in enumerate(zip(chunks, raw_durations), 1):
        seg_duration = raw * scale
        seg_duration = max(min_duration, min(max_duration, seg_duration))
        end = start + seg_duration
        if idx == len(chunks) or end > duration:
            end = duration
        lines.append(str(idx))
        lines.append(f'{format_timestamp(start)} --> {format_timestamp(end)}')
        caption = wrap_caption(
            chunk,
            max_chars_per_line=CAPTION_LINE_CHARS,
            verbatim=verbatim,
        )
        lines.extend(caption.splitlines())
        lines.append('')
        start = end
    Path(out_path).write_text('\n'.join(lines), encoding='utf-8')


def write_srt_with_segments(chunks, durations, out_path, gap=0.0, verbatim=False):
    if not chunks or not durations:
        return
    if len(chunks) != len(durations):
        raise SystemExit('Caption chunks and durations do not match.')

    start = 0.0
    lines = []
    for idx, (chunk, duration) in enumerate(zip(chunks, durations), 1):
        end = start + max(0.2, duration)
        lines.append(str(idx))
        lines.append(f'{format_timestamp(start)} --> {format_timestamp(end)}')
        if not verbatim:
            chunk = abbreviate_caption_text(chunk)
        caption = wrap_caption(
            chunk,
            max_chars_per_line=CAPTION_LINE_CHARS,
            verbatim=verbatim,
        )
        lines.extend(caption.splitlines())
        lines.append('')
        start = end + max(0.0, gap)
    Path(out_path).write_text('\n'.join(lines), encoding='utf-8')


def make_silence_audio(out_path, duration, sample_rate=44100):
    cmd = [
        'ffmpeg',
        '-y',
        '-f', 'lavfi',
        '-i', f'anullsrc=channel_layout=mono:sample_rate={sample_rate}',
        '-t', f'{duration:.2f}',
        '-c:a', 'libmp3lame',
        '-b:a', '128k',
        str(out_path),
    ]
    subprocess.run(cmd, check=True)


def render_tts_segments(chunks, args, out_path, gap=0.0):
    out_path = Path(out_path)
    temp_dir = out_path.with_suffix('.segments')
    temp_dir.mkdir(parents=True, exist_ok=True)

    segment_paths = []
    durations = []
    for idx, chunk in enumerate(chunks, 1):
        segment_path = temp_dir / f'segment_{idx:02d}.mp3'
        if args.tts_provider == 'piper':
            render_piper(chunk, segment_path, args.model, args.speaker)
        elif args.tts_provider == 'espeak':
            render_espeak(chunk, segment_path, args.espeak_voice, args.espeak_rate)
        elif args.tts_provider == 'elevenlabs':
            api_key = args.api_key or os.getenv('ELEVENLABS_API_KEY') or os.getenv('PROMO_ELEVENLABS_API_KEY')
            render_elevenlabs(chunk, segment_path, args.voice_id, args.model_id, api_key)
        elif args.tts_provider == 'edge':
            render_edge_tts(chunk, segment_path, args.edge_voice, args.edge_rate, args.edge_pitch)
        else:
            raise SystemExit(f'Unsupported provider: {args.tts_provider}')

        duration = ffprobe_duration(segment_path)
        segment_paths.append(segment_path)
        durations.append(duration)

    silence_path = None
    if gap > 0:
        silence_path = temp_dir / 'silence.mp3'
        make_silence_audio(silence_path, gap)

    concat_list = temp_dir / 'concat_list.txt'
    with concat_list.open('w', encoding='utf-8') as handle:
        for idx, segment_path in enumerate(segment_paths):
            handle.write(f"file '{segment_path.resolve().as_posix()}'\n")
            if silence_path and idx < len(segment_paths) - 1:
                handle.write(f"file '{silence_path.resolve().as_posix()}'\n")

    cmd = [
        'ffmpeg',
        '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_list),
        '-c:a', 'libmp3lame',
        '-b:a', '128k',
        str(out_path),
    ]
    subprocess.run(cmd, check=True)

    for segment_path in segment_paths:
        segment_path.unlink(missing_ok=True)
    if silence_path:
        silence_path.unlink(missing_ok=True)
    concat_list.unlink(missing_ok=True)
    shutil.rmtree(temp_dir, ignore_errors=True)

    return durations


def escape_drawtext(text):
    return (text.replace('\\', '\\\\')
                .replace(':', '\\:')
                .replace("'", "\\'")
                .replace('%', '\\%'))


def build_caption_filter(args, captions_path):
    if not (captions_path and args.burn_captions):
        return None
    subtitle_path = str(Path(captions_path).resolve()).replace('\\', '/')
    subtitle_path = subtitle_path.replace(':', '\\:')
    caption_style = (
        'FontName=Arial Black,'
        'FontSize=24,'
        'PrimaryColour=&HFFFFFF&,'
        'OutlineColour=&H000000&,'
        'Bold=1,'
        'BorderStyle=1,'
        'Outline=2,'
        'Shadow=0,'
        'Spacing=0,'
        'Alignment=2,'
        'MarginL=40,'
        'MarginR=40,'
        'MarginV=16,'
        'WrapStyle=1'
    )
    return f"subtitles='{subtitle_path}':force_style='{caption_style}'"


def build_video_filter(args, duration=None):
    width, height = parse_size(args.size)
    if args.fit_mode == 'blur':
        blur_sigma = max(1.0, args.blur_sigma)
        filters = [
            (
                f"split=2[bg][fg];"
                f"[bg]scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},gblur=sigma={blur_sigma:.1f}[bg];"
                f"[fg]scale={width}:{height}:force_original_aspect_ratio=decrease[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
            )
        ]
    elif args.fit_mode == 'pad':
        filters = [
            f'scale={width}:{height}:force_original_aspect_ratio=decrease',
            f'pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color={args.pad_color}',
        ]
    else:
        filters = [
            f'scale={width}:{height}:force_original_aspect_ratio=increase',
            f'crop={width}:{height}',
        ]
    if args.pulse_zoom:
        zoom_expr = (
            f"if(lt(mod(t\\,{args.pulse_zoom_period})\\,{args.pulse_zoom_on})"
            f"\\,1\\,{args.pulse_zoom_factor})"
        )
        filters.append(f'scale=iw*{zoom_expr}:ih*{zoom_expr}:eval=frame')
        filters.append(f'crop={width}:{height}')
    if args.hook_text:
        hook_text = escape_drawtext(args.hook_text)
        font = f":fontfile='{args.font_file}'" if args.font_file else ''
        filters.append(
            f"drawtext=text='{hook_text}'{font}:fontcolor=white:fontsize=56:box=1:boxcolor=black@0.45:boxborderw=16:x=(w-text_w)/2:y=120"
            f":enable='lt(t,{args.hook_duration})'"
        )
    if args.title:
        title_text = escape_drawtext(args.title)
        font = f":fontfile='{args.font_file}'" if args.font_file else ''
        title_enable = ''
        if args.title_duration is not None:
            title_enable = f":enable='lt(t,{args.title_duration})'"
        filters.append(
            f"drawtext=text='{title_text}'{font}:fontcolor=white:fontsize=48:box=1:boxcolor=black@0.35:boxborderw=14:x=(w-text_w)/2:y=70"
            f"{title_enable}"
        )
    if args.cta:
        cta_text = escape_drawtext(args.cta)
        font = f":fontfile='{args.font_file}'" if args.font_file else ''
        cta_enable = ''
        if duration and args.cta_delay is not None:
            start_time = max(0.0, duration - args.cta_delay)
            cta_enable = f":enable='gte(t,{start_time})'"
        filters.append(
            f"drawtext=text='{cta_text}'{font}:fontcolor=white:fontsize=42"
            f":box=1:boxcolor=black@0.6:boxborderw=18"
            f":borderw=2:bordercolor=black@0.9"
            f":shadowcolor=black@0.6:shadowx=2:shadowy=2"
            f":x=w-text_w-48:y=h-text_h-120"
            f"{cta_enable}"
        )
    if args.progress_bar and duration and duration > 0:
        bar_height = max(2, args.progress_bar_height)
        bar_padding = max(0, args.progress_bar_padding)
        bar_width = f"(iw*t/{duration})"
        filters.append(
            f"drawbox=x=0:y=h-{bar_padding + bar_height}:w={bar_width}:h={bar_height}:color={args.progress_bar_color}:t=fill"
        )
    if args.brand_mark:
        brand_text = args.brand_mark_text or args.brand
        highlight = args.brand_mark_highlight
        if highlight is None and brand_text.lower().startswith('odds'):
            highlight = brand_text[:4]
        if highlight is None:
            highlight = ''
        font = f":fontfile='{args.font_file}'" if args.font_file else ''
        padding = max(0, args.brand_mark_padding)
        base_filter = (
            f"drawtext=text='{escape_drawtext(brand_text)}'{font}"
            f":fontcolor={args.brand_mark_text_color}"
            f":fontsize={args.brand_mark_font_size}"
            f":shadowcolor=black@0.6:shadowx=2:shadowy=2"
            f":x={padding}:y=h-text_h-{padding}"
        )
        filters.append(base_filter)
        if highlight:
            highlight_filter = (
                f"drawtext=text='{escape_drawtext(highlight)}'{font}"
                f":fontcolor={args.brand_mark_accent_color}"
                f":fontsize={args.brand_mark_font_size}"
                f":shadowcolor=black@0.6:shadowx=2:shadowy=2"
                f":x={padding}:y=h-text_h-{padding}"
            )
            filters.append(highlight_filter)
    return ','.join(filters)


def parse_size(size):
    try:
        width, height = size.lower().split('x', 1)
        return int(width), int(height)
    except ValueError:
        raise SystemExit(f'Invalid size format: {size} (expected WIDTHxHEIGHT)')


def logo_overlay_expr(position, padding):
    if position == 'bottom-left':
        return str(padding), f'H-h-{padding}'
    if position == 'bottom-right':
        return f'W-w-{padding}', f'H-h-{padding}'
    if position == 'top-left':
        return str(padding), str(padding)
    if position == 'top-right':
        return f'W-w-{padding}', str(padding)
    raise SystemExit(f'Unsupported logo position: {position}')


def webshot_overlay_expr(position, padding):
    if position == 'center':
        return '(W-w)/2', '(H-h)/2'
    if position == 'top':
        return '(W-w)/2', str(padding)
    if position == 'bottom':
        return '(W-w)/2', f'H-h-{padding}'
    if position == 'top-left':
        return str(padding), str(padding)
    if position == 'top-right':
        return f'W-w-{padding}', str(padding)
    if position == 'bottom-left':
        return str(padding), f'H-h-{padding}'
    if position == 'bottom-right':
        return f'W-w-{padding}', f'H-h-{padding}'
    raise SystemExit(f'Unsupported webshot position: {position}')


def main():
    parser = argparse.ArgumentParser(description='Build a promo video with football clips and voiceover.')
    parser.add_argument('--clip', required=True, help='Path to background clip (mp4)')
    parser.add_argument('--audio', help='Path to voiceover audio (mp3/wav). If omitted, TTS will be used.')
    parser.add_argument('--tts-provider', default='none', choices=['none', 'piper', 'espeak', 'elevenlabs', 'edge'])
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
    parser.add_argument('--text-file', help='Text file with voiceover')
    parser.add_argument('--script-id', help='Template id from voiceover_templates.json')
    parser.add_argument('--brand', default='OddsWize')
    parser.add_argument('--cta-url', default='https://oddswize.com')
    parser.add_argument('--region', default='Ghana and Nigeria')
    parser.add_argument('--out', default='promotions/output/promo.mp4')
    parser.add_argument('--size', default='1080x1920')
    parser.add_argument('--fit-mode', default='crop', choices=['crop', 'blur', 'pad'])
    parser.add_argument('--blur-sigma', type=float, default=24.0)
    parser.add_argument('--pad-color', default='black')
    parser.add_argument('--fps', type=int, default=30)
    parser.add_argument('--music', help='Optional background music path')
    parser.add_argument('--music-volume', type=float, default=0.15)
    parser.add_argument('--captions', action='store_true', help='Generate an SRT captions file')
    parser.add_argument('--burn-captions', action='store_true', help='Burn captions into video (requires libass)')
    parser.add_argument('--caption-sync', dest='caption_sync', action='store_true',
                        help='Sync captions by generating TTS per segment')
    parser.add_argument('--no-caption-sync', dest='caption_sync', action='store_false',
                        help='Disable segment-based caption sync')
    parser.set_defaults(caption_sync=True)
    parser.add_argument('--caption-verbatim', dest='caption_verbatim', action='store_true',
                        help='Keep captions verbatim (no rewrites or abbreviations)')
    parser.add_argument('--no-caption-verbatim', dest='caption_verbatim', action='store_false',
                        help='Allow caption rewrites for readability')
    parser.set_defaults(caption_verbatim=True)
    parser.add_argument('--caption-gap', type=float, default=0.08,
                        help='Silence gap (seconds) between caption segments')
    parser.add_argument('--title', help='Overlay title text')
    parser.add_argument('--cta', help='Overlay CTA text')
    parser.add_argument('--font-file', help='Optional font file path for drawtext')
    parser.add_argument('--hook-text', help='Optional hook text overlay')
    parser.add_argument('--hook-duration', type=float, default=2.4)
    parser.add_argument('--title-duration', type=float, default=None)
    parser.add_argument('--cta-delay', type=float, default=None)
    parser.add_argument('--progress-bar', action='store_true', help='Draw a progress bar at the bottom')
    parser.add_argument('--progress-bar-height', type=int, default=6)
    parser.add_argument('--progress-bar-padding', type=int, default=10)
    parser.add_argument('--progress-bar-color', default='white@0.75')
    parser.add_argument('--pulse-zoom', action='store_true', help='Add a subtle zoom pulse to keep motion')
    parser.add_argument('--pulse-zoom-factor', type=float, default=1.06)
    parser.add_argument('--pulse-zoom-period', type=float, default=3.0)
    parser.add_argument('--pulse-zoom-on', type=float, default=1.4)
    parser.add_argument('--webshot', help='Optional website screenshot to overlay')
    parser.add_argument('--webshot-scale', type=float, default=0.62,
                        help='Webshot width as a fraction of video width')
    parser.add_argument('--webshot-position', default='top',
                        choices=['center', 'top', 'bottom', 'top-left', 'top-right', 'bottom-left', 'bottom-right'])
    parser.add_argument('--webshot-padding', type=int, default=120,
                        help='Webshot padding from the edge in pixels')
    parser.add_argument('--webshot-duration', type=float, default=1.2,
                        help='Seconds to show the webshot overlay')
    parser.add_argument('--webshot-start', type=float,
                        help='Start time for the webshot overlay in seconds')
    parser.add_argument('--webshot-border', dest='webshot_border', action='store_true',
                        help='Draw a border around the webshot overlay')
    parser.add_argument('--no-webshot-border', dest='webshot_border', action='store_false',
                        help='Disable the webshot border')
    parser.set_defaults(webshot_border=True)
    parser.add_argument('--webshot-border-color', default='white@0.95',
                        help='Border color for the webshot overlay')
    parser.add_argument('--webshot-border-padding', type=int, default=14,
                        help='Border thickness around the webshot overlay in pixels')
    parser.add_argument('--webshot-zoom', dest='webshot_zoom', action='store_true',
                        help='Add a quick zoom-in on the webshot overlay')
    parser.add_argument('--no-webshot-zoom', dest='webshot_zoom', action='store_false',
                        help='Disable the webshot zoom')
    parser.set_defaults(webshot_zoom=True)
    parser.add_argument('--webshot-zoom-factor', type=float, default=1.08,
                        help='Zoom factor for the webshot overlay')
    parser.add_argument('--webshot-zoom-duration', type=float, default=0.45,
                        help='Seconds to reach the zoom factor')
    parser.add_argument('--logo', help='Optional logo image path to overlay')
    parser.add_argument('--logo-scale', type=float, default=0.12, help='Logo width as a fraction of video width')
    parser.add_argument('--logo-position', default='bottom-left',
                        choices=['bottom-left', 'bottom-right', 'top-left', 'top-right'])
    parser.add_argument('--logo-padding', type=int, default=24, help='Logo padding from the edge in pixels')
    parser.add_argument('--brand-mark', dest='brand_mark', action='store_true',
                        help='Draw brand text in the corner')
    parser.add_argument('--no-brand-mark', dest='brand_mark', action='store_false',
                        help='Disable brand text mark')
    parser.set_defaults(brand_mark=False)
    parser.add_argument('--brand-mark-text', help='Brand text to draw (defaults to --brand)')
    parser.add_argument('--brand-mark-highlight',
                        help='Prefix of brand text to render in accent color (e.g., Odds)')
    parser.add_argument('--brand-mark-text-color', default='white')
    parser.add_argument('--brand-mark-accent-color', default='#6BCB4B')
    parser.add_argument('--brand-mark-font-size', type=int, default=46)
    parser.add_argument('--brand-mark-padding', type=int, default=44)
    parser.add_argument('--no-loop', action='store_true', help='Do not loop the clip to match audio length')
    parser.add_argument('--clip-montage', action='store_true',
                        help='Sample multiple segments from the clip and stitch them together')
    parser.add_argument('--clip-montage-length', type=float, default=4.0,
                        help='Seconds per montage segment (approx)')
    parser.add_argument('--clip-montage-seed', type=int,
                        help='Random seed for montage sampling')

    args = parser.parse_args()

    clip_path = Path(args.clip)
    if not clip_path.exists():
        raise SystemExit(f'Clip not found: {clip_path}')

    script_text = get_script_text(args)
    if script_text:
        script_text = fill_template(script_text, args.brand, args.cta_url, args.region)

    audio_path = Path(args.audio) if args.audio else None
    temp_audio = None
    tts_chunks = None
    tts_durations = None
    if audio_path is None:
        if args.tts_provider == 'none':
            raise SystemExit('Provide --audio or select a TTS provider')
        if not script_text:
            raise SystemExit('Provide voiceover text or a template when using TTS')
        temp_audio = Path(args.out).with_suffix('.voiceover.mp3')
        use_chunked = args.caption_sync and (args.captions or args.burn_captions)
        if use_chunked:
            tts_chunks = split_sentences(
                script_text,
                max_words=12,
                max_chars=CAPTION_CHUNK_CHARS,
                min_words=3,
            )
            if not tts_chunks:
                raise SystemExit('No caption chunks available for TTS sync.')
            tts_durations = render_tts_segments(tts_chunks, args, temp_audio, gap=args.caption_gap)
        else:
            if args.tts_provider == 'piper':
                render_piper(script_text, temp_audio, args.model, args.speaker)
            elif args.tts_provider == 'espeak':
                render_espeak(script_text, temp_audio, args.espeak_voice, args.espeak_rate)
            elif args.tts_provider == 'elevenlabs':
                api_key = args.api_key or os.getenv('ELEVENLABS_API_KEY') or os.getenv('PROMO_ELEVENLABS_API_KEY')
                render_elevenlabs(script_text, temp_audio, args.voice_id, args.model_id, api_key)
            elif args.tts_provider == 'edge':
                render_edge_tts(script_text, temp_audio, args.edge_voice, args.edge_rate, args.edge_pitch)
            else:
                raise SystemExit(f'Unsupported TTS provider: {args.tts_provider}')
        audio_path = temp_audio

    if not audio_path.exists():
        raise SystemExit(f'Audio not found: {audio_path}')

    duration = ffprobe_duration(audio_path)

    temp_clip = None
    if args.clip_montage:
        temp_clip = Path(args.out).with_suffix('.montage.mp4')
        montage_path = build_clip_montage(
            clip_path,
            temp_clip,
            duration,
            args.clip_montage_length,
            seed=args.clip_montage_seed,
        )
        if montage_path:
            clip_path = montage_path
            args.no_loop = True

    webshot_path = Path(args.webshot) if args.webshot else None
    webshot_start = None
    webshot_end = None
    if webshot_path:
        if not webshot_path.exists():
            raise SystemExit(f'Webshot not found: {webshot_path}')
        start = args.webshot_start
        segment_duration = None
        if start is None and tts_chunks and tts_durations:
            start, segment_duration = find_webshot_timing(
                tts_chunks,
                tts_durations,
                args.caption_gap,
                args.cta_url,
                args.brand,
            )
        if start is None:
            start = max(0.0, duration - args.webshot_duration)
        show_duration = max(0.2, args.webshot_duration)
        if segment_duration:
            show_duration = max(show_duration, segment_duration)
        end = min(duration, start + show_duration)
        if end <= start:
            webshot_path = None
        else:
            webshot_start = start
            webshot_end = end

    captions_path = None
    if args.captions or args.burn_captions:
        if not script_text:
            raise SystemExit('Captions need --text, --text-file, or --script-id')
        captions_path = Path(args.out).with_suffix('.srt')
        if tts_chunks and tts_durations:
            write_srt_with_segments(
                tts_chunks,
                tts_durations,
                captions_path,
                gap=args.caption_gap,
                verbatim=args.caption_verbatim,
            )
        else:
            write_srt(script_text, duration, captions_path, verbatim=args.caption_verbatim)

    caption_filter = build_caption_filter(args, captions_path)
    video_filter = build_video_filter(args, duration)

    logo_path = Path(args.logo) if args.logo else None
    logo_width = None
    logo_x = None
    logo_y = None
    webshot_width = None
    webshot_x = None
    webshot_y = None
    if logo_path and not logo_path.exists():
        raise SystemExit(f'Logo not found: {logo_path}')
    if logo_path or webshot_path:
        width, height = parse_size(args.size)
        if logo_path:
            logo_width = max(1, int(width * args.logo_scale))
            logo_x, logo_y = logo_overlay_expr(args.logo_position, args.logo_padding)
        if webshot_path:
            webshot_width = max(1, int(width * args.webshot_scale))
            webshot_x, webshot_y = webshot_overlay_expr(
                args.webshot_position,
                args.webshot_padding,
            )

    cmd = ['ffmpeg', '-y']
    if not args.no_loop:
        cmd += ['-stream_loop', '-1']
    cmd += ['-i', str(clip_path), '-i', str(audio_path)]

    input_index = 2
    music_index = None
    if args.music:
        cmd += ['-i', str(args.music)]
        music_index = input_index
        input_index += 1

    webshot_index = None
    if webshot_path:
        cmd += ['-loop', '1', '-i', str(webshot_path)]
        webshot_index = input_index
        input_index += 1

    logo_index = None
    if logo_path:
        cmd += ['-i', str(logo_path)]
        logo_index = input_index
        input_index += 1

    if args.music or logo_path or webshot_path:
        filter_parts = []
        filter_parts.append(f"[0:v]{video_filter}[base]")
        current = '[base]'

        if webshot_path:
            enable_expr = f"between(t,{webshot_start:.2f},{webshot_end:.2f})"
            scale_filter = f"scale={webshot_width}:-1"
            if args.webshot_zoom and webshot_start is not None:
                zoom_factor = max(1.0, args.webshot_zoom_factor)
                zoom_delta = zoom_factor - 1.0
                zoom_duration = min(args.webshot_zoom_duration, webshot_end - webshot_start)
                zoom_duration = max(0.1, zoom_duration)
                zoom_end = webshot_start + zoom_duration
                zoom_expr = (
                    f"if(lt(t,{webshot_start:.2f}),1,"
                    f"if(lt(t,{zoom_end:.2f}),1+{zoom_delta:.3f}*(t-{webshot_start:.2f})/{zoom_duration:.2f},{zoom_factor:.3f}))"
                )
                zoom_expr = zoom_expr.replace(',', '\\,')
                scale_filter = f"scale=w={webshot_width}*{zoom_expr}:h=-1:eval=frame"
            filter_parts.append(f"[{webshot_index}:v]{scale_filter}[webshot_base]")
            webshot_label = 'webshot_base'
            if args.webshot_border:
                border = max(2, args.webshot_border_padding)
                border_color = args.webshot_border_color
                filter_parts.append(
                    f"[webshot_base]pad=iw+{border * 2}:ih+{border * 2}:{border}:{border}:color={border_color}[webshot]"
                )
                webshot_label = 'webshot'
            filter_parts.append(
                f"{current}[{webshot_label}]overlay=x={webshot_x}:y={webshot_y}:enable='{enable_expr}'[with_webshot]"
            )
            current = '[with_webshot]'

        if logo_path:
            filter_parts.append(f"[{logo_index}:v]scale={logo_width}:-1[logo]")
            filter_parts.append(f"{current}[logo]overlay=x={logo_x}:y={logo_y}[with_logo]")
            current = '[with_logo]'

        if caption_filter:
            filter_parts.append(f"{current}{caption_filter}[with_captions]")
            current = '[with_captions]'

        if args.music:
            filter_parts.append(f"[{music_index}:a]volume={args.music_volume}[bg]")
            filter_parts.append(
                "[1:a][bg]sidechaincompress=threshold=0.02:ratio=5:attack=20:release=250[duck]"
            )
            filter_parts.append("[1:a][duck]amix=inputs=2:duration=first:dropout_transition=3[a]")

        cmd += ['-filter_complex', ';'.join(filter_parts), '-map', current]
        if args.music:
            cmd += ['-map', '[a]']
        else:
            cmd += ['-map', '1:a']
    else:
        if caption_filter:
            video_filter = f"{video_filter},{caption_filter}"
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
    if temp_clip and temp_clip.exists():
        temp_clip.unlink(missing_ok=True)

    if captions_path:
        print(f'Captions written to {captions_path}')

    print(f'Promo video written to {args.out}')


if __name__ == '__main__':
    main()
