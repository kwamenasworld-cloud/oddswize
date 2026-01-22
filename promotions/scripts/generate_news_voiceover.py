import argparse
import json
import os
import random
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup


DEFAULT_SOURCES = [
    'https://news.google.com/rss/search?q=soccer+betting+odds&hl=en-US&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=premier+league+odds&hl=en-US&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=champions+league+odds&hl=en-US&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=soccer+odds+news&hl=en-US&gl=US&ceid=US:en',
]
DEFAULT_HASHTAGS = '#oddswize #soccer #football #sportsbetting #bettingtips'
DEFAULT_CTA_PROMPT = 'Drop your slip and I might review one.'
DEFAULT_HOOKS = [
    'Stop scrolling.',
    'Stop scrolling. Weekend slip story.',
    'Chale, weekend slip time. Quick story.',
    'How far my people? Quick soccer slip.',
    'Save this. Weekend soccer tips.',
    'Kickoff is close. Here is the slip.',
    'Quick story before kickoff.',
    'Weekend slip story.',
]
DEFAULT_PROOF_LINES = [
    'Receipts ready.',
    'Keep receipts.',
    'Receipts set.',
]
STORY_INTROS = [
    'Story time. Slip on the table.',
    'Scene set. Weekend fixtures.',
    'Picture this. Kickoff is close.',
    'Quick scene. Fresh slip.',
]
TIP_LABELS = ['Safe play', 'Bold pick', 'Value watch']
DEFAULT_CONTRARIAN_LINES = [
    'Public leans obvious, I fade it.',
    'Crowd wants favorite, I fade it.',
    'Everyone leans obvious, I fade it.',
]
TIME_LOCK_TEMPLATES = [
    '{day_part} kickoff.',
    'Kickoff {day_part}.',
]
CAPTION_TEMPLATES = [
    'Weekend slip story: {headline}. Drop your slip {urgency}. {cta_url}',
    'Slip story: {headline}. Comment your slip {urgency}. {cta_url}',
    'Value watch: {headline}. Tap for lines {urgency}. {cta_url}',
    'Save this for matchday: {headline}. Odds check {urgency}. {cta_url}',
]
ENGAGEMENT_QUESTIONS = [
    'Who are you backing this weekend?',
    'Which pick is safest?',
    'Drop your best pick.',
    'Who ruins the slip?',
    'Which side are you fading?',
]
SOCCER_KEYWORDS = [
    'soccer',
    'premier league',
    'champions league',
    'europa league',
    'conference league',
    'la liga',
    'serie a',
    'bundesliga',
    'ligue 1',
    'fa cup',
    'efl cup',
    'carabao',
    'uefa',
    'fifa',
    'world cup',
    'afcon',
    'africa cup of nations',
    'caf',
    'conmebol',
    'concacaf',
    'mls',
]
NON_SOCCER_KEYWORDS = [
    'nfl',
    'college football',
    'ncaa',
    'cfb',
    'super bowl',
    'quarterback',
    'touchdown',
    'gridiron',
    'divisional',
    'wild card',
    'bowl game',
    'nba',
    'mlb',
    'nhl',
    'basketball',
    'baseball',
    'hockey',
    'cricket',
    'rugby',
    'tennis',
    'golf',
]
ESPN_SCOREBOARD_BASE = 'https://site.api.espn.com/apis/site/v2/sports/soccer'
DEFAULT_FIXTURE_DAYS = 7
DEFAULT_FIXTURE_LIMIT = 4
DEFAULT_FIXTURE_LEAGUES = [
    ('eng.1', 'Premier League'),
    ('esp.1', 'La Liga'),
    ('ita.1', 'Serie A'),
    ('ger.1', 'Bundesliga'),
    ('fra.1', 'Ligue 1'),
    ('uefa.champions', 'UEFA Champions League'),
    ('uefa.europa', 'UEFA Europa League'),
    ('uefa.europa.conf', 'UEFA Europa Conference League'),
]


def clean_title(title):
    title = ' '.join(title.split())
    if ' - ' in title:
        title = title.split(' - ', 1)[0].strip()
    title = re.sub(r'\s*\([^)]*\)', '', title)
    title = title.replace('&', 'and')
    title = re.sub(r'\.{2,}', '.', title)
    title = re.sub(r'[\s:;,-]+$', '', title)
    title = title.strip(' .,:;!-')
    return title


