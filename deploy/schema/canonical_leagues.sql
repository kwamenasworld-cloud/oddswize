-- Canonical league system (Postgres)
-- Run this migration to create canonical league + alias tables and fixtures with canonical league_id

CREATE TABLE IF NOT EXISTS leagues (
    league_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sport              TEXT NOT NULL,
    country_code       TEXT NOT NULL,
    region             TEXT,
    tier               INT,
    gender             TEXT,
    season_start       INT,
    season_end         INT,
    display_name       TEXT NOT NULL,
    normalized_name    TEXT NOT NULL,
    timezone           TEXT,
    created_at         TIMESTAMPTZ DEFAULT now(),
    updated_at         TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS league_aliases (
    id                 BIGSERIAL PRIMARY KEY,
    league_id          UUID REFERENCES leagues(league_id) ON DELETE CASCADE,
    provider           TEXT NOT NULL,
    provider_league_id TEXT,
    provider_name      TEXT,
    provider_country   TEXT,
    provider_season    TEXT,
    provider_sport     TEXT,
    priority           INT DEFAULT 0,
    active             BOOLEAN DEFAULT TRUE,
    created_at         TIMESTAMPTZ DEFAULT now(),
    updated_at         TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS league_overrides (
    id                 BIGSERIAL PRIMARY KEY,
    league_id          UUID REFERENCES leagues(league_id) ON DELETE CASCADE,
    provider           TEXT NOT NULL,
    provider_league_id TEXT,
    override_name      TEXT,
    override_country   TEXT,
    override_season    TEXT,
    active             BOOLEAN DEFAULT TRUE,
    created_at         TIMESTAMPTZ DEFAULT now(),
    updated_at         TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fixtures (
    fixture_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    league_id          UUID REFERENCES leagues(league_id),
    provider           TEXT NOT NULL,
    provider_fixture_id TEXT NOT NULL,
    home_team          TEXT NOT NULL,
    away_team          TEXT NOT NULL,
    kickoff_time       TIMESTAMPTZ,
    country_code       TEXT,
    sport              TEXT,
    raw_league_name    TEXT,
    raw_league_id      TEXT,
    confidence         NUMERIC,
    match_status       TEXT,
    created_at         TIMESTAMPTZ DEFAULT now(),
    updated_at         TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS unmapped_candidates (
    id                 BIGSERIAL PRIMARY KEY,
    fixture_id         UUID REFERENCES fixtures(fixture_id) ON DELETE CASCADE,
    candidates         JSONB,
    reason             TEXT,
    created_at         TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_leagues_norm ON leagues(sport, country_code, normalized_name, season_start, season_end);
CREATE INDEX IF NOT EXISTS idx_league_alias_provider ON league_aliases(provider, provider_league_id);
CREATE INDEX IF NOT EXISTS idx_league_alias_name ON league_aliases(provider, lower(provider_name));
CREATE INDEX IF NOT EXISTS idx_fixtures_league_time ON fixtures(league_id, kickoff_time);
CREATE INDEX IF NOT EXISTS idx_fixtures_provider ON fixtures(provider, provider_fixture_id);

