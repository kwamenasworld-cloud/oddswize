/**
 * OddsWize API Service
 * Connects to Cloudflare Workers backend
 */

// API Configuration
const CLOUDFLARE_API_URL = import.meta.env.VITE_CLOUDFLARE_API_URL || 'https://oddswize-api.kwamenahb.workers.dev';
const CLOUDFLARE_WS_URL = import.meta.env.VITE_CLOUDFLARE_WS_URL;
const STATIC_DATA_URL = '/data/odds_data.json';
const API_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS) || 10000;

const ODDS_CACHE_KEY = 'oddswize_odds_cache_v2';
const ODDS_CACHE_DEFAULT_TTL_MS = 15 * 60 * 1000;
const ODDS_CACHE_MAX_CHARS = Number(import.meta.env.VITE_ODDS_CACHE_MAX_CHARS) || 1500000;
const ODDS_SLIM_FIELDS = [
  'home_odds',
  'draw_odds',
  'away_odds',
  'home_draw',
  'draw_away',
  'home_away',
  'over_25',
  'under_25',
];
let oddsCacheMemory = null;
let oddsFetchPromise = null;

// Minimal team list to infer Premier League when league comes back empty
const PREMIER_TEAMS = new Set([
  'arsenal', 'aston villa', 'bournemouth', 'brentford', 'brighton', 'brighton & hove albion',
  'chelsea', 'crystal palace', 'everton', 'fulham', 'ipswich', 'leeds', 'leeds united',
  'leicester', 'leicester city', 'liverpool', 'man city', 'manchester city', 'man utd',
  'manchester united', 'newcastle', 'newcastle united', 'nottingham forest', 'forest',
  'southampton', 'spurs', 'tottenham', 'tottenham hotspur', 'west ham', 'west ham united',
  'wolves', 'wolverhampton', 'wolverhampton wanderers', 'burnley'
]);

const isPremierLeagueMatch = (home, away) => {
  const h = (home || '').toLowerCase();
  const a = (away || '').toLowerCase();
  return PREMIER_TEAMS.has(h) && PREMIER_TEAMS.has(a);
};

const slimOddsPayload = (payload) => {
  if (!payload || !Array.isArray(payload.data)) return payload;

  const slimLeagues = payload.data.map((league) => {
    const matches = Array.isArray(league?.matches) ? league.matches : [];
    let leagueName = league?.league || '';

    if (!leagueName) {
      const matchLeagueName = matches.find((m) => m?.league)?.league;
      if (matchLeagueName) {
        leagueName = matchLeagueName;
      } else if (matches.length > 0 && matches.every((m) => isPremierLeagueMatch(m?.home_team, m?.away_team))) {
        leagueName = 'Premier League';
      }
    }

    const slimMatches = matches
      .map((match) => {
        if (!match) return null;
        const matchLeague = match.league || leagueName
          || (isPremierLeagueMatch(match.home_team, match.away_team) ? 'Premier League' : '');
        const odds = Array.isArray(match.odds)
          ? match.odds.map((oddsEntry) => {
            if (!oddsEntry?.bookmaker) return null;
            const slimOdds = { bookmaker: oddsEntry.bookmaker };
            ODDS_SLIM_FIELDS.forEach((field) => {
              const value = oddsEntry[field];
              if (value !== undefined && value !== null) {
                slimOdds[field] = value;
              }
            });
            return slimOdds;
          }).filter(Boolean)
          : [];

        return {
          id: match.id,
          home_team: match.home_team,
          away_team: match.away_team,
          start_time: match.start_time,
          league: matchLeague,
          odds,
        };
      })
      .filter(Boolean);

    const slimLeague = { matches: slimMatches };
    if (leagueName) {
      slimLeague.league = leagueName;
    }
    return slimLeague;
  });

  return { ...payload, data: slimLeagues };
};

const readOddsCache = (allowExpired = false) => {
  if (oddsCacheMemory) {
    if (allowExpired || oddsCacheMemory.expiresAt > Date.now()) {
      return oddsCacheMemory;
    }
    oddsCacheMemory = null;
  }

  try {
    const raw = localStorage.getItem(ODDS_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || !parsed.payload || !parsed.storedAt) return null;
    const expiresAt = parsed.expiresAt || (parsed.storedAt + ODDS_CACHE_DEFAULT_TTL_MS);
    const cache = { ...parsed, expiresAt };
    if (!allowExpired && expiresAt <= Date.now()) return null;
    oddsCacheMemory = cache;
    return cache;
  } catch (error) {
    return null;
  }
};

