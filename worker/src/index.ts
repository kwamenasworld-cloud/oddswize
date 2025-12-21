/**
 * OddsWize API - Cloudflare Worker
 * Backend for betting odds comparison
 */

import type {
  Env,
  Match,
  LeagueGroup,
  OddsResponse,
  ArbitrageOpportunity,
  ArbitrageResponse,
  ErrorResponse,
  BookmakerOdds,
} from './types';

// Cache TTL in seconds
const CACHE_TTL = 900; // 15 minutes (matches scraper schedule)

// Ghana bookmakers
const GHANA_BOOKMAKERS = [
  'Betway Ghana',
  'SportyBet Ghana',
  '1xBet Ghana',
  '22Bet Ghana',
  'SoccaBet Ghana',
  'Betfox Ghana',
];

type LeagueKeyRule = {
  key: string;
  keywords: string[];
};

const LEAGUE_KEY_RULES: LeagueKeyRule[] = [
  { key: 'premier', keywords: ['premier league', 'english premier league', 'epl'] },
  { key: 'laliga', keywords: ['la liga', 'laliga', 'primera division'] },
  { key: 'seriea', keywords: ['serie a'] },
  { key: 'bundesliga', keywords: ['bundesliga'] },
  { key: 'ligue1', keywords: ['ligue 1'] },
  { key: 'ucl', keywords: ['uefa champions league', 'uefa champions league league phase', 'uefa champions league qualifiers', 'uefa champions league qualification', 'uefa champions league playoff', 'ucl'] },
  { key: 'uwcl', keywords: ['uefa champions league women', 'uefa womens champions league', 'uwcl'] },
  { key: 'europa', keywords: ['uefa europa league', 'europa league', 'uel'] },
  { key: 'conference', keywords: ['uefa europa conference league', 'uefa conference league', 'europa conference league', 'uecl'] },
];

