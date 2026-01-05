import { useState, useEffect, useMemo, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getMatchesByLeague, getStatus, triggerScan } from '../services/api';
import { getCanonicalLeagues, getCanonicalFixtures } from '../services/canonical';
import { BOOKMAKER_AFFILIATES, BOOKMAKER_ORDER, getAffiliateUrl } from '../config/affiliates';
import { LEAGUES, COUNTRIES, isCountryMatch, getLeagueTier, matchLeague, matchLeagueFuzzy } from '../config/leagues';
import { BookmakerLogo } from '../components/BookmakerLogo';
import { TeamLogo } from '../components/TeamLogo';
import { LeagueLogo } from '../components/LeagueLogo';
import { preloadTeamLogos, clearLogoCache } from '../services/teamLogos';
import ShareButton from '../components/ShareButton';

// Market types
const MARKETS = {
  '1x2': { id: '1x2', name: '1X2', labels: ['1', 'X', '2'], description: 'Match Result' },
  'double_chance': { id: 'double_chance', name: 'Double Chance', labels: ['1X', 'X2', '12'], description: 'Double Chance' },
  'over_under': { id: 'over_under', name: 'O/U 2.5', labels: ['Over', 'Under'], description: 'Over/Under 2.5 Goals' },
};

const DEFAULT_REFRESH_MS = 5 * 60 * 1000;
const MIN_REFRESH_MS = 2 * 60 * 1000;
const MAX_REFRESH_MS = 30 * 60 * 1000;
const COMPACT_BREAKPOINT = 520;

const resolveRefreshInterval = (cacheTtlSeconds) => {
  const ttlSeconds = Number(cacheTtlSeconds);
  if (!Number.isFinite(ttlSeconds) || ttlSeconds <= 0) {
    return DEFAULT_REFRESH_MS;
  }
  const ttlMs = ttlSeconds * 1000;
  return Math.min(Math.max(ttlMs, MIN_REFRESH_MS), MAX_REFRESH_MS);
};

const normalizePillKey = (value) => (
  (value || '').toString().toLowerCase().replace(/[^a-z0-9]+/g, '')
);

const resolvePillKey = (pill) => {
  if (!pill) return '';
  if (pill.type === 'league') {
    return normalizePillKey(pill.id || pill.name);
  }
  const baseValue = pill.logoId || pill.value || pill.label || pill.id;
  const matched = matchLeague(baseValue) || matchLeague(pill.value) || matchLeague(pill.label);
  return normalizePillKey(matched?.id || baseValue);
};

// Build popular leagues list from centralized config (with short display names)
const POPULAR_LEAGUES = [
  { id: 'all', name: 'All', country: 'all' },
  { ...LEAGUES.premier, name: 'EPL' },
  { ...LEAGUES.championship, name: 'Championship' },
  { ...LEAGUES.laliga, name: 'La Liga' },
  { ...LEAGUES.bundesliga, name: 'Bundesliga' },
  { ...LEAGUES.seriea, name: 'Serie A' },
  { ...LEAGUES.ligue1, name: 'Ligue 1' },
  { ...LEAGUES.ucl, name: 'UCL' },
  { ...LEAGUES.europa, name: 'Europa' },
  { ...LEAGUES.conference, name: 'Conference' },
  { ...LEAGUES.eredivisie, name: 'Eredivisie' },
  { ...LEAGUES.portugal, name: 'Primeira Liga' },
  { ...LEAGUES.ghana, name: 'Ghana PL' },
  { ...LEAGUES.facup, name: 'FA Cup' },
  { ...LEAGUES.eflcup, name: 'EFL Cup' },
  { ...LEAGUES.laliga2, name: 'La Liga 2' },
  { ...LEAGUES.bundesliga2, name: '2. Bundesliga' },
  { ...LEAGUES.serieb, name: 'Serie B' },
  { ...LEAGUES.ligue2, name: 'Ligue 2' },
  { id: 'unmapped', name: 'Unmapped/Other', country: 'all' },
];

// Build country filters from centralized config
const COUNTRY_FILTERS = [
  { id: 'all', name: 'All Countries' },
  ...Object.values(COUNTRIES)
    .filter(c => ['england', 'spain', 'germany', 'italy', 'france', 'portugal', 'netherlands', 'scotland', 'ghana', 'europe'].includes(c.id))
    .map(c => ({ id: c.id, name: c.name, flag: c.flag })),
];

// Quick league keyword tiles for canonical/text filtering
const LEAGUE_QUERY_TILES = [
  { id: 'premier', label: 'Premier League', value: 'premier league', logoId: 'premier' },
  { id: 'ucl', label: 'UCL', value: 'uefa champions league', logoId: 'ucl' },
  { id: 'uel', label: 'Europa', value: 'europa league', logoId: 'uel' },
  { id: 'uecl', label: 'Conference', value: 'conference league', logoId: 'conference' },
  { id: 'laliga', label: 'La Liga', value: 'la liga', logoId: 'laliga' },
  { id: 'laliga2', label: 'La Liga 2', value: 'la liga 2', logoId: 'laliga2' },
  { id: 'bundesliga', label: 'Bundesliga', value: 'bundesliga', logoId: 'bundesliga' },
  { id: 'bundesliga2', label: 'Bundesliga 2', value: 'bundesliga 2', logoId: 'bundesliga2' },
  { id: 'seriea', label: 'Serie A', value: 'serie a', logoId: 'seriea' },
  { id: 'serieb', label: 'Serie B', value: 'serie b', logoId: 'serieb' },
  { id: 'ligue1', label: 'Ligue 1', value: 'ligue 1', logoId: 'ligue1' },
  { id: 'ligue2', label: 'Ligue 2', value: 'ligue 2', logoId: 'ligue2' },
  { id: 'eredivisie', label: 'Eredivisie', value: 'eredivisie', logoId: 'eredivisie' },
  { id: 'primeira', label: 'Primeira Liga', value: 'primeira liga', logoId: 'primeira' },
  { id: 'mls', label: 'MLS', value: 'mls', logoId: 'mls' },
  { id: 'libertadores', label: 'Libertadores', value: 'libertadores', logoId: 'libertadores' },
  { id: 'sudamericana', label: 'Sudamericana', value: 'sudamericana', logoId: 'sudamericana' },
  { id: 'brasileirao', label: 'Serie A (BRA)', value: 'brasileirao', logoId: 'brasileirao' },
  { id: 'ligamx', label: 'Liga MX', value: 'liga mx', logoId: 'ligamx' },
  { id: 'j1', label: 'J1 League', value: 'j1 league', logoId: 'j1' },
  { id: 'k1', label: 'K League', value: 'k league', logoId: 'k1' },
  { id: 'a-league', label: 'A-League', value: 'a-league', logoId: 'a-league' },
  { id: 'wsl', label: 'FA WSL', value: 'women super league', logoId: 'wsl' },
  { id: 'uwcl', label: 'UWCL', value: 'uefa champions league women', logoId: 'uwcl' },
  { id: 'nwsl', label: 'NWSL', value: 'nwsl', logoId: 'nwsl' },
  { id: 'friendly', label: 'Friendlies', value: 'friendly' },
  { id: 'youth', label: 'U21/Youth', value: 'u21' },
];