def shorten_text(text, max_words):
    words = text.split()
    if len(words) <= max_words:
        return text
    return ' '.join(words[:max_words])


def strip_emoji(text):
    if not text:
        return text
    return ''.join(
        ch for ch in text
        if unicodedata.category(ch) not in {'So', 'Cs'}
    )


ASCII_TRANSLATE = str.maketrans({
    '\u2018': "'",
    '\u2019': "'",
    '\u201c': '"',
    '\u201d': '"',
    '\u2013': '-',
    '\u2014': '-',
    '\u2026': '...',
    '\u00a0': ' ',
})


def normalize_ascii(text):
    if not text:
        return text
    text = text.translate(ASCII_TRANSLATE)
    text = text.encode('ascii', 'ignore').decode('ascii')
    return ' '.join(text.split())


def clamp_word_count(text, max_words):
    words = text.split()
    if len(words) <= max_words:
        return text
    return ' '.join(words[:max_words])


def clamp_with_tail(text, max_words, tail):
    if not text:
        return text
    if not tail:
        return clamp_word_count(text, max_words)
    words = text.split()
    if len(words) <= max_words:
        return text
    tail_words = tail.split()
    if len(tail_words) >= max_words:
        return ' '.join(tail_words[:max_words])
    keep = max_words - len(tail_words)
    return ' '.join(words[:keep] + tail_words)


def fit_body_parts(body_parts, hook_line, tail, max_words, optional_lines=None):
    if not body_parts:
        return body_parts
    if max_words <= 0:
        return body_parts
    hook_words = len(hook_line.split()) if hook_line else 0
    tail_words = len(tail.split()) if tail else 0
    budget = max_words - hook_words - tail_words
    if budget <= 0:
        return body_parts
    trimmed = list(body_parts)

    def word_count(parts):
        return sum(len(part.split()) for part in parts if part)

    for line in optional_lines or []:
        if word_count(trimmed) <= budget:
            break
        if not line:
            continue
        trimmed = [part for part in trimmed if part != line]
    return trimmed


def format_spoken_url(url):
    if not url:
        return url
    spoken = url.replace('https://', '').replace('http://', '')
    spoken = spoken.split('?', 1)[0]
    return spoken.rstrip('/')


def format_day_part(date_value):
    if not date_value:
        return None
    local_dt = date_value.astimezone()
    day = local_dt.strftime('%A')
    hour = local_dt.hour
    if 5 <= hour < 12:
        part = 'morning'
    elif 12 <= hour < 17:
        part = 'afternoon'
    elif 17 <= hour < 22:
        part = 'night'
    else:
        part = 'late'
    return f'{day} {part}'


def build_time_lock_line(fixtures):
    if not fixtures:
        return 'Kickoff is close.'
    first = None
    for fixture in fixtures:
        fixture_date = fixture.get('date')
        if fixture_date:
            first = fixture_date
            break
    day_part = format_day_part(first)
    if not day_part:
        return 'Kickoff is close.'
    template = random.choice(TIME_LOCK_TEMPLATES)
    return template.format(day_part=day_part)


def format_espn_date(date_value):
    return date_value.strftime('%Y%m%d')


def parse_espn_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None


def resolve_fixture_leagues(league_ids=None):
    if not league_ids:
        return list(DEFAULT_FIXTURE_LEAGUES)
    known = {league_id: label for league_id, label in DEFAULT_FIXTURE_LEAGUES}
    return [(league_id, known.get(league_id, league_id)) for league_id in league_ids]


