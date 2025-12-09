import { useState, useEffect, useMemo } from 'react';
import { getMatches, getStatus, triggerScan } from '../services/api';
import { BOOKMAKER_AFFILIATES, BOOKMAKER_ORDER, getAffiliateUrl } from '../config/affiliates';
import { BookmakerLogo, StarRating, FeatureBadge, LiveIndicator } from '../components/BookmakerLogo';

// Demo data for when API is not available
const DEMO_MATCHES = [
  {
    home_team: 'Real Madrid',
    away_team: 'Sevilla',
    league: 'Spain. La Liga',
    start_time: Date.now() / 1000 + 86400,
    odds: [
      { bookmaker: 'Betway Ghana', home_odds: 1.28, draw_odds: 6.50, away_odds: 11.00 },
      { bookmaker: 'SportyBet Ghana', home_odds: 1.27, draw_odds: 6.40, away_odds: 10.50 },
      { bookmaker: '1xBet Ghana', home_odds: 1.29, draw_odds: 6.80, away_odds: 12.60 },
      { bookmaker: '22Bet Ghana', home_odds: 1.29, draw_odds: 6.80, away_odds: 12.60 },
      { bookmaker: 'SoccaBet Ghana', home_odds: 1.26, draw_odds: 6.20, away_odds: 10.00 },
    ],
  },
  {
    home_team: 'Barcelona',
    away_team: 'Osasuna',
    league: 'Spain. La Liga',
    start_time: Date.now() / 1000 + 172800,
    odds: [
      { bookmaker: 'Betway Ghana', home_odds: 1.25, draw_odds: 7.60, away_odds: 12.00 },
      { bookmaker: 'SportyBet Ghana', home_odds: 1.24, draw_odds: 7.40, away_odds: 11.50 },
      { bookmaker: '1xBet Ghana', home_odds: 1.26, draw_odds: 7.60, away_odds: 12.00 },
      { bookmaker: '22Bet Ghana', home_odds: 1.26, draw_odds: 7.60, away_odds: 12.00 },
      { bookmaker: 'SoccaBet Ghana', home_odds: 1.23, draw_odds: 7.20, away_odds: 11.00 },
    ],
  },
  {
    home_team: 'Manchester United',
    away_team: 'Liverpool',
    league: 'England. Premier League',
    start_time: Date.now() / 1000 + 259200,
    isLive: false,
    odds: [
      { bookmaker: 'Betway Ghana', home_odds: 3.20, draw_odds: 3.40, away_odds: 2.25 },
      { bookmaker: 'SportyBet Ghana', home_odds: 3.10, draw_odds: 3.35, away_odds: 2.30 },
      { bookmaker: '1xBet Ghana', home_odds: 3.25, draw_odds: 3.45, away_odds: 2.28 },
      { bookmaker: '22Bet Ghana', home_odds: 3.25, draw_odds: 3.45, away_odds: 2.28 },
      { bookmaker: 'SoccaBet Ghana', home_odds: 3.15, draw_odds: 3.30, away_odds: 2.20 },
    ],
  },
  {
    home_team: 'DR Congo',
    away_team: 'Benin',
    league: 'Africa Cup of Nations',
    start_time: Date.now() / 1000 + 345600,
    odds: [
      { bookmaker: 'Betway Ghana', home_odds: 1.75, draw_odds: 3.60, away_odds: 5.80 },
      { bookmaker: 'SportyBet Ghana', home_odds: 1.72, draw_odds: 3.55, away_odds: 5.60 },
      { bookmaker: '1xBet Ghana', home_odds: 1.80, draw_odds: 3.87, away_odds: 6.55 },
      { bookmaker: '22Bet Ghana', home_odds: 1.78, draw_odds: 3.70, away_odds: 6.00 },
      { bookmaker: 'SoccaBet Ghana', home_odds: 1.90, draw_odds: 3.50, away_odds: 5.40 },
    ],
  },
  {
    home_team: 'Arsenal',
    away_team: 'Chelsea',
    league: 'England. Premier League',
    start_time: Date.now() / 1000 + 432000,
    odds: [
      { bookmaker: 'Betway Ghana', home_odds: 1.85, draw_odds: 3.80, away_odds: 4.20 },
      { bookmaker: 'SportyBet Ghana', home_odds: 1.82, draw_odds: 3.75, away_odds: 4.10 },
      { bookmaker: '1xBet Ghana', home_odds: 1.88, draw_odds: 3.85, away_odds: 4.30 },
      { bookmaker: '22Bet Ghana', home_odds: 1.88, draw_odds: 3.85, away_odds: 4.30 },
      { bookmaker: 'SoccaBet Ghana', home_odds: 1.80, draw_odds: 3.70, away_odds: 4.00 },
    ],
  },
  {
    home_team: 'Accra Hearts',
    away_team: 'Asante Kotoko',
    league: 'Ghana Premier League',
    start_time: Date.now() / 1000 + 518400,
    odds: [
      { bookmaker: 'Betway Ghana', home_odds: 2.10, draw_odds: 3.20, away_odds: 3.50 },
      { bookmaker: 'SportyBet Ghana', home_odds: 2.05, draw_odds: 3.15, away_odds: 3.45 },
      { bookmaker: '1xBet Ghana', home_odds: 2.15, draw_odds: 3.25, away_odds: 3.55 },
      { bookmaker: '22Bet Ghana', home_odds: 2.12, draw_odds: 3.22, away_odds: 3.52 },
      { bookmaker: 'SoccaBet Ghana', home_odds: 2.00, draw_odds: 3.10, away_odds: 3.40 },
    ],
  },
];

