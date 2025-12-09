import { useState, useEffect, useMemo } from 'react';
import { getMatches, getStatus, triggerScan } from '../services/api';
import { BOOKMAKER_AFFILIATES, BOOKMAKER_ORDER, getAffiliateUrl } from '../config/affiliates';
import { BookmakerLogo } from '../components/BookmakerLogo';
import { TeamLogo } from '../components/TeamLogo';
import { preloadTeamLogos, clearLogoCache } from '../services/teamLogos';
import Sparkline, { generateOddsHistory, analyzeOddsMovement } from '../components/Sparkline';

// Market types
const MARKETS = {
  '1x2': { id: '1x2', name: '1X2', labels: ['1', 'X', '2'], description: 'Match Result' },
  'double_chance': { id: 'double_chance', name: 'Double Chance', labels: ['1X', 'X2', '12'], description: 'Double Chance' },
  'over_under': { id: 'over_under', name: 'O/U 2.5', labels: ['Over', 'Under'], description: 'Over/Under 2.5 Goals' },
};

// Helper to create demo match times at realistic kick-off hours
const getDemoTime = (daysFromNow, hour, minute = 0) => {
  const date = new Date();
  date.setDate(date.getDate() + daysFromNow);
  date.setHours(hour, minute, 0, 0);
  return Math.floor(date.getTime() / 1000);
};

// Movement patterns for demo data
const MOVEMENT_PATTERNS = ['steam', 'drift', 'random', 'random', 'steam', 'drift'];