const saveOddsCache = (payload, ttlSeconds, etag) => {
  const storedAt = Date.now();
  const ttlMs = Number.isFinite(ttlSeconds) && ttlSeconds > 0
    ? ttlSeconds * 1000
    : ODDS_CACHE_DEFAULT_TTL_MS;
  const cache = {
    payload,
    storedAt,
    expiresAt: storedAt + ttlMs,
    etag: etag || null,
  };
  try {
    const serialized = JSON.stringify(cache);
    if (serialized.length > ODDS_CACHE_MAX_CHARS) {
      oddsCacheMemory = null;
      return { storedAt, expiresAt: cache.expiresAt, skipped: true };
    }
    oddsCacheMemory = cache;
    localStorage.setItem(ODDS_CACHE_KEY, serialized);
  } catch (error) {
    // Ignore storage failures (private mode/quota)
  }
  return cache;
};

// Fetch helper with error handling
const fetchApi = async (endpoint, options = {}) => {
  const url = `${CLOUDFLARE_API_URL}${endpoint}`;
  const {
    timeoutMs = API_TIMEOUT_MS,
    headers,
    signal: requestSignal,
    returnResponse = false,
    ...fetchOptions
  } = options;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  if (requestSignal) {
    if (requestSignal.aborted) {
      controller.abort();
    } else {
      requestSignal.addEventListener('abort', () => controller.abort(), { once: true });
    }
  }

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...headers,
      },
    });

    if (returnResponse) {
      return response;
    }

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    if (error.name === 'AbortError') {
      console.error(`API request timed out after ${timeoutMs}ms: ${endpoint}`);
    } else {
      console.error(`API request failed: ${endpoint}`, error);
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
};

const buildWsUrl = (path) => {
  const base = CLOUDFLARE_WS_URL || CLOUDFLARE_API_URL;
  const url = new URL(path, base);
  if (url.protocol === 'https:') {
    url.protocol = 'wss:';
  } else if (url.protocol === 'http:') {
    url.protocol = 'ws:';
  }
  return url;
};

