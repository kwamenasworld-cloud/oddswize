import { useState, useEffect } from 'react';
import { getArbitrage } from '../services/api';
import { BOOKMAKER_AFFILIATES, getAffiliateUrl } from '../config/affiliates';

// Demo arbitrage opportunities
const DEMO_ARBITRAGE = [
  {
    home_team: 'DR Congo',
    away_team: 'Benin',
    profit_pct: 6.26,
    home_odds: 1.90,
    home_bookmaker: 'SoccaBet Ghana',
    draw_odds: 3.87,
    draw_bookmaker: '1xBet Ghana',
    away_odds: 6.55,
    away_bookmaker: '1xBet Ghana',
    stakes: {
      bankroll: 100,
      stake_home: 56.15,
      stake_draw: 27.57,
      stake_away: 16.29,
      guaranteed_return: 106.68,
      profit: 6.68,
    },
  },
  {
    home_team: 'Tunisia',
    away_team: 'Uganda',
    profit_pct: 3.84,
    home_odds: 1.77,
    home_bookmaker: '1xBet Ghana',
    draw_odds: 3.69,
    draw_bookmaker: '1xBet Ghana',
    away_odds: 8.00,
    away_bookmaker: 'SoccaBet Ghana',
    stakes: {
      bankroll: 100,
      stake_home: 58.82,
      stake_draw: 28.18,
      stake_away: 13.00,
      guaranteed_return: 103.99,
      profit: 3.99,
    },
  },
  {
    home_team: 'Burkina Faso',
    away_team: 'Equatorial Guinea',
    profit_pct: 3.42,
    home_odds: 2.25,
    home_bookmaker: 'SoccaBet Ghana',
    draw_odds: 3.42,
    draw_bookmaker: '1xBet Ghana',
    away_odds: 4.36,
    away_bookmaker: '1xBet Ghana',
    stakes: {
      bankroll: 100,
      stake_home: 46.02,
      stake_draw: 30.23,
      stake_away: 23.75,
      guaranteed_return: 103.54,
      profit: 3.54,
    },
  },
];

