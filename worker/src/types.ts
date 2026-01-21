// Environment bindings
export interface Env {
  ODDS_CACHE: KVNamespace;
  MATCHES_DATA: KVNamespace;
  ODDS_STREAM: DurableObjectNamespace;
  D1: D1Database;
  ENVIRONMENT: string;
  CORS_ORIGIN: string;
  API_SECRET: string;
  TURNSTILE_SECRET?: string;
}

// Match data types
export interface BookmakerOdds {
  bookmaker: string;
  home_odds: number | null;
  draw_odds: number | null;
  away_odds: number | null;
  url?: string;
  last_updated?: string;
}

export interface Match {
  id: string;
  home_team: string;
  away_team: string;
  league: string;
  league_key?: string;
  start_time: number;  // Unix timestamp in seconds
  odds: BookmakerOdds[];
  is_live?: boolean;
}

export interface LiveScoreEvent {
  league_key?: string;
  league?: string;
  event_id?: string;
  start_time?: number | null;
  home_team: string;
  away_team: string;
  home_score: number | null;
  away_score: number | null;
  state?: string | null;
  detail?: string | null;
  clock?: string | null;
}

export interface LeagueGroup {
  league: string;
  league_key?: string;
  matches: Match[];
}

export interface OddsResponse {
  success: boolean;
  data: LeagueGroup[];
  meta: {
    total_matches: number;
    total_bookmakers: number;
    last_updated: string;
    cache_ttl: number;
    stale?: boolean;
    offset?: number;
    limit?: number;
    returned_matches?: number;
    total_matches_all?: number;
    window_hours?: number;
    start_time_from?: number;
    start_time_to?: number;
  };
}

export interface ArbitrageOpportunity {
  id: string;
  match: string;
  league: string;
  profit_percentage: number;
  type: string;
  selections: {
    outcome: string;
    bookmaker: string;
    odds: number;
    stake_percentage: number;
  }[];
  total_stake: number;
  guaranteed_return: number;
}

export interface ArbitrageResponse {
  success: boolean;
  data: ArbitrageOpportunity[];
  meta: {
    total_opportunities: number;
    last_updated: string;
  };
}

// API Error response
export interface ErrorResponse {
  success: false;
  error: string;
  code: number;
}

// Bookmaker configuration
export interface BookmakerConfig {
  name: string;
  shortName: string;
  color: string;
  country: string;
  url: string;
}