def fetch_espn_fixtures(league_id, league_label, start_date=None, end_date=None):
    params = {}
    if start_date and end_date:
        params['dates'] = f'{format_espn_date(start_date)}-{format_espn_date(end_date)}'
    elif start_date:
        params['dates'] = format_espn_date(start_date)
    url = f'{ESPN_SCOREBOARD_BASE}/{league_id}/scoreboard'
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f'Warning: failed to fetch fixtures for {league_label}: {exc}')
        return []

    data = resp.json()
    fixtures = []
    for event in data.get('events', []):
        status_type = event.get('status', {}).get('type', {})
        if status_type.get('state') != 'pre' and status_type.get('name') != 'STATUS_SCHEDULED':
            continue
        competition = event.get('competitions', [{}])[0]
        competitors = competition.get('competitors', [])
        home = next((comp for comp in competitors if comp.get('homeAway') == 'home'), None)
        away = next((comp for comp in competitors if comp.get('homeAway') == 'away'), None)
        if not home or not away:
            continue
        home_team = home.get('team', {})
        away_team = away.get('team', {})
        home_name = home_team.get('shortDisplayName') or home_team.get('displayName')
        away_name = away_team.get('shortDisplayName') or away_team.get('displayName')
        if not home_name or not away_name:
            continue
        matchup = f'{home_name} vs {away_name}'
        fixture_date = parse_espn_datetime(event.get('date') or competition.get('date'))
        fixtures.append({
            'matchup': matchup,
            'date': fixture_date,
            'league': league_label,
        })
    return fixtures


def fetch_upcoming_fixtures(days_ahead=DEFAULT_FIXTURE_DAYS,
                            limit=DEFAULT_FIXTURE_LIMIT,
                            leagues=None):
    if days_ahead <= 0 or limit <= 0:
        return []
    start_date = datetime.now(timezone.utc).date()
    end_date = start_date + timedelta(days=days_ahead)
    leagues = leagues or DEFAULT_FIXTURE_LEAGUES

    fixtures = []
    for league_id, league_label in leagues:
        fixtures.extend(fetch_espn_fixtures(league_id, league_label, start_date, end_date))

    if not fixtures:
        return []

    max_date = datetime.max.replace(tzinfo=timezone.utc)
    fixtures.sort(key=lambda item: item.get('date') or max_date)
    seen = set()
    filtered = []
    for fixture in fixtures:
        matchup = fixture.get('matchup')
        if not matchup:
            continue
        key = normalize_matchup(matchup)
        if key in seen:
            continue
        seen.add(key)
        filtered.append(fixture)
        if len(filtered) >= limit:
            break
    return filtered


def fetch_upcoming_matchups(days_ahead=DEFAULT_FIXTURE_DAYS,
                            limit=DEFAULT_FIXTURE_LIMIT,
                            leagues=None):
    fixtures = fetch_upcoming_fixtures(
        days_ahead=days_ahead,
        limit=limit,
        leagues=leagues,
    )
    return [fixture['matchup'] for fixture in fixtures if fixture.get('matchup')]


def get_llm_config():
    api_key = os.getenv('PROMO_LLM_API_KEY') or os.getenv('OPENAI_API_KEY')
    model = os.getenv('PROMO_LLM_MODEL', 'gpt-4o-mini')
    return api_key, model