function normalizeLeagueName(name: string): string {
  return (name || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

function resolveLeagueKey(name: string): string | null {
  const normalized = normalizeLeagueName(name);
  if (!normalized) return null;
  let bestKey: string | null = null;
  let bestLen = 0;
  for (const rule of LEAGUE_KEY_RULES) {
    for (const keyword of rule.keywords) {
      if (normalized.includes(keyword) && keyword.length > bestLen) {
        bestKey = rule.key;
        bestLen = keyword.length;
      }
    }
  }
  return bestKey;
}

function attachLeagueKeys(groups: LeagueGroup[]): LeagueGroup[] {
  return groups.map((group) => {
    const groupKey = group.league_key || resolveLeagueKey(group.league);
    const matches = group.matches.map((match) => {
      const matchKey =
        match.league_key || groupKey || resolveLeagueKey(match.league || group.league);
      return matchKey ? { ...match, league_key: matchKey } : match;
    });
    return groupKey ? { ...group, league_key: groupKey, matches } : { ...group, matches };
  });
}

/**
 * CORS headers
 */
function corsHeaders(env: Env): HeadersInit {
  return {
    'Access-Control-Allow-Origin': env.CORS_ORIGIN,
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key',
    'Access-Control-Max-Age': '86400',
  };
}

/**
 * JSON response helper
 */
function jsonResponse(data: unknown, status = 200, env?: Env): Response {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(env ? corsHeaders(env) : {}),
  };

  return new Response(JSON.stringify(data), { status, headers });
}

/**
 * Error response helper
 */
function errorResponse(message: string, code = 500, env?: Env): Response {
  const error: ErrorResponse = {
    success: false,
    error: message,
    code,
  };
  return jsonResponse(error, code, env);
}

/**
 * Calculate arbitrage opportunities
 */
function findArbitrageOpportunities(matches: Match[]): ArbitrageOpportunity[] {
  const opportunities: ArbitrageOpportunity[] = [];

  for (const match of matches) {
    if (!match.odds || match.odds.length < 2) continue;

    // Find best odds for each outcome
    let bestHome = { odds: 0, bookmaker: '' };
    let bestDraw = { odds: 0, bookmaker: '' };
    let bestAway = { odds: 0, bookmaker: '' };

    for (const bookie of match.odds) {
      if (bookie.home_odds && bookie.home_odds > bestHome.odds) {
        bestHome = { odds: bookie.home_odds, bookmaker: bookie.bookmaker };
      }
      if (bookie.draw_odds && bookie.draw_odds > bestDraw.odds) {
        bestDraw = { odds: bookie.draw_odds, bookmaker: bookie.bookmaker };
      }
      if (bookie.away_odds && bookie.away_odds > bestAway.odds) {
        bestAway = { odds: bookie.away_odds, bookmaker: bookie.bookmaker };
      }
    }

    // Calculate 3-way arbitrage (1X2)
    if (bestHome.odds > 0 && bestDraw.odds > 0 && bestAway.odds > 0) {
      const margin =
        1 / bestHome.odds + 1 / bestDraw.odds + 1 / bestAway.odds;

      if (margin < 1) {
        const profit = ((1 / margin - 1) * 100).toFixed(2);
        const totalStake = 100;

        opportunities.push({
          id: `${match.id}-3way`,
          match: `${match.home_team} vs ${match.away_team}`,
          league: match.league,
          profit_percentage: parseFloat(profit),
          type: '3-Way (1X2)',
          selections: [
            {
              outcome: 'Home Win',
              bookmaker: bestHome.bookmaker,
              odds: bestHome.odds,
              stake_percentage: ((1 / bestHome.odds / margin) * 100),
            },
            {
              outcome: 'Draw',
              bookmaker: bestDraw.bookmaker,
              odds: bestDraw.odds,
              stake_percentage: ((1 / bestDraw.odds / margin) * 100),
            },
            {
              outcome: 'Away Win',
              bookmaker: bestAway.bookmaker,
              odds: bestAway.odds,
              stake_percentage: ((1 / bestAway.odds / margin) * 100),
            },
          ],
          total_stake: totalStake,
          guaranteed_return: totalStake * (1 / margin),
        });
      }
    }
  }

  return opportunities.sort((a, b) => b.profit_percentage - a.profit_percentage);
}

/**
 * Get all odds data
 */
async function getOddsData(env: Env): Promise<OddsResponse> {
  try {
    // Try to get from KV cache first
    const cached = await env.ODDS_CACHE.get('all_odds', 'json');

    if (cached) {
      const cachedResponse = cached as OddsResponse;
      return {
        ...cachedResponse,
        data: attachLeagueKeys(cachedResponse.data || []),
      };
    }

    // If no cache, return empty data
    // In production, this would fetch from external APIs or scraped data
    const emptyResponse: OddsResponse = {
      success: true,
      data: [],
      meta: {
        total_matches: 0,
        total_bookmakers: GHANA_BOOKMAKERS.length,
        last_updated: new Date().toISOString(),
        cache_ttl: CACHE_TTL,
      },
    };

    return emptyResponse;
  } catch (error) {
    console.error('Error fetching odds:', error);
    throw error;
  }
}

/**
 * Update odds data (called by external scraper or scheduled job)
 */
async function updateOddsData(
  env: Env,
  data: LeagueGroup[]
): Promise<{ success: boolean; message: string }> {
  try {
    const normalizedData = attachLeagueKeys(data);
    const totalMatches = normalizedData.reduce(
      (sum, league) => sum + league.matches.length,
      0
    );

    const oddsResponse: OddsResponse = {
      success: true,
      data: normalizedData,
      meta: {
        total_matches: totalMatches,
        total_bookmakers: GHANA_BOOKMAKERS.length,
        last_updated: new Date().toISOString(),
        cache_ttl: CACHE_TTL,
      },
    };

    // Store in KV with 1 hour TTL (scraper runs every 15min, so plenty of buffer)
    // Only store the main cache to avoid hitting KV write limits (1000/day on free tier)
    await env.ODDS_CACHE.put('all_odds', JSON.stringify(oddsResponse), {
      expirationTtl: 3600, // 1 hour
    });

    return {
      success: true,
      message: `Updated ${totalMatches} matches across ${data.length} leagues`,
    };
  } catch (error) {
    console.error('Error updating odds:', error);
    throw error;
  }
}

/**
 * Router - handle all API requests
 */
async function handleRequest(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const path = url.pathname;

  // Handle CORS preflight
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders(env) });
  }

  try {
    // Health check
    if (path === '/' || path === '/health') {
      return jsonResponse(
        {
          status: 'ok',
          service: 'OddsWize API',
          version: '1.0.0',
          timestamp: new Date().toISOString(),
        },
        200,
        env
      );
    }

    // GET /api/odds - Get all odds data
    if (path === '/api/odds' && request.method === 'GET') {
      const data = await getOddsData(env);
      return jsonResponse(data, 200, env);
    }

    // GET /api/odds/:league - Get odds for specific league
    if (path.startsWith('/api/odds/') && request.method === 'GET') {
      const league = decodeURIComponent(path.replace('/api/odds/', ''));
      const allData = await getOddsData(env);
      const leagueData = allData.data.filter(
        (l) => l.league.toLowerCase() === league.toLowerCase()
      );

      return jsonResponse(
        {
          success: true,
          data: leagueData,
          meta: {
            ...allData.meta,
            total_matches: leagueData.reduce(
              (sum, l) => sum + l.matches.length,
              0
            ),
          },
        },
        200,
        env
      );
    }

    // GET /api/arbitrage - Get arbitrage opportunities
    if (path === '/api/arbitrage' && request.method === 'GET') {
      const allData = await getOddsData(env);
      const allMatches = allData.data.flatMap((l) => l.matches);
      const opportunities = findArbitrageOpportunities(allMatches);

      const response: ArbitrageResponse = {
        success: true,
        data: opportunities,
        meta: {
          total_opportunities: opportunities.length,
          last_updated: allData.meta.last_updated,
        },
      };

      return jsonResponse(response, 200, env);
    }

    // GET /api/match/:id - Get single match
    if (path.startsWith('/api/match/') && request.method === 'GET') {
      const matchId = path.replace('/api/match/', '');
      const allData = await getOddsData(env);

      // Search for match in all leagues
      let foundMatch: Match | null = null;
      for (const league of allData.data) {
        const match = league.matches.find(m => m.id === matchId);
        if (match) {
          foundMatch = match;
          break;
        }
      }

      if (!foundMatch) {
        return errorResponse('Match not found', 404, env);
      }

      return jsonResponse({ success: true, data: foundMatch }, 200, env);
    }

    // GET /api/bookmakers - Get list of bookmakers
    if (path === '/api/bookmakers' && request.method === 'GET') {
      return jsonResponse(
        {
          success: true,
          data: GHANA_BOOKMAKERS.map((name) => ({
            name,
            country: 'Ghana',
          })),
        },
        200,
        env
      );
    }

    // POST /api/odds/update - Update odds data (protected endpoint)
    if (path === '/api/odds/update' && request.method === 'POST') {
      try {
        // Check for API key
        const apiKey = request.headers.get('X-API-Key');
        console.log('API Key received:', apiKey ? 'Yes' : 'No');
        console.log('Expected API Secret exists:', env.API_SECRET ? 'Yes' : 'No');

        if (!apiKey || apiKey !== env.API_SECRET) {
          console.log('Auth failed');
          return errorResponse('Unauthorized', 401, env);
        }

        console.log('Parsing request body...');
        const body = (await request.json()) as LeagueGroup[];
        console.log('Body parsed, leagues:', body.length);

        console.log('Updating odds data...');
        const result = await updateOddsData(env, body);
        console.log('Update result:', result);

        return jsonResponse(result, 200, env);
      } catch (error) {
        console.error('Error in /api/odds/update:', error);
        return errorResponse(`Update failed: ${error}`, 500, env);
      }
    }

    // 404 for unknown routes
    return errorResponse('Not found', 404, env);
  } catch (error) {
    console.error('Request error:', error);
    return errorResponse('Internal server error', 500, env);
  }
}

