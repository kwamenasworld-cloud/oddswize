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
  // English Premier League
  'man utd': 'Manchester United',
  'man united': 'Manchester United',
  'manchester united': 'Manchester United',
  'man city': 'Manchester City',
  'manchester city': 'Manchester City',
  'spurs': 'Tottenham Hotspur',
  'tottenham': 'Tottenham Hotspur',
  'tottenham hotspur': 'Tottenham Hotspur',
  'wolves': 'Wolverhampton Wanderers',
  'wolverhampton': 'Wolverhampton Wanderers',
  'wolverhampton wanderers': 'Wolverhampton Wanderers',
  'brighton': 'Brighton',
  'brighton hove albion': 'Brighton',
  'brighton & hove albion': 'Brighton',
  'west ham': 'West Ham United',
  'west ham united': 'West Ham United',
  'newcastle': 'Newcastle United',
  'newcastle united': 'Newcastle United',
  'nottm forest': 'Nottingham Forest',
  'nott forest': 'Nottingham Forest',
  'nottingham': 'Nottingham Forest',
  'nottingham forest': 'Nottingham Forest',
  'sheff utd': 'Sheffield United',
  'sheff united': 'Sheffield United',
  'sheffield united': 'Sheffield United',
  'leicester': 'Leicester City',
  'leicester city': 'Leicester City',
  'crystal palace': 'Crystal Palace',
  'aston villa': 'Aston Villa',
  'arsenal': 'Arsenal',
  'chelsea': 'Chelsea',
  'liverpool': 'Liverpool',
  'everton': 'Everton',
  'fulham': 'Fulham',
  'bournemouth': 'AFC Bournemouth',
  'afc bournemouth': 'AFC Bournemouth',
  'brentford': 'Brentford',
  'ipswich': 'Ipswich Town',
  'ipswich town': 'Ipswich Town',
  'southampton': 'Southampton',

  // Spanish La Liga
  'real madrid': 'Real Madrid',
  'barcelona': 'Barcelona',
  'sevilla': 'Sevilla',
  'osasuna': 'Osasuna',
  'atletico madrid': 'Atletico Madrid',
  'atlético madrid': 'Atletico Madrid',
  'athletic bilbao': 'Athletic Bilbao',
  'athletic club': 'Athletic Bilbao',
  'real sociedad': 'Real Sociedad',
  'real betis': 'Real Betis',
  'villarreal': 'Villarreal',
  'valencia': 'Valencia',
  'celta vigo': 'Celta Vigo',
  'getafe': 'Getafe',
  'espanyol': 'Espanyol',
  'deportivo alaves': 'Alaves',
  'alaves': 'Alaves',
  'mallorca': 'Mallorca',
  'rayo vallecano': 'Rayo Vallecano',
  'girona': 'Girona',
  'las palmas': 'Las Palmas',
  'leganes': 'Leganes',
  'valladolid': 'Real Valladolid',

  // German Bundesliga
  'bayern': 'Bayern Munich',
  'bayern munich': 'Bayern Munich',
  'bayern munchen': 'Bayern Munich',
  'bayern münchen': 'Bayern Munich',
  'dortmund': 'Borussia Dortmund',
  'borussia dortmund': 'Borussia Dortmund',
  'gladbach': 'Borussia Monchengladbach',
  'borussia m\'gladbach': 'Borussia Monchengladbach',
  'monchengladbach': 'Borussia Monchengladbach',
  'rb leipzig': 'RB Leipzig',
  'leipzig': 'RB Leipzig',
  'leverkusen': 'Bayer Leverkusen',
  'bayer leverkusen': 'Bayer Leverkusen',
  'frankfurt': 'Eintracht Frankfurt',
  'eintracht frankfurt': 'Eintracht Frankfurt',
  'wolfsburg': 'VfL Wolfsburg',
  'hoffenheim': 'TSG Hoffenheim',
  'freiburg': 'SC Freiburg',
  'mainz': 'Mainz 05',
  'augsburg': 'FC Augsburg',
  'stuttgart': 'VfB Stuttgart',
  'union berlin': 'Union Berlin',
  'werder bremen': 'Werder Bremen',
  'cologne': 'FC Koln',
  'koln': 'FC Koln',

  // French Ligue 1
  'psg': 'Paris Saint-Germain',
  'paris': 'Paris Saint-Germain',
  'paris saint germain': 'Paris Saint-Germain',
  'paris sg': 'Paris Saint-Germain',
  'lyon': 'Lyon',
  'olympique lyon': 'Lyon',
  'olympique lyonnais': 'Lyon',
  'marseille': 'Marseille',
  'olympique marseille': 'Marseille',
  'monaco': 'Monaco',
  'as monaco': 'Monaco',
  'lille': 'Lille',
  'nice': 'Nice',
  'lens': 'RC Lens',
  'rennes': 'Rennes',
  'strasbourg': 'Strasbourg',
  'nantes': 'Nantes',
  'reims': 'Reims',
  'montpellier': 'Montpellier',
  'toulouse': 'Toulouse',
  'brest': 'Brest',

  // Italian Serie A
  'inter': 'Inter Milan',
  'inter milan': 'Inter Milan',
  'internazionale': 'Inter Milan',
  'milan': 'AC Milan',
  'ac milan': 'AC Milan',
  'juventus': 'Juventus',
  'juventus fc': 'Juventus',
  'napoli': 'Napoli',
  'ssc napoli': 'Napoli',
  'roma': 'AS Roma',
  'as roma': 'AS Roma',
  'lazio': 'Lazio',
  'ss lazio': 'Lazio',
  'atalanta': 'Atalanta',
  'atalanta bc': 'Atalanta',
  'fiorentina': 'Fiorentina',
  'torino': 'Torino',
  'bologna': 'Bologna',
  'udinese': 'Udinese',
  'sassuolo': 'Sassuolo',
  'verona': 'Verona',
  'hellas verona': 'Verona',
  'genoa': 'Genoa',
  'cagliari': 'Cagliari',
  'empoli': 'Empoli',
  'lecce': 'Lecce',
  'monza': 'Monza',
  'como': 'Como',
  'parma': 'Parma',
  'venezia': 'Venezia',

  // African Teams
  'accra hearts': 'Hearts of Oak',
  'hearts': 'Hearts of Oak',
  'hearts of oak': 'Hearts of Oak',
  'asante kotoko': 'Asante Kotoko',
  'kotoko': 'Asante Kotoko',
  'dr congo': 'DR Congo',
  'benin': 'Benin',

  // International
  'england': 'England',
  'germany': 'Germany',
  'spain': 'Spain',
  'france': 'France',
  'italy': 'Italy',
  'brazil': 'Brazil',
  'argentina': 'Argentina',
  'portugal': 'Portugal',
  'netherlands': 'Netherlands',
  'belgium': 'Belgium',
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

/**
 * Force refresh a specific team's logo
 */
export const refreshTeamLogo = async (teamName) => {
  const cacheKey = normalizeTeamName(teamName).toLowerCase();
  delete logoCache[cacheKey];
  return await fetchTeamLogo(teamName);
};

/**
 * Debug: Log cache status
 */
export const getLogoStats = () => {
  const total = Object.keys(logoCache).length;
  const withLogos = Object.values(logoCache).filter(v => v !== null).length;
  return { total, withLogos, cached: logoCache };
};

export default {
  getTeamLogo,
  preloadTeamLogos,
  getCachedLogo,
  clearLogoCache,
  refreshTeamLogo,
  getLogoStats
};
