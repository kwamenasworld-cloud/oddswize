/**
 * Team Logo Service
 * Automatically fetches team logos from TheSportsDB API
 */

// TheSportsDB free API (no key required for basic usage)
const SPORTSDB_API = 'https://www.thesportsdb.com/api/v1/json/3';

// Local cache for team logos (persisted to localStorage)
const CACHE_KEY = 'oddswize_team_logos_v2'; // v2 to clear old cache
const CACHE_EXPIRY = 7 * 24 * 60 * 60 * 1000; // 7 days

// Static logos removed - API returns correct URLs from r2.thesportsdb.com
const STATIC_LOGOS = {};

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
// Includes variations from different bookmakers (SportyBet, Betway, 1xBet, etc.)
const TEAM_NAME_MAPPINGS = {
  // English Premier League
  'man utd': 'Manchester United',
  'man united': 'Manchester United',
  'manchester united': 'Manchester United',
  'manchester utd': 'Manchester United',
  'mufc': 'Manchester United',
  'man city': 'Manchester City',
  'manchester city': 'Manchester City',
  'mcfc': 'Manchester City',
  'spurs': 'Tottenham Hotspur',
  'tottenham': 'Tottenham Hotspur',
  'tottenham hotspur': 'Tottenham Hotspur',
  'tottenham fc': 'Tottenham Hotspur',
  'wolves': 'Wolverhampton Wanderers',
  'wolverhampton': 'Wolverhampton Wanderers',
  'wolverhampton wanderers': 'Wolverhampton Wanderers',
  'wolverhampton fc': 'Wolverhampton Wanderers',
  'brighton': 'Brighton',
  'brighton hove albion': 'Brighton',
  'brighton & hove albion': 'Brighton',
  'brighton and hove albion': 'Brighton',
  'brighton fc': 'Brighton',
  'west ham': 'West Ham United',
  'west ham united': 'West Ham United',
  'west ham fc': 'West Ham United',
  'newcastle': 'Newcastle United',
  'newcastle united': 'Newcastle United',
  'newcastle utd': 'Newcastle United',
  'newcastle fc': 'Newcastle United',
  'nottm forest': 'Nottingham Forest',
  'nott forest': 'Nottingham Forest',
  'nottingham': 'Nottingham Forest',
  'nottingham forest': 'Nottingham Forest',
  'nottingham f': 'Nottingham Forest',
  'nott\'m forest': 'Nottingham Forest',
  'sheff utd': 'Sheffield United',
  'sheff united': 'Sheffield United',
  'sheffield united': 'Sheffield United',
  'sheffield utd': 'Sheffield United',
  'leicester': 'Leicester City',
  'leicester city': 'Leicester City',
  'leicester fc': 'Leicester City',
  'crystal palace': 'Crystal Palace',
  'crystal palace fc': 'Crystal Palace',
  'aston villa': 'Aston Villa',
  'aston villa fc': 'Aston Villa',
  'arsenal': 'Arsenal',
  'arsenal fc': 'Arsenal',
  'chelsea': 'Chelsea',
  'chelsea fc': 'Chelsea',
  'liverpool': 'Liverpool',
  'liverpool fc': 'Liverpool',
  'everton': 'Everton',
  'everton fc': 'Everton',
  'fulham': 'Fulham',
  'fulham fc': 'Fulham',
  'bournemouth': 'AFC Bournemouth',
  'afc bournemouth': 'AFC Bournemouth',
  'a.f.c. bournemouth': 'AFC Bournemouth',
  'brentford': 'Brentford',
  'brentford fc': 'Brentford',
  'ipswich': 'Ipswich Town',
  'ipswich town': 'Ipswich Town',
  'ipswich fc': 'Ipswich Town',
  'southampton': 'Southampton',
  'southampton fc': 'Southampton',
  'luton': 'Luton Town',
  'luton town': 'Luton Town',
  'burnley': 'Burnley',
  'burnley fc': 'Burnley',
  'sheffield wednesday': 'Sheffield Wednesday',
  'sheff wed': 'Sheffield Wednesday',
  'sheff wednesday': 'Sheffield Wednesday',

  // Spanish La Liga
  'real madrid': 'Real Madrid',
  'real madrid cf': 'Real Madrid',
  'r. madrid': 'Real Madrid',
  'barcelona': 'Barcelona',
  'fc barcelona': 'Barcelona',
  'barca': 'Barcelona',
  'sevilla': 'Sevilla',
  'sevilla fc': 'Sevilla',
  'osasuna': 'Osasuna',
  'ca osasuna': 'Osasuna',
  'atletico madrid': 'Atletico Madrid',
  'atlético madrid': 'Atletico Madrid',
  'atletico': 'Atletico Madrid',
  'atlético': 'Atletico Madrid',
  'atl. madrid': 'Atletico Madrid',
  'atl madrid': 'Atletico Madrid',
  'athletic bilbao': 'Athletic Bilbao',
  'athletic club': 'Athletic Bilbao',
  'ath bilbao': 'Athletic Bilbao',
  'ath. bilbao': 'Athletic Bilbao',
  'real sociedad': 'Real Sociedad',
  'r. sociedad': 'Real Sociedad',
  'real betis': 'Real Betis',
  'r. betis': 'Real Betis',
  'betis': 'Real Betis',
  'villarreal': 'Villarreal',
  'villarreal cf': 'Villarreal',
  'valencia': 'Valencia',
  'valencia cf': 'Valencia',
  'celta vigo': 'Celta Vigo',
  'celta': 'Celta Vigo',
  'rc celta': 'Celta Vigo',
  'getafe': 'Getafe',
  'getafe cf': 'Getafe',
  'espanyol': 'Espanyol',
  'rcd espanyol': 'Espanyol',
  'deportivo alaves': 'Alaves',
  'alaves': 'Alaves',
  'cd alaves': 'Alaves',
  'alavés': 'Alaves',
  'mallorca': 'Mallorca',
  'rcd mallorca': 'Mallorca',
  'rayo vallecano': 'Rayo Vallecano',
  'rayo': 'Rayo Vallecano',
  'girona': 'Girona',
  'girona fc': 'Girona',
  'las palmas': 'Las Palmas',
  'ud las palmas': 'Las Palmas',
  'leganes': 'Leganes',
  'leganés': 'Leganes',
  'cd leganes': 'Leganes',
  'valladolid': 'Real Valladolid',
  'real valladolid': 'Real Valladolid',

  // German Bundesliga
  'bayern': 'Bayern Munich',
  'bayern munich': 'Bayern Munich',
  'bayern munchen': 'Bayern Munich',
  'bayern münchen': 'Bayern Munich',
  'fc bayern': 'Bayern Munich',
  'fc bayern munich': 'Bayern Munich',
  'fc bayern munchen': 'Bayern Munich',
  'fc bayern münchen': 'Bayern Munich',
  'dortmund': 'Borussia Dortmund',
  'borussia dortmund': 'Borussia Dortmund',
  'bvb': 'Borussia Dortmund',
  'b. dortmund': 'Borussia Dortmund',
  'gladbach': 'Borussia Monchengladbach',
  'borussia m\'gladbach': 'Borussia Monchengladbach',
  'monchengladbach': 'Borussia Monchengladbach',
  'mönchengladbach': 'Borussia Monchengladbach',
  'b. monchengladbach': 'Borussia Monchengladbach',
  'borussia mgladbach': 'Borussia Monchengladbach',
  'rb leipzig': 'RB Leipzig',
  'leipzig': 'RB Leipzig',
  'rasenballsport leipzig': 'RB Leipzig',
  'leverkusen': 'Bayer Leverkusen',
  'bayer leverkusen': 'Bayer Leverkusen',
  'b. leverkusen': 'Bayer Leverkusen',
  'bayer 04': 'Bayer Leverkusen',
  'bayer 04 leverkusen': 'Bayer Leverkusen',
  'frankfurt': 'Eintracht Frankfurt',
  'eintracht frankfurt': 'Eintracht Frankfurt',
  'e. frankfurt': 'Eintracht Frankfurt',
  'wolfsburg': 'VfL Wolfsburg',
  'vfl wolfsburg': 'VfL Wolfsburg',
  'hoffenheim': 'TSG Hoffenheim',
  'tsg hoffenheim': 'TSG Hoffenheim',
  '1899 hoffenheim': 'TSG Hoffenheim',
  'freiburg': 'SC Freiburg',
  'sc freiburg': 'SC Freiburg',
  'mainz': 'Mainz 05',
  'mainz 05': 'Mainz 05',
  'fsv mainz': 'Mainz 05',
  '1. fsv mainz 05': 'Mainz 05',
  'augsburg': 'FC Augsburg',
  'fc augsburg': 'FC Augsburg',
  'stuttgart': 'VfB Stuttgart',
  'vfb stuttgart': 'VfB Stuttgart',
  'union berlin': 'Union Berlin',
  '1. fc union berlin': 'Union Berlin',
  'fc union berlin': 'Union Berlin',
  'werder bremen': 'Werder Bremen',
  'sv werder bremen': 'Werder Bremen',
  'bremen': 'Werder Bremen',
  'cologne': 'FC Koln',
  'koln': 'FC Koln',
  'köln': 'FC Koln',
  '1. fc koln': 'FC Koln',
  '1. fc köln': 'FC Koln',
  'fc cologne': 'FC Koln',
  'heidenheim': 'FC Heidenheim',
  '1. fc heidenheim': 'FC Heidenheim',
  'fc heidenheim 1846': 'FC Heidenheim',
  'darmstadt': 'Darmstadt 98',
  'sv darmstadt': 'Darmstadt 98',
  'sv darmstadt 98': 'Darmstadt 98',
  'bochum': 'VfL Bochum',
  'vfl bochum': 'VfL Bochum',

  // French Ligue 1
  'psg': 'Paris Saint-Germain',
  'paris': 'Paris Saint-Germain',
  'paris saint germain': 'Paris Saint-Germain',
  'paris sg': 'Paris Saint-Germain',
  'paris saint-germain': 'Paris Saint-Germain',
  'lyon': 'Lyon',
  'olympique lyon': 'Lyon',
  'olympique lyonnais': 'Lyon',
  'ol': 'Lyon',
  'ol lyon': 'Lyon',
  'marseille': 'Marseille',
  'olympique marseille': 'Marseille',
  'om': 'Marseille',
  'om marseille': 'Marseille',
  'monaco': 'Monaco',
  'as monaco': 'Monaco',
  'asm': 'Monaco',
  'lille': 'Lille',
  'losc lille': 'Lille',
  'losc': 'Lille',
  'nice': 'Nice',
  'ogc nice': 'Nice',
  'lens': 'RC Lens',
  'rc lens': 'RC Lens',
  'rennes': 'Rennes',
  'stade rennais': 'Rennes',
  'strasbourg': 'Strasbourg',
  'rc strasbourg': 'Strasbourg',
  'nantes': 'Nantes',
  'fc nantes': 'Nantes',
  'reims': 'Reims',
  'stade de reims': 'Reims',
  'stade reims': 'Reims',
  'montpellier': 'Montpellier',
  'montpellier hsc': 'Montpellier',
  'toulouse': 'Toulouse',
  'toulouse fc': 'Toulouse',
  'brest': 'Brest',
  'stade brestois': 'Brest',
  'le havre': 'Le Havre',
  'le havre ac': 'Le Havre',
  'lorient': 'Lorient',
  'fc lorient': 'Lorient',
  'clermont': 'Clermont Foot',
  'clermont foot': 'Clermont Foot',
  'metz': 'FC Metz',
  'fc metz': 'FC Metz',

  // Italian Serie A
  'inter': 'Inter Milan',
  'inter milan': 'Inter Milan',
  'internazionale': 'Inter Milan',
  'fc internazionale': 'Inter Milan',
  'inter milano': 'Inter Milan',
  'milan': 'AC Milan',
  'ac milan': 'AC Milan',
  'a.c. milan': 'AC Milan',
  'juventus': 'Juventus',
  'juventus fc': 'Juventus',
  'juve': 'Juventus',
  'napoli': 'Napoli',
  'ssc napoli': 'Napoli',
  'roma': 'AS Roma',
  'as roma': 'AS Roma',
  'a.s. roma': 'AS Roma',
  'lazio': 'Lazio',
  'ss lazio': 'Lazio',
  's.s. lazio': 'Lazio',
  'atalanta': 'Atalanta',
  'atalanta bc': 'Atalanta',
  'atalanta bergamo': 'Atalanta',
  'fiorentina': 'Fiorentina',
  'acf fiorentina': 'Fiorentina',
  'torino': 'Torino',
  'torino fc': 'Torino',
  'bologna': 'Bologna',
  'bologna fc': 'Bologna',
  'udinese': 'Udinese',
  'udinese calcio': 'Udinese',
  'sassuolo': 'Sassuolo',
  'us sassuolo': 'Sassuolo',
  'verona': 'Verona',
  'hellas verona': 'Verona',
  'h. verona': 'Verona',
  'genoa': 'Genoa',
  'genoa cfc': 'Genoa',
  'cagliari': 'Cagliari',
  'cagliari calcio': 'Cagliari',
  'empoli': 'Empoli',
  'empoli fc': 'Empoli',
  'lecce': 'Lecce',
  'us lecce': 'Lecce',
  'monza': 'Monza',
  'ac monza': 'Monza',
  'como': 'Como',
  'como 1907': 'Como',
  'parma': 'Parma',
  'parma calcio': 'Parma',
  'venezia': 'Venezia',
  'venezia fc': 'Venezia',
  'frosinone': 'Frosinone',
  'frosinone calcio': 'Frosinone',
  'salernitana': 'Salernitana',
  'us salernitana': 'Salernitana',

  // Dutch Eredivisie
  'ajax': 'Ajax',
  'afc ajax': 'Ajax',
  'ajax amsterdam': 'Ajax',
  'psv': 'PSV Eindhoven',
  'psv eindhoven': 'PSV Eindhoven',
  'feyenoord': 'Feyenoord',
  'feyenoord rotterdam': 'Feyenoord',
  'az': 'AZ Alkmaar',
  'az alkmaar': 'AZ Alkmaar',
  'twente': 'FC Twente',
  'fc twente': 'FC Twente',
  'utrecht': 'FC Utrecht',
  'fc utrecht': 'FC Utrecht',

  // Portuguese Liga
  'benfica': 'Benfica',
  'sl benfica': 'Benfica',
  'porto': 'FC Porto',
  'fc porto': 'FC Porto',
  'sporting': 'Sporting Lisbon',
  'sporting cp': 'Sporting Lisbon',
  'sporting lisbon': 'Sporting Lisbon',
  'braga': 'SC Braga',
  'sc braga': 'SC Braga',

  // African Teams - Ghana
  'accra hearts': 'Hearts of Oak',
  'hearts': 'Hearts of Oak',
  'hearts of oak': 'Hearts of Oak',
  'accra hearts of oak': 'Hearts of Oak',
  'asante kotoko': 'Asante Kotoko',
  'kotoko': 'Asante Kotoko',
  'kumasi asante kotoko': 'Asante Kotoko',
  'accra lions': 'Accra Lions',
  'lions': 'Accra Lions',
  'great olympics': 'Great Olympics',
  'olympics': 'Great Olympics',
  'medeama': 'Medeama SC',
  'medeama sc': 'Medeama SC',
  'aduana stars': 'Aduana Stars',
  'aduana': 'Aduana Stars',
  'bechem united': 'Bechem United',
  'bechem': 'Bechem United',
  'dreams fc': 'Dreams FC',
  'dreams': 'Dreams FC',
  'legon cities': 'Legon Cities',
  'legon cities fc': 'Legon Cities',
  'gold stars': 'Bibiani Gold Stars',
  'bibiani gold stars': 'Bibiani Gold Stars',
  'karela united': 'Karela United',
  'karela': 'Karela United',
  'samartex': 'Samartex FC',
  'samartex fc': 'Samartex FC',
  'berekum chelsea': 'Berekum Chelsea',

  // African Teams - Other
  'dr congo': 'DR Congo',
  'benin': 'Benin',
  'al ahly': 'Al Ahly',
  'zamalek': 'Zamalek',
  'kaizer chiefs': 'Kaizer Chiefs',
  'orlando pirates': 'Orlando Pirates',
  'mamelodi sundowns': 'Mamelodi Sundowns',
  'sundowns': 'Mamelodi Sundowns',
  'esperance': 'Esperance Tunis',
  'esperance tunis': 'Esperance Tunis',
  'tp mazembe': 'TP Mazembe',
  'mazembe': 'TP Mazembe',
  'wydad': 'Wydad Casablanca',
  'wydad casablanca': 'Wydad Casablanca',

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
  'holland': 'Netherlands',
  'belgium': 'Belgium',
  'croatia': 'Croatia',
  'morocco': 'Morocco',
  'senegal': 'Senegal',
  'ghana': 'Ghana',
  'nigeria': 'Nigeria',
  'cameroon': 'Cameroon',
  'egypt': 'Egypt',
  'south africa': 'South Africa',
  'usa': 'United States',
  'united states': 'United States',
  'mexico': 'Mexico',
  'japan': 'Japan',
  'south korea': 'South Korea',
  'korea republic': 'South Korea',
  'australia': 'Australia',
};