// Date filter options
const DATE_FILTERS = [
  { id: 'today', name: 'Today', icon: '📅' },
  { id: 'tomorrow', name: 'Tomorrow', icon: '📆' },
  { id: 'weekend', name: 'Weekend', icon: '🗓️' },
  { id: 'all', name: 'All', icon: '📋' },
];

// Sort options for matches
const SORT_OPTIONS = [
  { id: 'time', name: 'Kick-off Time', icon: '🕐' },
  { id: 'popularity', name: 'Popularity', icon: '🔥' },
  { id: 'bookmakers', name: 'Most Bookmakers', icon: '📊' },
  { id: 'league', name: 'League Name', icon: '🏆' },
];

// Calculate popularity score for a match using centralized league tiers
const getPopularityScore = (match) => {
  let score = 0;

  // Score based on number of bookmakers (more bookmakers = more popular)
  const bookmakerCount = match.odds?.length || 0;
  score += bookmakerCount * 15;

  // Score based on league tier from centralized config (tier 1 = most popular)
  const tier = getLeagueTier(match.league);
  score += (5 - tier) * 25; // Tier 1 = +100, Tier 2 = +75, etc.

  // Bonus for matches happening soon (within 24 hours)
  const now = Date.now() / 1000;
  const timeDiff = (match.start_time || 0) - now;
  if (timeDiff > 0 && timeDiff < 86400) {
    score += Math.max(0, 50 - (timeDiff / 3600)); // More points for sooner matches
  }

  return score;
};

// Format relative time (e.g., "5 mins ago")
const formatRelativeTime = (dateString) => {
  if (!dateString) return 'Unknown';

  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
};

// Check if date falls within filter
const matchesDateFilter = (timestamp, filter) => {
  if (filter === 'all') return true;

  const matchDate = new Date(timestamp * 1000);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);
  const dayAfterTomorrow = new Date(today);
  dayAfterTomorrow.setDate(dayAfterTomorrow.getDate() + 2);

  // Get next weekend
  const daysUntilSaturday = (6 - today.getDay() + 7) % 7;
  const saturday = new Date(today);
  saturday.setDate(saturday.getDate() + daysUntilSaturday);
  const monday = new Date(saturday);
  monday.setDate(monday.getDate() + 2);

  switch (filter) {
    case 'today':
      return matchDate >= today && matchDate < tomorrow;
    case 'tomorrow':
      return matchDate >= tomorrow && matchDate < dayAfterTomorrow;
    case 'weekend':
      return matchDate >= saturday && matchDate < monday;
    default:
      return true;
  }
};

// Odds field mapping for each market
const MARKET_FIELDS = {
  '1x2': ['home_odds', 'draw_odds', 'away_odds'],
  'double_chance': ['home_draw', 'draw_away', 'home_away'],
  'over_under': ['over_25', 'under_25'],
};

