// Centralized League Configuration
// Contains all naming variations from different bookmakers/APIs
// This ensures consistent league matching across the app

export const LEAGUES = {
  // Premier League (England)
  premier: {
    id: 'premier',
    name: 'Premier League',
    country: 'england',
    tier: 1,
    keywords: [
      'England. Premier League',
      'English Premier League',
      'EPL',
      'England Premier',
      'Barclays Premier League',
      'England 1. Premier League',
    ],
  },

  // La Liga (Spain)
  laliga: {
    id: 'laliga',
    name: 'La Liga',
    country: 'spain',
    tier: 1,
    keywords: [
      'Spain. La Liga',
      'Spain. LaLiga',
      'Spanish La Liga',
      'LaLiga Santander',
      'LaLiga EA Sports',
      'Spain Primera',
      'Spain 1. La Liga',
    ],
  },

  // Serie A (Italy)
  seriea: {
    id: 'seriea',
    name: 'Serie A',
    country: 'italy',
    tier: 1,
    keywords: [
      'Italy. Serie A',
      'Italian Serie A',
      'Serie A TIM',
      'Italy Serie A',
      'Italy 1. Serie A',
    ],
  },

  // Bundesliga (Germany)
  bundesliga: {
    id: 'bundesliga',
    name: 'Bundesliga',
    country: 'germany',
    tier: 1,
    keywords: [
      'Germany. Bundesliga',
      'German Bundesliga',
      'Bundesliga',
      '1. Bundesliga',
      'Germany Bundesliga',
    ],
  },

  // Ligue 1 (France)
  ligue1: {
    id: 'ligue1',
    name: 'Ligue 1',
    country: 'france',
    tier: 1,
    keywords: [
      'France. Ligue 1',
      'French Ligue 1',
      'Ligue 1',
      'Ligue 1 Uber Eats',
      'France Ligue 1',
    ],
  },

  // Champions League
  ucl: {
    id: 'ucl',
    name: 'Champions League',
    country: 'europe',
    tier: 1,
    keywords: [
      'UEFA Champions League',
      'UEFA. Champions League',
      'UCL',
      'Europe. Champions League',
      'UEFA Champions League. League Phase',
    ],
  },

  // Europa League
  europa: {
    id: 'europa',
    name: 'Europa League',
    country: 'europe',
    tier: 2,
    keywords: [
      'UEFA Europa League',
      'UEFA. Europa League',
      'UEL',
      'Europe. Europa League',
      'UEFA Europa League. League Phase',
    ],
  },

  // Conference League
  conference: {
    id: 'conference',
    name: 'Conference League',
    country: 'europe',
    tier: 2,
    keywords: [
      'UEFA Europa Conference League',
      'UEFA Conference League',
      'UECL',
      'UEFA. Conference League',
      'Europa Conference League',
      'International Clubs. UEFA Europa Conference League',
    ],
  },

  // English League One
  leagueone: {
    id: 'leagueone',
    name: 'League One',
    country: 'england',
    tier: 3,
    keywords: [
      'England. League One',
      'English League One',
      'EFL League One',
      'Sky Bet League One',
    ],
  },

  // English League Two
  leaguetwo: {
    id: 'leaguetwo',
    name: 'League Two',
    country: 'england',
    tier: 3,
    keywords: [
      'England. League Two',
      'English League Two',
      'EFL League Two',
      'Sky Bet League Two',
    ],
  },

  // English National League (Conference)
  nationalleague: {
    id: 'nationalleague',
    name: 'National League',
    country: 'england',
    tier: 4,
    keywords: [
      'England. Conference National',
      'England. National League',
      'National League',
      'Vanarama National League',
    ],
  },

  // Ghana Premier League
  ghana: {
    id: 'ghana',
    name: 'Ghana Premier',
    country: 'ghana',
    tier: 2,
    keywords: [
      'Ghana. Premier League',
      'Ghana Premier League',
      'Ghana Premier',
      'Ghana.',
      'GPL',
      'Ghanaian Premier League',
    ],
  },

  // FA Cup (England)
  facup: {
    id: 'facup',
    name: 'FA Cup',
    country: 'england',
    tier: 2,
    keywords: [
      'England. FA Cup',
      'FA Cup',
      'English FA Cup',
      'Emirates FA Cup',
    ],
  },

  // EFL Cup / Carabao Cup
  eflcup: {
    id: 'eflcup',
    name: 'EFL Cup',
    country: 'england',
    tier: 2,
    keywords: [
      'England. EFL Cup',
      'England. League Cup',
      'EFL Cup',
      'Carabao Cup',
      'English League Cup',
    ],
  },

  // Championship (England)
  championship: {
    id: 'championship',
    name: 'Championship',
    country: 'england',
    tier: 2,
    keywords: [
      'England. Championship',
      'English Championship',
      'Championship',
      'EFL Championship',
      'Sky Bet Championship',
    ],
  },

  // La Liga 2 (Spain)
  laliga2: {
    id: 'laliga2',
    name: 'La Liga 2',
    country: 'spain',
    tier: 3,
    keywords: [
      'Spain. La Liga 2',
      'Spain. LaLiga 2',
      'LaLiga 2',
      'Segunda Division',
      'LaLiga SmartBank',
      'LaLiga Hypermotion',
    ],
  },

  // Serie B (Italy)
  serieb: {
    id: 'serieb',
    name: 'Serie B',
    country: 'italy',
    tier: 3,
    keywords: [
      'Italy. Serie B',
      'Italian Serie B',
      'Serie B',
      'Serie BKT',
    ],
  },

  // 2. Bundesliga (Germany)
  bundesliga2: {
    id: 'bundesliga2',
    name: '2. Bundesliga',
    country: 'germany',
    tier: 3,
    keywords: [
      'Germany. 2nd Bundesliga',
      'Germany. 2. Bundesliga',
      '2. Bundesliga',
      'Bundesliga 2',
      'German 2. Bundesliga',
    ],
  },

  // 3. Liga (Germany)
  bundesliga3: {
    id: 'bundesliga3',
    name: '3. Liga',
    country: 'germany',
    tier: 4,
    keywords: [
      'Germany. 3rd Liga',
      'Germany. 3. Liga',
      '3. Liga',
      'German 3. Liga',
    ],
  },

  // Ligue 2 (France)
  ligue2: {
    id: 'ligue2',
    name: 'Ligue 2',
    country: 'france',
    tier: 3,
    keywords: [
      'France. Ligue 2',
      'French Ligue 2',
      'Ligue 2',
      'Ligue 2 BKT',
    ],
  },

  // Eredivisie (Netherlands)
  eredivisie: {
    id: 'eredivisie',
    name: 'Eredivisie',
    country: 'netherlands',
    tier: 2,
    keywords: [
      'Netherlands. Eredivisie',
      'Dutch Eredivisie',
      'Eredivisie',
      'Holland. Eredivisie',
    ],
  },

  // Primeira Liga (Portugal)
  portugal: {
    id: 'portugal',
    name: 'Primeira Liga',
    country: 'portugal',
    tier: 2,
    keywords: [
      'Portugal. Primeira Liga',
      'Portuguese Primeira Liga',
      'Primeira Liga',
      'Liga Portugal',
      'Portugal. Liga Portugal',
    ],
  },

  // Scottish Premiership
  scotland: {
    id: 'scotland',
    name: 'Scottish Premiership',
    country: 'scotland',
    tier: 2,
    keywords: [
      'Scotland. Premiership',
      'Scottish Premiership',
      'Scotland Premier',
      'SPFL Premiership',
    ],
  },

  // Belgian Pro League
  belgium: {
    id: 'belgium',
    name: 'Pro League',
    country: 'belgium',
    tier: 2,
    keywords: [
      'Belgium. Pro League',
      'Belgian Pro League',
      'Jupiler Pro League',
      'Belgium. Jupiler',
    ],
  },

  // Turkish Super Lig
  turkey: {
    id: 'turkey',
    name: 'Super Lig',
    country: 'turkey',
    tier: 2,
    keywords: [
      'Turkey. Super Lig',
      'Turkish Super Lig',
      'Super Lig',
      'Trendyol Super Lig',
    ],
  },

  // MLS (USA)
  mls: {
    id: 'mls',
    name: 'MLS',
    country: 'usa',
    tier: 2,
    keywords: [
      'USA. MLS',
      'Major League Soccer',
      'MLS',
      'USA. Major League Soccer',
    ],
  },

  // Saudi Pro League
  saudi: {
    id: 'saudi',
    name: 'Saudi Pro League',
    country: 'saudi',
    tier: 2,
    keywords: [
      'Saudi Arabia. Pro League',
      'Saudi Pro League',
      'Saudi Arabia. Saudi Pro League',
      'Roshn Saudi League',
    ],
  },

  // Brazilian Serie A
  brazil: {
    id: 'brazil',
    name: 'Brasileirao',
    country: 'brazil',
    tier: 2,
    keywords: [
      'Brazil. Serie A',
      'Brasileirao',
      'Brazilian Serie A',
      'Campeonato Brasileiro',
    ],
  },

  // Argentine Primera
  argentina: {
    id: 'argentina',
    name: 'Primera Division',
    country: 'argentina',
    tier: 2,
    keywords: [
      'Argentina. Primera',
      'Argentine Primera',
      'Liga Profesional',
      'Argentina. Liga Profesional',
    ],
  },

  // World Cup
  worldcup: {
    id: 'worldcup',
    name: 'World Cup',
    country: 'international',
    tier: 1,
    keywords: [
      'FIFA World Cup',
      'World Cup',
      'World. World Cup',
      'International. World Cup',
    ],
  },

  // AFCON
  afcon: {
    id: 'afcon',
    name: 'AFCON',
    country: 'africa',
    tier: 1,
    keywords: [
      'Africa Cup of Nations',
      'AFCON',
      'CAF. Africa Cup',
      'African Cup of Nations',
      'Africa. AFCON',
    ],
  },

  // Copa America
  copa: {
    id: 'copa',
    name: 'Copa America',
    country: 'southamerica',
    tier: 1,
    keywords: [
      'Copa America',
      'CONMEBOL Copa America',
      'South America. Copa America',
    ],
  },

  // Euro Championship
  euro: {
    id: 'euro',
    name: 'Euro Championship',
    country: 'europe',
    tier: 1,
    keywords: [
      'UEFA Euro',
      'Euro Championship',
      'European Championship',
      'UEFA European Championship',
    ],
  },
};

