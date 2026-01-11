# Promotions Automation

This folder contains scripts to generate short promo videos with football clips and AI voiceover, plus text templates for quick social posts.

Requirements
- Python 3.10+
- ffmpeg in PATH (ffmpeg + ffprobe)
- Free TTS options: Piper (recommended) or eSpeak in PATH

Quick start (voiceover + video)
1) Put a clip in promotions/assets/clips/ (vertical 9:16 recommended).
2) Create a voiceover:
   python promotions/scripts/render_voiceover.py --provider piper --model <MODEL.onnx> --script-id value_picks_short --out promotions/output/voiceover.mp3
3) Build the promo:
   python promotions/scripts/build_promo.py --clip promotions/assets/clips/clip.mp4 --audio promotions/output/voiceover.mp3 --out promotions/output/promo.mp4 --title "OddsWize" --cta "Compare odds today" --font-file "C:\\Windows\\Fonts\\arial.ttf"

Free TTS notes
- Piper sounds best. Download a Piper model, then pass --model to render_voiceover.py.
- eSpeak is fully offline and very lightweight: use --provider espeak.

Templates
- promotions/scripts/voiceover_templates.json

Captions
- Use --captions to write an SRT file next to the output.
- Use --burn-captions to bake captions into the video (requires ffmpeg with libass support).

Automation ideas
- Schedule daily "value picks" posts with generate_daily_posts.py
- Auto-post to Telegram via a bot (free)
- Auto-generate a daily promo video using a fixed clip + new script text
- Add ref=promo_auto to all links for attribution
