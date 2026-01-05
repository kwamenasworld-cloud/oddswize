const TEAM_POPULARITY = {
  // England
  'manchester united': 10,
  'manchester city': 9,
  'liverpool': 9,
  'arsenal': 8,
  'chelsea': 8,
  'tottenham hotspur': 7,
  'newcastle united': 6,
  'aston villa': 5,
  'west ham united': 5,
  'everton': 4,
  'leicester city': 4,

  // Spain
  'real madrid': 10,
  'barcelona': 9,
  'atletico madrid': 7,
  'athletic bilbao': 5,
  'real sociedad': 5,
  'sevilla': 5,
  'valencia': 5,
  'villarreal': 5,

  // Germany
  'bayern munich': 9,
  'borussia dortmund': 7,
  'rb leipzig': 6,
  'bayer leverkusen': 6,
  'eintracht frankfurt': 5,

  // Italy
  'juventus': 8,
  'inter milan': 7,
  'ac milan': 7,
  'napoli': 6,
  'roma': 6,
  'lazio': 5,
  'atalanta': 5,

  // France
  'paris saint germain': 8,
  'marseille': 6,
  'lyon': 5,
  'monaco': 5,

  // Netherlands
  'ajax': 6,
  'psv eindhoven': 5,
  'feyenoord': 5,

  // Portugal
  'benfica': 6,
  'fc porto': 6,
  'sporting lisbon': 5,
  'sc braga': 4,

  // Scotland
  'celtic': 6,
  'rangers': 6,

  // Africa (Ghana focus)
  'hearts of oak': 6,
  'asante kotoko': 6,
  'medeama sc': 5,
  'aduana stars': 4,
  'bechem united': 4,
  'great olympics': 4,

  // Africa (wider)
  'al ahly': 6,
  'zamalek': 5,
  'esperance tunis': 5,
  'tp mazembe': 5,
  'mamelodi sundowns': 5,
  'kaizer chiefs': 4,
  'orlando pirates': 4,
  'wydad casablanca': 4,
};

const TEAM_ALIASES = {
  'man utd': 'manchester united',
  'man united': 'manchester united',
  'man city': 'manchester city',
  'spurs': 'tottenham hotspur',
  'psg': 'paris saint germain',
  'inter': 'inter milan',
  'ac milan': 'ac milan',
  'bayern': 'bayern munich',
  'dortmund': 'borussia dortmund',
  'athletic club': 'athletic bilbao',
  'porto': 'fc porto',
  'sporting': 'sporting lisbon',
  'kotoko': 'asante kotoko',
  'hearts': 'hearts of oak',
  'sundowns': 'mamelodi sundowns',
};

const normalizeTeamName = (value) => (
  (value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
);

export const getTeamPopularityScore = (teamName) => {
  if (!teamName) return 0;
  const normalized = normalizeTeamName(teamName);
  if (!normalized) return 0;
  const alias = TEAM_ALIASES[normalized];
  return TEAM_POPULARITY[alias || normalized] || 0;
};

export const getTeamPopularityMap = () => TEAM_POPULARITY;

export default {
  getTeamPopularityScore,
  getTeamPopularityMap,
};
