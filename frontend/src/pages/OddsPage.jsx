import { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getMatches, getStatus, triggerScan } from '../services/api';
import { BOOKMAKER_AFFILIATES, BOOKMAKER_ORDER, getAffiliateUrl } from '../config/affiliates';
import { LEAGUES, COUNTRIES, matchesAnyLeague, isCountryMatch, getLeagueTier } from '../config/leagues';
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
];

// Build country filters from centralized config
const COUNTRY_FILTERS = [
  { id: 'all', name: 'All Countries' },
  ...Object.values(COUNTRIES)
    .filter(c => ['england', 'spain', 'germany', 'italy', 'france', 'portugal', 'netherlands', 'scotland', 'ghana', 'europe'].includes(c.id))
    .map(c => ({ id: c.id, name: c.name, flag: c.flag })),
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
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
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

  useEffect(() => {
    loadData();
  }, []);

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

  // Preload team logos when matches change
  useEffect(() => {
    if (matches.length > 0) {
      const teamNames = matches.flatMap(m => [m.home_team, m.away_team]);
      preloadTeamLogos(teamNames.slice(0, 100));
    }
  }, [matches]);

  const loadData = async () => {
    setError(null);
    try {
      const [matchData, statusData] = await Promise.all([
        getMatches(500, 0, 2),  // Get up to 500 matches, min 2 bookmakers
        getStatus(),
      ]);

      // Enrich matches with synthetic market data if missing
      const enrichedMatches = (matchData.matches || matchData).map(match => ({
        ...match,
        odds: match.odds?.map(odds => ({
          ...odds,
          // Generate synthetic double chance and over/under if not present
          home_draw: odds.home_draw || calculateDoubleChance(odds.home_odds, odds.draw_odds),
          draw_away: odds.draw_away || calculateDoubleChance(odds.draw_odds, odds.away_odds),
          home_away: odds.home_away || calculateDoubleChance(odds.home_odds, odds.away_odds),
          over_25: odds.over_25 || generateOverUnder(odds.home_odds, odds.away_odds, true),
          under_25: odds.under_25 || generateOverUnder(odds.home_odds, odds.away_odds, false),
        }))
      }));

      setMatches(enrichedMatches);
      setStatus(statusData);
    } catch (err) {
      console.error('Failed to load odds:', err);
      setError('Unable to load odds. Please try again later.');
      setMatches([]);
    } finally {
      setLoading(false);
    }
  };

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
      await loadData();
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
    setTimeout(() => setSelectedOdd(null), 3000);
  };

  // Filter matches based on search, league, country, and date
  const filteredMatches = useMemo(() => {
    return matches.filter((match) => {
      const searchLower = searchQuery.toLowerCase();

      const matchesSearch =
        !searchQuery ||
        match.home_team.toLowerCase().includes(searchLower) ||
        match.away_team.toLowerCase().includes(searchLower) ||
        match.league.toLowerCase().includes(searchLower);

      // League filter using centralized matching
      const matchesLeague = matchesAnyLeague(match.league, selectedLeagues);

      // Country filter using centralized matching
      const matchesCountry = isCountryMatch(match.league, selectedCountry);

      const matchesDate = matchesDateFilter(match.start_time, selectedDate);

      return matchesSearch && matchesLeague && matchesCountry && matchesDate;
    });
  }, [matches, searchQuery, selectedLeagues, selectedCountry, selectedDate]);

  // Filter visible league pills based on selected country
  const visibleLeagues = useMemo(() => {
    if (selectedCountry === 'all') {
      return POPULAR_LEAGUES;
    }
    return POPULAR_LEAGUES.filter(league =>
      league.country === 'all' || league.country === selectedCountry
    );
  }, [selectedCountry]);

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

    // For league sort, group by league and sort league names
    const groups = {};
    filteredMatches.forEach(match => {
      if (!groups[match.league]) {
        groups[match.league] = [];
      }
      groups[match.league].push(match);
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
      <div className="odds-toolbar">
        <div className="toolbar-left">
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
        </div>

        <div className="toolbar-center">
          <div className="league-filters">
            {visibleLeagues.map((league) => (
              <button
                key={league.id}
                className={`league-btn ${
                  league.id === 'all'
                    ? selectedLeagues.length === 0 ? 'active' : ''
                    : selectedLeagues.includes(league.id) ? 'active' : ''
                }`}
                onClick={() => {
                  if (league.id === 'all') {
                    // Clear all selections
                    setSelectedLeagues([]);
                  } else {
                    // Toggle league selection
                    setSelectedLeagues(prev =>
                      prev.includes(league.id)
                        ? prev.filter(id => id !== league.id) // Remove if already selected
                        : [...prev, league.id] // Add if not selected
                    );
                  }
                }}
              >
                <LeagueLogo leagueId={league.id} size={14} />
                <span className="league-name">{league.name}</span>
              </button>
            ))}
          </div>
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
        </div>

        <div className="toolbar-right">
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
      <div className="odds-container">
        {/* Table Header - Bookmakers */}
        <div className="odds-header" style={{ gridTemplateColumns: `minmax(200px, 280px) 100px repeat(${activeBookmakers.length}, minmax(120px, 1fr))` }}>
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
        <div className="outcome-row" style={{ gridTemplateColumns: `minmax(200px, 280px) 100px repeat(${activeBookmakers.length}, minmax(120px, 1fr))` }}>
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
            <span className="empty-icon">📊</span>
            <p>No odds available yet</p>
            <span>Data is being collected. Check back in a few minutes.</span>
            <button className="retry-btn" onClick={loadData}>Refresh</button>
          </div>
        )}

        {/* No Results from filter */}
        {!loading && !error && filteredMatches.length === 0 && matches.length > 0 && (
          <div className="empty-state">
            <span className="empty-icon">🔍</span>
            <p>No matches found</p>
            <span>Try adjusting your search or filters</span>
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

              return (
                <div key={idx} className="match-row" style={{ gridTemplateColumns: `minmax(200px, 280px) 100px repeat(${activeBookmakers.length}, minmax(120px, 1fr))` }}>
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
                      bestHome={best1x2Home.value || 0}
                      bestDraw={best1x2Draw.value || 0}
                      bestAway={best1x2Away.value || 0}
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
                            <span key={i} className="odd empty">-</span>
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
        <div className="scroll-hint-mobile">
          <span>Swipe for more bookmakers</span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </div>
      </div>

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
