import argparse
import os
import random
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

from generate_news_voiceover import (
    DEFAULT_FIXTURE_DAYS,
    DEFAULT_FIXTURE_LIMIT,
    DEFAULT_HASHTAGS,
    DEFAULT_SOURCES,
    fetch_headlines,
    fetch_upcoming_fixtures,
    generate_story,
    pick_hook_line,
    resolve_fixture_leagues,
    shorten_text,
)


VIDEO_EXTENSIONS = ('.mp4', '.mov', '.mkv', '.webm')


def probe_fps(video_path):
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=avg_frame_rate',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    value = result.stdout.strip()
    if not value:
        return None
    try:
        fps_value = float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        try:
            fps_value = float(value)
        except ValueError:
            return None
    fps_int = int(round(fps_value))
    if fps_int <= 0:
        return None
    return fps_int


def list_clips(clips_dir):
    clips_path = Path(clips_dir)
    if not clips_path.exists():
        raise SystemExit(f'Clips folder not found: {clips_path}')
    clips = [path for path in clips_path.rglob('*') if path.suffix.lower() in VIDEO_EXTENSIONS]
    return sorted(clips)


def pick_clip(clips, strategy):
    if not clips:
        raise SystemExit('No clips found. Add mp4 files to promotions/assets/clips.')
    if strategy == 'latest':
        return max(clips, key=lambda path: path.stat().st_mtime)
    return random.choice(clips)


def resolve_headless(args):
    if args.headed:
        return False
    if args.headless:
        return True
    env_value = (
        os.getenv('PROMO_HEADLESS')
        or os.getenv('TIKTOK_HEADLESS')
        or os.getenv('INSTAGRAM_HEADLESS')
        or os.getenv('CI')
    )
    if not env_value:
        return False
    return str(env_value).strip().lower() in {'1', 'true', 'yes', 'y'}


def env_default(key, fallback=None):
    value = os.getenv(key)
    if value is None or value == '':
        return fallback
    return value


def run_build_promo(args, clip_path, voiceover_path, out_path):
    cmd = [
        sys.executable,
        str(Path(__file__).with_name('build_promo.py')),
        '--clip', str(clip_path),
        '--tts-provider', args.tts_provider,
        '--text-file', str(voiceover_path),
        '--brand', args.brand,
        '--cta-url', args.cta_url,
        '--out', str(out_path),
        '--size', args.size,
        '--title', args.title,
        '--cta', args.cta,
        '--hook-text', args.hook_text,
        '--hook-duration', str(args.hook_duration),
        '--fit-mode', args.fit_mode,
        '--blur-sigma', str(args.blur_sigma),
        '--pad-color', args.pad_color,
    ]

    if args.fps:
        cmd += ['--fps', str(args.fps)]

    if args.clip_montage:
        cmd += ['--clip-montage', '--clip-montage-length', str(args.clip_montage_length)]
        if args.clip_montage_seed is not None:
            cmd += ['--clip-montage-seed', str(args.clip_montage_seed)]

    if args.logo:
        cmd += ['--logo', str(args.logo)]
        cmd += ['--logo-scale', str(args.logo_scale)]
        cmd += ['--logo-position', args.logo_position]
        cmd += ['--logo-padding', str(args.logo_padding)]

    if args.webshot:
        cmd += ['--webshot', str(args.webshot)]
        cmd += ['--webshot-scale', str(args.webshot_scale)]
        cmd += ['--webshot-position', args.webshot_position]
        cmd += ['--webshot-padding', str(args.webshot_padding)]
        cmd += ['--webshot-duration', str(args.webshot_duration)]
        cmd += ['--webshot-border' if args.webshot_border else '--no-webshot-border']
        cmd += ['--webshot-border-color', args.webshot_border_color]
        cmd += ['--webshot-border-padding', str(args.webshot_border_padding)]
        cmd += ['--webshot-zoom' if args.webshot_zoom else '--no-webshot-zoom']
        cmd += ['--webshot-zoom-factor', str(args.webshot_zoom_factor)]
        cmd += ['--webshot-zoom-duration', str(args.webshot_zoom_duration)]
        if args.webshot_start is not None:
            cmd += ['--webshot-start', str(args.webshot_start)]

    if args.brand_mark:
        cmd += ['--brand-mark']
        if args.brand_mark_text:
            cmd += ['--brand-mark-text', args.brand_mark_text]
        if args.brand_mark_highlight is not None:
            cmd += ['--brand-mark-highlight', args.brand_mark_highlight]
        cmd += ['--brand-mark-text-color', args.brand_mark_text_color]
        cmd += ['--brand-mark-accent-color', args.brand_mark_accent_color]
        cmd += ['--brand-mark-font-size', str(args.brand_mark_font_size)]
        cmd += ['--brand-mark-padding', str(args.brand_mark_padding)]

    if args.font_file:
        cmd += ['--font-file', args.font_file]

    if args.burn_captions:
        cmd += ['--burn-captions']
    cmd += ['--caption-verbatim' if args.caption_verbatim else '--no-caption-verbatim']

    if args.music:
        cmd += ['--music', str(args.music)]
        cmd += ['--music-volume', str(args.music_volume)]

    if args.title_duration is not None:
        cmd += ['--title-duration', str(args.title_duration)]

    if args.cta_delay is not None:
        cmd += ['--cta-delay', str(args.cta_delay)]

    if args.progress_bar:
        cmd += ['--progress-bar']
        cmd += ['--progress-bar-height', str(args.progress_bar_height)]
        cmd += ['--progress-bar-color', args.progress_bar_color]

    if args.pulse_zoom:
        cmd += ['--pulse-zoom']
        cmd += ['--pulse-zoom-factor', str(args.pulse_zoom_factor)]
        cmd += ['--pulse-zoom-period', str(args.pulse_zoom_period)]
        cmd += ['--pulse-zoom-on', str(args.pulse_zoom_on)]

    if args.tts_provider == 'piper':
        if not args.piper_model:
            raise SystemExit('Missing --piper-model for Piper.')
        cmd += ['--model', args.piper_model]
        if args.piper_speaker is not None:
            cmd += ['--speaker', str(args.piper_speaker)]
    elif args.tts_provider == 'espeak':
        cmd += ['--espeak-voice', args.espeak_voice, '--espeak-rate', str(args.espeak_rate)]
    elif args.tts_provider == 'elevenlabs':
        if args.elevenlabs_voice_id:
            cmd += ['--voice-id', args.elevenlabs_voice_id]
        if args.elevenlabs_model_id:
            cmd += ['--model-id', args.elevenlabs_model_id]
        if args.elevenlabs_api_key:
            cmd += ['--api-key', args.elevenlabs_api_key]
    elif args.tts_provider == 'edge':
        cmd += ['--edge-voice', args.edge_voice, '--edge-rate', args.edge_rate, '--edge-pitch', args.edge_pitch]

    subprocess.run(cmd, check=True)