// Demo data with all markets
const DEMO_MATCHES = [
  {
    home_team: 'Real Madrid',
    away_team: 'Sevilla',
    league: 'Spain. La Liga',
    start_time: getDemoTime(1, 21, 0),
    movement: 'steam', // Home odds shortening - money on Real Madrid
    odds: [
      { bookmaker: 'Betway Ghana', home_odds: 1.28, draw_odds: 6.50, away_odds: 11.00, home_draw: 1.10, draw_away: 3.80, home_away: 1.18, over_25: 1.65, under_25: 2.20 },
      { bookmaker: 'SportyBet Ghana', home_odds: 1.27, draw_odds: 6.40, away_odds: 10.50, home_draw: 1.09, draw_away: 3.70, home_away: 1.17, over_25: 1.62, under_25: 2.25 },
      { bookmaker: '1xBet Ghana', home_odds: 1.29, draw_odds: 6.80, away_odds: 12.60, home_draw: 1.11, draw_away: 4.00, home_away: 1.20, over_25: 1.68, under_25: 2.18 },
      { bookmaker: '22Bet Ghana', home_odds: 1.29, draw_odds: 6.80, away_odds: 12.60, home_draw: 1.11, draw_away: 4.00, home_away: 1.20, over_25: 1.70, under_25: 2.15 },
      { bookmaker: 'SoccaBet Ghana', home_odds: 1.26, draw_odds: 6.20, away_odds: 10.00, home_draw: 1.08, draw_away: 3.60, home_away: 1.15, over_25: 1.60, under_25: 2.30 },
    ],
  },
  {
    home_team: 'Barcelona',
    away_team: 'Osasuna',
    league: 'Spain. La Liga',
    start_time: getDemoTime(2, 16, 0),
    movement: 'drift', // Away odds lengthening
    odds: [
      { bookmaker: 'Betway Ghana', home_odds: 1.25, draw_odds: 7.60, away_odds: 12.00, home_draw: 1.08, draw_away: 4.20, home_away: 1.15, over_25: 1.55, under_25: 2.40 },
      { bookmaker: 'SportyBet Ghana', home_odds: 1.24, draw_odds: 7.40, away_odds: 11.50, home_draw: 1.07, draw_away: 4.10, home_away: 1.14, over_25: 1.52, under_25: 2.45 },
      { bookmaker: '1xBet Ghana', home_odds: 1.26, draw_odds: 7.60, away_odds: 12.00, home_draw: 1.09, draw_away: 4.25, home_away: 1.16, over_25: 1.58, under_25: 2.38 },
      { bookmaker: '22Bet Ghana', home_odds: 1.26, draw_odds: 7.60, away_odds: 12.00, home_draw: 1.09, draw_away: 4.25, home_away: 1.16, over_25: 1.56, under_25: 2.42 },
      { bookmaker: 'SoccaBet Ghana', home_odds: 1.23, draw_odds: 7.20, away_odds: 11.00, home_draw: 1.06, draw_away: 4.00, home_away: 1.13, over_25: 1.50, under_25: 2.50 },
    ],
  },
  {
    home_team: 'Manchester United',
    away_team: 'Liverpool',
    league: 'England. Premier League',
    start_time: getDemoTime(3, 17, 30),
    movement: 'steam', // Liverpool odds shortening - big match steam
    odds: [
      { bookmaker: 'Betway Ghana', home_odds: 3.20, draw_odds: 3.40, away_odds: 2.25, home_draw: 1.65, draw_away: 1.35, home_away: 1.32, over_25: 1.72, under_25: 2.10 },
      { bookmaker: 'SportyBet Ghana', home_odds: 3.10, draw_odds: 3.35, away_odds: 2.30, home_draw: 1.62, draw_away: 1.37, home_away: 1.30, over_25: 1.70, under_25: 2.12 },
      { bookmaker: '1xBet Ghana', home_odds: 3.25, draw_odds: 3.45, away_odds: 2.28, home_draw: 1.68, draw_away: 1.36, home_away: 1.34, over_25: 1.75, under_25: 2.08 },
      { bookmaker: '22Bet Ghana', home_odds: 3.25, draw_odds: 3.45, away_odds: 2.28, home_draw: 1.68, draw_away: 1.36, home_away: 1.34, over_25: 1.78, under_25: 2.05 },
      { bookmaker: 'SoccaBet Ghana', home_odds: 3.15, draw_odds: 3.30, away_odds: 2.20, home_draw: 1.60, draw_away: 1.33, home_away: 1.28, over_25: 1.68, under_25: 2.15 },
    ],
  },
  {
    home_team: 'DR Congo',
    away_team: 'Benin',
    league: 'Africa Cup of Nations',
    start_time: getDemoTime(4, 14, 0),
    movement: 'random',
    odds: [
      { bookmaker: 'Betway Ghana', home_odds: 1.75, draw_odds: 3.60, away_odds: 5.80, home_draw: 1.22, draw_away: 2.15, home_away: 1.38, over_25: 2.10, under_25: 1.72 },
      { bookmaker: 'SportyBet Ghana', home_odds: 1.72, draw_odds: 3.55, away_odds: 5.60, home_draw: 1.20, draw_away: 2.10, home_away: 1.35, over_25: 2.05, under_25: 1.75 },
      { bookmaker: '1xBet Ghana', home_odds: 1.80, draw_odds: 3.87, away_odds: 6.55, home_draw: 1.25, draw_away: 2.30, home_away: 1.42, over_25: 2.15, under_25: 1.70 },
      { bookmaker: '22Bet Ghana', home_odds: 1.78, draw_odds: 3.70, away_odds: 6.00, home_draw: 1.23, draw_away: 2.20, home_away: 1.40, over_25: 2.12, under_25: 1.72 },
      { bookmaker: 'SoccaBet Ghana', home_odds: 1.90, draw_odds: 3.50, away_odds: 5.40, home_draw: 1.28, draw_away: 2.05, home_away: 1.45, over_25: 2.00, under_25: 1.80 },
    ],
  },
  {
    home_team: 'Arsenal',
    away_team: 'Chelsea',
    league: 'England. Premier League',
    start_time: getDemoTime(5, 15, 0),
    movement: 'steam', // Over 2.5 steaming
    odds: [
      { bookmaker: 'Betway Ghana', home_odds: 1.85, draw_odds: 3.80, away_odds: 4.20, home_draw: 1.28, draw_away: 1.95, home_away: 1.30, over_25: 1.65, under_25: 2.22 },
      { bookmaker: 'SportyBet Ghana', home_odds: 1.82, draw_odds: 3.75, away_odds: 4.10, home_draw: 1.26, draw_away: 1.92, home_away: 1.28, over_25: 1.62, under_25: 2.25 },
      { bookmaker: '1xBet Ghana', home_odds: 1.88, draw_odds: 3.85, away_odds: 4.30, home_draw: 1.30, draw_away: 1.98, home_away: 1.32, over_25: 1.68, under_25: 2.18 },
      { bookmaker: '22Bet Ghana', home_odds: 1.88, draw_odds: 3.85, away_odds: 4.30, home_draw: 1.30, draw_away: 1.98, home_away: 1.32, over_25: 1.70, under_25: 2.15 },
      { bookmaker: 'SoccaBet Ghana', home_odds: 1.80, draw_odds: 3.70, away_odds: 4.00, home_draw: 1.24, draw_away: 1.88, home_away: 1.26, over_25: 1.60, under_25: 2.28 },
    ],
  },
  {
    home_team: 'Accra Hearts',
    away_team: 'Asante Kotoko',
    league: 'Ghana Premier League',
    start_time: getDemoTime(6, 16, 0),
    movement: 'drift', // Draw drifting - less likely
    odds: [
      { bookmaker: 'Betway Ghana', home_odds: 2.10, draw_odds: 3.20, away_odds: 3.50, home_draw: 1.28, draw_away: 1.65, home_away: 1.35, over_25: 2.20, under_25: 1.65 },
      { bookmaker: 'SportyBet Ghana', home_odds: 2.05, draw_odds: 3.15, away_odds: 3.45, home_draw: 1.26, draw_away: 1.62, home_away: 1.33, over_25: 2.15, under_25: 1.68 },
      { bookmaker: '1xBet Ghana', home_odds: 2.15, draw_odds: 3.25, away_odds: 3.55, home_draw: 1.30, draw_away: 1.68, home_away: 1.38, over_25: 2.25, under_25: 1.62 },
      { bookmaker: '22Bet Ghana', home_odds: 2.12, draw_odds: 3.22, away_odds: 3.52, home_draw: 1.29, draw_away: 1.66, home_away: 1.36, over_25: 2.22, under_25: 1.64 },
      { bookmaker: 'SoccaBet Ghana', home_odds: 2.00, draw_odds: 3.10, away_odds: 3.40, home_draw: 1.24, draw_away: 1.60, home_away: 1.31, over_25: 2.10, under_25: 1.70 },
    ],
  },
];