def extract_json_blob(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                return None
    return None


def normalize_spoken_url(text, cta_url):
    if not text or not cta_url:
        return text
    spoken = format_spoken_url(cta_url)
    if not spoken:
        return text
    return text.replace(cta_url, spoken)


def pick_hook_line(hook, max_words):
    if hook:
        return hook
    if max_words <= 55:
        short_hooks = [line for line in DEFAULT_HOOKS if len(line.split()) <= 4]
        if short_hooks:
            return random.choice(short_hooks)
    return random.choice(DEFAULT_HOOKS)


def build_brand_explainer(brand, cta_url, include_url=True):
    explainer = f'{brand} compares odds across books so you see value.'
    spoken = format_spoken_url(cta_url)
    if include_url and spoken:
        explainer = f'{explainer} Visit {spoken}.'
    return explainer


def build_proof_line(proof_line=None):
    if proof_line:
        return proof_line.strip()
    return random.choice(DEFAULT_PROOF_LINES)


def build_contrarian_line():
    return random.choice(DEFAULT_CONTRARIAN_LINES)


def strip_brand_mentions(text, brand, cta_url):
    if not text:
        return text
    patterns = []
    if brand:
        patterns.append(re.escape(brand))
    if cta_url:
        patterns.append(re.escape(cta_url))
    spoken = format_spoken_url(cta_url)
    if spoken:
        patterns.append(re.escape(spoken))
    if not patterns:
        return text
    combined = r'(?:' + '|'.join(patterns) + r')'
    sentences = re.split(r'(?<=[.!?])\s+', text)
    kept = [sentence for sentence in sentences if not re.search(combined, sentence, flags=re.IGNORECASE)]
    if kept:
        return ' '.join(kept)
    return text


def ensure_brand_explainer(text, brand, cta_url):
    if not text:
        tail = build_brand_explainer(brand, cta_url, include_url=True)
        return tail, tail
    spoken = format_spoken_url(cta_url)
    text = re.sub(r'\bvisit[.!?]*\s*$', '', text, flags=re.IGNORECASE)
    if brand:
        text = re.sub(
            rf'\bvisit\s+{re.escape(brand)}[.!?]*\s*$',
            '',
            text,
            flags=re.IGNORECASE,
        )
    if spoken:
        text = text.replace(spoken, '').replace(cta_url, '')
    lower = text.lower()
    needs_explainer = brand and (brand.lower() not in lower or 'compare' not in lower)
    needs_url = bool(spoken)
    tail_parts = []
    if needs_explainer:
        tail_parts.append(build_brand_explainer(brand, cta_url, include_url=False))
    if needs_url:
        tail_parts.append(f'Visit {spoken}.')
    tail = ' '.join(tail_parts).strip()
    if tail:
        return f'{text} {tail}', tail
    return text, ''


MATCHUP_REGEX = re.compile(
    r"([A-Za-z0-9&'.-]+(?:\s+[A-Za-z0-9&'.-]+){0,3})\s+"
    r"(?:vs\.?|v)\s+"
    r"([A-Za-z0-9&'.-]+(?:\s+[A-Za-z0-9&'.-]+){0,3})",
    re.IGNORECASE,
)


def extract_matchups(headlines, limit=3):
    matchups = []
    for title in headlines:
        for match in MATCHUP_REGEX.finditer(title):
            home = match.group(1).strip()
            away = match.group(2).strip()
            matchup = f'{home} vs {away}'
            if matchup not in matchups:
                matchups.append(matchup)
            if len(matchups) >= limit:
                return matchups
    return matchups


def extract_matchups_from_text(text):
    if not text:
        return []
    matchups = []
    for match in MATCHUP_REGEX.finditer(text):
        home = match.group(1).strip()
        away = match.group(2).strip()
        matchup = f'{home} vs {away}'
        if matchup not in matchups:
            matchups.append(matchup)
    return matchups


def normalize_matchup(text):
    return re.sub(r'\s+', ' ', text.strip().lower())


def contains_non_soccer_terms(text):
    if not text:
        return False
    lower = text.lower()
    return any(keyword in lower for keyword in NON_SOCCER_KEYWORDS)


def estimate_tip_count(matchups, max_words, hook_line, story_intro, cta_prompt, brand_explainer,
                       proof_line=None, time_lock_line=None, contrarian_line=None):
    if not matchups:
        return 0
    extra_lines = [proof_line, time_lock_line]
    if len(matchups) > 1 and contrarian_line:
        extra_lines.append(contrarian_line)
    overhead = sum(
        len(part.split())
        for part in (hook_line, story_intro, cta_prompt, brand_explainer, *extra_lines)
        if part
    )
    remaining = max_words - overhead
    if remaining <= 0:
        return 1
    count = 0
    for matchup in matchups[:3]:
        tip_words = len(matchup.split()) + 2 + 2 + 1 + 4  # label + line + because + reason
        if remaining - tip_words < 0:
            break
        remaining -= tip_words
        count += 1
    return max(1, count)


def validate_llm_voiceover(voiceover, allowed_matchups, tip_count,
                           required_phrases=None, required_labels=None):
    if not voiceover:
        return False
    if contains_non_soccer_terms(voiceover):
        return False
    found_matchups = extract_matchups_from_text(voiceover)
    if not allowed_matchups:
        if found_matchups:
            return False
    else:
        normalized_allowed = {normalize_matchup(m) for m in allowed_matchups}
        normalized_found = {normalize_matchup(m) for m in found_matchups}
        if not normalized_found:
            return False
        if not normalized_found.issubset(normalized_allowed):
            return False
        if tip_count and len(normalized_found) < min(tip_count, len(normalized_allowed)):
            return False
    required_because = max(1, tip_count or 0)
    if voiceover.lower().count('because') < required_because:
        return False
    required_lines = max(1, tip_count or 0)
    if voiceover.lower().count('line:') < required_lines:
        return False
    if required_phrases:
        lowered = voiceover.lower()
        for phrase in required_phrases:
            if phrase and phrase.lower() not in lowered:
                return False
    if required_labels:
        lowered = voiceover.lower()
        for label in required_labels:
            if label and label.lower() not in lowered:
                return False
    return True


def generate_story_with_llm(headlines, brand, cta_url, hashtags, max_words, hook,
                            matchups=None, story_intro=None, tip_count=None,
                            model_override=None, proof_line=None,
                            time_lock_line=None, contrarian_line=None,
                            cta_prompt=None):
    api_key, model = get_llm_config()
    if not api_key:
        return None, None
    if model_override:
        model = model_override

    headline_text = '\n'.join(f'- {title}' for title in headlines) if headlines else '- No headlines'
    matchups = matchups or []
    matchup_text = '\n'.join(f'- {matchup}' for matchup in matchups) if matchups else '- None found'
    if story_intro is None:
        story_intro = random.choice(STORY_INTROS)
    tip_count = tip_count or (min(3, len(matchups)) if matchups else 0)
    if tip_count <= 0:
        return None, None
    cta_prompt = cta_prompt or DEFAULT_CTA_PROMPT
    prompt_lines = [
        'Write a short, attention-grabbing soccer betting tips story for a vertical promo video.',
        'Make it feel viral: hook in the first line, short punchy sentences, and clear momentum.',
        'Use a simple story arc: hook -> tension/picks -> payoff/CTA.',
        'Mention this weekend or before kickoff.',
        f'Include exactly {tip_count} upcoming match tips (use the matchups list).',
        'Format each tip as: "Safe play: Team A vs Team B, line: TEAM A or draw (double chance), because REASON."',
        'Use labels Safe play, Bold pick, or Value watch.',
        'Include at least one Safe play and one Bold pick if you have 2+ tips.',
        'Each tip must include an explicit line pick after "line:" (moneyline, draw no bet, double chance,',
        'both teams to score, or over 2.5 goals).',
        'Explain why for each tip in a short clause (3-5 words). No stats.',
        f'Keep it under {max_words} words and make it sound energetic but clear.',
        'Use West African English flavor lightly (short phrases only).',
        'Do not promise guaranteed wins. No "lock" language.',
        'Avoid exact scorelines or margin predictions.',
        'Do not invent matchups; only use provided matchups or those in headlines.',
        'Do not mention the brand name or any URL; we will add the CTA.',
        'Avoid American football terms. Soccer only.',
        'Use plain ASCII punctuation only (no emoji).',
        'Start with this hook line verbatim.',
    ]
    if proof_line:
        prompt_lines.append(f'Include this proof line verbatim near the start: "{proof_line}"')
    if time_lock_line:
        prompt_lines.append(f'Include this time-lock line verbatim: "{time_lock_line}"')
    if contrarian_line:
        prompt_lines.append(f'Include this contrarian turn line verbatim: "{contrarian_line}"')
    prompt_lines.append(f'Include this CTA line verbatim: "{cta_prompt}"')
    prompt_lines.append(
        'Caption should be 1-2 sentences, include a comment prompt and urgency, and end with these hashtags exactly.'
    )
    prompt_lines.append('Return strict JSON with keys: voiceover, caption.')
    prompt_lines.append(f'Brand: {brand}')
    prompt_lines.append(f'Hook to use: {hook}')
    if story_intro:
        prompt_lines.append(f'Story beat to include: {story_intro}')
    prompt_lines.append(f'Matchups:\n{matchup_text}')
    prompt_lines.append(f'Headlines:\n{headline_text}')
    prompt_lines.append(f'Hashtags: {hashtags}')
    prompt = '\n'.join(prompt_lines)
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': 'You are a sports social media copywriter.'},
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.7,
        'max_tokens': 300,
    }
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    try:
        resp = requests.post('https://api.openai.com/v1/chat/completions',
                             json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f'Warning: LLM request failed: {exc}')
        return None, None

    data = resp.json()
    content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
    parsed = extract_json_blob(content)
    if not parsed:
        print('Warning: LLM response was not valid JSON.')
        return None, None

    voiceover = strip_emoji(str(parsed.get('voiceover', '')).strip())
    caption = strip_emoji(str(parsed.get('caption', '')).strip())
    voiceover = normalize_spoken_url(voiceover, cta_url)
    voiceover = strip_brand_mentions(voiceover, brand, cta_url)
    required_phrases = [hook, cta_prompt]
    if proof_line:
        required_phrases.append(proof_line)
    if time_lock_line:
        required_phrases.append(time_lock_line)
    if contrarian_line and tip_count >= 2:
        required_phrases.append(contrarian_line)
    required_labels = ['Safe play']
    if tip_count >= 2:
        required_labels.append('Bold pick')
    if not validate_llm_voiceover(
        voiceover,
        matchups,
        tip_count,
        required_phrases=required_phrases,
        required_labels=required_labels,
    ):
        print('Warning: LLM voiceover failed validation; falling back.')
        return None, None
    voiceover, tail = ensure_brand_explainer(voiceover, brand, cta_url)
    if cta_prompt:
        tail = f'{cta_prompt} {tail}'.strip() if tail else cta_prompt
    voiceover = clamp_with_tail(voiceover, max_words, tail)
    voiceover = normalize_ascii(voiceover)
    caption = normalize_ascii(caption)
    return voiceover or None, caption or None