// ---------------------------------------------------------------------------
// D1 canonical leagues/fixtures
// ---------------------------------------------------------------------------

async function initD1Schema(env: Env) {
  // Minimal check: ensure tables exist
  const schema = `
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
  `;
  await env.D1.exec(schema);
}

async function listLeaguesD1(env: Env): Promise<Response> {
  const res = await env.D1.prepare(
    'SELECT league_id, display_name, slug, sport, country_code, tier, season_start, season_end FROM leagues ORDER BY sport, country_code, display_name'
  ).all();
  return jsonResponse(res.results || [], 200, env);
}

async function listFixturesD1(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const leagueId = url.searchParams.get('league_id');
  const country = url.searchParams.get('country');
  const sport = url.searchParams.get('sport');
  const dateFrom = url.searchParams.get('date_from');
  const dateTo = url.searchParams.get('date_to');
  const limit = Math.min(parseInt(url.searchParams.get('limit') || '200', 10), 1000);
  const offset = parseInt(url.searchParams.get('offset') || '0', 10);

  const filters: string[] = [];
  const params: any[] = [];
  if (leagueId) { filters.push('league_id = ?'); params.push(leagueId); }
  if (country) { filters.push('country_code = ?'); params.push(country); }
  if (sport) { filters.push('sport = ?'); params.push(sport); }
  if (dateFrom) { filters.push('kickoff_time >= ?'); params.push(parseInt(dateFrom, 10)); }
  if (dateTo) { filters.push('kickoff_time <= ?'); params.push(parseInt(dateTo, 10)); }

  const where = filters.length ? `WHERE ${filters.join(' AND ')}` : '';
  const sql = `SELECT fixture_id, league_id, provider, provider_fixture_id, home_team, away_team, kickoff_time, country_code, sport, raw_league_name, confidence
               FROM fixtures ${where}
               ORDER BY kickoff_time
               LIMIT ? OFFSET ?`;
  params.push(limit, offset);

  const res = await env.D1.prepare(sql).bind(...params).all();
  return jsonResponse(res.results || [], 200, env);
}

