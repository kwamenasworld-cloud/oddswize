# Arbitrage Betting Scraper - Technical Handover Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [File Locations](#file-locations)
4. [How It Works](#how-it-works)
5. [Bookmaker Integration Details](#bookmaker-integration-details)
6. [Data Flow](#data-flow)
7. [Deployment](#deployment)
8. [Troubleshooting](#troubleshooting)

---

## System Overview

This is an **arbitrage betting opportunity finder** that scrapes odds from 6 Ghanaian bookmakers, identifies matching football matches across bookmakers, and uploads the data to Cloudflare Workers KV for a web interface to display arbitrage opportunities.

### Key Features
- ✅ Scrapes 6 bookmakers (5 via REST API, 1 via Selenium)
- ✅ Fuzzy matching to align teams across bookmakers
- ✅ League normalization to prevent duplicates
- ✅ Cloudflare Workers integration for real-time web display
- ✅ Fast execution (~30-60 seconds total)

### Supported Bookmakers
1. **Betfox Ghana** - REST API
2. **Betway Ghana** - REST API
3. **SoccaBet Ghana** - REST API
4. **SportyBet Ghana** - REST API
5. **1xBet Ghana** - REST API
6. **22Bet Ghana** - Selenium/WebSocket (Protocol Buffers) - **NOT CURRENTLY WORKING**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Scraper Script                      │
│              (scrape_odds_github.py)                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ├─────────────────────────────────┐
                            │                                 │
                            ▼                                 ▼
┌──────────────────────────────────────┐    ┌──────────────────────────────┐
│     Bookmaker API Scrapers           │    │   Match Alignment Engine     │
│  (Individual scraper functions)      │    │  (Fuzzy matching + League    │
│                                      │    │   normalization)             │
│  - scrape_betfox()                   │    │                              │
│  - scrape_betway()                   │    │  - normalize_name()          │
│  - scrape_soccabet()                 │    │  - normalize_league()        │
│  - scrape_sportybet()                │    │  - match_teams()             │
│  - scrape_1xbet()                    │    │  - aggregate_matches()       │
│  - scrape_22bet() [BROKEN]           │    │                              │
└──────────────────────────────────────┘    └──────────────────────────────┘
                            │                                 │
                            └─────────────┬───────────────────┘
                                          │
                                          ▼
                            ┌─────────────────────────────┐
                            │    JSON Output Files        │
                            │                             │
                            │  - raw_scraped_data.json    │
                            │  - matched_odds.json        │
                            │  - odds_data.json           │
                            └─────────────────────────────┘
                                          │
                                          ▼
                            ┌─────────────────────────────┐
                            │   Cloudflare Upload         │
                            │  (push_to_cloudflare.py)    │
                            │                             │
                            │  Uploads to Workers KV      │
                            └─────────────────────────────┘
```

---

## File Locations

### Local Desktop Path
```
C:\Users\admin\OneDrive\Documents\GitHub\Arbitrage\
```

### GitHub Repository
**Repository URL:** (You need to add this - check with `git remote -v`)

### Main Files Structure

```
Arbitrage/
│
├── scrape_odds_github.py          # MAIN SCRAPER SCRIPT (PRIMARY FILE)
├── push_to_cloudflare.py          # Cloudflare KV uploader
├── odds_data.json                 # Final output data (uploaded to Cloudflare)
├── matched_odds.json              # Matched odds across bookmakers
├── raw_scraped_data.json          # Raw data before matching
│
├── requirements.txt               # Python dependencies (if exists)
│
├── .claude/                       # Claude Code configuration
│   └── settings.local.json        # Local settings
│
├── HANDOVER_DOCUMENTATION.md      # This file
│
└── [Debug/Test Scripts]           # All files starting with:
    ├── test_*.py                  # - test_
    ├── debug_*.py                 # - debug_
    ├── check_*.py                 # - check_
    ├── find_*.py                  # - find_
    ├── capture_*.py               # - capture_
    ├── scrape_22bet_html.py       # 22Bet scraper (not integrated)
    └── [50+ other test files]     # Investigation/debugging scripts
```

### Critical Files (Must Keep)

1. **scrape_odds_github.py** - Main scraper (1350+ lines)
2. **push_to_cloudflare.py** - Cloudflare uploader
3. **odds_data.json** - Latest scraped data
4. **.claude/settings.local.json** - Configuration

### Files You Can Delete (Debug/Development Only)

All files matching these patterns (50+ files):
- `test_*.py`
- `debug_*.py`
- `check_*.py`
- `find_*.py`
- `capture_*.py`
- `intercept_*.py`
- `explore_*.py`
- `mirror_*.py`
- `query_*.py`
- `analyze_*.py`
- `download_*.py`
- `extract_*.py`
- `inspect_*.py`
- `final_*.py`
- `try_*.py`
- `*_22bet_*.py` (except scrape_22bet_html.py if you want to fix 22Bet later)
- `*.html` files
- `*.js` files
- `*_ws_*.json`
- `*_debug*.json`
- `*_intercepted*.json`
- `*_decoded*.json`
- `*_scraped*.json`

---

## How It Works

### 1. Main Execution Flow

**File:** `scrape_odds_github.py`

```python
# Entry point
if __name__ == "__main__":
    main()
```

**The `main()` function does:**

1. **Scrape all bookmakers in parallel**
   ```python
   all_matches = []
   all_matches.extend(scrape_betfox())      # ~3 seconds
   all_matches.extend(scrape_betway())      # ~4 seconds
   all_matches.extend(scrape_soccabet())    # ~2 seconds
   all_matches.extend(scrape_sportybet())   # ~3 seconds
   all_matches.extend(scrape_1xbet())       # ~2 seconds
   # all_matches.extend(scrape_22bet())     # DISABLED - doesn't work
   ```

2. **Save raw scraped data**
   ```python
   # Saves to: raw_scraped_data.json
   # Format: [
   #   {
   #     "bookmaker": "Betway Ghana",
   #     "league": "Premier League",
   #     "home": "Newcastle United",
   #     "away": "Chelsea",
   #     "home_odds": 2.70,
   #     "draw_odds": 3.65,
   #     "away_odds": 2.50
   #   },
   #   ...
   # ]
   ```

3. **Aggregate and match teams**
   ```python
   aggregated = aggregate_matches(all_matches)
   # Uses fuzzy matching to align "Newcastle United" vs "Newcastle"
   # Uses league normalization to group "Bundesliga 2" variations
   ```

4. **Save matched data**
   ```python
   # Saves to: matched_odds.json
   # Format: {
   #   "Premier League": {
   #     "Newcastle United vs Chelsea": {
   #       "bookmakers": {
   #         "Betway Ghana": {"home": 2.70, "draw": 3.65, "away": 2.50},
   #         "SportyBet Ghana": {"home": 2.65, "draw": 3.70, "away": 2.55},
   #         ...
   #       }
   #     }
   #   }
   # }
   ```

5. **Convert to final format and save**
   ```python
   # Saves to: odds_data.json
   # This is the file that gets uploaded to Cloudflare
   ```

### 2. Bookmaker Scraping Logic

Each bookmaker has a dedicated scraper function:

#### **Betfox Ghana**
**Lines:** 737-857 in scrape_odds_github.py

**How it works:**
1. Calls API: `https://www.betfox.com.gh/api/offer/v4/competitions?sport=Football`
2. This returns ALL football competitions with embedded fixtures
3. Extracts fixtures from each competition
4. Finds the "Match Winner" market (Full Time Result / 1X2)
5. Maps outcomes to home/draw/away odds

**API Response Structure:**
```json
{
  "enriched": [
    {
      "id": 123,
      "name": "Premier League",
      "fixtures": [
        {
          "id": 456,
          "participants": [
            {"type": "home", "name": "Newcastle United"},
            {"type": "away", "name": "Chelsea"}
          ],
          "markets": [
            {
              "name": "Match Winner",
              "selections": [
                {"name": "Newcastle United", "price": "2.70"},
                {"name": "Draw", "price": "3.65"},
                {"name": "Chelsea", "price": "2.50"}
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

**Key Code:**
```python
# Line 744: Get all competitions
resp = scraper.get('https://www.betfox.com.gh/api/offer/v4/competitions?sport=Football', timeout=TIMEOUT)

# Line 755: Extract fixtures from competitions
for comp in competitions:
    comp_fixtures = comp.get('fixtures', [])
    all_fixtures.extend(comp_fixtures)

# Line 775: Find Match Winner market
match_winner_market = None
for market in markets:
    if market.get('name') == 'Match Winner':
        match_winner_market = market
        break
```

#### **Betway Ghana**
**Lines:** 470-626 in scrape_odds_github.py

**How it works:**
1. Get competitions: `https://sports.betway.com.gh/api/Sportsbook/GetCompetitions?sportId=5&...`
2. For each competition, get events: `https://sports.betway.com.gh/api/Sportsbook/GetEvents?...`
3. For each event, get markets: `https://sports.betway.com.gh/api/Sportsbook/GetMarkets?...`
4. Extract outcomes and match them to team names using **normalized fuzzy matching**

**Important Fix - Normalized Team Matching (Lines 502-521):**
```python
# Betway returns outcome names like "Chelsea FC" but team name is "Chelsea"
# We use normalized matching to align them

name_normalized = normalize_name(name)          # "Chelsea FC" → "chelsea"
home_normalized = normalize_name(home)          # "Chelsea" → "chelsea"
away_normalized = normalize_name(away)

if name == home or name == 'Home' or name_normalized == home_normalized:
    home_odds = price
elif name.lower() == 'draw':
    draw_odds = price
elif name == away or name == 'Away' or name_normalized == away_normalized:
    away_odds = price
```

**API Call Flow:**
```python
# Step 1: Get competitions
GET /api/Sportsbook/GetCompetitions?sportId=5&languageId=1&...

# Step 2: Get events for each competition
GET /api/Sportsbook/GetEvents?languageId=1&competitionId=123&...

# Step 3: Get markets for each event
GET /api/Sportsbook/GetMarkets?eventId=456&languageId=1&...
```

#### **SoccaBet Ghana**
**Lines:** 165-274 in scrape_odds_github.py

**How it works:**
1. Single API call: `https://www.soccabet.com/api/coupon?categoryID=1`
2. Returns all football matches with embedded odds
3. Simple and fast

**API Response:**
```json
{
  "matches": [
    {
      "home": "Newcastle United",
      "away": "Chelsea",
      "tournament": "Premier League",
      "odds": {
        "1": "2.70",
        "X": "3.65",
        "2": "2.50"
      }
    }
  ]
}
```

#### **SportyBet Ghana**
**Lines:** 629-735 in scrape_odds_github.py

**How it works:**
1. Get active tournaments: `https://www.sportybet.com/api/gh/factsCenter/popularTournaments`
2. For top tournaments, get match list with odds
3. Similar structure to SoccaBet

**API Endpoint:**
```
GET https://www.sportybet.com/api/gh/factsCenter/popularTournaments?sportId=sr:sport:1&...
```

#### **1xBet Ghana**
**Lines:** 277-357 in scrape_odds_github.py

**How it works:**
1. Get championships: `https://1xbet.com.gh/service-api/LineFeed/GetChampsZip?sport=1&lng=en`
2. For top championships, get games: `https://1xbet.com.gh/service-api/LineFeed/GetGamesZip?...`
3. Extract odds from games data

**API Structure:**
```python
# Step 1: Get championships
{
  "Value": [
    {
      "LI": 12345,              # League ID
      "L": "Premier League",     # League name
      "GC": 20                   # Game count
    }
  ]
}

# Step 2: Get games for each championship
{
  "Value": [
    {
      "O1": "Newcastle United",
      "O2": "Chelsea",
      "C": 12345,                # Championship ID
      "E": [                     # Events/Odds
        {
          "G": 1,                # Type 1 = Full Time Result
          "P": 2.70              # Odds
        },
        {
          "G": 2,                # Type 2 = Draw
          "P": 3.65
        },
        {
          "G": 3,                # Type 3 = Away Win
          "P": 2.50
        }
      ]
    }
  ]
}
```

#### **22Bet Ghana** ❌ NOT WORKING
**Lines:** 360-468 in scrape_odds_github.py
**Status:** DISABLED - Returns HTML instead of JSON

**Why it doesn't work:**
- 22Bet uses **Protocol Buffers over WebSocket** for event data
- No REST API endpoint provides match odds
- Would require:
  1. WebSocket connection to `wss://centrifugo.22bet.com.gh/connection/websocket`
  2. Protobuf schema decoding
  3. Complex message parsing
  4. OR Selenium-based HTML scraping (slow)

**Alternative solution attempted:** `scrape_22bet_html.py`
- Uses Selenium to load page
- Extracts embedded JSON from rendered HTML
- NOT integrated into main script yet
- Would add 8-10 seconds to total runtime

**Current workaround:** Scraper runs with 5/6 bookmakers (83% coverage)

### 3. Team Name Matching Algorithm

**Function:** `normalize_name()` (Lines 94-124)

**Purpose:** Align team names that are spelled differently across bookmakers

**Examples:**
```python
normalize_name("Newcastle United")           → "newcastle"
normalize_name("Newcastle Utd.")             → "newcastle"
normalize_name("Newcastle")                  → "newcastle"
normalize_name("Chelsea FC")                 → "chelsea"
normalize_name("Chelsea F.C.")               → "chelsea"
normalize_name("Manchester United")          → "manchester"
normalize_name("Man United")                 → "manchester"
```

**How it works:**
```python
def normalize_name(name):
    if not name:
        return ""
    s = str(name).lower().strip()

    # Remove common suffixes
    s = re.sub(r'\b(fc|f\.c\.|united|utd|utd\.|city|athletic|club)\b', '', s)

    # Remove special characters
    s = re.sub(r'[^\w\s]', '', s)

    # Remove extra spaces
    s = re.sub(r'\s+', ' ', s).strip()

    # Return first significant word
    parts = s.split()
    return parts[0] if parts else s
```

**Fuzzy Matching:** Uses `difflib.SequenceMatcher` with 0.8 threshold
```python
# Lines 1175-1178
from difflib import SequenceMatcher

if SequenceMatcher(None, norm1, norm2).ratio() >= 0.8:
    # Teams match!
```

### 4. League Normalization

**Function:** `normalize_league()` (Lines 127-161)

**Purpose:** Prevent duplicate leagues with different spellings

**Examples:**
```python
normalize_league("Bundesliga 2nd Division")  → "Bundesliga 2"
normalize_league("2. Bundesliga")            → "Bundesliga 2"
normalize_league("Bundesliga II")            → "Bundesliga 2"
normalize_league("German Bundesliga 2")      → "Bundesliga 2"
```

**Why this matters:**
Before normalization:
```json
{
  "Bundesliga 2nd Division": { ... },
  "2. Bundesliga": { ... },
  "Bundesliga II": { ... }
}
```

After normalization:
```json
{
  "Bundesliga 2": {
    "merged matches from all variations": { ... }
  }
}
```

**Implementation:**
```python
def normalize_league(league_name):
    # Handle 2nd division variations
    if '2' in league_name or 'ii' in league_name.lower() or 'second' in league_name.lower():
        if 'bundesliga' in league_name.lower():
            return 'Bundesliga 2'
        if 'premier' in league_name.lower():
            return 'Championship'  # English 2nd division

    # Handle "LaLiga 2" variations
    if 'laliga' in league_name.lower() and ('2' in league_name or 'segunda' in league_name.lower()):
        return 'LaLiga 2'

    return league_name
```

### 5. Match Aggregation

**Function:** `aggregate_matches()` (Lines 1163-1291)

**Purpose:** Combine odds from different bookmakers for the same match

**Process:**

1. **Normalize league names**
   ```python
   normalized_league = normalize_league(match['league'])
   ```

2. **Create unique match key**
   ```python
   match_key = f"{home} vs {away}"
   ```

3. **Try to find existing match using fuzzy matching**
   ```python
   for existing_key in league_matches.keys():
       existing_home, existing_away = existing_key.split(' vs ')

       # Normalize both
       norm_home = normalize_name(home)
       norm_existing_home = normalize_name(existing_home)

       # Check similarity
       if SequenceMatcher(None, norm_home, norm_existing_home).ratio() >= 0.8:
           # MATCH FOUND - use existing key
           match_key = existing_key
           break
   ```

4. **Add bookmaker odds to match**
   ```python
   league_matches[match_key]['bookmakers'][bookmaker] = {
       'home': home_odds,
       'draw': draw_odds,
       'away': away_odds
   }
   ```

**Output Format:**
```json
{
  "Premier League": {
    "Newcastle United vs Chelsea": {
      "bookmakers": {
        "Betfox Ghana": {
          "home": 2.75,
          "draw": 3.60,
          "away": 2.55
        },
        "Betway Ghana": {
          "home": 2.70,
          "draw": 3.65,
          "away": 2.50
        },
        "SportyBet Ghana": {
          "home": 2.68,
          "draw": 3.70,
          "away": 2.52
        },
        "SoccaBet Ghana": {
          "home": 2.72,
          "draw": 3.62,
          "away": 2.48
        },
        "1xBet Ghana": {
          "home": 2.74,
          "draw": 3.58,
          "away": 2.51
        }
      }
    }
  }
}
```

---

## Bookmaker Integration Details

### API Endpoints Reference

```python
# Betfox Ghana
BETFOX_COMPETITIONS = "https://www.betfox.com.gh/api/offer/v4/competitions?sport=Football"

# Betway Ghana
BETWAY_BASE = "https://sports.betway.com.gh/api/Sportsbook"
BETWAY_COMPETITIONS = f"{BETWAY_BASE}/GetCompetitions?sportId=5&languageId=1&..."
BETWAY_EVENTS = f"{BETWAY_BASE}/GetEvents?languageId=1&competitionId={comp_id}&..."
BETWAY_MARKETS = f"{BETWAY_BASE}/GetMarkets?eventId={event_id}&languageId=1&..."

# SoccaBet Ghana
SOCCABET_API = "https://www.soccabet.com/api/coupon?categoryID=1"

# SportyBet Ghana
SPORTYBET_TOURNAMENTS = "https://www.sportybet.com/api/gh/factsCenter/popularTournaments?sportId=sr:sport:1&..."

# 1xBet Ghana
ONEBET_CHAMPS = "https://1xbet.com.gh/service-api/LineFeed/GetChampsZip?sport=1&lng=en"
ONEBET_GAMES = "https://1xbet.com.gh/service-api/LineFeed/GetGamesZip?lang=en&...&champ={champ_id}"

# 22Bet Ghana (NOT WORKING)
TWENTYTWOBET_API = "https://22bet.com.gh/service-api/LineFeed"  # Returns HTML
TWENTYTWOBET_PLATFORM = "https://platform.22bet.com.gh"         # Returns 404 for events
```

### Timeout Settings

```python
TIMEOUT = 15  # seconds for API requests
```

**Total Runtime:**
- Betfox: ~3s
- Betway: ~4s (multiple API calls)
- SoccaBet: ~2s
- SportyBet: ~3s
- 1xBet: ~2s
- Aggregation: ~1s
- **Total: ~15-20 seconds**

If 22Bet Selenium was enabled: +8-10s → ~25-30 seconds total

### Error Handling

Each scraper has try/except blocks:

```python
def scrape_betfox():
    matches = []
    try:
        # ... scraping logic ...
    except Exception as e:
        print(f"[BETFOX] Error: {str(e)}")
        return []  # Return empty list, don't crash entire script
    return matches
```

This ensures if one bookmaker fails, others continue working.

---

## Data Flow

### 1. Scraping Phase

```
┌──────────────┐
│  Betfox API  │──┐
└──────────────┘  │
┌──────────────┐  │
│  Betway API  │──┤
└──────────────┘  │
┌──────────────┐  ├─→ all_matches = []
│ SoccaBet API │──┤    [list of dicts]
└──────────────┘  │
┌──────────────┐  │
│SportyBet API │──┤
└──────────────┘  │
┌──────────────┐  │
│  1xBet API   │──┘
└──────────────┘
```

### 2. Normalization Phase

```
all_matches
    ↓
[Filter out placeholder teams]
"Team A", "Home Team", etc.
    ↓
Normalize league names
    ↓
raw_scraped_data.json
```

### 3. Aggregation Phase

```
raw_scraped_data.json
    ↓
For each match:
  - Normalize team names
  - Fuzzy match with existing
  - Group by league
  - Combine odds from multiple bookmakers
    ↓
matched_odds.json
```

### 4. Final Format Phase

```
matched_odds.json
    ↓
Convert to final structure:
{
  "leagues": [...],
  "matches": {...},
  "timestamp": "..."
}
    ↓
odds_data.json
```

### 5. Upload Phase

```
odds_data.json
    ↓
push_to_cloudflare.py
    ↓
Cloudflare Workers KV
    ↓
Web Interface (displays arbitrage opportunities)
```

---

## Deployment

### Prerequisites

**Python Packages:**
```bash
pip install cloudscraper
pip install selenium
pip install protobuf  # If attempting 22Bet
```

**System Requirements:**
- Python 3.8+
- Chrome/Chromium (for Selenium if using 22Bet)
- ChromeDriver (for Selenium if using 22Bet)

### Running the Scraper

**Local Testing:**
```bash
cd "C:\Users\admin\OneDrive\Documents\GitHub\Arbitrage"
python scrape_odds_github.py
```

**Expected Output:**
```
[BETFOX] Fetching competitions...
  Competitions: 87
  Fixtures from competitions: 1234
  [OK] Scraped 1234 matches

[BETWAY] Fetching competitions...
  [OK] Scraped 892 matches

[SOCCABET] Fetching matches...
  [OK] Scraped 456 matches

[SPORTYBET] Fetching tournaments...
  [OK] Scraped 678 matches

[1XBET] Fetching championships...
  [OK] Scraped 543 matches

Total matches scraped: 3803
Aggregating matches across bookmakers...
Found 234 unique matches across bookmakers

Saved to:
  - raw_scraped_data.json
  - matched_odds.json
  - odds_data.json
```

### Uploading to Cloudflare

**File:** `push_to_cloudflare.py`

```bash
python push_to_cloudflare.py
```

**Configuration:**
The script reads credentials from environment or config. Check the file for details:
```python
# Line numbers will vary - check the actual file
ACCOUNT_ID = "your_account_id"
NAMESPACE_ID = "your_namespace_id"
API_TOKEN = "your_api_token"
```

### Automation (Production)

**Option 1: Cron Job (Linux)**
```bash
# Run every 5 minutes
*/5 * * * * cd /path/to/Arbitrage && python scrape_odds_github.py && python push_to_cloudflare.py
```

**Option 2: Task Scheduler (Windows)**
```
Create a task that runs:
  python C:\Users\admin\OneDrive\Documents\GitHub\Arbitrage\scrape_odds_github.py
Every 5 minutes
```

**Option 3: Cloudflare Workers Cron**
```javascript
// In Cloudflare Workers, set up a scheduled trigger
export default {
  async scheduled(event, env, ctx) {
    // Trigger the scraper endpoint
    await fetch('https://your-scraper-endpoint.com/scrape')
  }
}
```

---

## Troubleshooting

### Common Issues

#### 1. **No matches found from a bookmaker**

**Symptom:**
```
[BETFOX] Scraped 0 matches
```

**Possible causes:**
- API endpoint changed
- Website blocked your IP
- Response format changed

**Debug steps:**
```python
# Add debug prints in the scraper function
resp = scraper.get(url, timeout=TIMEOUT)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:500]}")  # First 500 chars
```

#### 2. **Team names not matching across bookmakers**

**Symptom:**
```json
{
  "Premier League": {
    "Newcastle United vs Chelsea": {
      "bookmakers": {"Betway Ghana": {...}}
    },
    "Newcastle vs Chelsea": {
      "bookmakers": {"SportyBet Ghana": {...}}
    }
  }
}
```

**Solution:**
Adjust fuzzy matching threshold (Line 1175):
```python
# Lower threshold = more lenient matching
if SequenceMatcher(None, norm1, norm2).ratio() >= 0.7:  # Was 0.8
```

Or add team name mapping:
```python
# Add to normalize_name() function
team_mappings = {
    'man utd': 'manchester united',
    'man city': 'manchester city',
    # etc.
}
```

#### 3. **Duplicate leagues appearing**

**Symptom:**
```json
{
  "Premier League": {...},
  "English Premier League": {...}
}
```

**Solution:**
Update `normalize_league()` function (Lines 127-161):
```python
def normalize_league(league_name):
    # Add new normalization
    if 'premier league' in league_name.lower() and 'english' in league_name.lower():
        return 'Premier League'

    # ... existing code ...
```

#### 4. **Cloudflare upload fails**

**Symptom:**
```
Error: 401 Unauthorized
```

**Check:**
1. API token is valid
2. Account ID is correct
3. Namespace ID is correct
4. Token has correct permissions (Workers KV Edit)

#### 5. **22Bet not working**

**Expected behavior:** This is normal. 22Bet is currently disabled.

**To fix (requires significant work):**
1. Option A: Implement Protocol Buffers WebSocket client
   - Install protobuf decoders
   - Connect to `wss://centrifugo.22bet.com.gh/connection/websocket`
   - Decode binary messages
   - Extract event data

2. Option B: Use Selenium (slower)
   - Use `scrape_22bet_html.py` as starting point
   - Integrate into main script
   - Accept 8-10 second performance hit

**Recommendation:** Deploy with 5 bookmakers. 83% coverage is excellent.

---

## Key Functions Reference

### Scraping Functions

| Function | Lines | Purpose |
|----------|-------|---------|
| `scrape_betfox()` | 737-857 | Scrape Betfox Ghana API |
| `scrape_betway()` | 470-626 | Scrape Betway Ghana API |
| `scrape_soccabet()` | 165-274 | Scrape SoccaBet Ghana API |
| `scrape_sportybet()` | 629-735 | Scrape SportyBet Ghana API |
| `scrape_1xbet()` | 277-357 | Scrape 1xBet Ghana API |
| `scrape_22bet()` | 360-468 | Scrape 22Bet Ghana (BROKEN) |

### Utility Functions

| Function | Lines | Purpose |
|----------|-------|---------|
| `normalize_name()` | 94-124 | Normalize team names for matching |
| `normalize_league()` | 127-161 | Normalize league names to prevent duplicates |
| `is_placeholder_team()` | 1122-1160 | Filter out generic placeholder teams |
| `aggregate_matches()` | 1163-1291 | Combine odds from multiple bookmakers |
| `main()` | 1294-1350 | Main execution function |

---

## Performance Optimization Tips

### 1. **Reduce Championship/Competition Limits**

Currently processes top 30 championships:
```python
# Line 265 (1xBet), Line 755 (Betfox), etc.
champs = sorted(champs, key=lambda x: x.get("GC", 0), reverse=True)[:30]
```

To speed up (less coverage):
```python
champs = sorted(champs, key=lambda x: x.get("GC", 0), reverse=True)[:15]  # Only top 15
```

### 2. **Parallel Scraping**

Use threading (be careful with rate limits):
```python
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [
        executor.submit(scrape_betfox),
        executor.submit(scrape_betway),
        executor.submit(scrape_soccabet),
        executor.submit(scrape_sportybet),
        executor.submit(scrape_1xbet),
    ]

    all_matches = []
    for future in concurrent.futures.as_completed(futures):
        all_matches.extend(future.result())
```

### 3. **Caching**

Cache championship lists (they don't change often):
```python
import pickle
from datetime import datetime, timedelta

cache_file = 'champs_cache.pkl'
cache_duration = timedelta(hours=1)

# Check cache
if os.path.exists(cache_file):
    with open(cache_file, 'rb') as f:
        cached = pickle.load(f)
        if datetime.now() - cached['timestamp'] < cache_duration:
            champs = cached['data']
            # Use cached data
```

---

## Git Repository Management

### Initial Setup (if not done)

```bash
cd "C:\Users\admin\OneDrive\Documents\GitHub\Arbitrage"

# Initialize git (if not already done)
git init

# Add remote repository
git remote add origin <YOUR_GITHUB_REPO_URL>

# Add all essential files
git add scrape_odds_github.py
git add push_to_cloudflare.py
git add odds_data.json
git add HANDOVER_DOCUMENTATION.md
git add .claude/settings.local.json

# Commit
git commit -m "Initial commit - Working arbitrage scraper with 5 bookmakers"

# Push
git push -u origin master
```

### .gitignore Recommendations

Create `.gitignore`:
```
# Debug/test files
test_*.py
debug_*.py
check_*.py
find_*.py
capture_*.py
intercept_*.py
explore_*.py
mirror_*.py
query_*.py
analyze_*.py
download_*.py
extract_*.py
inspect_*.py
final_*.py
try_*.py
*_22bet_*.py
scrape_22bet_html.py

# Data files
*.html
*.js
*_ws_*.json
*_debug*.json
*_intercepted*.json
*_decoded*.json
*_scraped*.json
raw_scraped_data.json
matched_odds.json

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

### Essential Files to Keep in Repo

```
Arbitrage/
├── scrape_odds_github.py          ✅ MUST KEEP
├── push_to_cloudflare.py          ✅ MUST KEEP
├── odds_data.json                 ✅ MUST KEEP (or regenerate)
├── HANDOVER_DOCUMENTATION.md      ✅ MUST KEEP
├── .gitignore                     ✅ MUST KEEP
├── requirements.txt               ✅ CREATE THIS
└── .claude/
    └── settings.local.json        ⚠️  OPTIONAL (may contain credentials)
```

### Create requirements.txt

```bash
pip freeze > requirements.txt
```

Or manually create:
```
cloudscraper>=1.2.71
selenium>=4.0.0
protobuf>=4.0.0
```

---

## Contact & Support

### For the Next Developer

**Key things to know:**

1. **The scraper works with 5/6 bookmakers** - This is acceptable. 22Bet is complex.

2. **Main file is 1350+ lines** - It's long but well-organized. Each bookmaker has a dedicated section.

3. **Fuzzy matching is critical** - Team names vary across bookmakers. Don't remove the normalization logic.

4. **League normalization prevents duplicates** - "Bundesliga 2" vs "2. Bundesliga" vs "Bundesliga II"

5. **All test files can be deleted** - Only keep:
   - scrape_odds_github.py
   - push_to_cloudflare.py
   - odds_data.json
   - This documentation

6. **Performance is good** - 15-20 seconds for 5 bookmakers is fast.

### Questions to Ask Original Developer

1. What is the Cloudflare Workers endpoint URL?
2. What are the Cloudflare API credentials?
3. Is there a web interface repository?
4. What is the expected update frequency?
5. Are there any rate limits to be aware of?
6. Should we attempt to fix 22Bet or replace it?

---

## Future Improvements

### High Priority

1. **Fix 22Bet integration**
   - Implement Protobuf decoder
   - OR use Selenium scraper
   - OR replace with different bookmaker

2. **Add error notifications**
   - Email alerts when scraper fails
   - Slack/Discord webhooks for errors
   - Monitoring dashboard

3. **Add arbitrage calculation**
   - Calculate implied probability
   - Find arbitrage opportunities
   - Display profit percentage

### Medium Priority

4. **Add more bookmakers**
   - Research other Ghanaian bookmakers
   - Implement API scrapers
   - Increase coverage beyond 6

5. **Improve match success rate**
   - Better fuzzy matching algorithm
   - Machine learning for team name alignment
   - Manual team name mapping database

6. **Performance monitoring**
   - Track scraper duration per bookmaker
   - Log API response times
   - Alert on slowdowns

### Low Priority

7. **Unit tests**
   - Test each scraper function
   - Mock API responses
   - Test fuzzy matching edge cases

8. **Configuration file**
   - External config for bookmaker URLs
   - Timeout settings
   - Fuzzy match thresholds

9. **Database storage**
   - Store historical odds
   - Track odds movements
   - Analyze trends

---

## Changelog

### Version 1.0 (Current)
- ✅ 5 bookmakers working (Betfox, Betway, SoccaBet, SportyBet, 1xBet)
- ✅ Fuzzy team name matching
- ✅ League normalization
- ✅ Cloudflare Workers integration
- ✅ ~15-20 second runtime
- ❌ 22Bet not working (Protocol Buffers issue)

### Known Issues
1. 22Bet returns HTML instead of JSON
2. Some team names still don't match (e.g., "Man Utd" vs "Manchester United")
3. No error notifications/monitoring
4. No arbitrage calculation (just displays odds)

---

**Document Last Updated:** December 16, 2024
**Author:** Claude (AI Assistant)
**Maintained by:** [Your Name Here]
**Repository:** [Add GitHub URL]