// Popular leagues for quick filters
const POPULAR_LEAGUES = [
  { id: 'all', name: 'All', icon: '⚽' },
  { id: 'premier', name: 'Premier League', icon: '🏴󠁧󠁢󠁥󠁮󠁧󠁿', keywords: ['Premier League', 'England'] },
  { id: 'laliga', name: 'La Liga', icon: '🇪🇸', keywords: ['La Liga', 'Spain'] },
  { id: 'ghana', name: 'Ghana', icon: '🇬🇭', keywords: ['Ghana'] },
  { id: 'afcon', name: 'AFCON', icon: '🌍', keywords: ['Africa Cup', 'AFCON'] },
];

// Date filter options
const DATE_FILTERS = [
  { id: 'today', name: 'Today', icon: '📅' },
  { id: 'tomorrow', name: 'Tomorrow', icon: '📆' },
  { id: 'weekend', name: 'Weekend', icon: '🗓️' },
  { id: 'all', name: 'All', icon: '📋' },
];

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
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [status, setStatus] = useState(null);
  const [useDemo, setUseDemo] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLeague, setSelectedLeague] = useState('all');
  const [selectedMarket, setSelectedMarket] = useState('1x2');
  const [selectedOdd, setSelectedOdd] = useState(null);
  const [selectedDate, setSelectedDate] = useState('all');
  const [enabledBookies, setEnabledBookies] = useState(() =>
    BOOKMAKER_ORDER.reduce((acc, b) => ({ ...acc, [b]: true }), {})
  );
  const [showAllMatches, setShowAllMatches] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  // Preload team logos when matches change
  useEffect(() => {
    if (matches.length > 0) {
      const teamNames = matches.flatMap(m => [m.home_team, m.away_team]);
      preloadTeamLogos(teamNames.slice(0, 100));
    }
  }, [matches]);

  const loadData = async () => {
    try {
      const [matchData, statusData] = await Promise.all([
        getMatches(100, 0, 3),
        getStatus(),
      ]);

      // Add demo market data to API matches if missing
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
      setUseDemo(false);
    } catch (error) {
      console.log('API unavailable, using demo data');
      setMatches(DEMO_MATCHES);
      setUseDemo(true);
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

  // Filter matches based on search, league, and date
  const filteredMatches = useMemo(() => {
    return matches.filter((match) => {
      const searchLower = searchQuery.toLowerCase();
      const matchesSearch =
        !searchQuery ||
        match.home_team.toLowerCase().includes(searchLower) ||
        match.away_team.toLowerCase().includes(searchLower) ||
        match.league.toLowerCase().includes(searchLower);

      let matchesLeague = selectedLeague === 'all';
      if (!matchesLeague) {
        const league = POPULAR_LEAGUES.find((l) => l.id === selectedLeague);
        if (league && league.keywords) {
          matchesLeague = league.keywords.some((keyword) =>
            match.league.toLowerCase().includes(keyword.toLowerCase())
          );
        }
      }

      const matchesDate = matchesDateFilter(match.start_time, selectedDate);

      return matchesSearch && matchesLeague && matchesDate;
    });
  }, [matches, searchQuery, selectedLeague, selectedDate]);

  // Get featured/top matches (Premier League, big games with movement)
  const featuredMatches = useMemo(() => {
    const topLeagues = ['Premier League', 'England', 'La Liga', 'Spain', 'Champions'];
    return matches
      .filter(m =>
        topLeagues.some(kw => m.league.toLowerCase().includes(kw.toLowerCase())) ||
        m.movement === 'steam'
      )
      .slice(0, 3);
  }, [matches]);

  // Toggle bookmaker visibility
  const toggleBookie = (bookie) => {
    setEnabledBookies(prev => ({ ...prev, [bookie]: !prev[bookie] }));
  };

  // Get active bookmakers
  const activeBookmakers = BOOKMAKER_ORDER.filter(b => enabledBookies[b]);

  // Group matches by league
  const groupedMatches = useMemo(() => {
    const groups = {};
    filteredMatches.forEach(match => {
      if (!groups[match.league]) {
        groups[match.league] = [];
      }
      groups[match.league].push(match);
    });
    return groups;
  }, [filteredMatches]);

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
              const oddsHistory = generateOddsHistory(match.odds?.[0]?.home_odds, 72, match.movement || 'random');
              const movement = analyzeOddsMovement(oddsHistory);

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
                    {movement.trend !== 'stable' && (
                      <span className={`movement-badge ${movement.trend}`}>
                        {movement.trend === 'steam' ? '🔥 HOT' : '📈 DRIFT'}
                      </span>
                    )}
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
            setSelectedLeague('all');
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
            {POPULAR_LEAGUES.map((league) => (
              <button
                key={league.id}
                className={`league-btn ${selectedLeague === league.id ? 'active' : ''}`}
                onClick={() => setSelectedLeague(league.id)}
              >
                <span className="league-icon">{league.icon}</span>
                <span className="league-name">{league.name}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="toolbar-right">
          <button
            className="refresh-btn"
            onClick={handleRefresh}
            disabled={refreshing || useDemo}
          >
            <svg className={`refresh-icon ${refreshing ? 'spinning' : ''}`} viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
            </svg>
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
          {useDemo && <span className="demo-tag">Demo Mode</span>}
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
            <span>Loading odds...</span>
          </div>
        )}

        {/* No Results */}
        {!loading && filteredMatches.length === 0 && (
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

              // Generate odds history for display (computed each render for demo simplicity)
              const primaryField = marketFields[0];
              const primaryOdds = match.odds?.[0]?.[primaryField];
              const oddsHistory = generateOddsHistory(primaryOdds, 72, match.movement || 'random');
              const movement = analyzeOddsMovement(oddsHistory);

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
                    {/* Movement indicator */}
                    {movement.trend !== 'stable' && (
                      <div className="odds-movement">
                        <Sparkline
                          data={oddsHistory}
                          width={36}
                          height={14}
                        />
                        <span className={`movement-tag ${movement.trend}`}>
                          {movement.trend === 'steam' ? '🔥 STEAM' : '📈 DRIFT'}
                        </span>
                      </div>
                    )}
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
          <span className="stat-num">{status?.total_matches || matches.length * 5}</span>
          <span className="stat-lbl">Total Matches</span>
        </div>
        <div className="stat">
          <span className="stat-num">{filteredMatches.length}</span>
          <span className="stat-lbl">Displayed</span>
        </div>
        <div className="stat">
          <span className="stat-num">{Object.keys(groupedMatches).length}</span>
          <span className="stat-lbl">Leagues</span>
        </div>
        <div className="stat highlight">
          <span className="stat-num">{status?.arbitrage_count || 0}</span>
          <span className="stat-lbl">Arb Opps</span>
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