// Countries for filtering
export const COUNTRIES = {
  england: { id: 'england', name: 'England', flag: '🏴󠁧󠁢󠁥󠁮󠁧󠁿' },
  spain: { id: 'spain', name: 'Spain', flag: '🇪🇸' },
  italy: { id: 'italy', name: 'Italy', flag: '🇮🇹' },
  germany: { id: 'germany', name: 'Germany', flag: '🇩🇪' },
  france: { id: 'france', name: 'France', flag: '🇫🇷' },
  netherlands: { id: 'netherlands', name: 'Netherlands', flag: '🇳🇱' },
  portugal: { id: 'portugal', name: 'Portugal', flag: '🇵🇹' },
  scotland: { id: 'scotland', name: 'Scotland', flag: '🏴󠁧󠁢󠁳󠁣󠁴󠁿' },
  belgium: { id: 'belgium', name: 'Belgium', flag: '🇧🇪' },
  turkey: { id: 'turkey', name: 'Turkey', flag: '🇹🇷' },
  ghana: { id: 'ghana', name: 'Ghana', flag: '🇬🇭' },
  usa: { id: 'usa', name: 'USA', flag: '🇺🇸' },
  saudi: { id: 'saudi', name: 'Saudi Arabia', flag: '🇸🇦' },
  brazil: { id: 'brazil', name: 'Brazil', flag: '🇧🇷' },
  argentina: { id: 'argentina', name: 'Argentina', flag: '🇦🇷' },
  europe: { id: 'europe', name: 'Europe', flag: '🇪🇺' },
  international: { id: 'international', name: 'International', flag: '🌍' },
  africa: { id: 'africa', name: 'Africa', flag: '🌍' },
  southamerica: { id: 'southamerica', name: 'South America', flag: '🌎' },
};

