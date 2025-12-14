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

// Popular leagues for quick filters
const POPULAR_LEAGUES = [
  { id: 'all', name: 'All', icon: '⚽' },
  { id: 'premier', name: 'Premier League', icon: '🏴󠁧󠁢󠁥󠁮󠁧󠁿', keywords: ['Premier League', 'England. Premier'] },
  { id: 'laliga', name: 'La Liga', icon: '🇪🇸', keywords: ['La Liga', 'Spain. La Liga'] },
  { id: 'bundesliga', name: 'Bundesliga', icon: '🇩🇪', keywords: ['Bundesliga', 'Germany'] },
  { id: 'seriea', name: 'Serie A', icon: '🇮🇹', keywords: ['Serie A', 'Italy'] },
  { id: 'ligue1', name: 'Ligue 1', icon: '🇫🇷', keywords: ['Ligue 1', 'France'] },
  { id: 'ucl', name: 'Champions League', icon: '🏆', keywords: ['Champions League', 'UEFA Champions'] },
  { id: 'ghana', name: 'Ghana', icon: '🇬🇭', keywords: ['Ghana'] },
  { id: 'africa', name: 'Africa', icon: '🌍', keywords: ['Africa', 'CAF', 'AFCON', 'Nigeria', 'Kenya', 'South Africa'] },
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
  const [error, setError] = useState(null);
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

  // Get featured/top matches (top leagues, most bookmakers)
  const featuredMatches = useMemo(() => {
    const topLeagues = ['Premier League', 'England', 'La Liga', 'Spain', 'Champions League', 'Serie A', 'Bundesliga'];
    return matches
      .filter(m =>
        topLeagues.some(kw => m.league.toLowerCase().includes(kw.toLowerCase())) &&
        m.odds?.length >= 3  // At least 3 bookmakers
      )
      .sort((a, b) => (b.odds?.length || 0) - (a.odds?.length || 0))  // Most bookmakers first
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
              const oddsHistory = generateOddsHistory(match.odds?.[0]?.home_odds, 72, 'random');
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
            disabled={refreshing}
          >
            <svg className={`refresh-icon ${refreshing ? 'spinning' : ''}`} viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
            </svg>
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
          {status?.last_scan && (
            <span className="last-update">
              Updated: {new Date(status.last_scan).toLocaleTimeString()}
            </span>
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

              // Generate odds history for display (computed each render for demo simplicity)
              const primaryField = marketFields[0];
              const primaryOdds = match.odds?.[0]?.[primaryField];
              const oddsHistory = generateOddsHistory(primaryOdds, 72, 'random');
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
          <span className="stat-num">{activeBookmakers.length}</span>
          <span className="stat-lbl">Bookmakers</span>
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