def run_upload(script_name, video_path, caption_path, headless, dry_run):
    cmd = [
        sys.executable,
        str(Path(__file__).with_name(script_name)),
        '--video', str(video_path),
        '--caption-file', str(caption_path),
    ]
    cmd.append('--headless' if headless else '--headed')
    if dry_run:
        cmd.append('--dry-run')
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(description='Generate a betting-news promo and upload it.')
    parser.add_argument('--clips-dir', default='promotions/assets/clips')
    parser.add_argument('--clip-strategy', choices=['random', 'latest'], default='random')
    parser.add_argument('--clip-montage', dest='clip_montage', action='store_true',
                        help='Sample multiple segments from the selected clip')
    parser.add_argument('--no-clip-montage', dest='clip_montage', action='store_false',
                        help='Disable montage sampling')
    parser.set_defaults(clip_montage=True)
    parser.add_argument('--clip-montage-length', type=float, default=4.0)
    parser.add_argument('--clip-montage-seed', type=int)
    parser.add_argument('--logo')
    parser.add_argument('--logo-scale', type=float, default=0.12)
    parser.add_argument('--logo-position', default='bottom-left',
                        choices=['bottom-left', 'bottom-right', 'top-left', 'top-right'])
    parser.add_argument('--logo-padding', type=int, default=24)
    parser.add_argument('--webshot')
    parser.add_argument('--webshot-scale', type=float, default=0.5)
    parser.add_argument('--webshot-position', default='top-right',
                        choices=['center', 'top', 'bottom', 'top-left', 'top-right', 'bottom-left', 'bottom-right'])
    parser.add_argument('--webshot-padding', type=int, default=64)
    parser.add_argument('--webshot-duration', type=float, default=1.2)
    parser.add_argument('--webshot-start', type=float)
    parser.add_argument('--webshot-border', dest='webshot_border', action='store_true')
    parser.add_argument('--no-webshot-border', dest='webshot_border', action='store_false')
    parser.set_defaults(webshot_border=True)
    parser.add_argument('--webshot-border-color', default='white@0.95')
    parser.add_argument('--webshot-border-padding', type=int, default=14)
    parser.add_argument('--webshot-zoom', dest='webshot_zoom', action='store_true')
    parser.add_argument('--no-webshot-zoom', dest='webshot_zoom', action='store_false')
    parser.set_defaults(webshot_zoom=True)
    parser.add_argument('--webshot-zoom-factor', type=float, default=1.08)
    parser.add_argument('--webshot-zoom-duration', type=float, default=0.45)
    parser.add_argument('--brand-mark', dest='brand_mark', action='store_true')
    parser.add_argument('--no-brand-mark', dest='brand_mark', action='store_false')
    parser.set_defaults(brand_mark=True)
    parser.add_argument('--brand-mark-text')
    parser.add_argument('--brand-mark-highlight')
    parser.add_argument('--brand-mark-text-color', default='white')
    parser.add_argument('--brand-mark-accent-color', default='#6BCB4B')
    parser.add_argument('--brand-mark-font-size', type=int, default=54)
    parser.add_argument('--brand-mark-padding', type=int, default=44)
    parser.add_argument('--brand', default='OddsWize')
    parser.add_argument('--cta-url', default='https://oddswize.com/odds?ref=promo_auto')
    parser.add_argument('--title', default='OddsWize')
    parser.add_argument('--cta', default='')
    parser.add_argument('--size', default='1080x1920')
    parser.add_argument('--fps', type=int, help='Override output fps (defaults to clip fps)')
    parser.add_argument('--fit-mode', default='crop', choices=['crop', 'blur', 'pad'])
    parser.add_argument('--blur-sigma', type=float, default=24.0)
    parser.add_argument('--pad-color', default='black')
    parser.add_argument('--font-file')
    parser.add_argument('--music')
    parser.add_argument('--music-volume', type=float, default=0.12)
    parser.add_argument('--tts-provider', default=env_default('PROMO_TTS_PROVIDER', 'elevenlabs'),
                        choices=['espeak', 'piper', 'elevenlabs', 'edge'])
    parser.add_argument('--piper-model', default=env_default('PROMO_PIPER_MODEL'))
    parser.add_argument('--piper-speaker', type=int)
    parser.add_argument('--espeak-voice', default=env_default('PROMO_ESPEAK_VOICE', 'en'))
    parser.add_argument('--espeak-rate', type=int, default=175)
    parser.add_argument('--elevenlabs-voice-id', default=env_default('PROMO_ELEVENLABS_VOICE_ID', 'x86DtpnPPuq2BpEiKPRy'))
    parser.add_argument('--elevenlabs-model-id', default='eleven_multilingual_v2')
    parser.add_argument('--elevenlabs-api-key', default=env_default('PROMO_ELEVENLABS_API_KEY'))
    parser.add_argument('--edge-voice', default=env_default('PROMO_EDGE_VOICE', 'en-NG-AbeoNeural'))
    parser.add_argument('--edge-rate', default=env_default('PROMO_EDGE_RATE', '+0%'))
    parser.add_argument('--edge-pitch', default=env_default('PROMO_EDGE_PITCH', '+0Hz'))
    parser.add_argument('--source', action='append', help='RSS feed URL (repeatable)')
    parser.add_argument('--max-items', type=int, default=3)
    parser.add_argument('--fixtures', dest='use_fixtures', action='store_true',
                        help='Use upcoming fixtures from ESPN')
    parser.add_argument('--no-fixtures', dest='use_fixtures', action='store_false',
                        help='Disable fixture lookup')
    parser.set_defaults(use_fixtures=True)
    parser.add_argument('--fixtures-days', type=int, default=DEFAULT_FIXTURE_DAYS)
    parser.add_argument('--fixtures-limit', type=int, default=DEFAULT_FIXTURE_LIMIT)
    parser.add_argument('--fixture-league', action='append',
                        help='ESPN league id to include (repeatable)')
    parser.add_argument('--hashtags', default=DEFAULT_HASHTAGS)
    parser.add_argument('--hook', help='Optional hook line for the voiceover')
    parser.add_argument('--max-words', type=int, default=70)
    parser.add_argument('--llm', dest='use_llm', action='store_true',
                        help='Use an LLM to write the story script')
    parser.add_argument('--no-llm', dest='use_llm', action='store_false',
                        help='Disable LLM story generation')
    parser.set_defaults(use_llm=None)
    parser.add_argument('--llm-model', help='Override the LLM model name')
    parser.add_argument('--proof-line', help='Optional proof/receipts line for the voiceover')
    parser.add_argument('--voiceover-out', default='promotions/output/weekly_voiceover.txt')
    parser.add_argument('--caption-out', default='promotions/output/weekly_caption.txt')
    parser.add_argument('--out', default='promotions/output/weekly_promo.mp4')
    parser.add_argument('--caption', default='')
    parser.add_argument('--caption-file')
    parser.add_argument('--burn-captions', dest='burn_captions', action='store_true')
    parser.add_argument('--no-burn-captions', dest='burn_captions', action='store_false')
    parser.set_defaults(burn_captions=True)
    parser.add_argument('--caption-verbatim', dest='caption_verbatim', action='store_true')
    parser.add_argument('--no-caption-verbatim', dest='caption_verbatim', action='store_false')
    parser.set_defaults(caption_verbatim=True)
    parser.add_argument('--hook-duration', type=float, default=2.4)
    parser.add_argument('--hook-overlay', dest='hook_overlay', action='store_true')
    parser.add_argument('--no-hook-overlay', dest='hook_overlay', action='store_false')
    parser.set_defaults(hook_overlay=False)
    parser.add_argument('--title-duration', type=float, default=1.6)
    parser.add_argument('--cta-delay', type=float, default=4.5)
    parser.add_argument('--progress-bar', dest='progress_bar', action='store_true')
    parser.add_argument('--no-progress-bar', dest='progress_bar', action='store_false')
    parser.set_defaults(progress_bar=True)
    parser.add_argument('--progress-bar-height', type=int, default=6)
    parser.add_argument('--progress-bar-color', default='white@0.75')
    parser.add_argument('--pulse-zoom', dest='pulse_zoom', action='store_true')
    parser.add_argument('--no-pulse-zoom', dest='pulse_zoom', action='store_false')
    parser.set_defaults(pulse_zoom=False)
    parser.add_argument('--pulse-zoom-factor', type=float, default=1.06)
    parser.add_argument('--pulse-zoom-period', type=float, default=3.0)
    parser.add_argument('--pulse-zoom-on', type=float, default=1.4)
    parser.add_argument('--skip-tiktok', action='store_true')
    parser.add_argument('--skip-reels', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--headed', action='store_true')

    args = parser.parse_args()

    logo_path = Path(args.logo) if args.logo else None
    if logo_path and not logo_path.exists():
        raise SystemExit(f'Logo not found: {logo_path}')
    if logo_path:
        args.logo = logo_path

    webshot_path = Path(args.webshot) if args.webshot else None
    if webshot_path is None:
        default_webshot = Path('promotions/assets/oddswize_screenshot.png')
        if default_webshot.exists():
            webshot_path = default_webshot
    if webshot_path and not webshot_path.exists():
        raise SystemExit(f'Webshot not found: {webshot_path}')
    args.webshot = webshot_path

    clips = list_clips(args.clips_dir)
    clip = pick_clip(clips, args.clip_strategy)
    if args.fps is None:
        args.fps = probe_fps(clip) or 30
    if args.music:
        args.music = Path(args.music)
        if not args.music.exists():
            raise SystemExit(f'Music file not found: {args.music}')
    else:
        default_music = Path('promotions/assets/music/bed.mp3')
        if default_music.exists():
            args.music = default_music
        else:
            args.music = None

    sources = args.source or DEFAULT_SOURCES
    headlines = fetch_headlines(sources, args.max_items)
    fixtures = []
    if args.use_fixtures:
        leagues = resolve_fixture_leagues(args.fixture_league)
        fixtures = fetch_upcoming_fixtures(
            days_ahead=args.fixtures_days,
            limit=args.fixtures_limit,
            leagues=leagues,
        )
    hook_line = pick_hook_line(args.hook, args.max_words)
    voiceover_text, caption_text = generate_story(
        headlines,
        args.brand,
        args.cta_url,
        args.hashtags,
        args.max_words,
        hook=hook_line,
        use_llm=args.use_llm,
        llm_model=args.llm_model,
        fixtures=fixtures,
        proof_line=args.proof_line,
    )
    args.hook_text = shorten_text(hook_line, 6) if args.hook_overlay else ''
    if args.caption_file:
        caption_text = Path(args.caption_file).read_text(encoding='utf-8').strip()
    elif args.caption:
        caption_text = args.caption

    voiceover_path = Path(args.voiceover_out)
    voiceover_path.parent.mkdir(parents=True, exist_ok=True)
    voiceover_path.write_text(voiceover_text, encoding='utf-8')

    caption_path = Path(args.caption_out)
    caption_path.parent.mkdir(parents=True, exist_ok=True)
    caption_path.write_text(caption_text, encoding='utf-8')

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    clip_label = str(clip).encode('cp1252', errors='replace').decode('cp1252')
    print(f'Using clip: {clip_label}')
    run_build_promo(args, clip, voiceover_path, out_path)

    if args.dry_run:
        print('Dry run enabled; skipping uploads.')
        return

    headless = resolve_headless(args)

    if not args.skip_tiktok:
        run_upload('upload_to_tiktok.py', out_path, caption_path, headless, args.dry_run)

    if not args.skip_reels:
        run_upload('upload_to_instagram_reels.py', out_path, caption_path, headless, args.dry_run)


if __name__ == '__main__':
    main()