function ArbitragePage() {
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [bankroll, setBankroll] = useState(100);
  const [useDemo, setUseDemo] = useState(false);

  useEffect(() => {
    loadArbitrage();
  }, [bankroll]);

  const loadArbitrage = async () => {
    try {
      const data = await getArbitrage(bankroll);
      setOpportunities(data);
      setUseDemo(false);
    } catch (error) {
      console.log('API unavailable, using demo data');
      // Scale demo stakes by bankroll
      const scaledDemo = DEMO_ARBITRAGE.map((arb) => ({
        ...arb,
        stakes: {
          ...arb.stakes,
          bankroll,
          stake_home: (arb.stakes.stake_home / 100) * bankroll,
          stake_draw: (arb.stakes.stake_draw / 100) * bankroll,
          stake_away: (arb.stakes.stake_away / 100) * bankroll,
          guaranteed_return: (arb.stakes.guaranteed_return / 100) * bankroll,
          profit: (arb.stakes.profit / 100) * bankroll,
        },
      }));
      setOpportunities(scaledDemo);
      setUseDemo(true);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container">
        <div className="loading">
          <div className="spinner"></div>
          <span>Scanning for arbitrage...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      {/* Promo Banner */}
      <div className="promo-banner" style={{ background: 'linear-gradient(90deg, #00c853 0%, #00a152 100%)' }}>
        <div className="promo-text">
          <strong>Guaranteed Profit!</strong> These arbitrage opportunities give you risk-free returns.
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <label style={{ fontSize: '0.9rem' }}>Bankroll: GHS</label>
          <input
            type="number"
            value={bankroll}
            onChange={(e) => setBankroll(Number(e.target.value) || 100)}
            style={{
              padding: '0.5rem',
              borderRadius: '6px',
              border: 'none',
              width: '100px',
              fontWeight: 'bold',
            }}
          />
        </div>
      </div>

      {/* Stats Banner */}
      <div className="stats-banner">
        <div className="stat-item">
          <div className="stat-value">{opportunities.length}</div>
          <div className="stat-label">Opportunities Found</div>
        </div>
        <div className="stat-item">
          <div className="stat-value">
            {opportunities.length > 0
              ? `${opportunities[0].profit_pct.toFixed(2)}%`
              : '0%'}
          </div>
          <div className="stat-label">Best Profit</div>
        </div>
        <div className="stat-item">
          <div className="stat-value">
            GHS {opportunities.reduce((sum, o) => sum + (o.stakes?.profit || 0), 0).toFixed(2)}
          </div>
          <div className="stat-label">Total Potential Profit</div>
        </div>
      </div>

      {/* Arbitrage Cards */}
      <div className="odds-section">
        <div className="section-header">
          <h2 className="section-title">
            Arbitrage Opportunities {useDemo && '(Demo Data)'}
          </h2>
        </div>

        {opportunities.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: '#666' }}>
            <p style={{ fontSize: '1.2rem', marginBottom: '1rem' }}>No arbitrage opportunities found right now.</p>
            <p>Arbitrage is rare (~0.5-2% of matches). Check back later for new opportunities!</p>
          </div>
        ) : (
          <div className="arb-grid">
            {opportunities.map((arb, idx) => (
              <div key={idx} className="arb-card">
                <div className="arb-header">
                  <div className="arb-profit">+{arb.profit_pct.toFixed(2)}%</div>
                  <div className="arb-type">1X2</div>
                </div>
                <div className="arb-body">
                  <div className="arb-match">
                    {arb.home_team} vs {arb.away_team}
                  </div>

                  <div className="arb-selections">
                    <a
                      href={getAffiliateUrl(arb.home_bookmaker)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="arb-selection"
                    >
                      <span className="arb-outcome">Home Win</span>
                      <div className="arb-odds-info">
                        <div className="arb-odds">{arb.home_odds.toFixed(2)}</div>
                        <div className="arb-bookmaker">{arb.home_bookmaker}</div>
                      </div>
                    </a>

                    {arb.draw_odds > 0 && (
                      <a
                        href={getAffiliateUrl(arb.draw_bookmaker)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="arb-selection"
                      >
                        <span className="arb-outcome">Draw</span>
                        <div className="arb-odds-info">
                          <div className="arb-odds">{arb.draw_odds.toFixed(2)}</div>
                          <div className="arb-bookmaker">{arb.draw_bookmaker}</div>
                        </div>
                      </a>
                    )}

                    <a
                      href={getAffiliateUrl(arb.away_bookmaker)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="arb-selection"
                    >
                      <span className="arb-outcome">Away Win</span>
                      <div className="arb-odds-info">
                        <div className="arb-odds">{arb.away_odds.toFixed(2)}</div>
                        <div className="arb-bookmaker">{arb.away_bookmaker}</div>
                      </div>
                    </a>
                  </div>

                  <div className="arb-stakes">
                    <div className="arb-stakes-title">Stake Calculator (GHS {bankroll})</div>
                    <div className="arb-stake-row">
                      <span>Home ({arb.home_bookmaker.split(' ')[0]})</span>
                      <span>GHS {arb.stakes?.stake_home?.toFixed(2)}</span>
                    </div>
                    {arb.draw_odds > 0 && (
                      <div className="arb-stake-row">
                        <span>Draw ({arb.draw_bookmaker.split(' ')[0]})</span>
                        <span>GHS {arb.stakes?.stake_draw?.toFixed(2)}</span>
                      </div>
                    )}
                    <div className="arb-stake-row">
                      <span>Away ({arb.away_bookmaker.split(' ')[0]})</span>
                      <span>GHS {arb.stakes?.stake_away?.toFixed(2)}</span>
                    </div>
                    <div className="arb-stake-row total">
                      <span>Guaranteed Profit</span>
                      <span style={{ color: '#00c853' }}>
                        +GHS {arb.stakes?.profit?.toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* How it Works */}
      <div className="odds-section">
        <div className="section-header">
          <h2 className="section-title">How Arbitrage Works</h2>
        </div>
        <div style={{ padding: '1.5rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem' }}>
            <div>
              <h3 style={{ color: '#00c853', marginBottom: '0.5rem' }}>1. We Find the Gaps</h3>
              <p style={{ fontSize: '0.9rem', color: '#666' }}>
                We compare odds from 5 Ghana bookmakers in real-time to find pricing inefficiencies.
              </p>
            </div>
            <div>
              <h3 style={{ color: '#00c853', marginBottom: '0.5rem' }}>2. Calculate Stakes</h3>
              <p style={{ fontSize: '0.9rem', color: '#666' }}>
                We calculate exactly how much to bet on each outcome to guarantee a profit regardless of the result.
              </p>
            </div>
            <div>
              <h3 style={{ color: '#00c853', marginBottom: '0.5rem' }}>3. Place Your Bets</h3>
              <p style={{ fontSize: '0.9rem', color: '#666' }}>
                Click through to each bookmaker using our links and place the calculated stakes. Profit is guaranteed!
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ArbitragePage;
