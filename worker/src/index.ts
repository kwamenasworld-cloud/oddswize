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
  LiveScoreEvent,
  BookmakerOdds,
} from './types';
import { OddsStream } from './oddsStream';

// Cache TTL in seconds
const CACHE_TTL = 900; // 15 minutes (matches scraper schedule)
const FAST_CACHE_TTL_SECONDS = 600; // Overlay updates expire quickly

// Ghana bookmakers
const GHANA_BOOKMAKERS = [
  'Betway Ghana',
  'SportyBet Ghana',
  '1xBet Ghana',
  '22Bet Ghana',
  'SoccaBet Ghana',
  'Betfox Ghana',
];

const COMMENTS_RATE_LIMIT_SECONDS = 30;
const COMMENTS_DAILY_LIMIT = 15;
let commentsSchemaReady = false;
let historySchemaReady = false;

const LIVE_SCORE_TTL_SECONDS = 20;
const ESPN_SCOREBOARD_BASE = 'https://site.api.espn.com/apis/site/v2/sports/soccer';
const ESPN_LEAGUE_MAP: Record<string, { id: string; name: string }> = {
  premier: { id: 'eng.1', name: 'Premier League' },
  championship: { id: 'eng.2', name: 'Championship' },
  leagueone: { id: 'eng.3', name: 'League One' },
  leaguetwo: { id: 'eng.4', name: 'League Two' },
  facup: { id: 'eng.fa', name: 'FA Cup' },
  eflcup: { id: 'eng.league_cup', name: 'EFL Cup' },
  laliga: { id: 'esp.1', name: 'La Liga' },
  laliga2: { id: 'esp.2', name: 'La Liga 2' },
  seriea: { id: 'ita.1', name: 'Serie A' },
  serieb: { id: 'ita.2', name: 'Serie B' },
  bundesliga: { id: 'ger.1', name: 'Bundesliga' },
  bundesliga2: { id: 'ger.2', name: 'Bundesliga 2' },
  ligue1: { id: 'fra.1', name: 'Ligue 1' },
  ligue2: { id: 'fra.2', name: 'Ligue 2' },
  ucl: { id: 'uefa.champions', name: 'UEFA Champions League' },
  uwcl: { id: 'uefa.champions.women', name: 'UEFA Champions League Women' },
  europa: { id: 'uefa.europa', name: 'UEFA Europa League' },
  conference: { id: 'uefa.europa.conf', name: 'UEFA Europa Conference League' },
  eredivisie: { id: 'ned.1', name: 'Eredivisie' },
  primeira: { id: 'por.1', name: 'Primeira Liga' },
  scotland: { id: 'sco.1', name: 'Scottish Premiership' },
  belgium: { id: 'bel.1', name: 'Belgian Pro League' },
  turkey: { id: 'tur.1', name: 'Turkish Super Lig' },
  mls: { id: 'usa.1', name: 'MLS' },
  libertadores: { id: 'conmebol.libertadores', name: 'CONMEBOL Libertadores' },
  sudamericana: { id: 'conmebol.sudamericana', name: 'CONMEBOL Sudamericana' },
  brasileirao: { id: 'bra.1', name: 'Serie A (Brazil)' },
  ligamx: { id: 'mex.1', name: 'Liga MX' },
  j1: { id: 'jpn.1', name: 'J1 League' },
  k1: { id: 'kor.1', name: 'K League 1' },
  'a-league': { id: 'aus.1', name: 'A-League' },
};

type LeagueKeyRule = {
  key: string;
  keywords: string[];
};

const LEAGUE_KEY_RULES: LeagueKeyRule[] = [
  { key: 'premier', keywords: ['premier league', 'english premier league', 'england premier league', 'epl'] },
  { key: 'scotland', keywords: ['scottish premiership', 'scotland premiership', 'scotland premier league', 'spfl premiership'] },
  { key: 'egypt', keywords: ['egypt premier league', 'egyptian premier league'] },
  { key: 'laliga', keywords: ['la liga', 'laliga', 'primera division'] },
  { key: 'seriea', keywords: ['serie a'] },
  { key: 'bundesliga', keywords: ['bundesliga'] },
  { key: 'ligue1', keywords: ['ligue 1'] },
  { key: 'ucl', keywords: ['uefa champions league', 'uefa champions league league phase', 'uefa champions league qualifiers', 'uefa champions league qualification', 'uefa champions league playoff', 'ucl'] },
  { key: 'uwcl', keywords: ['uefa champions league women', 'uefa womens champions league', 'uwcl'] },
  { key: 'europa', keywords: ['uefa europa league', 'europa league', 'uel'] },
  { key: 'conference', keywords: ['uefa europa conference league', 'uefa conference league', 'europa conference league', 'uecl'] },
];

const PREMIER_LEAGUE_EXCLUSIONS = [
  'premier league cup',
  'premier league other',
  'premier league u21',
  'premier league u 21',
  'premier league u-21',
  'premier league 2',
];

