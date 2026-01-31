-- D1 schema for canonical leagues and fixtures (SQLite)
CREATE TABLE IF NOT EXISTS leagues (
  league_id TEXT PRIMARY KEY,
  sport TEXT NOT NULL,
  country_code TEXT NOT NULL,
  region TEXT,
  tier INTEGER,
  gender TEXT,
  season_start INTEGER,
  season_end INTEGER,
  display_name TEXT NOT NULL,
  normalized_name TEXT NOT NULL,
  slug TEXT,
  timezone TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS league_aliases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  league_id TEXT NOT NULL,
  provider TEXT NOT NULL,
  provider_league_id TEXT,
  provider_name TEXT,
  provider_country TEXT,
  provider_season TEXT,
  provider_sport TEXT,
  priority INTEGER DEFAULT 0,
  active INTEGER DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fixtures (
  fixture_id TEXT PRIMARY KEY,
  league_id TEXT,
  provider TEXT NOT NULL,
  provider_fixture_id TEXT NOT NULL,
  home_team TEXT NOT NULL,
  away_team TEXT NOT NULL,
  kickoff_time INTEGER,
  country_code TEXT,
  sport TEXT,
  raw_league_name TEXT,
  raw_league_id TEXT,
  confidence REAL,
  match_status TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS unmapped_candidates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fixture_id TEXT NOT NULL,
  candidates TEXT,
  reason TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_leagues_norm ON leagues(sport, country_code, normalized_name, season_start, season_end);
CREATE INDEX IF NOT EXISTS idx_leagues_slug ON leagues(sport, slug);
CREATE INDEX IF NOT EXISTS idx_league_alias_provider ON league_aliases(provider, provider_league_id);
CREATE INDEX IF NOT EXISTS idx_fixtures_league_time ON fixtures(league_id, kickoff_time);
CREATE INDEX IF NOT EXISTS idx_fixtures_provider ON fixtures(provider, provider_fixture_id);

-- Odds history tables (snapshots)
CREATE TABLE IF NOT EXISTS odds_runs (
  run_id TEXT PRIMARY KEY,
  last_updated TEXT,
  total_matches INTEGER,
  total_leagues INTEGER,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS odds_matches (
  run_id TEXT,
  match_id TEXT,
  league TEXT,
  start_time INTEGER,
  home_team TEXT,
  away_team TEXT,
  PRIMARY KEY (run_id, match_id)
);

CREATE TABLE IF NOT EXISTS odds_lines (
  run_id TEXT,
  match_id TEXT,
  bookmaker TEXT,
  home_odds REAL,
  draw_odds REAL,
  away_odds REAL,
  PRIMARY KEY (run_id, match_id, bookmaker)
);

CREATE INDEX IF NOT EXISTS idx_odds_runs_updated ON odds_runs(last_updated);
CREATE INDEX IF NOT EXISTS idx_odds_matches_start ON odds_matches(start_time);
CREATE INDEX IF NOT EXISTS idx_odds_matches_league ON odds_matches(league);
CREATE INDEX IF NOT EXISTS idx_odds_lines_bookie ON odds_lines(bookmaker);
