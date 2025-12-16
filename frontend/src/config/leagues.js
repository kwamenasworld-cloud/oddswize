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
      'England Premier League',
      'English Premier League',
      'EPL',
      'England Premier',
      'England Premiership',
      'Barclays Premier League',
      'England 1. Premier League',
      'England PL',
      'England - Premier League',
      'Premier League', // Bare "Premier League" defaults to England (most common usage)
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
      'Spain La Liga',
      'Spain. LaLiga',
      'Spain LaLiga',
      'Spanish La Liga',
      'LaLiga Santander',
      'LaLiga EA Sports',
      'Spain Primera',
      'Spain 1. La Liga',
      'Spain - La Liga',
      'Spain - LaLiga',
      'La Liga', // Bare name after normalization removes country prefix
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
      'Serie A', // Bare name after normalization removes country prefix
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
    name: 'Premier League',
    country: 'ghana',
    tier: 2,
    keywords: [
      'Ghana. Premier League',
      'Ghana Premier League',
      'Ghana. Premier',
      'Ghana Premier',
      'Ghana PL',
      'Ghana - Premier League',
      'Ghana - Premier',
      'GPL',
      'Ghanaian Premier League',
      'Ghanaian Premier',
      'Ghana.',
    ],
  },

  // Kenya Premier League
  kenya: {
    id: 'kenya',
    name: 'Premier League',
    country: 'kenya',
    tier: 3,
    keywords: [
      'Kenya. Premier League',
      'Kenya Premier League',
      'Kenya. Premier',
      'Kenya Premier',
      'Kenya PL',
      'Kenya - Premier League',
      'Kenya - Premier',
      'Kenyan Premier League',
      'Kenyan Premier',
      'FKF Premier League',
      'FKF PL',
    ],
  },

  // Uganda Premier League
  uganda: {
    id: 'uganda',
    name: 'Premier League',
    country: 'uganda',
    tier: 3,
    keywords: [
      'Uganda. Premier League',
      'Uganda Premier League',
      'Uganda. Premier',
      'Uganda Premier',
      'Uganda PL',
      'Uganda - Premier League',
      'Uganda - Premier',
      'Ugandan Premier League',
      'Ugandan Premier',
    ],
  },

  // Tanzania Premier League
  tanzania: {
    id: 'tanzania',
    name: 'Premier League',
    country: 'tanzania',
    tier: 3,
    keywords: [
      'Tanzania. Premier League',
      'Tanzania Premier League',
      'Tanzania. Premier',
      'Tanzania Premier',
      'Tanzania PL',
      'Tanzania - Premier League',
      'Tanzania - Premier',
      'Tanzanian Premier League',
      'Tanzanian Premier',
    ],
  },

  // Nigeria Premier League
  nigeria: {
    id: 'nigeria',
    name: 'Premier League',
    country: 'nigeria',
    tier: 3,
    keywords: [
      'Nigeria. Premier League',
      'Nigeria Premier League',
      'Nigeria. Premier',
      'Nigeria Premier',
      'Nigeria PL',
      'Nigeria - Premier League',
      'Nigeria - Premier',
      'Nigerian Premier League',
      'Nigerian Premier',
      'Nigeria. NPFL',
      'Nigeria NPFL',
      'NPFL',
    ],
  },

  // South Africa Premier League
  southafrica: {
    id: 'southafrica',
    name: 'Premier League',
    country: 'southafrica',
    tier: 3,
    keywords: [
      'South Africa. Premier League',
      'South Africa Premier League',
      'South Africa. Premier',
      'South Africa Premier',
      'South Africa PL',
      'South Africa - Premier League',
      'South Africa - Premier',
      'South African Premier League',
      'South African Premier',
      'South Africa. PSL',
      'South Africa PSL',
      'DStv Premiership',
      'PSL South Africa',
    ],
  },

  // Egypt Premier League
  egypt: {
    id: 'egypt',
    name: 'Premier League',
    country: 'egypt',
    tier: 3,
    keywords: [
      'Egypt. Premier League',
      'Egypt Premier League',
      'Egypt. Premier',
      'Egypt Premier',
      'Egypt PL',
      'Egypt - Premier League',
      'Egypt - Premier',
      'Egyptian Premier League',
      'Egyptian Premier',
      'Egyptian League',
    ],
  },

  // Morocco Botola
  morocco: {
    id: 'morocco',
    name: 'Botola Pro',
    country: 'morocco',
    tier: 3,
    keywords: [
      'Morocco. Botola',
      'Morocco Premier',
      'Moroccan Botola',
      'Botola Pro',
    ],
  },

  // Algeria Ligue 1
  algeria: {
    id: 'algeria',
    name: 'Ligue 1',
    country: 'algeria',
    tier: 3,
    keywords: [
      'Algeria. Ligue 1',
      'Algerian Ligue 1',
      'Algeria Premier',
    ],
  },

  // Tunisia Ligue 1
  tunisia: {
    id: 'tunisia',
    name: 'Ligue 1',
    country: 'tunisia',
    tier: 3,
    keywords: [
      'Tunisia. Ligue 1',
      'Tunisian Ligue 1',
      'Tunisia Premier',
    ],
  },

  // Zambia Super League
  zambia: {
    id: 'zambia',
    name: 'Super League',
    country: 'zambia',
    tier: 3,
    keywords: [
      'Zambia. Super League',
      'Zambian Super League',
      'Zambia Premier',
    ],
  },

  // Zimbabwe Premier League
  zimbabwe: {
    id: 'zimbabwe',
    name: 'Premier League',
    country: 'zimbabwe',
    tier: 3,
    keywords: [
      'Zimbabwe. Premier League',
      'Zimbabwe Premier League',
      'Zimbabwe. Premier',
      'Zimbabwe Premier',
      'Zimbabwe - Premier League',
      'Zimbabwe - Premier',
      'Zimbabwean Premier League',
      'Zimbabwean Premier',
    ],
  },

  // Rwanda Premier League
  rwanda: {
    id: 'rwanda',
    name: 'Premier League',
    country: 'rwanda',
    tier: 4,
    keywords: [
      'Rwanda. Premier League',
      'Rwanda Premier League',
      'Rwanda. Premier',
      'Rwanda Premier',
      'Rwanda - Premier League',
      'Rwandan Premier League',
    ],
  },

  // Botswana Premier League
  botswana: {
    id: 'botswana',
    name: 'Premier League',
    country: 'botswana',
    tier: 4,
    keywords: [
      'Botswana. Premier League',
      'Botswana Premier League',
      'Botswana. Premier',
      'Botswana Premier',
      'Botswana - Premier League',
    ],
  },

  // Ethiopia Premier League
  ethiopia: {
    id: 'ethiopia',
    name: 'Premier League',
    country: 'ethiopia',
    tier: 4,
    keywords: [
      'Ethiopia. Premier League',
      'Ethiopia Premier League',
      'Ethiopia. Premier',
      'Ethiopia Premier',
      'Ethiopia - Premier League',
      'Ethiopian Premier League',
    ],
  },

  // Ivory Coast (Cote d'Ivoire) Ligue 1
  ivorycoast: {
    id: 'ivorycoast',
    name: 'Ligue 1',
    country: 'ivorycoast',
    tier: 3,
    keywords: [
      "Ivory Coast. Ligue 1",
      "Ivory Coast Ligue 1",
      "Cote d'Ivoire. Ligue 1",
      "Cote d'Ivoire Ligue 1",
      "Ivory Coast - Ligue 1",
    ],
  },

  // Senegal Ligue 1
  senegal: {
    id: 'senegal',
    name: 'Ligue 1',
    country: 'senegal',
    tier: 3,
    keywords: [
      'Senegal. Ligue 1',
      'Senegal Ligue 1',
      'Senegal. Premier',
      'Senegal Premier',
      'Senegal - Ligue 1',
      'Senegalese Ligue 1',
    ],
  },

  // Cameroon Elite One
  cameroon: {
    id: 'cameroon',
    name: 'Elite One',
    country: 'cameroon',
    tier: 3,
    keywords: [
      'Cameroon. Elite One',
      'Cameroon Elite One',
      'Cameroon. Premier',
      'Cameroon Premier',
      'Cameroon - Elite One',
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
      'England Championship',
      'England. EFL Championship',
      'England EFL Championship',
      'English Championship',
      'Championship',
      'EFL Championship',
      'Sky Bet Championship',
      'England - Championship',
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
      '2nd Bundesliga',
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

  // Japanese J-League
  japan: {
    id: 'japan',
    name: 'J-League',
    country: 'japan',
    tier: 2,
    keywords: [
      'Japan. J-League',
      'Japan. J1 League',
      'Japanese J-League',
      'J1 League',
      'J-League',
    ],
  },

  // Chinese Super League
  china: {
    id: 'china',
    name: 'Super League',
    country: 'china',
    tier: 3,
    keywords: [
      'China. Super League',
      'Chinese Super League',
      'CSL',
    ],
  },

  // South Korean K-League
  korea: {
    id: 'korea',
    name: 'K-League',
    country: 'korea',
    tier: 3,
    keywords: [
      'South Korea. K-League',
      'Korea. K-League',
      'Korean K-League',
      'K League 1',
    ],
  },

  // Australian A-League
  australia: {
    id: 'australia',
    name: 'A-League',
    country: 'australia',
    tier: 3,
    keywords: [
      'Australia. A-League',
      'Australian A-League',
      'A-League',
    ],
  },

  // Indian Super League
  india: {
    id: 'india',
    name: 'Super League',
    country: 'india',
    tier: 3,
    keywords: [
      'India. Super League',
      'Indian Super League',
      'ISL',
    ],
  },

  // Colombian Primera A
  colombia: {
    id: 'colombia',
    name: 'Primera A',
    country: 'colombia',
    tier: 3,
    keywords: [
      'Colombia. Primera A',
      'Colombian Primera A',
      'Liga BetPlay',
    ],
  },

  // Chilean Primera Division
  chile: {
    id: 'chile',
    name: 'Primera Division',
    country: 'chile',
    tier: 3,
    keywords: [
      'Chile. Primera',
      'Chilean Primera',
      'Primera Division Chile',
    ],
  },

  // Mexican Liga MX
  mexico: {
    id: 'mexico',
    name: 'Liga MX',
    country: 'mexico',
    tier: 2,
    keywords: [
      'Mexico. Liga MX',
      'Mexican Liga MX',
      'Liga MX',
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
  // Europe
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

  // Africa
  ghana: { id: 'ghana', name: 'Ghana', flag: '🇬🇭' },
  kenya: { id: 'kenya', name: 'Kenya', flag: '🇰🇪' },
  uganda: { id: 'uganda', name: 'Uganda', flag: '🇺🇬' },
  tanzania: { id: 'tanzania', name: 'Tanzania', flag: '🇹🇿' },
  nigeria: { id: 'nigeria', name: 'Nigeria', flag: '🇳🇬' },
  southafrica: { id: 'southafrica', name: 'South Africa', flag: '🇿🇦' },
  egypt: { id: 'egypt', name: 'Egypt', flag: '🇪🇬' },
  morocco: { id: 'morocco', name: 'Morocco', flag: '🇲🇦' },
  algeria: { id: 'algeria', name: 'Algeria', flag: '🇩🇿' },
  tunisia: { id: 'tunisia', name: 'Tunisia', flag: '🇹🇳' },
  zambia: { id: 'zambia', name: 'Zambia', flag: '🇿🇲' },
  zimbabwe: { id: 'zimbabwe', name: 'Zimbabwe', flag: '🇿🇼' },
  rwanda: { id: 'rwanda', name: 'Rwanda', flag: '🇷🇼' },
  botswana: { id: 'botswana', name: 'Botswana', flag: '🇧🇼' },
  ethiopia: { id: 'ethiopia', name: 'Ethiopia', flag: '🇪🇹' },
  ivorycoast: { id: 'ivorycoast', name: 'Ivory Coast', flag: '🇨🇮' },
  senegal: { id: 'senegal', name: 'Senegal', flag: '🇸🇳' },
  cameroon: { id: 'cameroon', name: 'Cameroon', flag: '🇨🇲' },

  // Americas
  usa: { id: 'usa', name: 'USA', flag: '🇺🇸' },
  brazil: { id: 'brazil', name: 'Brazil', flag: '🇧🇷' },
  argentina: { id: 'argentina', name: 'Argentina', flag: '🇦🇷' },
  mexico: { id: 'mexico', name: 'Mexico', flag: '🇲🇽' },
  colombia: { id: 'colombia', name: 'Colombia', flag: '🇨🇴' },
  chile: { id: 'chile', name: 'Chile', flag: '🇨🇱' },

  // Asia & Oceania
  japan: { id: 'japan', name: 'Japan', flag: '🇯🇵' },
  china: { id: 'china', name: 'China', flag: '🇨🇳' },
  korea: { id: 'korea', name: 'South Korea', flag: '🇰🇷' },
  australia: { id: 'australia', name: 'Australia', flag: '🇦🇺' },
  india: { id: 'india', name: 'India', flag: '🇮🇳' },

  // Middle East
  saudi: { id: 'saudi', name: 'Saudi Arabia', flag: '🇸🇦' },

  // Regions
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
  // Europe
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

  // Africa
  'ghana': 'ghana',
  'ghanaian': 'ghana',
  'kenya': 'kenya',
  'kenyan': 'kenya',
  'uganda': 'uganda',
  'ugandan': 'uganda',
  'tanzania': 'tanzania',
  'tanzanian': 'tanzania',
  'nigeria': 'nigeria',
  'nigerian': 'nigeria',
  'south africa': 'southafrica',
  'southafrica': 'southafrica',
  'south african': 'southafrica',
  'egypt': 'egypt',
  'egyptian': 'egypt',
  'morocco': 'morocco',
  'moroccan': 'morocco',
  'algeria': 'algeria',
  'algerian': 'algeria',
  'tunisia': 'tunisia',
  'tunisian': 'tunisia',
  'zambia': 'zambia',
  'zambian': 'zambia',
  'zimbabwe': 'zimbabwe',
  'zimbabwean': 'zimbabwe',
  'rwanda': 'rwanda',
  'rwandan': 'rwanda',
  'botswana': 'botswana',
  'ethiopia': 'ethiopia',
  'ethiopian': 'ethiopia',
  'ivory coast': 'ivorycoast',
  'ivorycoast': 'ivorycoast',
  "cote d'ivoire": 'ivorycoast',
  'senegal': 'senegal',
  'senegalese': 'senegal',
  'cameroon': 'cameroon',
  'cameroonian': 'cameroon',

  // Americas
  'usa': 'usa',
  'united states': 'usa',
  'brazil': 'brazil',
  'brazilian': 'brazil',
  'argentina': 'argentina',
  'argentine': 'argentina',
  'mexico': 'mexico',
  'mexican': 'mexico',
  'colombia': 'colombia',
  'colombian': 'colombia',
  'chile': 'chile',
  'chilean': 'chile',

  // Asia & Oceania
  'japan': 'japan',
  'japanese': 'japan',
  'china': 'china',
  'chinese': 'china',
  'south korea': 'korea',
  'korea': 'korea',
  'korean': 'korea',
  'australia': 'australia',
  'australian': 'australia',
  'india': 'india',
  'indian': 'india',

  // Middle East
  'saudi arabia': 'saudi',
  'saudi': 'saudi',

  // Regions
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

      // For certain keywords, require exact match to avoid false positives
      // "Premier League": prevents "Kenya Premier League" from matching
      // "La Liga": prevents "Argentina Trofeo De Campeones De La Liga Profesional" from matching
      const requiresExactMatch = keywordLower === 'premier league' || keywordLower === 'la liga';
      const isMatch = requiresExactMatch
        ? lower === keywordLower
        : lower.includes(keywordLower);

      if (isMatch && keywordLower.length > bestMatchLength) {
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
  return league.keywords.some(kw => {
    const kwLower = kw.toLowerCase();
    // For certain keywords, require exact match to avoid false positives
    const requiresExactMatch = kwLower === 'premier league' || kwLower === 'la liga';
    return requiresExactMatch ? lower === kwLower : lower.includes(kwLower);
  });
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