// Popular leagues for quick filters (ordered by popularity)
export const POPULAR_LEAGUE_IDS = [
  'premier',
  'laliga',
  'ghana',
  'ucl',
  'seriea',
  'bundesliga',
  'ligue1',
  'europa',
];

// Get popular leagues config
export const getPopularLeagues = () => {
  return POPULAR_LEAGUE_IDS.map(id => LEAGUES[id]).filter(Boolean);
};

// Country name variations mapping to our country IDs
// Used for parsing "Country. League" format from APIs
const COUNTRY_NAME_TO_ID = {
  'england': 'england',
  'english': 'england',
  'spain': 'spain',
  'spanish': 'spain',
  'italy': 'italy',
  'italian': 'italy',
  'germany': 'germany',
  'german': 'germany',
  'france': 'france',
  'french': 'france',
  'netherlands': 'netherlands',
  'dutch': 'netherlands',
  'holland': 'netherlands',
  'portugal': 'portugal',
  'portuguese': 'portugal',
  'scotland': 'scotland',
  'scottish': 'scotland',
  'belgium': 'belgium',
  'belgian': 'belgium',
  'turkey': 'turkey',
  'turkish': 'turkey',
  'ghana': 'ghana',
  'ghanaian': 'ghana',
  'usa': 'usa',
  'united states': 'usa',
  'saudi arabia': 'saudi',
  'brazil': 'brazil',
  'brazilian': 'brazil',
  'argentina': 'argentina',
  'argentine': 'argentina',
  'europe': 'europe',
  'european': 'europe',
  'uefa': 'europe',
  'international': 'international',
  'international clubs': 'europe', // UEFA club competitions
  'world': 'international',
  'africa': 'africa',
  'african': 'africa',
  'caf': 'africa',
  'south america': 'southamerica',
  'conmebol': 'southamerica',
};

