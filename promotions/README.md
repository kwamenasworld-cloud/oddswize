# Promotions Automation

This folder contains scripts to generate short promo videos with football clips and AI voiceover, plus text templates for quick social posts.

Requirements
- Python 3.10+
- ffmpeg in PATH (ffmpeg + ffprobe)
- Free TTS options: Piper (recommended) or eSpeak in PATH
- For West African accent (free, online): edge-tts (no API key)
- For uploads: Playwright Chromium (`python -m playwright install chromium`)

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
- Captions default to verbatim text so the overlay matches the voiceover. Use `--no-caption-verbatim` if you want shorter, auto-abbreviated lines.
- Captions are synced by segment (default). Use `--no-caption-sync` to disable per-segment TTS timing.
- If captions are too tall or get cut off, adjust caption style in `promotions/scripts/build_promo.py` (FontSize, MarginV, and CAPTION_LINE_CHARS).

Automation ideas
- Schedule daily "value picks" posts with generate_daily_posts.py
- Generate WhatsApp-ready messages with generate_whatsapp_messages.py
- Generate referral links with generate_referral_links.py
- Auto-post to Telegram via a bot (free)
- Auto-generate a daily promo video using a fixed clip + new script text
- Add ref=promo_auto to all links for attribution

Telegram (free)
1) Create a Telegram bot via @BotFather and copy the token.
2) Add the bot to your channel/group and make it an admin.
3) Post a message:
   python promotions/scripts/post_to_telegram.py --message "Top picks today: https://oddswize.com/odds?ref=promo_auto"
4) Post daily picks automatically:
   python promotions/scripts/post_daily_telegram.py --min-edge 6 --count 5

GitHub Actions (fully automated)
- Add secrets in GitHub repo settings:
  - TELEGRAM_BOT_TOKEN
  - TELEGRAM_CHAT_ID
  - PROMO_CLIP_URL (optional, direct mp4 link)
- Workflow will generate a promo video daily and post to Telegram.
- If PROMO_CLIP_URL is not set, a simple football-themed background is generated.

One-command news promo + upload (self-hosted)
1) Put vertical clips in promotions/assets/clips/.
2) (Optional) Add a background bed at promotions/assets/music/bed.mp3.
3) Capture login sessions (one-time):
   python promotions/scripts/capture_tiktok_state.py --out promotions/tmp/tiktok_storage_state.json
   python promotions/scripts/capture_instagram_state.py --out promotions/tmp/instagram_storage_state.json
4) Run locally:
   python promotions/scripts/run_news_promo.py --logo logo_cropped.PNG
5) Or run the "News Promo Upload (Self-Hosted)" workflow (manual).

Notes
- You can pass the storage state via `TIKTOK_STORAGE_STATE_B64` secret instead of a file.
- Use `TIKTOK_HEADLESS=true` or `INSTAGRAM_HEADLESS=true` if you need headless mode.
- Instagram can use `INSTAGRAM_STORAGE_STATE_B64` or `INSTAGRAM_STORAGE_STATE_PATH`.
- The news voiceover uses Google News RSS and ends with the OddsWize promo CTA.
- You can set defaults once via env vars:
  - `PROMO_TTS_PROVIDER` (espeak, piper, elevenlabs, edge)
  - `PROMO_ESPEAK_VOICE` or `PROMO_PIPER_MODEL` or `PROMO_ELEVENLABS_VOICE_ID`
  - `PROMO_ELEVENLABS_API_KEY` if using ElevenLabs
  - `PROMO_EDGE_VOICE` (e.g., en-NG-AbeoNeural) with `PROMO_TTS_PROVIDER=edge`
- Viral defaults in `run_news_promo.py`:
  - Shorter scripts (max 70 words), hook overlay, lower-third captions, progress bar, and subtle zoom pulses.
- Script output includes explicit line picks (for example, draw no bet or over 2.5) plus a reason.

Clip selection and smooth playback
- If you see jumpy cuts, disable montage sampling:
  - `python promotions/scripts/run_news_promo.py --no-clip-montage`
- If a long clip contains decode errors, extract short safe clips and point the runner at them:
  - `mkdir promotions/assets/clips_safe`
  - `ffmpeg -ss 0 -t 15 -i promotions/assets/clips/your_long_clip.mp4 -c copy promotions/assets/clips_safe/clip_01.mp4`
  - `python promotions/scripts/run_news_promo.py --clips-dir promotions/assets/clips_safe --no-clip-montage`

Fit mode (avoid cropping)
- Default is `--fit-mode crop` (fills the frame).
- Use `--fit-mode blur` or `--fit-mode pad` if you want the full clip to be visible without cropping.

Webshot overlay tips
- If the website screenshot covers text, move it with `--webshot-position` (for example, `top`) and reduce `--webshot-scale`.

WhatsApp (free)
1) Generate messages and links:
   python promotions/scripts/generate_whatsapp_messages.py --min-edge 6 --count 5
2) Open the generated links in promotions/output/whatsapp_links.csv

Referral links (free)
1) Generate links for names/handles:
   python promotions/scripts/generate_referral_links.py --names "kwame,ama,kojo"
2) Share each unique link and track ref codes in analytics.

Email digest (free)
- Use promotions/templates/email_digest.html with a free email tool.

Troubleshooting
- ElevenLabs quota errors: reduce script length (`--max-words`) or run a shorter voiceover first.
- Captions not matching the voiceover: ensure `--caption-verbatim` and `--caption-sync` are on (both default).
- Captions cut off: lower FontSize or increase margins in `promotions/scripts/build_promo.py`.

Windows env var setup
- Current shell session:
  - `$env:PROMO_ELEVENLABS_API_KEY='YOUR_KEY'`
- Persist for the user:
  - `[Environment]::SetEnvironmentVariable('PROMO_ELEVENLABS_API_KEY','YOUR_KEY','User')`
