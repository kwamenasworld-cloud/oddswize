import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { TeamLogo } from '../components/TeamLogo';
import { BookmakerLogo } from '../components/BookmakerLogo';
import { LeagueLogo } from '../components/LeagueLogo';
import { BOOKMAKER_AFFILIATES, BOOKMAKER_ORDER, getBookmakerConfig } from '../config/affiliates';
import { LEAGUES, matchLeague, getLeagueTier } from '../config/leagues';
import { getTeamPopularityScore } from '../config/popularity';
import { getLatestArticles, formatArticleDate } from '../data/articles';
import { trackAffiliateClick } from '../services/analytics';
import { getCachedOdds, getMatchesByLeague } from '../services/api';

const SITE_URL = 'https://oddswize.com';
const VALUE_MARKET_FIELDS = ['home_odds', 'draw_odds', 'away_odds'];
const MIN_VALUE_EDGE = 5;

// Betting tips for engagement
const BETTING_TIPS = [
  {
    id: 'compare',
    title: 'Compare Before You Bet',
    description: 'Always compare odds across multiple bookmakers. A 0.10 difference can significantly impact your returns.',
  },
  {
    id: 'value',
    title: 'Understand Value Betting',
    description: 'Value betting means finding odds that are higher than the true probability. Our highlights show you where the value is.',
  },
  {
    id: 'knowledge',
    title: 'Bet on What You Know',
    description: 'Focus on leagues and teams you follow closely. Better knowledge leads to better predictions and more informed bets.',
  },
  {
    id: 'bankroll',
    title: 'Bankroll Management',
    description: 'Never bet more than 2-5% of your bankroll on a single bet. Consistent staking leads to long-term success.',
  },
];

const TipIcon = ({ id }) => {
  switch (id) {
    case 'compare':
      return (
        <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M3 3v18h18" />
          <path d="M7 15l3-3 3 3 5-6" />
        </svg>
      );
    case 'value':
      return (
        <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 1v22" />
          <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7H14.5a3.5 3.5 0 0 1 0 7H7" />
        </svg>
      );
    case 'knowledge':
      return (
        <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 20v-6" />
          <path d="M12 4a8 8 0 0 0-4 15" />
          <path d="M12 4a8 8 0 0 1 4 15" />
          <circle cx="12" cy="10" r="2" />
        </svg>
      );
    case 'bankroll':
      return (
        <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="6" width="18" height="12" rx="2" />
          <circle cx="12" cy="12" r="3" />
          <path d="M3 10h3M18 10h3" />
        </svg>
      );
    default:
      return null;
  }
};

// Popular leagues for navigation - using centralized config
const POPULAR_LEAGUES = [
  LEAGUES.premier,
  LEAGUES.laliga,
  LEAGUES.ligue1,
  LEAGUES.ucl,
  LEAGUES.seriea,
  LEAGUES.bundesliga,
];