def is_soccer_headline(title):
    lower = title.lower()
    for keyword in NON_SOCCER_KEYWORDS:
        if keyword in lower:
            return False
    if 'soccer' in lower:
        return True
    if any(keyword in lower for keyword in SOCCER_KEYWORDS):
        return True
    if 'football' in lower:
        return True
    return False


def fetch_headlines(sources, max_items):
    headlines = []
    seen = set()
    for url in sources:
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f'Warning: failed to fetch {url}: {exc}')
            continue

        soup = BeautifulSoup(resp.text, 'xml')
        for item in soup.find_all('item'):
            title_tag = item.find('title')
            if not title_tag:
                continue
            title = clean_title(title_tag.get_text(strip=True))
            if not title or title in seen:
                continue
            if not is_soccer_headline(title):
                continue
            seen.add(title)
            headlines.append(title)
            if len(headlines) >= max_items:
                return headlines
    return headlines


REASONS_BY_LABEL = {
    'Safe play': [
        'tempo stays high',
        'chance creation steady',
        'control edge should show',
        'matchup favors control',
    ],
    'Bold pick': [
        'press can force errors',
        'one moment can swing it',
        'space opens late',
        'upset path is there',
    ],
    'Value watch': [
        'line feels generous',
        'market still soft',
        'price looks wide',
        'number is a shade high',
    ],
}