/**
 * Extract country/region from league string
 * Handles formats like "Country. League Name" or "Region. Competition"
 *
 * Returns: { hasPrefix: boolean, countryId: string|null }
 * - hasPrefix: true if string has "Something. League" format
 * - countryId: the mapped country ID, or null if country not recognized
 */
const extractCountryFromLeague = (leagueString) => {
  if (!leagueString) return { hasPrefix: false, countryId: null };

  // Pattern: "Country. League Name" - extract everything before first ". "
  const match = leagueString.match(/^([^.]+)\.\s*/);
  if (match) {
    const extracted = match[1].trim().toLowerCase();
    return {
      hasPrefix: true,
      countryId: COUNTRY_NAME_TO_ID[extracted] || null
    };
  }
  return { hasPrefix: false, countryId: null };
};

/**
 * Match a league string against known leagues
 * Uses country-first matching to prevent false positives
 *
 * Algorithm:
 * 1. Check if string has "Country. League" format
 * 2. If yes and country is recognized, only match leagues from that country
 * 3. If yes but country is NOT recognized (e.g., Jamaica), return null
 * 4. If no country prefix, use keyword matching with specificity scoring
 *
 * @param {string} leagueString - The league name from the API
 * @returns {object|null} - The matched league config or null
 */
export const matchLeague = (leagueString) => {
  if (!leagueString) return null;
  const lower = leagueString.toLowerCase().trim();

  // Step 1: Check for "Country. League" format
  const { hasPrefix, countryId } = extractCountryFromLeague(leagueString);

  // Step 2: If string has country prefix format
  if (hasPrefix) {
    // If country is recognized, only search that country's leagues
    if (countryId) {
      const countryLeagues = Object.values(LEAGUES).filter(
        l => l.country === countryId
      );

      for (const league of countryLeagues) {
        for (const keyword of league.keywords) {
          if (lower.includes(keyword.toLowerCase())) {
            return league;
          }
        }
      }
    }

    // Country prefix exists but either:
    // - Country not recognized (e.g., "Jamaica. Premier League")
    // - Country recognized but no matching league
    // Return null to prevent false positives
    return null;
  }

  // Step 3: No country prefix - use keyword matching with specificity
  // This handles formats like "EPL", "UCL", "Bundesliga"
  const allLeagues = Object.values(LEAGUES);
  let bestMatch = null;
  let bestMatchLength = 0;

  for (const league of allLeagues) {
    for (const keyword of league.keywords) {
      const keywordLower = keyword.toLowerCase();
      if (lower.includes(keywordLower) && keywordLower.length > bestMatchLength) {
        bestMatch = league;
        bestMatchLength = keywordLower.length;
      }
    }
  }

  return bestMatch;
};