function OddsPage() {
  const [searchParams] = useSearchParams();
  const [matches, setMatches] = useState([]);
  const [canonicalLeagues, setCanonicalLeagues] = useState([]);
  const [useCanonical, setUseCanonical] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [leagueQuery, setLeagueQuery] = useState('');
  const [selectedLeagues, setSelectedLeagues] = useState(() => {
    // Initialize from URL param if present
    const leagueParam = searchParams.get('league');
    if (leagueParam) {
      // Check if it's a valid league ID
      const league = POPULAR_LEAGUES.find(l => l.id === leagueParam);
      if (league && league.id !== 'all') {
        return [leagueParam];
      }
    }
    return [];
  });
  const [selectedCountry, setSelectedCountry] = useState('all');
  const [selectedMarket, setSelectedMarket] = useState('1x2');
  const [selectedOdd, setSelectedOdd] = useState(null);
  const [selectedDate, setSelectedDate] = useState('all');
  const [enabledBookies, setEnabledBookies] = useState(() =>
    BOOKMAKER_ORDER.reduce((acc, b) => ({ ...acc, [b]: true }), {})
  );
  const [showAllMatches, setShowAllMatches] = useState(false);
  const [selectedSort, setSelectedSort] = useState('time');
  const [refreshIntervalMs, setRefreshIntervalMs] = useState(DEFAULT_REFRESH_MS);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);
  const [compactView, setCompactView] = useState(() => {
    if (typeof window === 'undefined') return false;
    if (window.matchMedia) {
      return window.matchMedia(`(max-width: ${COMPACT_BREAKPOINT}px)`).matches;
    }
    return window.innerWidth <= COMPACT_BREAKPOINT;
  });
  const loadDataRef = useRef(() => {});
  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mediaQuery = window.matchMedia(`(max-width: ${COMPACT_BREAKPOINT}px)`);
    const handleChange = (event) => {
      setCompactView(event.matches);
    };
    handleChange(mediaQuery);
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
    mediaQuery.addListener(handleChange);
    return () => mediaQuery.removeListener(handleChange);
  }, []);

  // Pause auto-refresh when the tab is hidden
  useEffect(() => {
    const handleVisibility = () => {
      const visible = document.visibilityState === 'visible';
      setAutoRefreshEnabled(visible);
      if (visible) {
        loadDataRef.current({ silent: true });
      }
    };
    handleVisibility();
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, []);

  // Auto-refresh odds periodically to keep prices fresh without manual refresh
  useEffect(() => {
    if (!autoRefreshEnabled) return;
    const interval = setInterval(() => {
      loadDataRef.current({ silent: true });
    }, refreshIntervalMs);
    return () => clearInterval(interval);
  }, [autoRefreshEnabled, refreshIntervalMs]);

  // Sync horizontal scroll between sticky header and content
  useEffect(() => {
    if (compactView) return;
    const stickyHeader = document.querySelector('.odds-sticky-header');
    const content = document.querySelector('.odds-container');

    if (!stickyHeader || !content) return;

    const syncContentToHeader = () => {
      stickyHeader.scrollLeft = content.scrollLeft;
    };

    const syncHeaderToContent = () => {
      content.scrollLeft = stickyHeader.scrollLeft;
    };

    content.addEventListener('scroll', syncContentToHeader);
    stickyHeader.addEventListener('scroll', syncHeaderToContent);

    return () => {
      content.removeEventListener('scroll', syncContentToHeader);
      stickyHeader.removeEventListener('scroll', syncHeaderToContent);
    };
  }, [loading, compactView]); // Re-attach when loading changes

  // Sync URL params with selected leagues (handles navigation from HomePage)
  useEffect(() => {
    const leagueParam = searchParams.get('league');
    if (leagueParam) {
      const league = POPULAR_LEAGUES.find(l => l.id === leagueParam);
      if (league && league.id !== 'all') {
        setSelectedLeagues([leagueParam]);
        // Also reset country filter to show all when filtering by league from URL
        setSelectedCountry('all');
      }
    }
  }, [searchParams]);

  // Drop canonical-only selections when falling back to non-canonical data
  useEffect(() => {
    if (useCanonical) return;
    const allowed = new Set(POPULAR_LEAGUES.map(l => l.id));
    setSelectedLeagues(prev => prev.filter(id => allowed.has(id)));
  }, [useCanonical]);

  // If canonical data lacks the selected league(s), fall back to worker odds
  useEffect(() => {
    if (loading || !useCanonical) return;
    if (selectedLeagues.length === 0) return;
    const requested = selectedLeagues.filter(id => id && id !== 'all' && id !== 'unmapped');
    if (requested.length === 0) return;
    const hasRequested = matches.some(match => {
      const key = match.league_key || matchLeague(match.league)?.id || null;
      return key && requested.includes(key);
    });
    if (!hasRequested) {
      loadData({ silent: true, forceWorker: true });
    }
  }, [selectedLeagues, useCanonical, matches, loading]);

  // Preload team logos when matches change
  useEffect(() => {
    if (matches.length > 0) {
      const teamNames = matches.flatMap(m => [m.home_team, m.away_team]);
      preloadTeamLogos(teamNames.slice(0, 100));
    }
  }, [matches]);

  const loadData = async (opts = {}) => {
    const silent = opts?.silent;
    const forceWorker = Boolean(opts?.forceWorker);
    const bypassCache = Boolean(opts?.bypassCache);
    setError(null);
    try {
      let statusData = null;
      let fetchedMatches = null;
      const fetchWorkerData = async () => {
        const [matchData, statusDataResp] = await Promise.all([
          getMatchesByLeague({ allowStale: !bypassCache, bypassCache }),
          getStatus(),
        ]);
        const leagues = matchData.leagues || [];
        if (matchData?.meta?.cache_ttl) {
          setRefreshIntervalMs(resolveRefreshInterval(matchData.meta.cache_ttl));
        }
        const flattened = leagues.flatMap(league =>
          (league.matches || []).map(match => ({
            ...match,
            league: league.league || match.league,
          }))
        );
        fetchedMatches = flattened.filter(
          match => match.odds && Array.isArray(match.odds) && match.odds.length >= 1
        );
        statusData = statusDataResp;
        if (statusDataResp?.cacheTtl) {
          setRefreshIntervalMs(resolveRefreshInterval(statusDataResp.cacheTtl));
        }
        setUseCanonical(false);
      };

      if (!forceWorker) {
        // Try canonical backend first
        try {
          const [canonLeagues, canonFixtures, statusResp] = await Promise.all([
            getCanonicalLeagues(),
            getCanonicalFixtures(2000, 0),
            getStatus(),
          ]);
          setCanonicalLeagues(canonLeagues || []);
          // Map canonical fixtures to match shape (no odds available yet, so placeholder)
          fetchedMatches = (canonFixtures || []).map(f => {
            const canonLeague = canonLeagues.find(l => l.league_id === f.league_id);
            const leagueName = canonLeague?.display_name || f.raw_league_name || 'Unmapped/Other';
            const mappedKey = canonLeague?.slug || matchLeague(leagueName)?.id || null;
            return {
              home_team: f.home_team,
              away_team: f.away_team,
              league: leagueName,
              league_key: mappedKey || canonLeague?.league_id || null,
              canonical_league_id: f.league_id || null,
              start_time: f.kickoff_time,
              odds: [], // odds not stored in canonical fixtures; UI will show empty cells
            };
          });
          // If canonical returned nothing or misses requested leagues, fall back to worker data
          if (!fetchedMatches || fetchedMatches.length === 0) {
            throw new Error('No canonical fixtures, fallback to worker');
          }
          const requestedKeys = new Set();
          const requestedLeague = searchParams.get('league');
          if (requestedLeague && requestedLeague !== 'all') {
            requestedKeys.add(requestedLeague);
          }
          selectedLeagues.forEach(id => {
            if (id && id !== 'all' && id !== 'unmapped') requestedKeys.add(id);
          });
          if (requestedKeys.size > 0) {
            const hasRequested = fetchedMatches.some(match => {
              const key = match.league_key || matchLeague(match.league)?.id || null;
              return key && requestedKeys.has(key);
            });
            if (!hasRequested) {
              throw new Error('Canonical missing requested league, fallback to worker');
            }
          }
          setUseCanonical(true);
          statusData = statusResp;
          if (statusResp?.cacheTtl) {
            setRefreshIntervalMs(resolveRefreshInterval(statusResp.cacheTtl));
          }
        } catch (e) {
          await fetchWorkerData();
        }
      } else {
        await fetchWorkerData();
      }

      // Enrich matches with synthetic market data if missing
      const nowMs = Date.now();
      const enrichedMatches = (fetchedMatches || []).map(match => {
        const oddsArr = match.odds?.map(odds => ({
          ...odds,
          // Generate synthetic double chance and over/under if not present
          home_draw: odds.home_draw || calculateDoubleChance(odds.home_odds, odds.draw_odds),
          draw_away: odds.draw_away || calculateDoubleChance(odds.draw_odds, odds.away_odds),
          home_away: odds.home_away || calculateDoubleChance(odds.home_odds, odds.away_odds),
          over_25: odds.over_25 || generateOverUnder(odds.home_odds, odds.away_odds, true),
          under_25: odds.under_25 || generateOverUnder(odds.home_odds, odds.away_odds, false),
        })) || [];

        const startMs = (match.start_time || 0) * 1000;
        const hasOdds = oddsArr.length > 0;
        const missingBookies = oddsArr.length < BOOKMAKER_ORDER.length;
        const withinWindow = startMs
          ? (startMs > nowMs - 2 * 3600 * 1000 && startMs < nowMs + 48 * 3600 * 1000)
          : true;
        const pendingOdds = hasOdds && missingBookies && withinWindow;

        const derivedKey = match.league_key || matchLeague(match.league)?.id || null;

        return {
          ...match,
          odds: oddsArr,
          pendingOdds,
          league_key: derivedKey,
        };
      });

      setMatches(enrichedMatches);
      setStatus(statusData);
    } catch (err) {
      console.error('Failed to load odds:', err);
      setError('Unable to load odds. Please try again later.');
      setMatches([]);
    } finally {
      if (!silent) setLoading(false);
    }
  };
  loadDataRef.current = loadData;

  // Calculate synthetic double chance odds
  const calculateDoubleChance = (odds1, odds2) => {
    if (!odds1 || !odds2) return null;
    const prob1 = 1 / odds1;
    const prob2 = 1 / odds2;
    const combinedProb = prob1 + prob2;
    // Apply margin
    return Math.round((1 / combinedProb) * 0.92 * 100) / 100;
  };

  // Generate synthetic over/under odds
  const generateOverUnder = (homeOdds, awayOdds, isOver) => {
    if (!homeOdds || !awayOdds) return null;
    // Lower home/away odds typically mean more goals expected
    const avgOdds = (homeOdds + awayOdds) / 2;
    if (isOver) {
      return Math.round((1.4 + (avgOdds - 2) * 0.15) * 100) / 100;
    } else {
      return Math.round((2.8 - (avgOdds - 2) * 0.15) * 100) / 100;
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await triggerScan();
      await loadData({ bypassCache: true });
    } catch (error) {
      console.error('Failed to refresh:', error);
    } finally {
      setRefreshing(false);
    }
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp * 1000);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const isTomorrow = date.toDateString() === tomorrow.toDateString();

    if (isToday) {
      return `Today ${date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}`;
    }
    if (isTomorrow) {
      return `Tomorrow ${date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}`;
    }
    return date.toLocaleDateString('en-GB', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Get best odds for a specific field
  const getBestOdds = (match, field) => {
    const odds = match.odds || [];
    if (odds.length === 0) return { value: 0, bookmaker: '' };
    const validOdds = odds.filter(o => o[field] && o[field] > 0);
    if (validOdds.length === 0) return { value: 0, bookmaker: '' };
    const best = validOdds.reduce((max, o) => (o[field] > max[field] ? o : max), validOdds[0]);
    return { value: best[field], bookmaker: best.bookmaker };
  };

  // Calculate market average for an outcome
  const getMarketAverage = (match, field) => {
    const odds = match.odds || [];
    const validOdds = odds.filter(o => o[field] && o[field] > 0);
    if (validOdds.length === 0) return 0;
    const sum = validOdds.reduce((acc, o) => acc + o[field], 0);
    return sum / validOdds.length;
  };

  // Check if odds are significantly above market average
  const isAboveAverage = (oddsValue, average) => {
    if (!average || !oddsValue) return false;
    const diff = ((oddsValue - average) / average) * 100;
    return diff > 5;
  };

  const isBigEdge = (oddsValue, average) => {
    if (!average || !oddsValue) return false;
    const diff = ((oddsValue - average) / average) * 100;
    return diff > 10;
  };

  // Convert odds to implied probability
  const oddsToProb = (odds) => {
    if (!odds || odds <= 1) return 0;
    return (1 / odds) * 100;
  };

  // Handle odds click to show probability
  const handleOddsClick = (e, odds, outcome, bookmaker) => {
    e.preventDefault();
    const prob = oddsToProb(odds);
    setSelectedOdd({
      odds,
      prob: prob.toFixed(1),
      outcome,
      bookmaker,
      x: e.clientX,
      y: e.clientY,
    });
  };

  // Cleanup timeout for probability tooltip
  useEffect(() => {
    if (selectedOdd) {
      const timer = setTimeout(() => setSelectedOdd(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [selectedOdd]);

  const searchLeagueId = useMemo(() => {
    const query = searchQuery.trim();
    if (!query) return null;
    const exactMatch = matchLeague(query);
    if (exactMatch) return exactMatch.id;
    const fuzzyMatch = matchLeagueFuzzy(query);
    return fuzzyMatch ? fuzzyMatch.id : null;
  }, [searchQuery]);

  // Filter matches based on search, league, country, and date
  const filteredMatches = useMemo(() => {
    return matches.filter((match) => {
      const searchLower = searchQuery.toLowerCase();
      const leagueLower = (match.league || '').toLowerCase();
      const leagueQueryLower = leagueQuery.toLowerCase();

      const searchLeagueKey = searchLeagueId;
      const matchLeagueKey = match.league_key || matchLeague(match.league)?.id || null;
      const matchesSearch =
        !searchQuery ||
        match.home_team.toLowerCase().includes(searchLower) ||
        match.away_team.toLowerCase().includes(searchLower) ||
        leagueLower.includes(searchLower) ||
        (searchLeagueKey && matchLeagueKey === searchLeagueKey);

      const matchesLeagueText =
        !leagueQuery || leagueLower.includes(leagueQueryLower);

      // League filter using stable league keys (slug or canonical id fallback)
      const leagueKey = matchLeagueKey;
      const includesUnmapped = selectedLeagues.includes('unmapped');
      let matchesLeague = true;
      if (selectedLeagues.length > 0) {
        const matchesKnown = leagueKey ? selectedLeagues.includes(leagueKey) : false;
        const matchesUnmapped = includesUnmapped && !leagueKey;
        matchesLeague = matchesKnown || matchesUnmapped;
      }

      // Country filter using centralized matching
      const matchesCountry = isCountryMatch(match.league, selectedCountry);

      const matchesDate = matchesDateFilter(match.start_time, selectedDate);

      return matchesSearch && matchesLeagueText && matchesLeague && matchesCountry && matchesDate;
    });
  }, [matches, searchQuery, leagueQuery, selectedLeagues, selectedCountry, selectedDate, useCanonical, canonicalLeagues]);

  const hasFilters =
    Boolean(searchQuery || leagueQuery || selectedLeagues.length > 0 || selectedCountry !== 'all');
  const hasDateFilter = selectedDate !== 'all';

  const resetFilters = () => {
    setSearchQuery('');
    setLeagueQuery('');
    setSelectedLeagues([]);
    setSelectedCountry('all');
    setSelectedDate('all');
    setShowAllMatches(true);
  };

  // Filter visible league pills based on selected country
  const visibleLeagues = useMemo(() => {
    if (useCanonical && canonicalLeagues.length > 0) {
      const base = [
        { id: 'all', name: 'All', country: 'all' },
        { id: 'unmapped', name: 'Unmapped/Other', country: 'all' },
      ];
      const seen = new Set(base.map(l => l.id));
      const canon = [];
      canonicalLeagues.forEach(l => {
        const id = l.slug || matchLeague(l.display_name)?.id || l.league_id;
        if (!id || seen.has(id)) return;
        seen.add(id);
        canon.push({
          id,
          name: l.display_name,
          country: l.country_code || 'all',
        });
      });
      return base.concat(canon);
    }

    if (selectedCountry === 'all') {
      return POPULAR_LEAGUES;
    }
    return POPULAR_LEAGUES.filter(league =>
      league.country === 'all' || league.country === selectedCountry
    );
  }, [selectedCountry, useCanonical, canonicalLeagues]);

  // Combine primary league pills and keyword pills, deduping to avoid duplicates (e.g., Serie A twice)
  const combinedPills = useMemo(() => {
    const seen = new Set();
    const pills = [];

    const pushPill = (pill) => {
      const key = resolvePillKey(pill);
      if (!key || seen.has(key)) return;
      seen.add(key);
      pills.push(pill);
    };

    visibleLeagues.forEach(l => pushPill({ type: 'league', ...l }));
    LEAGUE_QUERY_TILES.forEach(t => pushPill({ type: 'keyword', ...t }));

    // Add a single All keyword reset if it's not already covered
    if (!seen.has('all')) {
      pushPill({ type: 'keyword', id: 'kw-all', label: 'All', value: '' });
    }

    return pills;
  }, [visibleLeagues]);

  // Get featured/top matches (today's matches from top leagues)
  const featuredMatches = useMemo(() => {
    const topLeagues = ['Premier League', 'England', 'La Liga', 'Spain', 'Champions League', 'Serie A', 'Bundesliga'];
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    return matches
      .filter(m => {
        // Must be today
        const matchDate = new Date(m.start_time * 1000);
        const isToday = matchDate >= today && matchDate < tomorrow;
        if (!isToday) return false;

        // Must be from top leagues
        const isTopLeague = topLeagues.some(kw => m.league.toLowerCase().includes(kw.toLowerCase()));

        // Must have at least 2 bookmakers
        const hasEnoughBookies = m.odds?.length >= 2;

        return isTopLeague && hasEnoughBookies;
      })
      .sort((a, b) => (a.start_time || 0) - (b.start_time || 0))  // Soonest first
      .slice(0, 3);
  }, [matches]);

  // Toggle bookmaker visibility
  const toggleBookie = (bookie) => {
    setEnabledBookies(prev => ({ ...prev, [bookie]: !prev[bookie] }));
  };

  // Get active bookmakers
  const activeBookmakers = BOOKMAKER_ORDER.filter(b => enabledBookies[b]);
  const oddsColumns = `minmax(var(--odds-match-min), var(--odds-match-max)) var(--odds-time) repeat(${activeBookmakers.length}, minmax(var(--odds-bookie-min), 1fr))`;

  // Sort function based on selected sort option
  const sortMatches = (matchList) => {
    return [...matchList].sort((a, b) => {
      switch (selectedSort) {
        case 'time':
          return (a.start_time || 0) - (b.start_time || 0);
        case 'popularity':
          return getPopularityScore(b) - getPopularityScore(a);
        case 'bookmakers':
          return (b.odds?.length || 0) - (a.odds?.length || 0);
        case 'league':
          return (a.league || '').localeCompare(b.league || '');
        default:
          return 0;
      }
    });
  };

  // Group matches by league (or flat list for certain sorts)
  const groupedMatches = useMemo(() => {
    // For popularity and bookmakers sort, show flat list sorted globally
    if (selectedSort === 'popularity' || selectedSort === 'bookmakers') {
      const sorted = sortMatches(filteredMatches);
      return { 'All Matches': sorted };
    }

    // For league sort, group by country + league name to ensure complete separation
    const groups = {};
    filteredMatches.forEach(match => {
      // Use matched league for grouping to normalize variants
      const matchedLeague = matchLeague(match.league);

      let groupKey;
      if (matchedLeague) {
        // Get country name for display
        const country = COUNTRIES[matchedLeague.country];
        const countryName = country ? country.name : matchedLeague.country;

        // Format: "Country - League Name" for clear separation
        // Special cases: International competitions don't need country prefix
        if (['europe', 'international', 'africa', 'southamerica'].includes(matchedLeague.country)) {
          groupKey = matchedLeague.name;
        } else {
          groupKey = `${countryName} - ${matchedLeague.name}`;
        }
      } else {
        // Unmatched leagues: extract country from "Country. League" format if present
        const countryMatch = match.league.match(/^([^.]+)\.\s*(.+)$/);
        if (countryMatch) {
          const countryPart = countryMatch[1].trim();
          const leaguePart = countryMatch[2].trim();
          // Use format "Country - League" for consistency, even for unknown leagues
          groupKey = `${countryPart} - ${leaguePart}`;
        } else {
          // No country prefix found - use original name
          groupKey = match.league;
        }
      }

      if (!groups[groupKey]) {
        groups[groupKey] = [];
      }
      groups[groupKey].push(match);
    });

    // Sort matches within each league by time
    Object.keys(groups).forEach(league => {
      groups[league] = sortMatches(groups[league]);
    });

    // For league sort, return sorted by league name
    if (selectedSort === 'league') {
      const sortedKeys = Object.keys(groups).sort();
      const sortedGroups = {};
      sortedKeys.forEach(key => {
        sortedGroups[key] = groups[key];
      });
      return sortedGroups;
    }

    return groups;
  }, [filteredMatches, selectedSort]);

  // Get current market config
  const currentMarket = MARKETS[selectedMarket];
  const marketFields = MARKET_FIELDS[selectedMarket];

  return (
    <div className="odds-page">
      {/* Hero Strip - Top Matches */}
      {!loading && featuredMatches.length > 0 && (
        <div className="hero-strip">
          <div className="hero-header">
            <h2>Today's Top Matches</h2>
            <span className="hero-subtitle">Big games with best odds</span>
          </div>
          <div className="hero-matches">
            {featuredMatches.map((match, idx) => {
              const bestHome = getBestOdds(match, 'home_odds');
              const bestDraw = getBestOdds(match, 'draw_odds');
              const bestAway = getBestOdds(match, 'away_odds');

              // Shorten team names for display
              const shortenName = (name) => {
                if (name.length <= 12) return name;
                // Common abbreviations
                const abbrevs = {
                  'Manchester United': 'Man United',
                  'Manchester City': 'Man City',
                  'Tottenham Hotspur': 'Tottenham',
                  'Wolverhampton': 'Wolves',
                  'Brighton & Hove': 'Brighton',
                  'Nottingham Forest': "Nott'm Forest",
                };
                return abbrevs[name] || name.slice(0, 11) + '...';
              };

              return (
                <div key={idx} className="hero-card">
                  <div className="hero-card-header">
                    <span className="hero-league">{match.league}</span>
                  </div>
                  <div className="hero-teams">
                    <div className="hero-team">
                      <TeamLogo teamName={match.home_team} size={36} />
                      <span title={match.home_team}>{shortenName(match.home_team)}</span>
                    </div>
                    <span className="hero-vs">vs</span>
                    <div className="hero-team">
                      <TeamLogo teamName={match.away_team} size={36} />
                      <span title={match.away_team}>{shortenName(match.away_team)}</span>
                    </div>
                  </div>
                  <div className="hero-odds">
                    <div className="hero-odd">
                      <span className="odd-label">1</span>
                      <span className="odd-value">{bestHome.value?.toFixed(2) || '-'}</span>
                    </div>
                    <div className="hero-odd">
                      <span className="odd-label">X</span>
                      <span className="odd-value">{bestDraw.value?.toFixed(2) || '-'}</span>
                    </div>
                    <div className="hero-odd">
                      <span className="odd-label">2</span>
                      <span className="odd-value">{bestAway.value?.toFixed(2) || '-'}</span>
                    </div>
                  </div>
                  <div className="hero-kickoff">
                    {formatTime(match.start_time)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Date Tabs */}
      <div className="date-tabs">
        {DATE_FILTERS.map((df) => (
          <button
            key={df.id}
            className={`date-tab ${selectedDate === df.id ? 'active' : ''}`}
            onClick={() => setSelectedDate(df.id)}
          >
            <span className="date-icon">{df.icon}</span>
            <span className="date-name">{df.name}</span>
          </button>
        ))}
      </div>

      {/* Bookie Filter Bar */}
      <div className="bookie-filter-bar">
        <span className="filter-label">Bookmakers:</span>
        <div className="bookie-toggles">
          {BOOKMAKER_ORDER.map((bookie) => {
            const config = BOOKMAKER_AFFILIATES[bookie];
            return (
              <button
                key={bookie}
                className={`bookie-toggle ${enabledBookies[bookie] ? 'active' : ''}`}
                onClick={() => toggleBookie(bookie)}
                title={enabledBookies[bookie] ? `Hide ${config.name}` : `Show ${config.name}`}
              >
                <BookmakerLogo bookmaker={bookie} size={20} />
              </button>
            );
          })}
        </div>
        <button
          className="toggle-all-btn"
          onClick={() => {
            const allEnabled = Object.values(enabledBookies).every(v => v);
            setEnabledBookies(
              BOOKMAKER_ORDER.reduce((acc, b) => ({ ...acc, [b]: !allEnabled }), {})
            );
          }}
        >
          {Object.values(enabledBookies).every(v => v) ? 'Hide All' : 'Show All'}
        </button>
      </div>

      {/* CTA Section */}
      <div className="cta-section">
        <button
          className="cta-btn cta-leagues"
          onClick={() => {
            setSelectedLeagues([]);
            setSelectedDate('all');
            setShowAllMatches(true);
          }}
        >
          <span className="cta-icon">🏆</span>
          <span className="cta-text">View All Leagues</span>
        </button>
        <button className="cta-btn cta-watchlist">
          <span className="cta-icon">⭐</span>
          <span className="cta-text">My Watchlist</span>
        </button>
      </div>

      {/* Header Bar */}
      <div className="filter-card">
        <div className="filter-card-top">
          <div className="search-wrapper">
            <svg className="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
            <input
              type="text"
              placeholder="Search teams or leagues..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-field"
            />
            {searchQuery && (
              <button className="clear-btn" onClick={() => setSearchQuery('')}>×</button>
            )}
          </div>
          <div className="filter-top-actions">
            <select
              className="country-select"
              value={selectedCountry}
              onChange={(e) => {
                setSelectedCountry(e.target.value);
                if (e.target.value !== 'all') setSelectedLeagues([]); // Reset leagues when selecting country
              }}
            >
              {COUNTRY_FILTERS.map((country) => (
                <option key={country.id} value={country.id}>
                  {country.name}
                </option>
              ))}
            </select>
            <div className="sort-selector">
              <label className="sort-label">Sort:</label>
              <select
                className="sort-select"
                value={selectedSort}
                onChange={(e) => setSelectedSort(e.target.value)}
              >
                {SORT_OPTIONS.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.icon} {option.name}
                  </option>
                ))}
              </select>
            </div>
            <button
              className="refresh-btn"
              onClick={handleRefresh}
              disabled={refreshing}
            >
              <svg className={`refresh-icon ${refreshing ? 'spinning' : ''}`} viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
              </svg>
              {refreshing ? 'Refreshing...' : 'Refresh'}
            </button>
            {status?.last_scan && (
              <div className="last-update-badge">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 6v6l4 2" />
                </svg>
                <span className="update-time">{formatRelativeTime(status.last_scan)}</span>
              </div>
            )}
          </div>
        </div>
        <div className="filter-pill-rail">
          {combinedPills.map(pill => {
            if (pill.type === 'league') {
              return (
                <button
                  key={`league-${pill.id}`}
                  className={`league-btn ${
                    pill.id === 'all'
                      ? selectedLeagues.length === 0 ? 'active' : ''
                      : selectedLeagues.includes(pill.id) ? 'active' : ''
                  }`}
                  onClick={() => {
                    if (pill.id === 'all') {
                      setSelectedLeagues([]);
                    } else {
                      setSelectedLeagues(prev =>
                        prev.includes(pill.id)
                          ? prev.filter(id => id !== pill.id)
                          : [...prev, pill.id]
                      );
                    }
                  }}
                >
                  <LeagueLogo leagueId={pill.id} size={14} />
                  <span className="league-name">{pill.name}</span>
                </button>
              );
            }
            // keyword pill
            const isActive = leagueQuery === pill.value;
            return (
              <button
                key={`kw-${pill.id}`}
                className={`league-btn keyword ${isActive ? 'active' : ''}`}
                onClick={() => setLeagueQuery(prev => prev === pill.value ? '' : pill.value)}
              >
                {pill.logoId ? (
                  <LeagueLogo leagueId={pill.logoId} size={14} className="league-query-logo" />
                ) : (
                  <span className="league-query-logo league-logo-fallback">
                    {(pill.label || '•').slice(0, 2)}
                  </span>
                )}
                <span className="league-name">{pill.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Market Tabs */}
      <div className="market-tabs">
        {Object.values(MARKETS).map((market) => (
          <button
            key={market.id}
            className={`market-tab ${selectedMarket === market.id ? 'active' : ''}`}
            onClick={() => setSelectedMarket(market.id)}
          >
            <span className="market-name">{market.name}</span>
            <span className="market-desc">{market.description}</span>
          </button>
        ))}
      </div>

      {/* Main Odds Grid */}
      <div className={`odds-wrapper ${compactView ? 'compact' : ''}`} style={{ '--odds-columns': oddsColumns }}>
        {!compactView && (
          <div className="odds-sticky-header">
            {/* Table Header - Bookmakers */}
            <div className="odds-header">
              <div className="header-match">Match</div>
              <div className="header-time">Kick-off</div>
              {activeBookmakers.map((name) => {
                const config = BOOKMAKER_AFFILIATES[name];
                return (
                  <a
                    key={name}
                    href={config.affiliateUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="header-bookmaker"
                  >
                    <BookmakerLogo bookmaker={name} size={28} />
                    <span className="bookie-name">{config.name}</span>
                  </a>
                );
              })}
            </div>

            {/* Outcome Labels Row */}
            <div className="outcome-row">
              <div className="outcome-match"></div>
              <div className="outcome-time"></div>
              {activeBookmakers.map((name) => (
                <div key={name} className={`outcome-labels ${selectedMarket === 'over_under' ? 'two-col' : ''}`}>
                  {currentMarket.labels.map((label, i) => (
                    <span key={i}>{label}</span>
                  ))}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Scrollable Content */}
        <div className="odds-container">
        {/* Loading State */}
        {loading && (
          <div className="loading-state">
            <div className="spinner"></div>
            <span>Loading odds from bookmakers...</span>
          </div>
        )}

        {/* Error State */}
        {!loading && error && (
          <div className="empty-state error-state">
            <span className="empty-icon">⚠️</span>
            <p>{error}</p>
            <button className="retry-btn" onClick={loadData}>Try Again</button>
          </div>
        )}

        {/* No Results */}
        {!loading && !error && filteredMatches.length === 0 && matches.length === 0 && (
          <div className="empty-state">
            <span className="empty-icon">dY"S</span>
            <p>{hasDateFilter ? 'No fixtures for the selected date' : 'No odds available yet'}</p>
            <span>
              {hasDateFilter
                ? 'Try a different date or show all matches.'
                : 'Data is being collected. Check back in a few minutes.'}
            </span>
            {hasDateFilter ? (
              <button className="retry-btn" onClick={() => setSelectedDate('all')}>Show All Dates</button>
            ) : (
              <button className="retry-btn" onClick={loadData}>Refresh</button>
            )}
          </div>
        )}

        {/* No Results from filter */}
        {!loading && !error && filteredMatches.length === 0 && matches.length > 0 && (
          <div className="empty-state">
            <span className="empty-icon">dY"?</span>
            <p>{hasFilters ? 'No matches for these filters' : 'No fixtures for the selected date'}</p>
            <span>
              {hasFilters
                ? 'Try clearing filters or adjusting your search.'
                : 'Try a different date or show all matches.'}
            </span>
            {hasFilters ? (
              <button className="retry-btn" onClick={resetFilters}>Reset Filters</button>
            ) : (
              <button className="retry-btn" onClick={() => setSelectedDate('all')}>Show All Dates</button>
            )}
          </div>
        )}

        {/* Matches grouped by league */}
        {!loading && Object.entries(groupedMatches).map(([league, leagueMatches]) => (
          <div key={league} className="league-group">
            <div className="league-header">
              <span className="league-dot"></span>
              <span className="league-title">{league}</span>
              <span className="match-count">{leagueMatches.length} matches</span>
            </div>

            {leagueMatches.map((match, idx) => {
              // Calculate best odds and averages for current market
              const bestOdds = marketFields.map(field => getBestOdds(match, field));
              const avgOdds = marketFields.map(field => getMarketAverage(match, field));

              // Calculate best 1x2 odds for sharing (always use 1x2 regardless of selected market)
              const best1x2Home = getBestOdds(match, 'home_odds');
              const best1x2Draw = getBestOdds(match, 'draw_odds');
              const best1x2Away = getBestOdds(match, 'away_odds');

              // Create share link for this specific match
              const shareLink = `${window.location.origin}/odds?match=${encodeURIComponent(match.home_team + ' vs ' + match.away_team)}`;

              if (compactView) {
                return (
                  <div key={idx} className="odds-card">
                    <div className="odds-card-header">
                      <div className="odds-card-teams">
                        <div className="odds-card-team">
                          <TeamLogo teamName={match.home_team} size={18} />
                          <span className="team-name">{match.home_team}</span>
                        </div>
                        <div className="odds-card-team">
                          <TeamLogo teamName={match.away_team} size={18} />
                          <span className="team-name">{match.away_team}</span>
                        </div>
                      </div>
                      <div className="odds-card-meta">
                        <span className="odds-card-time">{formatTime(match.start_time)}</span>
                        <span className="odds-card-league">{match.league}</span>
                        <div className="odds-card-share">
                          <ShareButton
                            home_team={match.home_team}
                            away_team={match.away_team}
                            league={match.league}
                            time={formatTime(match.start_time)}
                            bestHome={best1x2Home}
                            bestDraw={best1x2Draw}
                            bestAway={best1x2Away}
                            shareLink={shareLink}
                          />
                        </div>
                      </div>
                    </div>

                    <div className="odds-card-odds">
                      {activeBookmakers.map((bookmaker) => {
                        const bookieOdds = match.odds?.find((o) => o.bookmaker === bookmaker);
                        const config = BOOKMAKER_AFFILIATES[bookmaker];

                        return (
                          <div key={bookmaker} className="odds-card-row">
                            <a
                              href={config.affiliateUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="odds-card-bookie"
                            >
                              <BookmakerLogo bookmaker={bookmaker} size={22} />
                              <span className="odds-card-bookie-name">{config.name}</span>
                            </a>
                            <div className={`odds-card-values ${selectedMarket === 'over_under' ? 'two-col' : ''}`}>
                              {bookieOdds ? (
                                marketFields.map((field, i) => {
                                  const oddsValue = bookieOdds[field];
                                  const isBest = oddsValue && oddsValue === bestOdds[i].value;
                                  const isEdge = isBigEdge(oddsValue, avgOdds[i]);
                                  const isSmallEdge = !isEdge && isAboveAverage(oddsValue, avgOdds[i]);
                                  const edgePercent = avgOdds[i] ? ((oddsValue - avgOdds[i]) / avgOdds[i] * 100).toFixed(0) : 0;

                                  return (
                                    <a
                                      key={field}
                                      href={config.affiliateUrl}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className={`odd ${isBest ? 'best' : ''} ${isEdge ? 'big-edge' : isSmallEdge ? 'edge' : ''}`}
                                      onClick={(e) => handleOddsClick(e, oddsValue, currentMarket.labels[i], config.name)}
                                      title={`Click for probability  ${oddsToProb(oddsValue).toFixed(1)}%`}
                                    >
                                      <span className="odds-card-odd-label">{currentMarket.labels[i]}</span>
                                      <span className="odds-card-odd-value">{oddsValue ? oddsValue.toFixed(2) : '-'}</span>
                                      {isBest && oddsValue && <span className="best-tag">BEST</span>}
                                      {isEdge && oddsValue && <span className="edge-tag">+{edgePercent}%</span>}
                                    </a>
                                  );
                                })
                              ) : (
                                marketFields.map((_, i) => (
                                  <span key={i} className={`odd empty ${match.pendingOdds ? 'pending' : ''}`}>
                                    <span className="odds-card-odd-label">{currentMarket.labels[i]}</span>
                                    <span className="odds-card-odd-value">{match.pendingOdds ? 'Pending.' : '-'}</span>
                                  </span>
                                ))
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              }

              return (
                <div key={idx} className="match-row">
                  {/* Teams */}
                  <div className="match-teams-cell">
                    <div className="team-row">
                      <TeamLogo teamName={match.home_team} size={20} />
                      <span className="team-name">{match.home_team}</span>
                    </div>
                    <div className="team-row">
                      <TeamLogo teamName={match.away_team} size={20} />
                      <span className="team-name">{match.away_team}</span>
                    </div>
                    {/* Share button */}
                    <ShareButton
                      home_team={match.home_team}
                      away_team={match.away_team}
                      league={match.league}
                      time={formatTime(match.start_time)}
                      bestHome={best1x2Home}
                      bestDraw={best1x2Draw}
                      bestAway={best1x2Away}
                      shareLink={shareLink}
                    />
                  </div>

                  {/* Kick-off Time */}
                  <div className="match-time-cell">
                    <span className="kickoff-time">{formatTime(match.start_time)}</span>
                  </div>

                  {/* Odds for each bookmaker */}
                  {activeBookmakers.map((bookmaker) => {
                    const bookieOdds = match.odds?.find((o) => o.bookmaker === bookmaker);
                    const config = BOOKMAKER_AFFILIATES[bookmaker];

                    return (
                      <div key={bookmaker} className={`odds-cell ${selectedMarket === 'over_under' ? 'two-col' : ''}`}>
                        {bookieOdds ? (
                          marketFields.map((field, i) => {
                            const oddsValue = bookieOdds[field];
                            const isBest = oddsValue && oddsValue === bestOdds[i].value;
                            const isEdge = isBigEdge(oddsValue, avgOdds[i]);
                            const isSmallEdge = !isEdge && isAboveAverage(oddsValue, avgOdds[i]);
                            const edgePercent = avgOdds[i] ? ((oddsValue - avgOdds[i]) / avgOdds[i] * 100).toFixed(0) : 0;

                            return (
                              <a
                                key={field}
                                href={config.affiliateUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className={`odd ${isBest ? 'best' : ''} ${isEdge ? 'big-edge' : isSmallEdge ? 'edge' : ''}`}
                                onClick={(e) => handleOddsClick(e, oddsValue, currentMarket.labels[i], config.name)}
                                title={`Click for probability • ${oddsToProb(oddsValue).toFixed(1)}%`}
                              >
                                {oddsValue ? oddsValue.toFixed(2) : '-'}
                                {isBest && oddsValue && <span className="best-tag">BEST</span>}
                                {isEdge && oddsValue && <span className="edge-tag">+{edgePercent}%</span>}
                              </a>
                            );
                          })
                        ) : (
                          marketFields.map((_, i) => (
                            match.pendingOdds ? (
                              <span key={i} className="odd empty pending">
                                Pending…
                              </span>
                            ) : (
                              <span key={i} className="odd empty">-</span>
                            )
                          ))
                        )}
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        ))}

        {/* Mobile scroll hint */}
        {!compactView && (
          <div className="scroll-hint-mobile">
            <span>Swipe for more bookmakers</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </div>
        )}
        </div>{/* End odds-container */}
      </div>{/* End odds-wrapper */}

      {/* Quick Stats Footer */}
      <div className="quick-stats">
        <div className="stat">
          <span className="stat-num">{filteredMatches.length}</span>
          <span className="stat-lbl">Matches</span>
        </div>
        <div className="stat">
          <span className="stat-num">{Object.keys(groupedMatches).length}</span>
          <span className="stat-lbl">Leagues</span>
        </div>
        <div className="stat">
          <span className="stat-num">{activeBookmakers.length}</span>
          <span className="stat-lbl">Bookmakers</span>
        </div>
        <div className="stat last-updated-stat">
          <span className="stat-num update-icon">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 6v6l4 2" />
            </svg>
          </span>
          <span className="stat-lbl">{status?.last_scan ? formatRelativeTime(status.last_scan) : 'Loading...'}</span>
        </div>
      </div>

      {/* Probability Tooltip */}
      {selectedOdd && (
        <div
          className="probability-tooltip"
          style={{
            position: 'fixed',
            left: Math.min(selectedOdd.x, window.innerWidth - 180),
            top: selectedOdd.y - 80,
            zIndex: 1000,
          }}
          onClick={() => setSelectedOdd(null)}
        >
          <div className="prob-header">
            <span className="prob-outcome">{selectedOdd.outcome}</span>
            <span className="prob-bookie">{selectedOdd.bookmaker}</span>
          </div>
          <div className="prob-main">
            <span className="prob-odds">{selectedOdd.odds.toFixed(2)}</span>
            <span className="prob-arrow">=</span>
            <span className="prob-percent">{selectedOdd.prob}%</span>
          </div>
          <div className="prob-label">Implied Probability</div>
        </div>
      )}
    </div>
  );
}

export default OddsPage;