LINE_TEMPLATES_BY_LABEL = {
    'Safe play': [
        '{team} or draw (double chance)',
        '{team} draw no bet',
        'Both teams to score (Yes)',
    ],
    'Bold pick': [
        '{team} moneyline',
        '{team} to win',
        'Over 2.5 goals',
    ],
    'Value watch': [
        '{team} or draw (double chance)',
        '{team} draw no bet',
        'Over 2.5 goals',
        'Both teams to score (Yes)',
    ],
}


def split_matchup(matchup):
    if not matchup:
        return None, None
    parts = re.split(r'\s+vs\.?\s+|\s+v\s+', matchup, flags=re.IGNORECASE)
    if len(parts) >= 2:
        return parts[0].strip(), parts[1].strip()
    return matchup.strip(), None


def pick_line(label, matchup, idx=0):
    templates = LINE_TEMPLATES_BY_LABEL.get(label, LINE_TEMPLATES_BY_LABEL['Safe play'])
    template = random.choice(templates)
    if '{team}' not in template:
        return template
    home, away = split_matchup(matchup)
    team = home or away or matchup
    if label == 'Bold pick' and away:
        team = away
    elif label != 'Bold pick' and home:
        team = home
    elif away and idx % 2 == 1:
        team = away
    return template.format(team=team)


