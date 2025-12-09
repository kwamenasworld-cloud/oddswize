import { useState, useEffect, useMemo } from 'react';
import { getMatches, getStatus, triggerScan } from '../services/api';
import { BOOKMAKER_AFFILIATES, BOOKMAKER_ORDER, getAffiliateUrl } from '../config/affiliates';
import { BookmakerLogo } from '../components/BookmakerLogo';
import { TeamLogo } from '../components/TeamLogo';
import { preloadTeamLogos, clearLogoCache } from '../services/teamLogos';

// Helper to create demo match times at realistic kick-off hours
const getDemoTime = (daysFromNow, hour, minute = 0) => {
  const date = new Date();
  date.setDate(date.getDate() + daysFromNow);
  date.setHours(hour, minute, 0, 0);
  return Math.floor(date.getTime() / 1000);
};

// Demo data for when API is not available
const DEMO_MATCHES = [
  {
    home_team: 'Real Madrid',
    away_team: 'Sevilla',
    league: 'Spain. La Liga',
    start_time: getDemoTime(1, 21, 0), // Tomorrow 9:00 PM
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
    start_time: getDemoTime(2, 16, 0), // In 2 days 4:00 PM
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
    start_time: getDemoTime(3, 17, 30), // In 3 days 5:30 PM
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
    start_time: getDemoTime(4, 14, 0), // In 4 days 2:00 PM
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
    start_time: getDemoTime(5, 15, 0), // In 5 days 3:00 PM
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
    start_time: getDemoTime(6, 16, 0), // In 6 days 4:00 PM
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
  { id: 'all', name: 'All', icon: '⚽' },
  { id: 'premier', name: 'Premier League', icon: '🏴󠁧󠁢󠁥󠁮󠁧󠁿', keywords: ['Premier League', 'England'] },
  { id: 'laliga', name: 'La Liga', icon: '🇪🇸', keywords: ['La Liga', 'Spain'] },
  { id: 'ghana', name: 'Ghana', icon: '🇬🇭', keywords: ['Ghana'] },
  { id: 'afcon', name: 'AFCON', icon: '🌍', keywords: ['Africa Cup', 'AFCON'] },
];

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

  return (
    <div className="odds-page">
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
            className="clear-cache-btn"
            onClick={() => {
              clearLogoCache();
              window.location.reload();
            }}
            title="Clear cached logos and reload"
          >
            Reload Logos
          </button>
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

      {/* Main Odds Grid */}
      <div className="odds-container">
        {/* Table Header - Bookmakers */}
        <div className="odds-header">
          <div className="header-match">Match</div>
          <div className="header-time">Kick-off</div>
          {BOOKMAKER_ORDER.map((name) => {
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
          {BOOKMAKER_ORDER.map((name) => (
            <div key={name} className="outcome-labels">
              <span>1</span>
              <span>X</span>
              <span>2</span>
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
              const bestHome = getBestOdds(match, 'home');
              const bestDraw = getBestOdds(match, 'draw');
              const bestAway = getBestOdds(match, 'away');

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
                  </div>

                  {/* Kick-off Time */}
                  <div className="match-time-cell">
                    <span className="kickoff-time">{formatTime(match.start_time)}</span>
                  </div>

                  {/* Odds for each bookmaker */}
                  {BOOKMAKER_ORDER.map((bookmaker) => {
                    const bookieOdds = match.odds?.find((o) => o.bookmaker === bookmaker);
                    const config = BOOKMAKER_AFFILIATES[bookmaker];

                    return (
                      <div key={bookmaker} className="odds-cell">
                        {bookieOdds ? (
                          <>
                            <a
                              href={config.affiliateUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className={`odd ${bookieOdds.home_odds === bestHome.value ? 'best' : ''}`}
                            >
                              {bookieOdds.home_odds.toFixed(2)}
                            </a>
                            <a
                              href={config.affiliateUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className={`odd ${bookieOdds.draw_odds === bestDraw.value ? 'best' : ''}`}
                            >
                              {bookieOdds.draw_odds.toFixed(2)}
                            </a>
                            <a
                              href={config.affiliateUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className={`odd ${bookieOdds.away_odds === bestAway.value ? 'best' : ''}`}
                            >
                              {bookieOdds.away_odds.toFixed(2)}
                            </a>
                          </>
                        ) : (
                          <>
                            <span className="odd empty">-</span>
                            <span className="odd empty">-</span>
                            <span className="odd empty">-</span>
                          </>
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
    </div>
  );
}

export default OddsPage;