function normalizeLeagueName(name: string): string {
  return (name || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

function resolveLeagueKey(name: string): string | null {
  const normalized = normalizeLeagueName(name);
  if (!normalized) return null;
  if (PREMIER_LEAGUE_EXCLUSIONS.some(term => normalized.includes(term))) {
    return null;
  }
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

function parseCsvParam(value: string | null): string[] {
  if (!value) return [];
  return value
    .split(',')
    .map(part => part.trim().toLowerCase())
    .filter(Boolean);
}

const STREAM_DELTA_LIMIT = 250;

function slugify(value: string): string {
  return (value || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function buildMatchKey(match: Match): string {
  if (match.id) return match.id;
  const home = slugify(match.home_team);
  const away = slugify(match.away_team);
  const start = match.start_time || 0;
  return `${home}-vs-${away}-${start}`;
}

async function ensureHistorySchema(env: Env): Promise<void> {
  if (historySchemaReady) return;
  const schema = `
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
  `;
  await env.D1.exec(schema);
  historySchemaReady = true;
}

function resolveHistoryApiKey(request: Request, env: Env): string | null {
  const headerKey = request.headers.get('X-API-Key');
  if (headerKey) return headerKey;
  const auth = request.headers.get('Authorization') || '';
  if (auth.toLowerCase().startsWith('bearer ')) {
    return auth.slice(7).trim();
  }
  return null;
}

function authorizeHistoryRead(request: Request, env: Env): boolean {
  if (!env.HISTORY_API_KEY) return true;
  // Explicitly allow public access even if a history key exists.
  return true;
}

function buildMatchSignature(match: Match): string {
  const base = [
    match.home_team || '',
    match.away_team || '',
    String(match.start_time || 0),
    match.league || '',
  ].join('|');
  const odds = (match.odds || [])
    .map((entry) => {
      const parts = [
        entry.bookmaker,
        entry.home_odds ?? '',
        entry.draw_odds ?? '',
        entry.away_odds ?? '',
      ];
      return parts.join(':');
    })
    .sort()
    .join(',');
  return `${base}|${odds}`;
}

type OddsDelta =
  | {
      matches: Match[];
      removed_ids: string[];
      league_keys: string[];
    }
  | {
      full_refresh: true;
      reason: string;
      count: number;
    };

function buildOddsDelta(previous: OddsResponse | null, next: OddsResponse): OddsDelta | null {
  if (!previous?.data?.length) {
    const total = next?.meta?.total_matches || 0;
    return { full_refresh: true, reason: 'no_previous_cache', count: total };
  }

  const previousIndex = new Map<string, { signature: string; id: string; league_key?: string | null }>();
  for (const league of previous.data || []) {
    for (const match of league.matches || []) {
      const key = buildMatchKey(match);
      previousIndex.set(key, {
        signature: buildMatchSignature(match),
        id: match.id || key,
        league_key: match.league_key || league.league_key || resolveLeagueKey(match.league),
      });
    }
  }

  const changed: Match[] = [];
  const leagueKeys = new Set<string>();

  for (const league of next.data || []) {
    for (const match of league.matches || []) {
      const key = buildMatchKey(match);
      const signature = buildMatchSignature(match);
      const previousEntry = previousIndex.get(key);
      if (!previousEntry || previousEntry.signature !== signature) {
        changed.push(match);
        const keyValue = match.league_key || league.league_key || resolveLeagueKey(match.league);
        if (keyValue) {
          leagueKeys.add(keyValue);
        }
      }
      if (previousEntry) {
        previousIndex.delete(key);
      }
    }
  }

  const removed: string[] = [];
  for (const entry of previousIndex.values()) {
    removed.push(entry.id);
    if (entry.league_key) {
      leagueKeys.add(entry.league_key);
    }
  }

  if (changed.length === 0 && removed.length === 0) {
    return null;
  }

  if (changed.length + removed.length > STREAM_DELTA_LIMIT) {
    return {
      full_refresh: true,
      reason: 'delta_too_large',
      count: changed.length + removed.length,
    };
  }

  return {
    matches: changed,
    removed_ids: removed,
    league_keys: Array.from(leagueKeys),
  };
}

function buildOddsDeltaPartial(previous: OddsResponse | null, next: OddsResponse): OddsDelta | null {
  const total = next?.meta?.total_matches || 0;
  if (!next?.data?.length) return null;
  if (!previous?.data?.length) {
    return { full_refresh: true, reason: 'fast_no_previous_cache', count: total };
  }

  const previousIndex = new Map<string, { signature: string; league_key?: string | null }>();
  for (const league of previous.data || []) {
    for (const match of league.matches || []) {
      const key = buildMatchKey(match);
      previousIndex.set(key, {
        signature: buildMatchSignature(match),
        league_key: match.league_key || league.league_key || resolveLeagueKey(match.league),
      });
    }
  }

  const changed: Match[] = [];
  const leagueKeys = new Set<string>();

  for (const league of next.data || []) {
    for (const match of league.matches || []) {
      const key = buildMatchKey(match);
      const signature = buildMatchSignature(match);
      const previousEntry = previousIndex.get(key);
      if (!previousEntry || previousEntry.signature !== signature) {
        changed.push(match);
        const keyValue = match.league_key || league.league_key || resolveLeagueKey(match.league);
        if (keyValue) {
          leagueKeys.add(keyValue);
        }
      }
    }
  }

  if (changed.length === 0) {
    return null;
  }

  if (changed.length > STREAM_DELTA_LIMIT) {
    return {
      full_refresh: true,
      reason: 'fast_delta_limit',
      count: changed.length,
    };
  }

  return {
    matches: changed,
    removed_ids: [],
    league_keys: Array.from(leagueKeys),
  };
}

function mergeOddsResponses(base: OddsResponse, overlay: OddsResponse): OddsResponse {
  const baseData = attachLeagueKeys(base.data || []);
  const overlayData = attachLeagueKeys(overlay.data || []);
  const leagueMap = new Map<string, LeagueGroup>();

  const resolveGroupKey = (group: LeagueGroup): string | null => {
    return group.league_key || resolveLeagueKey(group.league) || slugify(group.league);
  };

  for (const league of baseData) {
    const key = resolveGroupKey(league);
    if (!key) continue;
    leagueMap.set(key, { ...league, matches: [...(league.matches || [])] });
  }

  for (const league of overlayData) {
    const key = resolveGroupKey(league);
    if (!key) continue;
    const existing = leagueMap.get(key) || {
      league: league.league,
      league_key: league.league_key || key,
      matches: [],
    };
    const matchMap = new Map<string, Match>();
    for (const match of existing.matches || []) {
      matchMap.set(buildMatchKey(match), match);
    }
    for (const match of league.matches || []) {
      matchMap.set(buildMatchKey(match), match);
    }
    const mergedLeague: LeagueGroup = {
      ...existing,
      league: existing.league || league.league,
      league_key: existing.league_key || league.league_key || key,
      matches: Array.from(matchMap.values()),
    };
    leagueMap.set(key, mergedLeague);
  }

  const mergedData = Array.from(leagueMap.values());
  const totalMatches = mergedData.reduce((sum, league) => sum + (league.matches?.length || 0), 0);

  const fullUpdated = base.meta?.last_updated;
  const fastUpdated = overlay.meta?.last_updated;
  const lastUpdated = [fullUpdated, fastUpdated].filter(Boolean).sort().pop() || new Date().toISOString();

  return {
    ...base,
    data: mergedData,
    meta: {
      ...base.meta,
      total_matches: totalMatches,
      last_updated: lastUpdated,
      last_updated_full: fullUpdated,
      last_updated_fast: fastUpdated,
      cache_ttl: Math.min(base.meta?.cache_ttl ?? CACHE_TTL, overlay.meta?.cache_ttl ?? FAST_CACHE_TTL_SECONDS),
      cache_ttl_full: base.meta?.cache_ttl,
      cache_ttl_fast: overlay.meta?.cache_ttl,
    },
  };
}

async function broadcastOddsUpdate(env: Env, payload: Record<string, unknown>): Promise<void> {
  try {
    const id = env.ODDS_STREAM.idFromName('odds-stream');
    const stub = env.ODDS_STREAM.get(id);
    await stub.fetch('https://oddswize.stream/broadcast', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    console.warn('Odds stream broadcast failed:', error);
  }
}

function parseScoreValue(value: unknown): number | null {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : null;
}

function toEpochSeconds(value: string | null | undefined): number | null {
  if (!value) return null;
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) return null;
  return Math.floor(parsed / 1000);
}

async function fetchEspnScoreboard(leagueId: string): Promise<any | null> {
  const url = `${ESPN_SCOREBOARD_BASE}/${leagueId}/scoreboard`;
  try {
    const response = await fetch(url, {
      cf: { cacheTtl: LIVE_SCORE_TTL_SECONDS, cacheEverything: true },
    });
    if (!response.ok) {
      console.warn(`Failed to fetch ESPN scoreboard for ${leagueId}: ${response.status}`);
      return null;
    }
    return await response.json();
  } catch (error) {
    console.warn(`Failed to fetch ESPN scoreboard for ${leagueId}:`, error);
    return null;
  }
}

function mapScoreboardEvents(
  leagueKey: string,
  leagueName: string,
  payload: any,
  stateFilter: Set<string> | null
): LiveScoreEvent[] {
  const events = Array.isArray(payload?.events) ? payload.events : [];
  const mapped: LiveScoreEvent[] = [];

  for (const event of events) {
    const competition = Array.isArray(event?.competitions) ? event.competitions[0] : null;
    const competitors = Array.isArray(competition?.competitors) ? competition.competitors : [];
    const home = competitors.find((comp: any) => comp?.homeAway === 'home');
    const away = competitors.find((comp: any) => comp?.homeAway === 'away');
    const homeName = home?.team?.shortDisplayName || home?.team?.displayName || home?.team?.name;
    const awayName = away?.team?.shortDisplayName || away?.team?.displayName || away?.team?.name;
    if (!homeName || !awayName) continue;

    const statusType = event?.status?.type || {};
    const state = (statusType.state || '').toLowerCase();
    if (stateFilter && (!state || !stateFilter.has(state))) {
      continue;
    }

    const detail = statusType.shortDetail || statusType.detail || statusType.description || null;
    const clock = event?.status?.displayClock || event?.status?.clock || null;
    const startTime = toEpochSeconds(event?.date || competition?.date);

    mapped.push({
      league_key: leagueKey,
      league: leagueName,
      event_id: event?.id,
      start_time: startTime,
      home_team: homeName,
      away_team: awayName,
      home_score: parseScoreValue(home?.score),
      away_score: parseScoreValue(away?.score),
      state: state || null,
      detail,
      clock,
    });
  }

  return mapped;
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
function jsonResponse(
  data: unknown,
  status = 200,
  env?: Env,
  extraHeaders: HeadersInit = {}
): Response {
  const headers = new Headers(env ? corsHeaders(env) : undefined);
  headers.set('Content-Type', 'application/json');

  const extra = new Headers(extraHeaders);
  extra.forEach((value, key) => headers.set(key, value));

  return new Response(JSON.stringify(data), { status, headers });
}

function buildCacheHeaders(
  prefix: string,
  meta?: { last_updated?: string; cache_ttl?: number }
): Record<string, string> {
  const lastUpdated = meta?.last_updated || new Date().toISOString();
  const ttlSeconds = Math.max(60, Math.floor(meta?.cache_ttl || CACHE_TTL));
  const maxAge = Math.min(300, ttlSeconds);
  const staleWhileRevalidate = Math.max(0, ttlSeconds - maxAge);
  const lastModified = new Date(lastUpdated).toUTCString();
  const safePrefix = prefix.replace(/[^a-z0-9-]+/gi, '-');

  return {
    'Cache-Control': `public, max-age=${maxAge}, stale-while-revalidate=${staleWhileRevalidate}`,
    'ETag': `W/"${safePrefix}-${lastUpdated}"`,
    'Last-Modified': lastModified,
  };
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

function handleOddsStream(request: Request, env: Env): Response {
  const id = env.ODDS_STREAM.idFromName('odds-stream');
  const stub = env.ODDS_STREAM.get(id);
  return stub.fetch(request);
}

function getClientIp(request: Request): string {
  const cfIp = request.headers.get('CF-Connecting-IP');
  if (cfIp) return cfIp;
  const forwarded = request.headers.get('X-Forwarded-For');
  if (!forwarded) return 'unknown';
  return forwarded.split(',')[0].trim() || 'unknown';
}

async function hashValue(value: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(value);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
}

async function ensureCommentsSchema(env: Env): Promise<void> {
  if (commentsSchemaReady) return;
  const schema = `
    CREATE TABLE IF NOT EXISTS comments (
      id TEXT PRIMARY KEY,
      match_id TEXT NOT NULL,
      match_name TEXT,
      league TEXT,
      author_name TEXT NOT NULL,
      author_id TEXT,
      content TEXT NOT NULL,
      prediction TEXT,
      likes INTEGER DEFAULT 0,
      status TEXT DEFAULT 'approved',
      ip_hash TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS comment_likes (
      comment_id TEXT NOT NULL,
      ip_hash TEXT NOT NULL,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (comment_id, ip_hash)
    );
    CREATE INDEX IF NOT EXISTS idx_comments_match ON comments(match_id, created_at);
  `;
  await env.D1.exec(schema);
  commentsSchemaReady = true;
}

function sanitizeComment(content: string): string {
  return (content || '')
    .replace(/<[^>]*>/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

async function verifyTurnstile(token: string | null, request: Request, env: Env): Promise<{ success: boolean; message?: string }> {
  if (!env.TURNSTILE_SECRET) {
    return { success: true };
  }
  if (!token) {
    return { success: false, message: 'Captcha required' };
  }
  const formData = new URLSearchParams();
  formData.append('secret', env.TURNSTILE_SECRET);
  formData.append('response', token);
  const ip = getClientIp(request);
  if (ip && ip !== 'unknown') {
    formData.append('remoteip', ip);
  }
  const response = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
    method: 'POST',
    body: formData,
  });
  const data = await response.json<{ success?: boolean; 'error-codes'?: string[] }>();
  if (!data?.success) {
    return { success: false, message: data?.['error-codes']?.join(', ') || 'Captcha failed' };
  }
  return { success: true };
}

async function listComments(request: Request, env: Env): Promise<Response> {
  await ensureCommentsSchema(env);
  const url = new URL(request.url);
  const matchId = url.searchParams.get('match_id');
  if (!matchId) return errorResponse('match_id is required', 400, env);
  const limit = Math.min(parseInt(url.searchParams.get('limit') || '20', 10), 50);
  const offset = Math.max(parseInt(url.searchParams.get('offset') || '0', 10), 0);

  const result = await env.D1.prepare(
    `SELECT id, match_id, match_name, league, author_name, content, prediction, likes, created_at
     FROM comments
     WHERE match_id = ? AND status = 'approved'
     ORDER BY datetime(created_at) DESC
     LIMIT ? OFFSET ?`
  ).bind(matchId, limit, offset).all();

  return jsonResponse({ success: true, data: result.results || [], meta: { count: result.results?.length || 0 } }, 200, env);
}

async function createComment(request: Request, env: Env): Promise<Response> {
  await ensureCommentsSchema(env);
  const body = await request.json() as {
    match_id?: string;
    match_name?: string;
    league?: string;
    author_name?: string;
    author_id?: string;
    content?: string;
    prediction?: string;
    turnstile_token?: string;
  };

  const matchId = body.match_id?.trim();
  const authorName = body.author_name?.trim();
  const content = sanitizeComment(body.content || '');

  if (!matchId) return errorResponse('match_id is required', 400, env);
  if (!authorName) return errorResponse('author_name is required', 400, env);
  if (!content || content.length < 3) return errorResponse('comment is too short', 400, env);
  if (content.length > 500) return errorResponse('comment is too long', 400, env);

  const captcha = await verifyTurnstile(body.turnstile_token || null, request, env);
  if (!captcha.success) {
    return errorResponse(captcha.message || 'Captcha failed', 400, env);
  }

  const ip = getClientIp(request);
  const ipHash = await hashValue(ip || 'unknown');

  const lastComment = await env.D1.prepare(
    `SELECT created_at FROM comments WHERE ip_hash = ? ORDER BY datetime(created_at) DESC LIMIT 1`
  ).bind(ipHash).first() as { created_at?: string } | null;

  if (lastComment?.created_at) {
    const lastTime = new Date(lastComment.created_at).getTime();
    if (!Number.isNaN(lastTime)) {
      const diffSeconds = (Date.now() - lastTime) / 1000;
      if (diffSeconds < COMMENTS_RATE_LIMIT_SECONDS) {
        return errorResponse('Slow down and try again', 429, env);
      }
    }
  }

  const daily = await env.D1.prepare(
    `SELECT COUNT(1) as count FROM comments WHERE ip_hash = ? AND created_at >= datetime('now','-24 hours')`
  ).bind(ipHash).first() as { count?: number } | null;

  if ((daily?.count || 0) >= COMMENTS_DAILY_LIMIT) {
    return errorResponse('Daily comment limit reached', 429, env);
  }

  const id = crypto.randomUUID();
  const createdAt = new Date().toISOString();
  const prediction = body.prediction?.trim() || null;

  await env.D1.prepare(
    `INSERT INTO comments (id, match_id, match_name, league, author_name, author_id, content, prediction, likes, status, ip_hash, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 'approved', ?, ?)`
  ).bind(
    id,
    matchId,
    body.match_name || null,
    body.league || null,
    authorName,
    body.author_id || null,
    content,
    prediction,
    ipHash,
    createdAt
  ).run();

  return jsonResponse({
    success: true,
    data: {
      id,
      match_id: matchId,
      match_name: body.match_name || null,
      league: body.league || null,
      author_name: authorName,
      content,
      prediction,
      likes: 0,
      created_at: createdAt,
    },
  }, 200, env);
}

async function likeComment(request: Request, env: Env, commentId: string): Promise<Response> {
  await ensureCommentsSchema(env);
  if (!commentId) return errorResponse('Comment id required', 400, env);
  const ipHash = await hashValue(getClientIp(request) || 'unknown');

  const existing = await env.D1.prepare(
    `SELECT 1 FROM comment_likes WHERE comment_id = ? AND ip_hash = ? LIMIT 1`
  ).bind(commentId, ipHash).first();

  if (existing) {
    return jsonResponse({ success: true, data: { liked: false } }, 200, env);
  }

  await env.D1.batch([
    env.D1.prepare(
      `INSERT INTO comment_likes (comment_id, ip_hash, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)`
    ).bind(commentId, ipHash),
    env.D1.prepare(
      `UPDATE comments SET likes = likes + 1 WHERE id = ?`
    ).bind(commentId),
  ]);

  return jsonResponse({ success: true, data: { liked: true } }, 200, env);
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
    let baseResponse: OddsResponse | null = null;

    if (cached) {
      const cachedResponse = cached as OddsResponse;
      baseResponse = {
        ...cachedResponse,
        data: attachLeagueKeys(cachedResponse.data || []),
      };
    } else {
      // Fall back to last known odds if the hot cache expired
      const backup = await env.ODDS_CACHE.get('last_odds', 'json');
      if (backup) {
        const backupResponse = backup as OddsResponse;
        baseResponse = {
          ...backupResponse,
          meta: {
            ...backupResponse.meta,
            cache_ttl: 60,
            stale: true,
          },
          data: attachLeagueKeys(backupResponse.data || []),
        };
      }
    }

    if (!baseResponse) {
      // If no cache, return empty data
      // In production, this would fetch from external APIs or scraped data
      baseResponse = {
        success: true,
        data: [],
        meta: {
          total_matches: 0,
          total_bookmakers: GHANA_BOOKMAKERS.length,
          last_updated: new Date().toISOString(),
          cache_ttl: CACHE_TTL,
        },
      };
    }

    const fastCached = await env.ODDS_CACHE.get('fast_odds', 'json');
    if (fastCached) {
      const fastResponse = fastCached as OddsResponse;
      return mergeOddsResponses(baseResponse, {
        ...fastResponse,
        data: attachLeagueKeys(fastResponse.data || []),
      });
    }

    return baseResponse;
  } catch (error) {
    console.error('Error fetching odds:', error);
    throw error;
  }
}

async function getLiveScores(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const leagueKeysParam = url.searchParams.get('league_keys') || url.searchParams.get('leagues');
  if (!leagueKeysParam) {
    return errorResponse('league_keys is required', 400, env);
  }

  const requestedKeys = Array.from(new Set(parseCsvParam(leagueKeysParam))).slice(0, 12);
  const stateParam = url.searchParams.get('state') || 'in';
  const requestedStates = parseCsvParam(stateParam);
  const stateFilter = stateParam.toLowerCase() === 'all' ? null : new Set(requestedStates);

  const supportedKeys = requestedKeys.filter(key => ESPN_LEAGUE_MAP[key]);
  const unsupportedKeys = requestedKeys.filter(key => !ESPN_LEAGUE_MAP[key]);
  const events: LiveScoreEvent[] = [];

  await Promise.all(
    supportedKeys.map(async (key) => {
      const league = ESPN_LEAGUE_MAP[key];
      if (!league) return;
      const payload = await fetchEspnScoreboard(league.id);
      if (!payload) return;
      const mapped = mapScoreboardEvents(key, league.name, payload, stateFilter);
      if (mapped.length) {
        events.push(...mapped);
      }
    })
  );

  const responsePayload = {
    success: true,
    data: events,
    meta: {
      requested_leagues: requestedKeys,
      supported_leagues: supportedKeys,
      unsupported_leagues: unsupportedKeys,
      total_events: events.length,
      last_updated: new Date().toISOString(),
      cache_ttl: LIVE_SCORE_TTL_SECONDS,
    },
  };

  return jsonResponse(responsePayload, 200, env, {
    'Cache-Control': `public, max-age=${LIVE_SCORE_TTL_SECONDS}, stale-while-revalidate=${LIVE_SCORE_TTL_SECONDS}`,
  });
}

function sliceOddsData(
  response: OddsResponse,
  offset: number,
  limit: number
): OddsResponse {
  if (!limit || limit <= 0) return response;

  const sliced: LeagueGroup[] = [];
  let cursor = 0;
  let returned = 0;

  for (const league of response.data || []) {
    if (returned >= limit) break;
    const matches = league.matches || [];
    const bucket: Match[] = [];

    for (const match of matches) {
      if (cursor >= offset && returned < limit) {
        bucket.push(match);
        returned += 1;
      }
      cursor += 1;
      if (returned >= limit) break;
    }

    if (bucket.length > 0) {
      sliced.push({ ...league, matches: bucket });
    }
  }

  return {
    ...response,
    data: sliced,
    meta: {
      ...response.meta,
      offset,
      limit,
      returned_matches: returned,
    },
  };
}

type OddsTimeFilter = {
  startTimeFrom?: number;
  startTimeTo?: number;
  windowHours?: number;
};

function parseEpochSeconds(value: string | null): number | undefined {
  if (!value) return undefined;
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return undefined;
  const normalized = parsed > 1_000_000_000_000 ? Math.floor(parsed / 1000) : Math.floor(parsed);
  return normalized >= 0 ? normalized : undefined;
}

function filterOddsDataByTime(
  response: OddsResponse,
  filter: OddsTimeFilter
): OddsResponse {
  const hasFrom = Number.isFinite(filter.startTimeFrom);
  const hasTo = Number.isFinite(filter.startTimeTo);
  if (!hasFrom && !hasTo) return response;

  const startFrom = filter.startTimeFrom ?? 0;
  const startTo = filter.startTimeTo ?? Number.POSITIVE_INFINITY;
  const filteredLeagues: LeagueGroup[] = [];
  let total = 0;

  for (const league of response.data || []) {
    const matches = (league.matches || []).filter((match) => {
      if (!match || !Number.isFinite(match.start_time)) return false;
      if (hasFrom && match.start_time < startFrom) return false;
      if (hasTo && match.start_time > startTo) return false;
      return true;
    });

    if (matches.length > 0) {
      filteredLeagues.push({ ...league, matches });
      total += matches.length;
    }
  }

  const totalAll = response.meta?.total_matches ?? total;

  return {
    ...response,
    data: filteredLeagues,
    meta: {
      ...response.meta,
      total_matches: total,
      total_matches_all: totalAll,
      window_hours: filter.windowHours,
      start_time_from: hasFrom ? startFrom : undefined,
      start_time_to: hasTo ? startTo : undefined,
    },
  };
}

async function batchStatements(env: Env, statements: D1PreparedStatement[], batchSize = 100): Promise<void> {
  for (let i = 0; i < statements.length; i += batchSize) {
    const chunk = statements.slice(i, i + batchSize);
    if (chunk.length) {
      await env.D1.batch(chunk);
    }
  }
}

async function storeOddsHistory(env: Env, oddsResponse: OddsResponse, runId: string): Promise<void> {
  if (!oddsResponse?.data?.length) return;
  await ensureHistorySchema(env);
  const lastUpdated = oddsResponse.meta?.last_updated || new Date().toISOString();
  const totalMatches = oddsResponse.meta?.total_matches ?? 0;
  const totalLeagues = oddsResponse.data.length;

  await env.D1.prepare(
    `INSERT OR REPLACE INTO odds_runs (run_id, last_updated, total_matches, total_leagues, created_at)
     VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)`
  ).bind(runId, lastUpdated, totalMatches, totalLeagues).run();

  const matchStmt = env.D1.prepare(
    `INSERT OR REPLACE INTO odds_matches
     (run_id, match_id, league, start_time, home_team, away_team)
     VALUES (?, ?, ?, ?, ?, ?)`
  );
  const oddsStmt = env.D1.prepare(
    `INSERT OR REPLACE INTO odds_lines
     (run_id, match_id, bookmaker, home_odds, draw_odds, away_odds)
     VALUES (?, ?, ?, ?, ?, ?)`
  );

  const matchStatements: D1PreparedStatement[] = [];
  const oddsStatements: D1PreparedStatement[] = [];

  for (const league of oddsResponse.data) {
    for (const match of league.matches || []) {
      const matchId = buildMatchKey(match);
      matchStatements.push(
        matchStmt.bind(
          runId,
          matchId,
          match.league || league.league || null,
          match.start_time || null,
          match.home_team || null,
          match.away_team || null
        )
      );

      for (const line of match.odds || []) {
        oddsStatements.push(
          oddsStmt.bind(
            runId,
            matchId,
            line.bookmaker || null,
            line.home_odds ?? null,
            line.draw_odds ?? null,
            line.away_odds ?? null
          )
        );
      }
    }
  }

  await batchStatements(env, matchStatements, 100);
  await batchStatements(env, oddsStatements, 100);
}

/**
 * Update odds data (called by external scraper or scheduled job)
 */
async function updateOddsData(
  env: Env,
  data: LeagueGroup[],
  runId?: string | null,
  lastUpdatedOverride?: string | null
): Promise<{ success: boolean; message: string }> {
  try {
    const normalizedData = attachLeagueKeys(data);
    const totalMatches = normalizedData.reduce(
      (sum, league) => sum + league.matches.length,
      0
    );
    const previous = await env.ODDS_CACHE.get('last_odds', 'json') as OddsResponse | null;
    const lastUpdated = lastUpdatedOverride || new Date().toISOString();
    const resolvedRunId = runId || lastUpdated;

    const oddsResponse: OddsResponse = {
      success: true,
      data: normalizedData,
      meta: {
        total_matches: totalMatches,
        total_bookmakers: GHANA_BOOKMAKERS.length,
        last_updated: lastUpdated,
        cache_ttl: CACHE_TTL,
      },
    };
    const delta = buildOddsDelta(previous, oddsResponse);

    // Store in KV with 1 hour TTL (scraper runs every 15min, so plenty of buffer)
    // Only store the main cache to avoid hitting KV write limits (1000/day on free tier)
    await env.ODDS_CACHE.put('all_odds', JSON.stringify(oddsResponse), {
      expirationTtl: 3600, // 1 hour
    });
    // Keep a persistent backup in case the scheduled scrape fails
    await env.ODDS_CACHE.put('last_odds', JSON.stringify(oddsResponse));

    if (delta) {
      if ('full_refresh' in delta) {
        await broadcastOddsUpdate(env, {
          type: 'odds_refresh',
          data: {
            reason: delta.reason,
            count: delta.count,
            last_updated: oddsResponse.meta.last_updated,
          },
        });
      } else if (delta.matches.length || delta.removed_ids.length) {
        await broadcastOddsUpdate(env, {
          type: 'odds_update',
          data: {
            matches: delta.matches,
            removed_ids: delta.removed_ids,
            league_keys: delta.league_keys,
            last_updated: oddsResponse.meta.last_updated,
          },
        });
      }
    }

    try {
      await storeOddsHistory(env, oddsResponse, resolvedRunId);
    } catch (error) {
      console.warn('Failed to store history in D1:', error);
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
 * Update fast odds overlay (partial updates for near-live feel)
 */
async function updateFastOddsData(
  env: Env,
  data: LeagueGroup[]
): Promise<{ success: boolean; message: string }> {
  try {
    const normalizedData = attachLeagueKeys(data);
    const totalMatches = normalizedData.reduce(
      (sum, league) => sum + league.matches.length,
      0
    );
    const previous = await env.ODDS_CACHE.get('fast_odds', 'json') as OddsResponse | null;

    const oddsResponse: OddsResponse = {
      success: true,
      data: normalizedData,
      meta: {
        total_matches: totalMatches,
        total_bookmakers: GHANA_BOOKMAKERS.length,
        last_updated: new Date().toISOString(),
        cache_ttl: FAST_CACHE_TTL_SECONDS,
      },
    };

    await env.ODDS_CACHE.put('fast_odds', JSON.stringify(oddsResponse), {
      expirationTtl: FAST_CACHE_TTL_SECONDS,
    });

    const delta = buildOddsDeltaPartial(previous, oddsResponse);
    if (delta) {
      if ('full_refresh' in delta) {
        await broadcastOddsUpdate(env, {
          type: 'odds_refresh',
          data: {
            reason: delta.reason,
            count: delta.count,
            last_updated: oddsResponse.meta.last_updated,
          },
        });
      } else if (delta.matches.length) {
        await broadcastOddsUpdate(env, {
          type: 'odds_update',
          data: {
            matches: delta.matches,
            removed_ids: [],
            league_keys: delta.league_keys,
            last_updated: oddsResponse.meta.last_updated,
          },
        });
      }
    }

    return {
      success: true,
      message: `Updated ${totalMatches} fast matches across ${data.length} leagues`,
    };
  } catch (error) {
    console.error('Error updating fast odds:', error);
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
      const limitParam = url.searchParams.get('limit');
      const offsetParam = url.searchParams.get('offset');
      const windowHoursParam = url.searchParams.get('window_hours');
      const startFromParam = url.searchParams.get('start_time_from');
      const startToParam = url.searchParams.get('start_time_to');
      const parsedLimit = limitParam ? parseInt(limitParam, 10) : 0;
      const parsedOffset = offsetParam ? parseInt(offsetParam, 10) : 0;
      const limit = Number.isFinite(parsedLimit) ? Math.max(0, Math.min(parsedLimit, 500)) : 0;
      const offset = Number.isFinite(parsedOffset) ? Math.max(0, parsedOffset) : 0;
      const parsedWindowHours = windowHoursParam ? Number(windowHoursParam) : NaN;
      const windowHours = Number.isFinite(parsedWindowHours) && parsedWindowHours > 0
        ? Math.min(parsedWindowHours, 168)
        : undefined;
      const startFrom = parseEpochSeconds(startFromParam);
      const startTo = parseEpochSeconds(startToParam);
      const nowSeconds = Math.floor(Date.now() / 1000);
      const startTimeFrom = windowHours ? nowSeconds : startFrom;
      const startTimeTo = windowHours ? nowSeconds + Math.round(windowHours * 3600) : startTo;

      const data = await getOddsData(env);
      const filteredData = filterOddsDataByTime(data, {
        startTimeFrom,
        startTimeTo,
        windowHours,
      });
      const responseData = limit > 0 ? sliceOddsData(filteredData, offset, limit) : filteredData;
      const cacheParts = ['odds'];
      if (Number.isFinite(startTimeFrom)) cacheParts.push(`from-${startTimeFrom}`);
      if (Number.isFinite(startTimeTo)) cacheParts.push(`to-${startTimeTo}`);
      if (Number.isFinite(windowHours)) cacheParts.push(`window-${windowHours}`);
      if (limit > 0) {
        cacheParts.push(`offset-${offset}`, `limit-${limit}`);
      }
      const cachePrefix = cacheParts.join('-');
      const cacheHeaders = buildCacheHeaders(cachePrefix, responseData.meta);
      const etag = cacheHeaders['ETag'];
      if (etag && request.headers.get('If-None-Match') === etag) {
        return new Response(null, {
          status: 304,
          headers: { ...corsHeaders(env), ...cacheHeaders },
        });
      }
      return jsonResponse(responseData, 200, env, cacheHeaders);
    }

    // GET /api/odds/stream - WebSocket odds stream
    if (path === '/api/odds/stream' && request.method === 'GET') {
      return handleOddsStream(request, env);
    }

    // GET /api/odds/:league - Get odds for specific league
    if (path.startsWith('/api/odds/') && request.method === 'GET') {
      const league = decodeURIComponent(path.replace('/api/odds/', ''));
      const allData = await getOddsData(env);
      const leagueData = allData.data.filter(
        (l) => l.league.toLowerCase() === league.toLowerCase()
      );

      const cacheHeaders = buildCacheHeaders(
        `odds-${league.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
        allData.meta
      );
      const etag = cacheHeaders['ETag'];
      if (etag && request.headers.get('If-None-Match') === etag) {
        return new Response(null, {
          status: 304,
          headers: { ...corsHeaders(env), ...cacheHeaders },
        });
      }

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
        env,
        cacheHeaders
      );
    }

    // GET /api/live-scores - Get live scores for leagues
    if (path === '/api/live-scores' && request.method === 'GET') {
      return getLiveScores(request, env);
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

      const cacheHeaders = buildCacheHeaders('arb', allData.meta);
      const etag = cacheHeaders['ETag'];
      if (etag && request.headers.get('If-None-Match') === etag) {
        return new Response(null, {
          status: 304,
          headers: { ...corsHeaders(env), ...cacheHeaders },
        });
      }

      return jsonResponse(response, 200, env, cacheHeaders);
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

    // GET /api/comments?match_id=... - list comments for a match
    if (path === '/api/comments' && request.method === 'GET') {
      return listComments(request, env);
    }

    // POST /api/comments - create a comment
    if (path === '/api/comments' && request.method === 'POST') {
      return createComment(request, env);
    }

    // POST /api/comments/:id/like - like a comment
    if (path.startsWith('/api/comments/') && request.method === 'POST') {
      const parts = path.split('/');
      if (parts.length === 5 && parts[4] === 'like') {
        const commentId = parts[3];
        return likeComment(request, env, commentId);
      }
    }

    // POST /api/odds/fast - Update fast odds overlay (protected endpoint)
    if (path === '/api/odds/fast' && request.method === 'POST') {
      try {
        const apiKey = request.headers.get('X-API-Key');
        if (!apiKey || apiKey !== env.API_SECRET) {
          return errorResponse('Unauthorized', 401, env);
        }

        const body = (await request.json()) as LeagueGroup[];
        if (!Array.isArray(body)) {
          return errorResponse('Invalid odds data format', 400, env);
        }

        const result = await updateFastOddsData(env, body);
        return jsonResponse(result, 200, env);
      } catch (error) {
        console.error('Error in /api/odds/fast:', error);
        return errorResponse(`Fast update failed: ${error}`, 500, env);
      }
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
        const runId = request.headers.get('X-Run-Id') || null;
        const runUpdated = request.headers.get('X-Run-Updated') || null;
        const result = await updateOddsData(env, body, runId, runUpdated);
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

// ---------------------------------------------------------------------------
// D1 odds history
// ---------------------------------------------------------------------------

async function listHistoryRuns(request: Request, env: Env): Promise<Response> {
  if (!authorizeHistoryRead(request, env)) {
    return errorResponse('Unauthorized', 401, env);
  }
  await ensureHistorySchema(env);
  const url = new URL(request.url);
  const limit = Math.min(parseInt(url.searchParams.get('limit') || '200', 10), 1000);
  const offset = parseInt(url.searchParams.get('offset') || '0', 10);

  const res = await env.D1.prepare(
    `SELECT run_id, last_updated, total_matches, total_leagues
     FROM odds_runs
     ORDER BY last_updated DESC
     LIMIT ? OFFSET ?`
  ).bind(limit, offset).all();

  return jsonResponse({
    success: true,
    data: res.results || [],
    meta: { limit, offset, returned: res.results?.length || 0 },
  }, 200, env);
}

async function listHistoryOdds(request: Request, env: Env): Promise<Response> {
  if (!authorizeHistoryRead(request, env)) {
    return errorResponse('Unauthorized', 401, env);
  }
  await ensureHistorySchema(env);
  const url = new URL(request.url);

  const limit = Math.min(parseInt(url.searchParams.get('limit') || '5000', 10), 25000);
  const offset = parseInt(url.searchParams.get('offset') || '0', 10);
  const runStart = url.searchParams.get('run_start');
  const runEnd = url.searchParams.get('run_end');
  const matchStart = parseEpochSeconds(url.searchParams.get('match_start'));
  const matchEnd = parseEpochSeconds(url.searchParams.get('match_end'));
  const league = url.searchParams.get('league');
  const bookmaker = url.searchParams.get('bookmaker');

  const filters: string[] = [];
  const params: any[] = [];
  if (runStart) { filters.push('r.last_updated >= ?'); params.push(runStart); }
  if (runEnd) { filters.push('r.last_updated <= ?'); params.push(runEnd); }
  if (Number.isFinite(matchStart)) { filters.push('m.start_time >= ?'); params.push(matchStart); }
  if (Number.isFinite(matchEnd)) { filters.push('m.start_time <= ?'); params.push(matchEnd); }
  if (league) { filters.push('m.league = ?'); params.push(league); }
  if (bookmaker) { filters.push('o.bookmaker = ?'); params.push(bookmaker); }

  const where = filters.length ? `WHERE ${filters.join(' AND ')}` : '';
  const sql = `
    SELECT
      r.run_id,
      r.last_updated,
      m.match_id,
      m.league,
      m.start_time,
      m.home_team,
      m.away_team,
      o.bookmaker,
      o.home_odds,
      o.draw_odds,
      o.away_odds
    FROM odds_lines o
    JOIN odds_matches m ON o.run_id = m.run_id AND o.match_id = m.match_id
    JOIN odds_runs r ON o.run_id = r.run_id
    ${where}
    ORDER BY r.last_updated DESC, m.start_time ASC
    LIMIT ? OFFSET ?
  `;
  params.push(limit, offset);

  const res = await env.D1.prepare(sql).bind(...params).all();

  return jsonResponse({
    success: true,
    data: res.results || [],
    meta: { limit, offset, returned: res.results?.length || 0 },
  }, 200, env);
}

async function handleHistory(request: Request, env: Env, path: string): Promise<Response> {
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders(env) });
  }
  if (path === '/api/history/runs' && request.method === 'GET') {
    return listHistoryRuns(request, env);
  }
  if (path === '/api/history/odds' && request.method === 'GET') {
    return listHistoryOdds(request, env);
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
    if (url.pathname.startsWith('/api/history/')) {
      return handleHistory(request, env, url.pathname);
    }
    if (url.pathname.startsWith('/api/canonical/')) {
      return handleCanonical(request, env, url.pathname);
    }
    return handleRequest(request, env);
  },

  async scheduled(controller: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
    await handleScheduled(controller, env, ctx);
  },
};

export { OddsStream };