def build_voiceover(headlines, brand, cta_url, hook=None, max_words=70, matchups=None,
                    story_intro=None, tip_count=None, fixtures=None,
                    proof_line=None, cta_prompt=None, time_lock_line=None,
                    contrarian_line=None):
    hook_line = pick_hook_line(hook, max_words)
    if story_intro is None:
        story_intro = random.choice(STORY_INTROS)
    brand_explainer = build_brand_explainer(brand, cta_url, include_url=True)
    proof_line = build_proof_line(proof_line)
    time_lock_line = time_lock_line or build_time_lock_line(fixtures)
    contrarian_line = contrarian_line or build_contrarian_line()

    if matchups is None:
        matchups = extract_matchups(headlines)

    cta_prompt = cta_prompt or DEFAULT_CTA_PROMPT
    tip_count = tip_count or estimate_tip_count(
        matchups,
        max_words,
        hook_line,
        story_intro,
        cta_prompt,
        brand_explainer,
        proof_line=proof_line,
        time_lock_line=time_lock_line,
        contrarian_line=contrarian_line,
    )
    if matchups and len(matchups) >= 2 and tip_count < 2 and story_intro:
        story_intro = None
        tip_count = estimate_tip_count(
            matchups,
            max_words,
            hook_line,
            story_intro,
            cta_prompt,
            brand_explainer,
            proof_line=proof_line,
            time_lock_line=time_lock_line,
            contrarian_line=contrarian_line,
        )
    if matchups:
        if len(matchups) >= 2 and tip_count < 2:
            tip_count = 2
        tip_count = min(len(matchups), max(1, tip_count))
    body_parts = []
    for line in (proof_line, time_lock_line, story_intro):
        if line:
            body_parts.append(line)
    if matchups:
        for idx, matchup in enumerate(matchups[:tip_count]):
            label = TIP_LABELS[idx % len(TIP_LABELS)]
            if idx == 1 and contrarian_line:
                body_parts.append(contrarian_line)
            pool = REASONS_BY_LABEL.get(label, REASONS_BY_LABEL['Safe play'])
            reason = random.choice(pool)
            line_pick = pick_line(label, matchup, idx)
            body_parts.append(f'{label}: {matchup}, line: {line_pick}, because {reason}.')
    elif headlines:
        short = shorten_text(headlines[0], 12)
        body_parts.append(f'Value watch: {short}, line: over 2.5 goals, because the market is reacting.')
    else:
        body_parts.append('Value watch: over 2.5 goals, because odds dey move.')

    tail = f'{cta_prompt} {brand_explainer}'.strip()
    body_parts = fit_body_parts(
        body_parts,
        hook_line,
        tail,
        max_words,
        optional_lines=[story_intro, proof_line, contrarian_line, time_lock_line],
    )
    body = ' '.join(body_parts).strip()
    voiceover_parts = [part for part in (hook_line, body, tail) if part]
    voiceover = ' '.join(voiceover_parts).strip()
    if len(voiceover.split()) > max_words:
        return clamp_with_tail(voiceover, max_words, tail)
    return voiceover


def build_caption(headlines, brand, cta_url, hashtags, matchups=None, fixtures=None):
    if matchups:
        short = matchups[0]
    else:
        short = headlines[0] if headlines else 'Soccer odds update'
    short = shorten_text(short, 12)
    urgency = 'before kickoff'
    if fixtures:
        day_part = format_day_part(fixtures[0].get('date'))
        if day_part:
            urgency = f'before {day_part} kickoff'
    template = random.choice(CAPTION_TEMPLATES)
    caption = template.format(headline=short, brand=brand, cta_url=cta_url, urgency=urgency)
    if random.random() < 0.8:
        caption = f'{caption} {random.choice(ENGAGEMENT_QUESTIONS)}'
    if hashtags:
        caption = f'{caption} {hashtags}'
    return caption.strip()


