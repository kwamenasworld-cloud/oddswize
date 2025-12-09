import { useState, useEffect } from 'react';
import { getMatches, getStatus, triggerScan } from '../services/api';
import { BOOKMAKER_AFFILIATES, BOOKMAKER_ORDER, getAffiliateUrl } from '../config/affiliates';

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
];

function OddsPage() {
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [status, setStatus] = useState(null);
  const [useDemo, setUseDemo] = useState(false);

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

  if (loading) {
    return (
      <div className="container">
        <div className="loading">
          <div className="spinner"></div>
          <span>Loading odds...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      {/* Bookmaker Promo */}
      <div className="promo-banner">
        <div className="promo-text">
          <strong>Betway Ghana</strong> - Get 50% Welcome Bonus up to GHS 200!
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
          <div className="stat-value">{status?.total_matches || matches.length * 5}</div>
          <div className="stat-label">Total Matches</div>
        </div>
        <div className="stat-item">
          <div className="stat-value">{status?.matched_events || matches.length}</div>
          <div className="stat-label">Compared Events</div>
        </div>
        <div className="stat-item">
          <div className="stat-value">{status?.bookmakers?.length || 5}</div>
          <div className="stat-label">Bookmakers</div>
        </div>
        <div className="stat-item">
          <div className="stat-value">{status?.arbitrage_count || 0}</div>
          <div className="stat-label">Arb Opportunities</div>
        </div>
      </div>

      {/* Bookmaker Links */}
      <div className="bookmaker-logos">
        {BOOKMAKER_ORDER.map((name) => {
          const config = BOOKMAKER_AFFILIATES[name];
          return (
            <a
              key={name}
              href={config.affiliateUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="bookmaker-logo-item"
            >
              <div className="bookmaker-badge" style={{ background: config.color }}>
                {config.name}
              </div>
              <div className="bookmaker-bonus">{config.signupBonus}</div>
            </a>
          );
        })}
      </div>

      {/* Odds Table */}
      <div className="odds-section">
        <div className="section-header">
          <h2 className="section-title">
            Football Odds Comparison {useDemo && '(Demo Data)'}
          </h2>
          <button
            className="refresh-btn"
            onClick={handleRefresh}
            disabled={refreshing || useDemo}
          >
            {refreshing ? 'Refreshing...' : 'Refresh Odds'}
          </button>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="odds-table">
            <thead>
              <tr>
                <th className="match-col">Match</th>
                {BOOKMAKER_ORDER.map((name) => (
                  <th key={name} colSpan="3">
                    <a
                      href={getAffiliateUrl(name)}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: BOOKMAKER_AFFILIATES[name]?.color }}
                    >
                      {BOOKMAKER_AFFILIATES[name]?.name || name}
                    </a>
                  </th>
                ))}
              </tr>
              <tr>
                <th></th>
                {BOOKMAKER_ORDER.map((name) => (
                  <>
                    <th key={`${name}-1`}>1</th>
                    <th key={`${name}-x`}>X</th>
                    <th key={`${name}-2`}>2</th>
                  </>
                ))}
              </tr>
            </thead>
            <tbody>
              {matches.map((match, idx) => {
                const bestHome = getBestOdds(match, 'home');
                const bestDraw = getBestOdds(match, 'draw');
                const bestAway = getBestOdds(match, 'away');

                return (
                  <tr key={idx}>
                    <td className="match-info">
                      <div className="match-teams">
                        {match.home_team} vs {match.away_team}
                      </div>
                      <div className="match-league">{match.league}</div>
                      <div className="match-time">{formatTime(match.start_time)}</div>
                    </td>
                    {BOOKMAKER_ORDER.map((bookmaker) => {
                      const bookieOdds = match.odds?.find((o) => o.bookmaker === bookmaker);
                      const config = BOOKMAKER_AFFILIATES[bookmaker];

                      return (
                        <>
                          <td key={`${bookmaker}-home`} className="odds-cell">
                            {bookieOdds?.home_odds ? (
                              <a
                                href={config.affiliateUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className={`odds-btn ${
                                  bookieOdds.home_odds === bestHome.value ? 'best' : ''
                                }`}
                              >
                                {bookieOdds.home_odds.toFixed(2)}
                              </a>
                            ) : (
                              <span className="odds-empty">-</span>
                            )}
                          </td>
                          <td key={`${bookmaker}-draw`} className="odds-cell">
                            {bookieOdds?.draw_odds ? (
                              <a
                                href={config.affiliateUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className={`odds-btn ${
                                  bookieOdds.draw_odds === bestDraw.value ? 'best' : ''
                                }`}
                              >
                                {bookieOdds.draw_odds.toFixed(2)}
                              </a>
                            ) : (
                              <span className="odds-empty">-</span>
                            )}
                          </td>
                          <td key={`${bookmaker}-away`} className="odds-cell">
                            {bookieOdds?.away_odds ? (
                              <a
                                href={config.affiliateUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className={`odds-btn ${
                                  bookieOdds.away_odds === bestAway.value ? 'best' : ''
                                }`}
                              >
                                {bookieOdds.away_odds.toFixed(2)}
                              </a>
                            ) : (
                              <span className="odds-empty">-</span>
                            )}
                          </td>
                        </>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default OddsPage;