// Deep links to key pages/leagues for discoverability
const SEO_LINKS = [
  { to: '/odds', label: 'Compare Odds' },
  { to: '/bookmakers', label: 'Bookmakers' },
  { to: '/news', label: 'News & Guides' },
  { to: '/odds?league=premier', label: 'Premier League Odds' },
  { to: '/odds?league=seriea', label: 'Serie A Odds' },
  { to: '/odds?league=laliga', label: 'La Liga Odds' },
  { to: '/odds?league=bundesliga', label: 'Bundesliga Odds' },
  { to: '/odds?league=ligue1', label: 'Ligue 1 Odds' },
  { to: '/odds?league=ucl', label: 'Champions League Odds' },
];
function HomePage() {
  const [featuredMatches, setFeaturedMatches] = useState([]);
  const [leagueMatchCounts, setLeagueMatchCounts] = useState({});
  const [totalMatches, setTotalMatches] = useState(0);
  const [loading, setLoading] = useState(true);
  const [valuePicks, setValuePicks] = useState([]);
  const [shareCopied, setShareCopied] = useState(false);
  const latestArticles = useMemo(() => getLatestArticles(4), []);

  const shareMessage = 'Compare odds across Ghana bookmakers with OddsWize. Find better value before you bet.';
  const shareUrl = SITE_URL;

  const handleShareSite = async () => {
    const payload = {
      title: 'OddsWize',
      text: shareMessage,
      url: shareUrl,
    };
    if (typeof navigator !== 'undefined' && navigator.share) {
      try {
        await navigator.share(payload);
        return;
      } catch (error) {
        // Ignore share cancel and fall back
      }
    }
    handleCopySite();
  };

  const handleShareWhatsApp = () => {
    const text = `${shareMessage}\n\n${shareUrl}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
  };

  const handleCopySite = async () => {
    const text = shareUrl;
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else if (typeof window !== 'undefined') {
        window.prompt('Copy this link:', text);
      }
      setShareCopied(true);
      setTimeout(() => setShareCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy link:', error);
    }
  };

  const formatOddValue = (value) => {
    const numberValue = Number(value);
    return Number.isFinite(numberValue) ? numberValue.toFixed(2) : '-';
  };

  const getMarketAverage = (match, field) => {
    const odds = match.odds || [];
    const values = odds
      .map(o => Number(o[field]))
      .filter(value => Number.isFinite(value) && value > 1);
    if (!values.length) return 0;
    const sum = values.reduce((acc, value) => acc + value, 0);
    return sum / values.length;
  };

  const getBestValueOffer = (match) => {
    const odds = match.odds || [];
    if (!odds.length) return null;
    const averages = VALUE_MARKET_FIELDS.map(field => getMarketAverage(match, field));
    const labels = [
      match.home_team ? `${match.home_team} win` : 'Home win',
      'Draw',
      match.away_team ? `${match.away_team} win` : 'Away win',
    ];
    let best = null;

    odds.forEach((bookie) => {
      VALUE_MARKET_FIELDS.forEach((field, index) => {
        const value = Number(bookie[field]);
        const average = averages[index];
        if (!Number.isFinite(value) || value <= 1 || !average) return;
        const edge = ((value - average) / average) * 100;
        if (edge < MIN_VALUE_EDGE) return;
        if (!best || edge > best.edge) {
          best = {
            bookmaker: bookie.bookmaker,
            odds: value,
            edge,
            label: labels[index],
          };
        }
      });
    });

    return best;
  };

  const buildValuePicks = (leagues, nowSeconds) => {
    const picks = [];
    const windowEnd = nowSeconds + (24 * 60 * 60);

    (leagues || []).forEach((league) => {
      const leagueMatches = league.matches || [];
      leagueMatches.forEach((match) => {
        const matchData = {
          ...match,
          league: league.league || match.league,
        };
        const startTime = Number(matchData.start_time || 0);
        if (!startTime || startTime < nowSeconds || startTime > windowEnd) return;
        if ((matchData.odds?.length || 0) < 2) return;
        const offer = getBestValueOffer(matchData);
        if (!offer) return;
        const popularityScore = getPopularityScore(matchData, nowSeconds);
        picks.push({
          match: matchData,
          offer,
          score: offer.edge + popularityScore * 0.2,
        });
      });
    });

    return picks
      .sort((a, b) => {
        const edgeDiff = b.offer.edge - a.offer.edge;
        if (edgeDiff !== 0) return edgeDiff;
        return b.score - a.score;
      })
      .slice(0, 4);
  };

  const applyHomeData = (leagues) => {
    const now = new Date();
    const nowSeconds = now.getTime() / 1000;
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    const counts = {};
    POPULAR_LEAGUES.forEach((league) => {
      counts[league.id] = 0;
    });

    let total = 0;
    const scored = [];

    (leagues || []).forEach((league) => {
      const leagueMatches = league.matches || [];
      total += leagueMatches.length;
      const matchedLeague = matchLeague(league.league);
      if (matchedLeague && Object.prototype.hasOwnProperty.call(counts, matchedLeague.id)) {
        counts[matchedLeague.id] += leagueMatches.length;
      }

      leagueMatches.forEach((match) => {
        const matchData = {
          ...match,
          league: league.league || match.league,
        };
        const matchDate = new Date((matchData.start_time || 0) * 1000);
        const isToday = matchDate >= today && matchDate < tomorrow;
        if (!isToday) return;
        if ((matchData.odds?.length || 0) < 2) return;
        scored.push({ match: matchData, score: getPopularityScore(matchData, nowSeconds) });
      });
    });

    scored.sort((a, b) => {
      const scoreDiff = b.score - a.score;
      if (scoreDiff !== 0) return scoreDiff;
      return (a.match.start_time || 0) - (b.match.start_time || 0);
    });

    setValuePicks(buildValuePicks(leagues, nowSeconds));
    setFeaturedMatches(scored.slice(0, 6).map(item => item.match));
    setLeagueMatchCounts(counts);
    setTotalMatches(total);
  };

  const loadMatches = async () => {
    try {
      const data = await getMatchesByLeague();
      applyHomeData(data.leagues || []);
    } catch (error) {
      console.error('Failed to load matches:', error);
      setFeaturedMatches([]);
      setLeagueMatchCounts({});
      setTotalMatches(0);
      setValuePicks([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const cached = getCachedOdds();
    if (cached?.data?.data?.length) {
      applyHomeData(cached.data.data);
      setLoading(false);
      const run = () => loadMatches();
      if (typeof window !== 'undefined' && window.requestIdleCallback) {
        window.requestIdleCallback(run, { timeout: 2000 });
      } else {
        setTimeout(run, 800);
      }
      return;
    }
    loadMatches();
  }, []);

  // Get best odds for a match
  const getBestOdds = (match, field) => {
    if (!match.odds || match.odds.length === 0) return { value: null, bookmaker: null };
    let best = { value: 0, bookmaker: null };
    match.odds.forEach((o) => {
      if (o[field] && o[field] > best.value) {
        best = { value: o[field], bookmaker: o.bookmaker };
      }
    });
    return best;
  };

  const getPopularityScore = (match, nowSeconds) => {
    const odds = match.odds || [];
    const bookmakerCount = odds.length;
    if (!bookmakerCount) return 0;

    const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
    const tier = getLeagueTier(match.league);
    const coverage = clamp(bookmakerCount / BOOKMAKER_ORDER.length, 0, 1);
    const coverageScore = Math.pow(coverage, 1.4) * 50;

    const completeCount = odds.filter(o => o.home_odds && o.draw_odds && o.away_odds).length;
    const completenessScore = (completeCount / bookmakerCount) * 10;
    const leagueScore = (5 - tier) * 18;

    const timeDiffHours = ((match.start_time || 0) - nowSeconds) / 3600;
    let timeScore = 0;
    if (timeDiffHours > 0) {
      if (timeDiffHours <= 6) {
        timeScore = 40;
      } else if (timeDiffHours <= 24) {
        timeScore = 40 - ((timeDiffHours - 6) * (20 / 18));
      } else if (timeDiffHours <= 48) {
        timeScore = 20 - ((timeDiffHours - 24) * (20 / 24));
      }
    }

    const marketSpread = (field) => {
      const values = odds
        .map(o => o[field])
        .filter(v => Number.isFinite(v) && v > 1);
      if (values.length < 2) return 0;
      const mean = values.reduce((sum, val) => sum + val, 0) / values.length;
      if (!mean) return 0;
      const variance = values.reduce((sum, val) => sum + (val - mean) ** 2, 0) / values.length;
      const cv = Math.sqrt(variance) / mean;
      return clamp(cv, 0, 0.25);
    };

    const spreadAvg = (
      marketSpread('home_odds') +
      marketSpread('draw_odds') +
      marketSpread('away_odds')
    ) / 3;
    const varianceScore = (spreadAvg / 0.25) * 15;

    const homePopularity = getTeamPopularityScore(match.home_team);
    const awayPopularity = getTeamPopularityScore(match.away_team);
    const teamScore = ((homePopularity + awayPopularity) / 2) * 3;

    return coverageScore + completenessScore + leagueScore + timeScore + varianceScore + teamScore;
  };

  // Format kickoff time
  const formatTime = (timestamp) => {
    if (!timestamp) return 'TBD';
    const date = new Date(timestamp * 1000);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const isTomorrow = date.toDateString() === tomorrow.toDateString();

    const timeStr = date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });

    if (isToday) return `Today ${timeStr}`;
    if (isTomorrow) return `Tomorrow ${timeStr}`;
    return date.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' }) + ` ${timeStr}`;
  };

  return (
    <div className="home-page">
      {/* Hero Section */}
      <section className="home-hero">
        <div className="hero-content">
          <h1>Compare Betting Odds in Ghana</h1>
          <p className="hero-subtitle">
            Find the best odds from Betway, Sportybet, 1xBet and more. Compare prices instantly and maximize your returns.
          </p>
          <div className="hero-stats">
            <div className="stat">
              <span className="stat-value">{BOOKMAKER_ORDER.length}</span>
              <span className="stat-label">Bookmakers</span>
            </div>
            <div className="stat">
              <span className="stat-value">
                {loading ? 'Loading...' : totalMatches > 0 ? `${totalMatches}+` : '0'}
              </span>
              <span className="stat-label">Matches</span>
            </div>
            <div className="stat">
              <span className="stat-value">30m</span>
              <span className="stat-label">Updates</span>
            </div>
          </div>
          <div className="hero-cta">
            <Link to="/odds" className="cta-primary">
              Compare Odds Now
            </Link>
            <Link to="/bookmakers" className="cta-secondary">
              View Bookmakers
            </Link>
          </div>
        </div>
        <div className="hero-visual">
          <div className="floating-odds">
            {BOOKMAKER_ORDER.slice(0, 4).map((bookie, i) => (
              <div key={bookie} className="floating-bookie" style={{ animationDelay: `${i * 0.2}s` }}>
                <BookmakerLogo bookmaker={bookie} size={32} />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Featured Matches */}
      <section className="home-section featured-section">
        <div className="section-header">
          <h2>Today's Top Matches</h2>
          <Link to="/odds" className="see-all">
            View All Matches
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </Link>
        </div>
        <div className="featured-grid">
          {loading ? (
            <div className="loading-state">Loading matches...</div>
          ) : featuredMatches.length > 0 ? (
            featuredMatches.map((match, idx) => {
              const bestHome = getBestOdds(match, 'home_odds');
              const bestDraw = getBestOdds(match, 'draw_odds');
              const bestAway = getBestOdds(match, 'away_odds');

              return (
                <Link to="/odds" key={idx} className="featured-card">
                  <div className="featured-league">{match.league}</div>
                  <div className="featured-teams">
                    <div className="featured-team">
                      <TeamLogo teamName={match.home_team} size={28} />
                      <span>{match.home_team}</span>
                    </div>
                    <span className="featured-vs">vs</span>
                    <div className="featured-team">
                      <TeamLogo teamName={match.away_team} size={28} />
                      <span>{match.away_team}</span>
                    </div>
                  </div>
                  <div className="featured-odds">
                    <div className="featured-odd">
                      <span className="odd-label">1</span>
                      <span className="odd-value">{formatOddValue(bestHome.value)}</span>
                    </div>
                    <div className="featured-odd">
                      <span className="odd-label">X</span>
                      <span className="odd-value">{formatOddValue(bestDraw.value)}</span>
                    </div>
                    <div className="featured-odd">
                      <span className="odd-label">2</span>
                      <span className="odd-value">{formatOddValue(bestAway.value)}</span>
                    </div>
                  </div>
                  <div className="featured-time">{formatTime(match.start_time)}</div>
                </Link>
              );
            })
          ) : (
            <div className="no-matches">
              <p>No featured matches at the moment</p>
              <Link to="/odds" className="view-all-btn">View All Odds</Link>
            </div>
          )}
        </div>
      </section>

      {/* Value Picks */}
      <section className="home-section value-section">
        <div className="section-header">
          <h2>Value Picks Today</h2>
          <span className="section-subtitle">Best edges across Ghana bookmakers</span>
        </div>
        <div className="value-grid">
          {loading ? (
            <div className="loading-state">Loading value picks...</div>
          ) : valuePicks.length > 0 ? (
            valuePicks.map((pick, idx) => {
              const match = pick.match;
              const offer = pick.offer;
              const config = getBookmakerConfig(offer.bookmaker);
              const matchLabel = `${match.home_team} vs ${match.away_team}`;
              const valuePercent = Math.round(offer.edge);

              return (
                <div key={`${matchLabel}-${idx}`} className="value-card">
                  <div className="value-card-header">
                    <span className="value-league">{match.league}</span>
                    <span className="value-time">{formatTime(match.start_time)}</span>
                  </div>
                  <div className="value-teams">
                    <div className="value-team">
                      <TeamLogo teamName={match.home_team} size={24} />
                      <span>{match.home_team}</span>
                    </div>
                    <span className="value-vs">vs</span>
                    <div className="value-team">
                      <TeamLogo teamName={match.away_team} size={24} />
                      <span>{match.away_team}</span>
                    </div>
                  </div>
                  <div className="value-offer">
                    <span className="value-label">Best value</span>
                    <span className="value-outcome">{offer.label}</span>
                    <span className="value-edge">+{valuePercent}%</span>
                  </div>
                  <div className="value-bookie">
                    <BookmakerLogo bookmaker={offer.bookmaker} size={28} />
                    <div className="value-bookie-details">
                      <span className="value-bookie-name">{config.name}</span>
                      <span className="value-odds">{formatOddValue(offer.odds)}</span>
                    </div>
                  </div>
                  <a
                    href={config.affiliateUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="value-cta"
                    onClick={() => trackAffiliateClick({
                      bookmaker: config.name,
                      placement: 'home_value_pick',
                      match: matchLabel,
                      league: match.league,
                      outcome: offer.label,
                      odds: offer.odds,
                      valuePercent,
                      url: config.affiliateUrl,
                    })}
                  >
                    Bet with {config.name}
                  </a>
                </div>
              );
            })
          ) : (
            <div className="value-empty">
              <p>No value picks available right now.</p>
              <Link to="/odds" className="value-empty-link">View all odds</Link>
            </div>
          )}
        </div>
      </section>

      {/* Popular Leagues */}
      <section className="home-section leagues-section">
        <div className="section-header">
          <h2>Popular Leagues</h2>
        </div>
        <div className="leagues-grid">
          {POPULAR_LEAGUES.map((league) => (
            <Link to={`/odds?league=${league.id}`} key={league.id} className="league-card">
              <LeagueLogo leagueId={league.id} size={40} />
              <span className="league-name">{league.name}</span>
              <span className="league-count">{leagueMatchCounts[league.id] || 0} matches</span>
            </Link>
          ))}
        </div>
      </section>

      {/* News Section for SEO */}
      <section className="home-section news-section">
        <div className="section-header">
          <h2>Betting News & Analysis</h2>
          <span className="section-subtitle">Expert insights and odds analysis</span>
        </div>
        <div className="news-grid">
          {latestArticles.map((article) => (
            <Link to={`/news/${article.slug}`} key={article.id} className="news-card">
              <div className="news-image">
                <img src={article.image} alt={article.title} loading="lazy" />
                <span className="news-category">{article.category}</span>
              </div>
              <div className="news-content">
                <h3>{article.title}</h3>
                <p>{article.excerpt}</p>
                <div className="news-meta">
                  <span className="news-date">{formatArticleDate(article.publishedAt)}</span>
                  <span className="news-readtime">{article.readTime}</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Betting Tips */}
      <section className="home-section tips-section">
        <div className="section-header">
          <h2>Betting Tips & Strategies</h2>
          <span className="section-subtitle">Improve your betting game</span>
        </div>
        <div className="tips-grid">
          {BETTING_TIPS.map((tip, idx) => (
            <div key={idx} className="tip-card">
              <span className="tip-icon" aria-hidden="true">
                <TipIcon id={tip.id} />
              </span>
              <h3>{tip.title}</h3>
              <p>{tip.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Share CTA */}
      <section className="home-section share-section">
        <div className="share-card">
          <div className="share-text">
            <h2>Share OddsWize</h2>
            <p>Help friends compare odds and find better value before they bet.</p>
          </div>
          <div className="share-actions">
            <button type="button" className="share-action primary" onClick={handleShareSite}>
              Share OddsWize
            </button>
            <button type="button" className="share-action whatsapp" onClick={handleShareWhatsApp}>
              Share on WhatsApp
            </button>
            <button type="button" className="share-action" onClick={handleCopySite}>
              {shareCopied ? 'Copied!' : 'Copy Link'}
            </button>
          </div>
        </div>
      </section>

      {/* SEO-friendly deep links to key pages/leagues */}
      <section className="home-section seo-links">
        <div className="seo-links-grid">
          {SEO_LINKS.map((item, idx) => (
            <Link key={idx} to={item.to} className="seo-link-pill">
              {item.label}
            </Link>
          ))}
        </div>
      </section>

      {/* Bookmakers Section */}
      <section className="home-section bookmakers-section">
        <div className="section-header">
          <h2>Licensed Bookmakers in Ghana</h2>
          <span className="section-subtitle">Compare odds from trusted sportsbooks</span>
        </div>
        <div className="bookmakers-grid">
          {BOOKMAKER_ORDER.map((bookie) => {
            const config = BOOKMAKER_AFFILIATES[bookie];
            return (
              <a
                key={bookie}
                href={config.affiliateUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="bookmaker-card-home"
                onClick={() => trackAffiliateClick({
                  bookmaker: config.name,
                  placement: 'home_bookmakers',
                  url: config.affiliateUrl,
                })}
              >
                <BookmakerLogo bookmaker={bookie} size={40} />
                <span className="bookmaker-name">{config.name}</span>
                <span className="bookmaker-bonus">{config.signupBonus || 'Sign Up Bonus'}</span>
              </a>
            );
          })}
        </div>
      </section>

      {/* FAQ for SEO */}
      <section className="home-section faq-section">
        <div className="section-header">
          <h2>Frequently Asked Questions</h2>
        </div>
        <div className="faq-list">
          <details className="faq-item">
            <summary>What is odds comparison and why does it matter?</summary>
            <p>
              Odds comparison allows you to see betting prices from multiple bookmakers side by side.
              Different bookmakers offer different odds for the same event, so comparing helps you
              find the best value and maximize potential returns on your bets.
            </p>
          </details>
          <details className="faq-item">
            <summary>Which bookmakers are available in Ghana?</summary>
            <p>
              OddsWize compares odds from {BOOKMAKER_ORDER.length} bookmakers operating in Ghana: Betway, Sportybet,
              1xBet, 22Bet, SoccaBet, and Betfox. All featured bookmakers are licensed to operate in Ghana
              and offer mobile money deposits.
            </p>
          </details>
          <details className="faq-item">
            <summary>How often are the odds updated?</summary>
            <p>
              Our odds are updated every 30 minutes to ensure you see current prices.
              Odds can change quickly, especially close to kick-off, so we recommend checking
              the bookmaker's website before placing your bet.
            </p>
          </details>
          <details className="faq-item">
            <summary>How do I find value bets?</summary>
            <p>
              Value bets occur when the odds offered are higher than the true probability of an outcome.
              By comparing odds across multiple bookmakers, you can spot when one bookmaker is offering
              better value than others and maximize your potential returns.
            </p>
          </details>
          <details className="faq-item">
            <summary>Is OddsWize free to use?</summary>
            <p>
              Yes, OddsWize is completely free to use. We compare odds from multiple bookmakers
              and help you find the best value. We may receive commission from bookmakers when
              you sign up through our links, but this doesn't affect the odds we display.
            </p>
          </details>
        </div>
      </section>

      {/* Final CTA */}
      <section className="home-cta-final">
        <h2>Ready to Find Better Odds?</h2>
        <p>Join thousands of Ghanaian bettors who use OddsWize to compare prices and maximize returns.</p>
        <Link to="/odds" className="cta-primary-large">
          Start Comparing Now
        </Link>
      </section>
    </div>
  );
}

export default HomePage;