def generate_story(headlines, brand, cta_url, hashtags, max_words, hook=None,
                   use_llm=None, llm_model=None, matchups_override=None,
                   fixtures=None, proof_line=None, cta_prompt=None):
    api_key, _ = get_llm_config()
    if use_llm is None:
        use_llm = bool(api_key)

    fixtures = fixtures or []
    fixture_matchups = matchups_override or []
    if not fixture_matchups and fixtures:
        fixture_matchups = [
            fixture['matchup'] for fixture in fixtures if fixture.get('matchup')
        ]
    matchups = fixture_matchups if fixture_matchups else extract_matchups(headlines)
    if headlines:
        for matchup in extract_matchups(headlines):
            if matchup not in matchups:
                matchups.append(matchup)
    matchups = matchups[:3]
    headlines_for_llm = headlines if not fixture_matchups else []
    hook_line = pick_hook_line(hook, max_words)
    story_intro = '' if max_words <= 55 else random.choice(STORY_INTROS)
    proof_line = build_proof_line(proof_line)
    time_lock_line = build_time_lock_line(fixtures)
    contrarian_line = build_contrarian_line()
    cta_prompt = cta_prompt or DEFAULT_CTA_PROMPT
    brand_explainer = build_brand_explainer(brand, cta_url, include_url=True)
    tip_count = estimate_tip_count(
        matchups,
        max_words,
        hook_line,
        story_intro,
        cta_prompt,
        brand_explainer,
        proof_line=proof_line,
        time_lock_line=time_lock_line,
        contrarian_line=contrarian_line,
    )
    if matchups and len(matchups) >= 2 and tip_count < 2:
        tip_count = 2
    if tip_count <= 0:
        use_llm = False
    voiceover = None
    caption = None
    if use_llm:
        voiceover, caption = generate_story_with_llm(
            headlines_for_llm,
            brand,
            cta_url,
            hashtags,
            max_words,
            hook_line,
            matchups=matchups,
            story_intro=story_intro,
            tip_count=tip_count,
            model_override=llm_model,
            proof_line=proof_line,
            time_lock_line=time_lock_line,
            contrarian_line=contrarian_line,
            cta_prompt=cta_prompt,
        )

    if not voiceover:
        voiceover = build_voiceover(
            headlines,
            brand,
            cta_url,
            hook=hook_line,
            max_words=max_words,
            matchups=matchups,
            story_intro=story_intro,
            tip_count=tip_count,
            fixtures=fixtures,
            proof_line=proof_line,
            time_lock_line=time_lock_line,
            contrarian_line=contrarian_line,
            cta_prompt=cta_prompt,
        )
    if not caption:
        caption = build_caption(
            headlines,
            brand,
            cta_url,
            hashtags,
            matchups=matchups,
            fixtures=fixtures,
        )

    voiceover = normalize_ascii(voiceover)
    caption = normalize_ascii(caption)
    return voiceover, caption


def main():
    parser = argparse.ArgumentParser(description='Generate a weekly betting-news voiceover script.')
    parser.add_argument('--source', action='append', help='RSS feed URL (repeatable)')
    parser.add_argument('--max-items', type=int, default=4)
    parser.add_argument('--brand', default='OddsWize')
    parser.add_argument('--cta-url', default='https://oddswize.com/odds?ref=promo_auto')
    parser.add_argument('--out', default='promotions/output/weekly_voiceover.txt')
    parser.add_argument('--caption-out', default='promotions/output/weekly_caption.txt')
    parser.add_argument('--hashtags', default=DEFAULT_HASHTAGS)
    parser.add_argument('--hook', help='Optional hook line for the voiceover')
    parser.add_argument('--max-words', type=int, default=70)
    parser.add_argument('--fixtures', dest='use_fixtures', action='store_true',
                        help='Use upcoming fixtures from ESPN')
    parser.add_argument('--no-fixtures', dest='use_fixtures', action='store_false',
                        help='Disable fixture lookup')
    parser.set_defaults(use_fixtures=True)
    parser.add_argument('--fixtures-days', type=int, default=DEFAULT_FIXTURE_DAYS)
    parser.add_argument('--fixtures-limit', type=int, default=DEFAULT_FIXTURE_LIMIT)
    parser.add_argument('--fixture-league', action='append',
                        help='ESPN league id to include (repeatable)')
    parser.add_argument('--llm', dest='use_llm', action='store_true',
                        help='Use an LLM to craft the story and caption')
    parser.add_argument('--no-llm', dest='use_llm', action='store_false',
                        help='Disable LLM story generation')
    parser.set_defaults(use_llm=None)
    parser.add_argument('--llm-model', help='Override the LLM model name')
    parser.add_argument('--proof-line', help='Optional proof/receipts line for the voiceover')

    args = parser.parse_args()

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

    voiceover, caption = generate_story(
        headlines,
        args.brand,
        args.cta_url,
        args.hashtags,
        args.max_words,
        hook=args.hook,
        use_llm=args.use_llm,
        llm_model=args.llm_model,
        fixtures=fixtures,
        proof_line=args.proof_line,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(voiceover, encoding='utf-8')

    caption_path = Path(args.caption_out)
    caption_path.parent.mkdir(parents=True, exist_ok=True)
    caption_path.write_text(caption, encoding='utf-8')

    print(f'Wrote voiceover to {out_path}')
    print(f'Wrote caption to {caption_path}')


if __name__ == '__main__':
    main()
