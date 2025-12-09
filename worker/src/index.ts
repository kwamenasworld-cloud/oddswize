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
const CACHE_TTL = 300; // 5 minutes

// Ghana bookmakers
const GHANA_BOOKMAKERS = [
  'Betway Ghana',
  'SportyBet Ghana',
  '1xBet Ghana',
  '22Bet Ghana',
  'SoccaBet Ghana',
];

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
      return cached as OddsResponse;
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
    const totalMatches = data.reduce(
      (sum, league) => sum + league.matches.length,
      0
    );

    const oddsResponse: OddsResponse = {
      success: true,
      data,
      meta: {
        total_matches: totalMatches,
        total_bookmakers: GHANA_BOOKMAKERS.length,
        last_updated: new Date().toISOString(),
        cache_ttl: CACHE_TTL,
      },
    };

    // Store in KV with TTL
    await env.ODDS_CACHE.put('all_odds', JSON.stringify(oddsResponse), {
      expirationTtl: CACHE_TTL * 2, // Keep slightly longer than cache TTL
    });

    // Also store individual matches for faster lookups
    for (const league of data) {
      for (const match of league.matches) {
        await env.MATCHES_DATA.put(
          `match:${match.id}`,
          JSON.stringify(match),
          { expirationTtl: CACHE_TTL * 2 }
        );
      }
    }

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
      const match = await env.MATCHES_DATA.get(`match:${matchId}`, 'json');

      if (!match) {
        return errorResponse('Match not found', 404, env);
      }

      return jsonResponse({ success: true, data: match }, 200, env);
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
      // Check for API key
      const apiKey = request.headers.get('X-API-Key');
      if (!apiKey || apiKey !== env.CORS_ORIGIN) {
        // Simple auth - in production use proper secrets
        return errorResponse('Unauthorized', 401, env);
      }

      const body = (await request.json()) as LeagueGroup[];
      const result = await updateOddsData(env, body);

      return jsonResponse(result, 200, env);
    }

    // 404 for unknown routes
    return errorResponse('Not found', 404, env);
  } catch (error) {
    console.error('Request error:', error);
    return errorResponse('Internal server error', 500, env);
  }
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
    return handleRequest(request, env);
  },

  async scheduled(controller: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
    await handleScheduled(controller, env, ctx);
  },
};
