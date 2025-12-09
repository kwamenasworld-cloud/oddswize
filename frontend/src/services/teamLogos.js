/**
 * Team Logo Service
 * Automatically fetches team logos from TheSportsDB API
 */

// TheSportsDB free API (no key required for basic usage)
const SPORTSDB_API = 'https://www.thesportsdb.com/api/v1/json/3';

// Local cache for team logos (persisted to localStorage)
const CACHE_KEY = 'oddswize_team_logos';
const CACHE_EXPIRY = 7 * 24 * 60 * 60 * 1000; // 7 days

// Load cache from localStorage
const loadCache = () => {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (cached) {
      const data = JSON.parse(cached);
      // Check if cache is expired
      if (Date.now() - data.timestamp < CACHE_EXPIRY) {
        return data.logos;
      }
    }
  } catch (e) {
    console.log('Cache load error:', e);
  }
  return {};
};

// Save cache to localStorage
const saveCache = (logos) => {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({
      timestamp: Date.now(),
      logos
    }));
  } catch (e) {
    console.log('Cache save error:', e);
  }
};

// In-memory cache
let logoCache = loadCache();

// Common team name mappings for better matching
const TEAM_NAME_MAPPINGS = {
  'man utd': 'Manchester United',
  'man united': 'Manchester United',
  'man city': 'Manchester City',
  'spurs': 'Tottenham',
  'tottenham hotspur': 'Tottenham',
  'wolves': 'Wolverhampton',
  'wolverhampton wanderers': 'Wolverhampton',
  'brighton hove albion': 'Brighton',
  'brighton & hove albion': 'Brighton',
  'west ham united': 'West Ham',
  'newcastle united': 'Newcastle',
  'nottm forest': 'Nottingham Forest',
  'nott forest': 'Nottingham Forest',
  'nottingham': 'Nottingham Forest',
  'sheff utd': 'Sheffield United',
  'sheff united': 'Sheffield United',
  'leicester city': 'Leicester',
  'crystal palace': 'Crystal Palace',
  'aston villa': 'Aston Villa',
  'bayern munchen': 'Bayern Munich',
  'bayern münchen': 'Bayern Munich',
  'borussia dortmund': 'Dortmund',
  'borussia m\'gladbach': 'Borussia Monchengladbach',
  'rb leipzig': 'RB Leipzig',
  'bayer leverkusen': 'Leverkusen',
  'eintracht frankfurt': 'Frankfurt',
  'atletico madrid': 'Atletico Madrid',
  'atlético madrid': 'Atletico Madrid',
  'athletic bilbao': 'Athletic Bilbao',
  'athletic club': 'Athletic Bilbao',
  'real sociedad': 'Real Sociedad',
  'real betis': 'Real Betis',
  'celta vigo': 'Celta Vigo',
  'deportivo alaves': 'Alaves',
  'paris saint germain': 'Paris Saint-Germain',
  'paris sg': 'Paris Saint-Germain',
  'psg': 'Paris Saint-Germain',
  'olympique lyon': 'Lyon',
  'olympique lyonnais': 'Lyon',
  'olympique marseille': 'Marseille',
  'as monaco': 'Monaco',
  'as roma': 'Roma',
  'ac milan': 'AC Milan',
  'inter milan': 'Inter',
  'internazionale': 'Inter',
  'juventus fc': 'Juventus',
  'atalanta bc': 'Atalanta',
  'ssc napoli': 'Napoli',
  'ss lazio': 'Lazio',
  'accra hearts': 'Hearts of Oak',
  'hearts of oak': 'Hearts of Oak',
  'asante kotoko': 'Asante Kotoko',
  'kotoko': 'Asante Kotoko',
};

/**
 * Normalize team name for searching
 */
const normalizeTeamName = (name) => {
  if (!name) return '';
  let normalized = name.toLowerCase().trim();

  // Check mappings
  if (TEAM_NAME_MAPPINGS[normalized]) {
    return TEAM_NAME_MAPPINGS[normalized];
  }

  // Remove common suffixes
  normalized = normalized
    .replace(/\s*(fc|sc|ac|cf|afc|united|city)$/i, '')
    .trim();

  // Check mappings again after cleaning
  if (TEAM_NAME_MAPPINGS[normalized]) {
    return TEAM_NAME_MAPPINGS[normalized];
  }

  // Return original with proper casing
  return name.trim();
};

/**
 * Fetch team logo from TheSportsDB
 */
const fetchTeamLogo = async (teamName) => {
  const searchName = normalizeTeamName(teamName);

  // Check cache first
  const cacheKey = searchName.toLowerCase();
  if (logoCache[cacheKey]) {
    return logoCache[cacheKey];
  }

  try {
    const response = await fetch(
      `${SPORTSDB_API}/searchteams.php?t=${encodeURIComponent(searchName)}`,
      { timeout: 5000 }
    );

    if (!response.ok) {
      throw new Error('API request failed');
    }

    const data = await response.json();

    if (data.teams && data.teams.length > 0) {
      // Get the first matching team
      const team = data.teams[0];
      const logoUrl = team.strTeamBadge || team.strTeamLogo || null;

      if (logoUrl) {
        // Cache the result
        logoCache[cacheKey] = logoUrl;
        saveCache(logoCache);
        return logoUrl;
      }
    }

    // Cache null result to avoid repeated failed requests
    logoCache[cacheKey] = null;
    saveCache(logoCache);
    return null;

  } catch (error) {
    console.log(`Failed to fetch logo for ${teamName}:`, error.message);
    return null;
  }
};

/**
 * Get team logo (from cache or fetch)
 */
export const getTeamLogo = async (teamName) => {
  const cacheKey = normalizeTeamName(teamName).toLowerCase();

  // Return cached value if exists (including null for failed lookups)
  if (cacheKey in logoCache) {
    return logoCache[cacheKey];
  }

  // Fetch from API
  return await fetchTeamLogo(teamName);
};

/**
 * Preload logos for multiple teams
 */
export const preloadTeamLogos = async (teamNames) => {
  const uniqueTeams = [...new Set(teamNames.filter(Boolean))];
  const uncached = uniqueTeams.filter(name => {
    const key = normalizeTeamName(name).toLowerCase();
    return !(key in logoCache);
  });

  // Batch fetch with rate limiting (max 5 concurrent)
  const batchSize = 5;
  for (let i = 0; i < uncached.length; i += batchSize) {
    const batch = uncached.slice(i, i + batchSize);
    await Promise.all(batch.map(name => fetchTeamLogo(name)));
    // Small delay between batches to avoid rate limiting
    if (i + batchSize < uncached.length) {
      await new Promise(resolve => setTimeout(resolve, 200));
    }
  }
};

/**
 * Get cached logo (sync, returns null if not cached)
 */
export const getCachedLogo = (teamName) => {
  const cacheKey = normalizeTeamName(teamName).toLowerCase();
  return logoCache[cacheKey] || null;
};

/**
 * Clear logo cache
 */
export const clearLogoCache = () => {
  logoCache = {};
  localStorage.removeItem(CACHE_KEY);
};

export default {
  getTeamLogo,
  preloadTeamLogos,
  getCachedLogo,
  clearLogoCache
};