// Check if a league string matches a specific league ID
export const isLeagueMatch = (leagueString, leagueId) => {
  if (!leagueString || !leagueId) return false;
  if (leagueId === 'all') return true;

  const league = LEAGUES[leagueId];
  if (!league) return false;

  const lower = leagueString.toLowerCase().trim();

  // Check for country prefix format
  const { hasPrefix, countryId } = extractCountryFromLeague(leagueString);

  if (hasPrefix) {
    // If country is recognized, only match if league's country matches
    if (countryId) {
      if (league.country !== countryId) return false;
    } else {
      // Country prefix exists but not recognized - don't match
      return false;
    }
  }

  // Keyword matching
  return league.keywords.some(kw => lower.includes(kw.toLowerCase()));
};

// Check if a league string matches any of the given league IDs
export const matchesAnyLeague = (leagueString, leagueIds) => {
  if (!leagueString || !leagueIds || leagueIds.length === 0) return true;
  if (leagueIds.includes('all')) return true;

  return leagueIds.some(id => isLeagueMatch(leagueString, id));
};

// Check if a league string matches a country
export const isCountryMatch = (leagueString, countryId) => {
  if (!leagueString || !countryId) return false;
  if (countryId === 'all') return true;

  // First try to extract country from "Country. League" format
  const { hasPrefix, countryId: extractedId } = extractCountryFromLeague(leagueString);
  if (hasPrefix && extractedId) {
    return extractedId === countryId;
  }

  // Then try matching via league config
  const matchedLeague = matchLeague(leagueString);
  if (matchedLeague) {
    return matchedLeague.country === countryId;
  }

  // Fallback: check if country name is in the string
  const country = COUNTRIES[countryId];
  if (country) {
    return leagueString.toLowerCase().includes(country.name.toLowerCase());
  }

  return false;
};

// Get league tier for popularity scoring (1 = highest)
export const getLeagueTier = (leagueString) => {
  const league = matchLeague(leagueString);
  return league?.tier || 4; // Default to tier 4 for unknown leagues
};

// Get all keywords for a league (useful for debugging)
export const getLeagueKeywords = (leagueId) => {
  return LEAGUES[leagueId]?.keywords || [];
};

// Get league by ID
export const getLeagueById = (leagueId) => {
  return LEAGUES[leagueId] || null;
};

// Get all leagues for a country
export const getLeaguesByCountry = (countryId) => {
  return Object.values(LEAGUES).filter(l => l.country === countryId);
};