// Popular leagues for quick filters
const POPULAR_LEAGUES = [
  { id: 'all', name: 'All Matches', icon: '⚽' },
  { id: 'premier', name: 'Premier League', icon: '🏴󠁧󠁢󠁥󠁮󠁧󠁿', keywords: ['Premier League', 'England'] },
  { id: 'laliga', name: 'La Liga', icon: '🇪🇸', keywords: ['La Liga', 'Spain'] },
  { id: 'ghana', name: 'Ghana', icon: '🇬🇭', keywords: ['Ghana'] },
  { id: 'afcon', name: 'AFCON', icon: '🌍', keywords: ['Africa Cup', 'AFCON'] },
];

// Skeleton loader component
function SkeletonRow() {
  return (
    <tr className="skeleton-row">
      <td className="match-info">
        <div className="skeleton skeleton-text" style={{ width: '70%' }}></div>
        <div className="skeleton skeleton-text" style={{ width: '50%', marginTop: '0.5rem' }}></div>
      </td>
      {BOOKMAKER_ORDER.map((name, idx) => (
        <td key={idx} colSpan="3"><div className="skeleton skeleton-odds"></div></td>
      ))}
    </tr>
  );
}

function OddsPage() {
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [status, setStatus] = useState(null);
  const [useDemo, setUseDemo] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLeague, setSelectedLeague] = useState('all');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [matchData, statusData] = await Promise.all([
        getMatches(100, 0, 3),
        getStatus(),
      ]);
      setMatches(matchData);
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
    return date.toLocaleDateString('en-GB', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getBestOdds = (match, type) => {
    const odds = match.odds || [];
    if (odds.length === 0) return { value: 0, bookmaker: '' };

    const key = `${type}_odds`;
    const best = odds.reduce((max, o) => (o[key] > max[key] ? o : max), odds[0]);
    return { value: best[key], bookmaker: best.bookmaker };
  };

  // Filter matches based on search and league
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

      return matchesSearch && matchesLeague;
    });
  }, [matches, searchQuery, selectedLeague]);

  const uniqueLeagues = useMemo(() => {
    return [...new Set(matches.map((m) => m.league))];
  }, [matches]);

  return (
    <div className="container">
      {/* Bookmaker Promo */}
      <div className="promo-banner">
        <div className="promo-content">
          <BookmakerLogo bookmaker="Betway Ghana" size={48} />
          <div className="promo-text">
            <strong>Betway Ghana</strong>
            <span>Get 50% Welcome Bonus up to GHS 200!</span>
          </div>
        </div>
        <a
          href={getAffiliateUrl('Betway Ghana')}
          target="_blank"
          rel="noopener noreferrer"
          className="promo-btn"
        >
          Claim Bonus
        </a>
      </div>

      {/* Stats */}
      <div className="stats-banner">
        <div className="stat-item">
          <div className="stat-icon">⚽</div>
          <div className="stat-content">
            <div className="stat-value">{status?.total_matches || matches.length * 5}</div>
            <div className="stat-label">Total Matches</div>
          </div>
        </div>
        <div className="stat-item">
          <div className="stat-icon">📊</div>
          <div className="stat-content">
            <div className="stat-value">{status?.matched_events || matches.length}</div>
            <div className="stat-label">Compared Events</div>
          </div>
        </div>
        <div className="stat-item">
          <div className="stat-icon">🏆</div>
          <div className="stat-content">
            <div className="stat-value">{uniqueLeagues.length || 5}</div>
            <div className="stat-label">Leagues</div>
          </div>
        </div>
        <div className="stat-item">
          <div className="stat-icon">💰</div>
          <div className="stat-content">
            <div className="stat-value">{status?.arbitrage_count || 0}</div>
            <div className="stat-label">Arb Opportunities</div>
          </div>
        </div>
      </div>

      {/* Bookmaker Logos with Ratings */}
      <div className="bookmaker-logos">
        {BOOKMAKER_ORDER.map((name) => {
          const config = BOOKMAKER_AFFILIATES[name];
          return (
            <a
              key={name}
              href={config.affiliateUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="bookmaker-logo-card"
            >
              <BookmakerLogo bookmaker={name} size={50} />
              <div className="bookmaker-info">
                <div className="bookmaker-name">{config.name}</div>
                <StarRating rating={config.rating} size={12} />
                <div className="bookmaker-bonus">{config.signupBonus}</div>
              </div>
            </a>
          );
        })}
      </div>

      {/* Odds Table */}
      <div className="odds-section">
        <div className="section-header">
          <h2 className="section-title">
            <span className="title-icon">📈</span>
            Football Odds Comparison {useDemo && <span className="demo-badge">Demo</span>}
          </h2>
          <button
            className="refresh-btn"
            onClick={handleRefresh}
            disabled={refreshing || useDemo}
          >
            <svg className="refresh-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
            </svg>
            {refreshing ? 'Refreshing...' : 'Refresh Odds'}
          </button>
        </div>

        {/* Search and Filters */}
        <div className="search-filter-bar">
          <div className="search-box">
            <svg className="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
            <input
              type="text"
              placeholder="Search teams or leagues..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
            {searchQuery && (
              <button className="clear-search" onClick={() => setSearchQuery('')}>
                ×
              </button>
            )}
          </div>
        </div>

        {/* League Filter Tabs */}
        <div className="filter-tabs">
          {POPULAR_LEAGUES.map((league) => (
            <button
              key={league.id}
              className={`filter-tab ${selectedLeague === league.id ? 'active' : ''}`}
              onClick={() => setSelectedLeague(league.id)}
            >
              <span className="filter-icon">{league.icon}</span>
              {league.name}
            </button>
          ))}
        </div>

        {/* Results count */}
        <div className="results-info">
          <span>Showing <strong>{filteredMatches.length}</strong> of {matches.length} matches</span>
          {!useDemo && (
            <span className="live-badge">
              <span className="live-dot"></span>
              Live Odds
            </span>
          )}
        </div>

        {/* Table Header with Bookmaker Logos */}
        <div className="bookmaker-header">
          <div className="match-header-cell">Match</div>
          {BOOKMAKER_ORDER.map((name) => {
            const config = BOOKMAKER_AFFILIATES[name];
            return (
              <a
                key={name}
                href={config.affiliateUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="bookmaker-header-cell"
              >
                <BookmakerLogo bookmaker={name} size={32} />
                <span className="bookmaker-header-name">{config.name}</span>
              </a>
            );
          })}
        </div>

        <div className="table-wrapper">
          <table className="odds-table">
            <thead>
              <tr>
                <th className="match-col sticky-col"></th>
                {BOOKMAKER_ORDER.map((name) => (
                  <th key={name} colSpan="3" className="bookmaker-th">
                    <span className="outcome-labels">
                      <span>1</span>
                      <span>X</span>
                      <span>2</span>
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <>
                  <SkeletonRow />
                  <SkeletonRow />
                  <SkeletonRow />
                  <SkeletonRow />
                  <SkeletonRow />
                </>
              ) : filteredMatches.length === 0 ? (
                <tr>
                  <td colSpan={1 + BOOKMAKER_ORDER.length * 3} className="no-results">
                    <div className="no-results-content">
                      <span className="no-results-icon">🔍</span>
                      <p>No matches found</p>
                      <span>Try adjusting your search or filters</span>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredMatches.map((match, idx) => {
                  const bestHome = getBestOdds(match, 'home');
                  const bestDraw = getBestOdds(match, 'draw');
                  const bestAway = getBestOdds(match, 'away');

                  return (
                    <tr key={idx} className={match.isLive ? 'live-match' : ''}>
                      <td className="match-info sticky-col">
                        <div className="match-teams">
                          {match.isLive && <LiveIndicator />}
                          {match.home_team} <span className="vs">vs</span> {match.away_team}
                        </div>
                        <div className="match-meta">
                          <span className="match-league">
                            <span className="league-dot"></span>
                            {match.league}
                          </span>
                          <span className="match-time">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <circle cx="12" cy="12" r="10" />
                              <path d="M12 6v6l4 2" />
                            </svg>
                            {formatTime(match.start_time)}
                          </span>
                        </div>
                      </td>
                      {BOOKMAKER_ORDER.map((bookmaker) => {
                        const bookieOdds = match.odds?.find((o) => o.bookmaker === bookmaker);
                        const config = BOOKMAKER_AFFILIATES[bookmaker];

                        return (
                          <td key={bookmaker} colSpan="3" className="odds-cell-group">
                            <div className="odds-trio">
                              {bookieOdds?.home_odds ? (
                                <a
                                  href={config.affiliateUrl}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className={`odds-btn ${bookieOdds.home_odds === bestHome.value ? 'best' : ''}`}
                                  style={bookieOdds.home_odds === bestHome.value ? { borderColor: config.color } : {}}
                                >
                                  {bookieOdds.home_odds.toFixed(2)}
                                </a>
                              ) : (
                                <span className="odds-empty">-</span>
                              )}
                              {bookieOdds?.draw_odds ? (
                                <a
                                  href={config.affiliateUrl}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className={`odds-btn ${bookieOdds.draw_odds === bestDraw.value ? 'best' : ''}`}
                                  style={bookieOdds.draw_odds === bestDraw.value ? { borderColor: config.color } : {}}
                                >
                                  {bookieOdds.draw_odds.toFixed(2)}
                                </a>
                              ) : (
                                <span className="odds-empty">-</span>
                              )}
                              {bookieOdds?.away_odds ? (
                                <a
                                  href={config.affiliateUrl}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className={`odds-btn ${bookieOdds.away_odds === bestAway.value ? 'best' : ''}`}
                                  style={bookieOdds.away_odds === bestAway.value ? { borderColor: config.color } : {}}
                                >
                                  {bookieOdds.away_odds.toFixed(2)}
                                </a>
                              ) : (
                                <span className="odds-empty">-</span>
                              )}
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Mobile scroll hint */}
        <div className="scroll-hint">
          <span>Swipe to see more bookmakers</span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="20" height="20">
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </div>
      </div>
    </div>
  );
}

export default OddsPage;