async function ingestFixturesD1(request: Request, env: Env): Promise<Response> {
  const apiKey = request.headers.get('X-API-Key');
  if (!apiKey || apiKey !== env.API_SECRET) {
    return errorResponse('Unauthorized', 401, env);
  }
  const payload = await request.json() as any[];
  if (!Array.isArray(payload)) return errorResponse('Invalid payload', 400, env);

  try {
    const stmt = env.D1.prepare(
      `INSERT OR REPLACE INTO fixtures
       (fixture_id, league_id, provider, provider_fixture_id, home_team, away_team, kickoff_time, country_code, sport, raw_league_name, raw_league_id, confidence, match_status, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)`
    );

    const batch = env.D1.batch(
      payload.map(f => {
        const id = f.fixture_id || crypto.randomUUID();
        return stmt.bind(
          id,
          f.league_id || null,
          f.provider,
          f.provider_fixture_id,
          f.home_team,
          f.away_team,
          f.kickoff_time || null,
          f.country_code || null,
          f.sport || null,
          f.raw_league_name || null,
          f.raw_league_id || null,
          f.confidence || null,
          f.match_status || null,
        );
      })
    );

    await batch;
    return jsonResponse({ success: true, inserted: payload.length }, 200, env);
  } catch (e) {
    console.error('D1 ingest error', e);
    return errorResponse(`D1 ingest failed: ${e}`, 500, env);
  }
}

async function handleCanonical(request: Request, env: Env, path: string): Promise<Response> {
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders(env) });
  }
  if (path === '/api/canonical/leagues' && request.method === 'GET') {
    return listLeaguesD1(env);
  }
  if (path === '/api/canonical/fixtures' && request.method === 'GET') {
    return listFixturesD1(request, env);
  }
  if (path === '/api/canonical/ingest' && request.method === 'POST') {
    return ingestFixturesD1(request, env);
  }
  return errorResponse('Not found', 404, env);
}

/**
 * Scheduled handler - runs periodically to refresh data
 */
async function handleScheduled(
  controller: ScheduledController,
  env: Env,
  ctx: ExecutionContext
): Promise<void> {
  console.log('Scheduled job triggered at:', new Date().toISOString());

  // In production, this would:
  // 1. Fetch data from odds APIs
  // 2. Process and normalize the data
  // 3. Store in KV

  // For now, just log that the job ran
  // The actual data population would come from:
  // - External API calls (if using odds APIs)
  // - A separate scraper service that POSTs to /api/odds/update

  console.log('Scheduled job completed');
}

// Export the worker
export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname.startsWith('/api/canonical/')) {
      return handleCanonical(request, env, url.pathname);
    }
    return handleRequest(request, env);
  },

  async scheduled(controller: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
    await handleScheduled(controller, env, ctx);
  },
};