/**
 * Remove accents and diacritics from text
 */
const removeAccents = (str) => {
  return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
};

/**
 * Normalize team name for searching
 * Handles variations from different bookmakers (SportyBet, Betway, 1xBet, etc.)
 */
const normalizeTeamName = (name) => {
  if (!name) return '';

  // Step 1: Basic cleanup
  let normalized = name.toLowerCase().trim();

  // Step 2: Remove accents (é -> e, ü -> u, etc.)
  normalized = removeAccents(normalized);

  // Step 3: Normalize common separators and special characters
  normalized = normalized
    .replace(/[''`]/g, "'")  // Normalize quotes
    .replace(/[–—]/g, '-')   // Normalize dashes
    .replace(/\s+/g, ' ')    // Normalize whitespace
    .replace(/\./g, '')      // Remove dots (F.C. -> FC)
    .replace(/,/g, '')       // Remove commas
    .trim();

  // Step 4: Check mappings with cleaned name
  if (TEAM_NAME_MAPPINGS[normalized]) {
    return TEAM_NAME_MAPPINGS[normalized];
  }

  // Step 5: Try without common prefixes/suffixes
  const cleaned = normalized
    .replace(/^(fc|cf|ac|sc|afc|ssc|as|ss|rc|cd|ud|sd|ca|us|vfl|vfb|sv|tsv|tsg|1\.\s*fc)\s+/i, '')
    .replace(/\s+(fc|cf|ac|sc|afc|united|utd|city|town|wanderers|rovers|athletic|albion|hotspur)$/i, '')
    .trim();

  if (TEAM_NAME_MAPPINGS[cleaned]) {
    return TEAM_NAME_MAPPINGS[cleaned];
  }

  // Step 6: Try partial matching on first word (for teams like "Real Madrid CF")
  const firstWord = normalized.split(' ')[0];
  if (firstWord.length > 3 && TEAM_NAME_MAPPINGS[firstWord]) {
    return TEAM_NAME_MAPPINGS[firstWord];
  }

  // Step 7: Return original name with proper title casing
  return name.trim()
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};

/**
 * Get static logo if available
 */
const getStaticLogo = (teamName) => {
  const searchName = normalizeTeamName(teamName).toLowerCase();

  // Direct match
  if (STATIC_LOGOS[searchName]) {
    return STATIC_LOGOS[searchName];
  }

  // Try partial match
  for (const [key, url] of Object.entries(STATIC_LOGOS)) {
    if (searchName.includes(key) || key.includes(searchName)) {
      return url;
    }
  }

  return null;
};

/**
 * Fetch team logo from TheSportsDB
 */
const fetchTeamLogo = async (teamName) => {
  const searchName = normalizeTeamName(teamName);
  const cacheKey = searchName.toLowerCase();

  // Check memory cache first
  if (logoCache[cacheKey]) {
    return logoCache[cacheKey];
  }

  // Check static logos - these are reliable and don't need API calls
  const staticLogo = getStaticLogo(teamName);
  if (staticLogo) {
    logoCache[cacheKey] = staticLogo;
    saveCache(logoCache);
    return staticLogo;
  }

  // Fetch from API with proper timeout using AbortController
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 5000);

  try {

    const response = await fetch(
      `${SPORTSDB_API}/searchteams.php?t=${encodeURIComponent(searchName)}`,
      { signal: controller.signal }
    );

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`API request failed with status ${response.status}`);
    }

    const data = await response.json();

    if (data.teams && data.teams.length > 0) {
      // Get the first matching team
      const team = data.teams[0];
      // API uses strBadge (not strTeamBadge)
      const logoUrl = team.strBadge || team.strLogo || team.strTeamBadge || null;

      if (logoUrl) {
        // Cache the result
        logoCache[cacheKey] = logoUrl;
        saveCache(logoCache);
        return logoUrl;
      }
    }

    // Don't cache null for API failures - allow retry
    return null;

  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      // Request timeout
    } else {
      console.error(`[TeamLogos] Failed to fetch logo for ${teamName}:`, error.message);
    }
    return null;
  }
};

/**
 * Get team logo (from cache or fetch)
 */
export const getTeamLogo = async (teamName) => {
  if (!teamName) return null;

  const cacheKey = normalizeTeamName(teamName).toLowerCase();

  // Return cached value if it's a valid URL (not null)
  if (logoCache[cacheKey]) {
    return logoCache[cacheKey];
  }

  // Check static logos immediately
  const staticLogo = getStaticLogo(teamName);
  if (staticLogo) {
    logoCache[cacheKey] = staticLogo;
    saveCache(logoCache);
    return staticLogo;
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
  if (!teamName) return null;

  const cacheKey = normalizeTeamName(teamName).toLowerCase();

  // Check memory cache first
  if (logoCache[cacheKey]) {
    return logoCache[cacheKey];
  }

  // Check static logos (sync, no API call)
  const staticLogo = getStaticLogo(teamName);
  if (staticLogo) {
    logoCache[cacheKey] = staticLogo;
    return staticLogo;
  }

  return null;
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
