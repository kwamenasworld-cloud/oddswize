/**
 * OddsWize API Service
 * Connects to Cloudflare Workers backend
 */

// API Configuration
const CLOUDFLARE_API_URL = import.meta.env.VITE_CLOUDFLARE_API_URL || 'https://oddswize-api.kwamenahb.workers.dev';
const STATIC_DATA_URL = '/data/odds_data.json';

// Fetch helper with error handling
const fetchApi = async (endpoint, options = {}) => {
  const url = `${CLOUDFLARE_API_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`API request failed: ${endpoint}`, error);
    throw error;
  }
};

// Try to fetch from static JSON file (fallback)
const fetchStaticData = async () => {
  try {
    const response = await fetch(STATIC_DATA_URL);
    if (!response.ok) throw new Error('Static data not available');
    return await response.json();
  } catch (error) {
    console.log('Static data not available');
    return null;
  }
};

/**
 * Get all matches with odds comparison
 */
export const getMatches = async (limit = 100, offset = 0, minBookmakers = 2) => {
  try {
    // Try Cloudflare API first
    const data = await fetchApi('/api/odds');

    // Validate response structure
    if (data.success && data.data && Array.isArray(data.data)) {
      // Flatten matches from all leagues with validation
      const allMatches = data.data.flatMap(league => {
        if (!league || !Array.isArray(league.matches)) {
          return [];
        }
        return league.matches.map(match => ({
          ...match,
          league: league.league || 'Unknown',
        }));
      });

      // Filter by minimum bookmakers
      const filtered = allMatches.filter(
        match => match.odds && Array.isArray(match.odds) && match.odds.length >= minBookmakers
      );

      return {
        matches: filtered.slice(offset, offset + limit),
        total: filtered.length,
        meta: data.meta || {},
      };
    }

    throw new Error('Invalid API response structure');
  } catch (error) {
    // Fallback to static data
    console.warn('Cloudflare API unavailable, using static data:', error.message);

    try {
      const staticData = await fetchStaticData();

      if (staticData && Array.isArray(staticData.matches)) {
        const filtered = staticData.matches.filter(
          match => match.odds && Array.isArray(match.odds) && match.odds.length >= minBookmakers
        );
        return {
          matches: filtered.slice(offset, offset + limit),
          total: filtered.length,
          meta: {
            last_updated: staticData.last_updated || new Date().toISOString(),
            total_matches: filtered.length,
          },
        };
      }
    } catch (staticError) {
      console.error('Failed to load static data:', staticError);
    }

    throw new Error('Unable to load odds data from any source');
  }
};

/**
 * Get matches grouped by league
 */
export const getMatchesByLeague = async () => {
  try {
    const data = await fetchApi('/api/odds');

    if (data.success && data.data) {
      return {
        leagues: data.data,
        meta: data.meta,
      };
    }

    throw new Error('Invalid API response');
  } catch (error) {
    // Fallback to static data
    const staticData = await fetchStaticData();

    if (staticData && staticData.matches) {
      // Group by league
      const leagueMap = {};
      for (const match of staticData.matches) {
        const league = match.league || 'Unknown';
        if (!leagueMap[league]) {
          leagueMap[league] = [];
        }
        leagueMap[league].push(match);
      }

      const leagues = Object.entries(leagueMap).map(([league, matches]) => ({
        league,
        matches,
      }));

      return {
        leagues,
        meta: {
          last_updated: staticData.last_updated,
          total_matches: staticData.matches.length,
        },
      };
    }

    throw error;
  }
};

/**
 * Get arbitrage opportunities
 */
export const getArbitrage = async (bankroll = 100) => {
  try {
    const data = await fetchApi('/api/arbitrage');

    if (data.success) {
      // Calculate stakes based on bankroll
      return data.data.map(opp => ({
        ...opp,
        selections: opp.selections.map(sel => ({
          ...sel,
          stake: (sel.stake_percentage / 100) * bankroll,
        })),
        total_stake: bankroll,
        guaranteed_return: opp.guaranteed_return * (bankroll / 100),
      }));
    }

    throw new Error('Invalid API response');
  } catch (error) {
    // Fallback to static data
    const staticData = await fetchStaticData();

    if (staticData && staticData.arbitrage) {
      return staticData.arbitrage;
    }

    throw error;
  }
};

/**
 * Get scanner/API status
 */
export const getStatus = async () => {
  try {
    const data = await fetchApi('/health');

    return {
      status: data.status,
      last_scan: data.timestamp,
      service: data.service,
      version: data.version,
    };
  } catch (error) {
    // Fallback to static data
    const staticData = await fetchStaticData();

    if (staticData && staticData.stats) {
      return {
        status: 'ok',
        last_scan: staticData.last_updated,
        ...staticData.stats,
      };
    }

    return {
      status: 'offline',
      last_scan: null,
    };
  }
};

/**
 * Get bookmaker list
 */
export const getBookmakers = async () => {
  try {
    const data = await fetchApi('/api/bookmakers');

    if (data.success) {
      return data.data;
    }

    throw new Error('Invalid API response');
  } catch (error) {
    // Return default Ghana bookmakers
    return [
      { name: 'Betway Ghana', country: 'Ghana' },
      { name: 'SportyBet Ghana', country: 'Ghana' },
      { name: '1xBet Ghana', country: 'Ghana' },
      { name: '22Bet Ghana', country: 'Ghana' },
      { name: 'SoccaBet Ghana', country: 'Ghana' },
    ];
  }
};

/**
 * Get single match by ID
 */
export const getMatch = async (matchId) => {
  try {
    const data = await fetchApi(`/api/match/${matchId}`);

    if (data.success) {
      return data.data;
    }

    throw new Error('Match not found');
  } catch (error) {
    console.error(`Failed to fetch match ${matchId}:`, error);
    throw error;
  }
};

/**
 * Get last update time
 */
export const getLastUpdate = async () => {
  try {
    const data = await fetchApi('/api/odds');

    if (data.success && data.meta) {
      return {
        lastUpdated: data.meta.last_updated,
        cacheTtl: data.meta.cache_ttl,
        totalMatches: data.meta.total_matches,
      };
    }

    throw new Error('Invalid API response');
  } catch (error) {
    const staticData = await fetchStaticData();

    if (staticData) {
      return {
        lastUpdated: staticData.last_updated,
        nextUpdate: staticData.next_update,
      };
    }

    return null;
  }
};

/**
 * Trigger data refresh (not available in Cloudflare - data is pushed from scraper)
 */
export const triggerScan = async () => {
  console.log('Manual scan not available - data is refreshed automatically');
  return {
    message: 'Data is refreshed automatically every 15 minutes',
    status: 'scheduled',
  };
};

// Default export for backward compatibility
export default {
  getMatches,
  getMatchesByLeague,
  getArbitrage,
  getStatus,
  getBookmakers,
  getMatch,
  getLastUpdate,
  triggerScan,
};