export const connectOddsStream = ({ leagueKeys = [], onMessage, onOpen, onClose, onError } = {}) => {
  if (typeof window === 'undefined' || typeof WebSocket === 'undefined') {
    return null;
  }
  const url = buildWsUrl('/api/odds/stream');
  const keys = Array.isArray(leagueKeys)
    ? leagueKeys.map(key => (key || '').toString().trim().toLowerCase()).filter(Boolean)
    : [];
  if (keys.length) {
    url.searchParams.set('league_keys', keys.join(','));
  }
  const socket = new WebSocket(url.toString());

  if (typeof onOpen === 'function') {
    socket.addEventListener('open', onOpen);
  }
  if (typeof onClose === 'function') {
    socket.addEventListener('close', onClose);
  }
  if (typeof onError === 'function') {
    socket.addEventListener('error', onError);
  }
  if (typeof onMessage === 'function') {
    socket.addEventListener('message', (event) => {
      let parsed = null;
      try {
        parsed = JSON.parse(event.data);
      } catch {
        parsed = null;
      }
      onMessage(parsed, event);
    });
  }
  return socket;
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

const fetchOddsData = async (options = {}) => {
  const {
    allowStale = true,
    bypassCache = false,
    limit,
    offset,
    windowHours,
    startTimeFrom,
    startTimeTo,
  } = options;
  const cachedFallback = bypassCache ? null : readOddsCache(true);
  const parsedLimit = Number.isFinite(limit) ? Math.max(0, Math.floor(limit)) : 0;
  const parsedOffset = Number.isFinite(offset) ? Math.max(0, Math.floor(offset)) : 0;
  const isEmptyOddsPayload = (payload) => {
    if (!payload || !payload.success) return false;
    const total = payload?.meta?.total_matches;
    const hasMatches = Array.isArray(payload?.data)
      && payload.data.some(league => Array.isArray(league.matches) && league.matches.length > 0);
    if (Number.isFinite(total)) {
      return total <= 0 && !hasMatches;
    }
    return !hasMatches;
  };
  const normalizeEpoch = (value) => {
    if (!Number.isFinite(value)) return undefined;
    const normalized = value > 1000000000000 ? Math.floor(value / 1000) : Math.floor(value);
    return normalized >= 0 ? normalized : undefined;
  };
  const parsedWindowHours = Number.isFinite(windowHours) && windowHours > 0
    ? Math.min(Math.floor(windowHours), 168)
    : 0;
  const parsedStartFrom = normalizeEpoch(startTimeFrom);
  const parsedStartTo = normalizeEpoch(startTimeTo);
  const hasTimeFilter = parsedWindowHours > 0
    || Number.isFinite(parsedStartFrom)
    || Number.isFinite(parsedStartTo);
  const isPaged = parsedLimit > 0;

  const query = new URLSearchParams();
  if (parsedLimit > 0) {
    query.set('limit', String(parsedLimit));
    if (parsedOffset > 0) {
      query.set('offset', String(parsedOffset));
    }
  }
  if (parsedWindowHours > 0) {
    query.set('window_hours', String(parsedWindowHours));
  }
  if (Number.isFinite(parsedStartFrom)) {
    query.set('start_time_from', String(parsedStartFrom));
  }
  if (Number.isFinite(parsedStartTo)) {
    query.set('start_time_to', String(parsedStartTo));
  }
  const endpoint = query.toString() ? `/api/odds?${query.toString()}` : '/api/odds';

  if (isPaged || hasTimeFilter) {
    const response = await fetchApi(endpoint, { returnResponse: true, cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    const payload = await response.json();
    const slimPayload = slimOddsPayload(payload);
    if (isEmptyOddsPayload(slimPayload)) {
      if (cachedFallback?.payload) {
        return {
          data: cachedFallback.payload,
          meta: cachedFallback.payload.meta || {},
          cache: { source: 'stale', stale: true, storedAt: cachedFallback.storedAt },
        };
      }
      throw new Error('Empty odds payload');
    }
    return {
      data: slimPayload,
      meta: slimPayload.meta || {},
      cache: { source: 'network', stale: false },
    };
  }

  const now = Date.now();
  const cached = bypassCache ? null : readOddsCache(allowStale);

  if (!bypassCache && cached && cached.expiresAt > now) {
    return {
      data: cached.payload,
      meta: cached.payload.meta || {},
      cache: { source: 'local', stale: false, storedAt: cached.storedAt },
    };
  }

  if (oddsFetchPromise && !bypassCache) {
    return oddsFetchPromise;
  }

  const requestHeaders = {};
  if (cached?.etag) {
    requestHeaders['If-None-Match'] = cached.etag;
  }

  const fetchPromise = (async () => {
    const response = await fetchApi(endpoint, {
      returnResponse: true,
      headers: requestHeaders,
      cache: bypassCache ? 'no-store' : 'default',
    });

    if (response.status === 304 && cached?.payload) {
      return {
        data: cached.payload,
        meta: cached.payload.meta || {},
        cache: { source: 'etag', stale: false, storedAt: cached.storedAt },
      };
    }

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const payload = await response.json();
    const slimPayload = slimOddsPayload(payload);
    if (isEmptyOddsPayload(slimPayload)) {
      if (cachedFallback?.payload) {
        return {
          data: cachedFallback.payload,
          meta: cachedFallback.payload.meta || {},
          cache: { source: 'stale', stale: true, storedAt: cachedFallback.storedAt },
        };
      }
      throw new Error('Empty odds payload');
    }
    const ttlSeconds = slimPayload?.meta?.cache_ttl;
    const etag = response.headers.get('ETag');
    const saved = saveOddsCache(slimPayload, ttlSeconds, etag);

    return {
      data: slimPayload,
      meta: slimPayload.meta || {},
      cache: { source: 'network', stale: false, storedAt: saved.storedAt },
    };
  })();

  if (!bypassCache) {
    oddsFetchPromise = fetchPromise;
  }

  try {
    return await fetchPromise;
  } catch (error) {
    if (allowStale && cached?.payload) {
      return {
        data: cached.payload,
        meta: cached.payload.meta || {},
        cache: { source: 'stale', stale: true, storedAt: cached.storedAt },
      };
    }
    throw error;
  } finally {
    if (!bypassCache) {
      oddsFetchPromise = null;
    }
  }
};

export const getCachedOdds = () => {
  const cached = readOddsCache(true);
  if (!cached) return null;
  return {
    data: cached.payload,
    meta: cached.payload.meta || {},
    cache: {
      source: 'local',
      stale: cached.expiresAt <= Date.now(),
      storedAt: cached.storedAt,
    },
  };
};

export const clearOddsCacheMemory = () => {
  oddsCacheMemory = null;
};

/**
 * Get all matches with odds comparison
 */
export const getMatches = async (limit = 100, offset = 0, minBookmakers = 1, options = {}) => {
  try {
    // Try Cloudflare API first (with local cache + ETag support)
    const oddsResponse = await fetchOddsData(options);
    const data = oddsResponse.data;

    // Validate response structure
    if (data.success && data.data && Array.isArray(data.data)) {
      // Flatten matches from all leagues with validation
      const allMatches = data.data.flatMap(league => {
        if (!league || !Array.isArray(league.matches)) {
          return [];
        }
        return league.matches.map(match => ({
          ...match,
          // Some scrapers emit empty league for EPL; infer it so frontend filters work
          league: (() => {
            const leagueName = league.league || match.league;
            if (leagueName) return leagueName;
            return isPremierLeagueMatch(match.home_team, match.away_team)
              ? 'Premier League'
              : 'Unknown';
          })(),
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
        cache: oddsResponse.cache,
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
export const getMatchesByLeague = async (options = {}) => {
  try {
    const oddsResponse = await fetchOddsData(options);
    const data = oddsResponse.data;

    if (data.success && data.data) {
      return {
        leagues: data.data,
        meta: data.meta,
        cache: oddsResponse.cache,
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
export const getLastUpdate = async (options = {}) => {
  try {
    const oddsResponse = await fetchOddsData(options);
    const data = oddsResponse.data;

    if (data.success && data.meta) {
      return {
        lastUpdated: data.meta.last_updated,
        cacheTtl: data.meta.cache_ttl,
        totalMatches: data.meta.total_matches,
        cache: oddsResponse.cache,
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
 * Get scanner/API status
 */
export const getStatus = async () => {
  try {
    const lastUpdate = await getLastUpdate({ allowStale: true });
    if (lastUpdate?.lastUpdated) {
      return {
        status: 'ok',
        last_scan: lastUpdate.lastUpdated,
        cacheTtl: lastUpdate.cacheTtl,
        totalMatches: lastUpdate.totalMatches,
      };
    }
  } catch (error) {
    // Fall back to health endpoint below
  }

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

export const getLiveScores = async (leagueKeys = [], options = {}) => {
  const keys = Array.isArray(leagueKeys) ? leagueKeys : [];
  const filtered = keys
    .map(key => (key || '').toString().trim().toLowerCase())
    .filter(Boolean);

  if (filtered.length === 0) {
    return { success: true, data: [], meta: { requested_leagues: [] } };
  }

  const params = new URLSearchParams();
  params.set('league_keys', filtered.join(','));
  if (options.state) {
    params.set('state', options.state);
  }
  const data = await fetchApi(`/api/live-scores?${params.toString()}`, {
    timeoutMs: options.timeoutMs || 8000,
  });
  if (data?.success) {
    return data;
  }
  throw new Error('Live scores unavailable');
};

/**
 * Trigger data refresh (not available in Cloudflare - data is pushed from scraper)
 */
export const triggerScan = async () => {
  console.log('Manual scan not available - data is refreshed automatically');
  return {
    message: 'Data refreshes every few minutes (full refresh about every 15 minutes)',
    status: 'scheduled',
  };
};

// Default export for backward compatibility
export default {
  getCachedOdds,
  clearOddsCacheMemory,
  getMatches,
  getMatchesByLeague,
  getArbitrage,
  getStatus,
  getLiveScores,
  connectOddsStream,
  getBookmakers,
  getMatch,
  getLastUpdate,
  triggerScan,
};
