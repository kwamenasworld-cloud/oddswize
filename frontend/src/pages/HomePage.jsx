import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { TeamLogo } from '../components/TeamLogo';
import { BookmakerLogo } from '../components/BookmakerLogo';
import { LeagueLogo } from '../components/LeagueLogo';
import { BOOKMAKER_AFFILIATES, BOOKMAKER_ORDER, getBookmakerConfig } from '../config/affiliates';
import { LEAGUES, matchLeague, getLeagueTier } from '../config/leagues';
import { getTeamPopularityScore } from '../config/popularity';
import { getLatestArticles, formatArticleDate } from '../data/articles';
import { trackAffiliateClick, trackEvent } from '../services/analytics';
import { getPreferences, getUser, logIn, updateNotificationSetting } from '../services/userPreferences';
import { clearOddsCacheMemory, getCachedOdds, getMatchesByLeague } from '../services/api';
import { usePageMeta } from '../services/seo';

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
  LEAGUES.ghana,
  LEAGUES.nigeria,
];

// Deep links to key pages/leagues for discoverability
const SEO_LINKS = [
  { to: '/odds', label: 'Compare Odds' },
  { to: '/bookmakers', label: 'Bookmakers' },
  { to: '/news', label: 'News & Guides' },
  { to: '/guides/odds-calculator/', label: 'Odds Calculator', external: true },
  { to: '/odds?league=premier', label: 'Premier League Odds' },
  { to: '/odds?league=seriea', label: 'Serie A Odds' },
  { to: '/odds?league=laliga', label: 'La Liga Odds' },
  { to: '/odds?league=bundesliga', label: 'Bundesliga Odds' },
  { to: '/odds?league=ligue1', label: 'Ligue 1 Odds' },
  { to: '/odds?league=ucl', label: 'Champions League Odds' },
  { to: '/ghana-odds', label: 'Ghana Odds' },
  { to: '/nigeria-odds', label: 'Nigeria Odds' },
  { to: '/ghana-premier-league-odds', label: 'Ghana Premier League Odds' },
  { to: '/npfl-odds', label: 'NPFL Odds' },
];
function HomePage() {
  const [featuredMatches, setFeaturedMatches] = useState([]);
  const [leagueMatchCounts, setLeagueMatchCounts] = useState({});
  const [totalMatches, setTotalMatches] = useState(0);
  const [loading, setLoading] = useState(true);
  const [valuePicks, setValuePicks] = useState([]);
  const [shareCopied, setShareCopied] = useState(false);
  const [digestIdentifier, setDigestIdentifier] = useState('');
  const [digestError, setDigestError] = useState('');
  const [digestCopied, setDigestCopied] = useState(false);
  const [digestUser, setDigestUser] = useState(() => getUser());
  const [digestPrefs, setDigestPrefs] = useState(() => getPreferences());
  const [pushStatus, setPushStatus] = useState('');
  const latestArticles = useMemo(() => getLatestArticles(4), []);

  const shareMessage = 'Compare odds across Ghana and Nigeria bookmakers with OddsWize. Find better value before you bet.';
  const shareUrl = `${SITE_URL}/?ref=share`;

  usePageMeta({
    title: 'OddsWize - Compare Betting Odds in Ghana',
    description: 'Compare odds from Betway, SportyBet, 1xBet, 22Bet and more. Find the best prices and value picks before you bet.',
    url: SITE_URL,
    image: `${SITE_URL}/og-image.png`,
  });

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
      clearOddsCacheMemory();
      setLoading(false);
    }
  };

  const validateIdentifier = (value) => {
    const trimmed = value.trim();
    if (!trimmed) return false;
    const isEmail = trimmed.includes('@');
    const isPhone = /^\+?[\d\s-]{10,}$/.test(trimmed.replace(/\s/g, ''));
    return isEmail || isPhone;
  };

  const digestDateLabel = new Date().toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  });
  const digestLink = `${SITE_URL}/odds?ref=digest`;
  const digestWhatsappLink = `${SITE_URL}/odds?ref=whatsapp_digest`;

  const buildDigestText = (picks, link) => {
    const shareLink = link || digestLink;
    if (!picks || picks.length === 0) {
      return `OddsWize Daily Digest (${digestDateLabel})

No top value picks right now. Check back later.

Compare all odds:
${shareLink}`;
    }

    const lines = picks.slice(0, 5).map((pick, index) => {
      const match = pick.match;
      const offer = pick.offer;
      const config = getBookmakerConfig(offer.bookmaker);
      const valuePercent = Math.round(offer.edge);
      return `${index + 1}. ${match.home_team} vs ${match.away_team} (${match.league}) - ${offer.label} @ ${config.name} +${valuePercent}% (${formatTime(match.start_time)})`;
    });

    return `OddsWize Daily Digest (${digestDateLabel})

${lines.join('\n')}

Compare all odds:
${shareLink}`;
  };

  const handleCopyDigest = async () => {
    try {
      const text = buildDigestText(valuePicks, digestLink);
      await navigator.clipboard.writeText(text);
      setDigestCopied(true);
      trackEvent('share', {
        method: 'copy_text',
        placement: 'daily_digest',
        link_url: digestLink,
      });
      setTimeout(() => setDigestCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy digest:', error);
    }
  };

  const handleShareDigest = () => {
    const text = buildDigestText(valuePicks, digestWhatsappLink);
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
    trackEvent('share', {
      method: 'whatsapp',
      placement: 'daily_digest',
      link_url: digestWhatsappLink,
    });
  };

  const handleDigestSignup = (event) => {
    event.preventDefault();
    setDigestError('');
    const identifier = digestIdentifier.trim();
    if (!validateIdentifier(identifier)) {
      setDigestError('Enter a valid email or phone number.');
      return;
    }
    const user = logIn(identifier);
    updateNotificationSetting('dailyDigest', true);
    const prefs = getPreferences();
    setDigestUser(user);
    setDigestPrefs(prefs);
    setDigestIdentifier('');
    trackEvent('digest_signup', {
      method: identifier.includes('@') ? 'email' : 'phone',
      placement: 'home_digest',
    });
  };

  const handleEnablePush = async () => {
    if (typeof window === 'undefined' || !('Notification' in window)) {
      setPushStatus('unsupported');
      return;
    }
    try {
      const permission = await Notification.requestPermission();
      if (permission === 'granted') {
        updateNotificationSetting('push', true);
        setDigestPrefs(getPreferences());
        setPushStatus('enabled');
        try {
          new Notification('OddsWize alerts enabled', {
            body: 'We will show value alerts in this browser while the page is open.',
            icon: '/logo.png',
          });
        } catch (error) {
          // Ignore notification display errors
        }
        trackEvent('push_opt_in', {
          result: 'granted',
          placement: 'home_digest',
        });
      } else {
        setPushStatus(permission === 'denied' ? 'denied' : 'default');
        trackEvent('push_opt_in', {
          result: permission,
          placement: 'home_digest',
        });
      }
    } catch (error) {
      console.error('Failed to enable alerts:', error);
      setPushStatus('error');
    }
  };

  const buildValueShareText = (pick) => {
    const match = pick.match;
    const offer = pick.offer;
    const config = getBookmakerConfig(offer.bookmaker);
    const matchLabel = `${match.home_team} vs ${match.away_team}`;
    const valuePercent = Math.round(offer.edge);
    const shareLink = `${SITE_URL}/odds?match=${encodeURIComponent(matchLabel)}&ref=whatsapp`;

    return {
      shareLink,
      text: `Value pick: ${matchLabel}
League: ${match.league}
Kickoff: ${formatTime(match.start_time)}
Best value: ${offer.label} at ${config.name} (+${valuePercent}% edge)

Compare odds on OddsWize:
${shareLink}`,
    };
  };

  const handleShareValuePick = (pick) => {
    const match = pick.match;
    const { text, shareLink } = buildValueShareText(pick);
    const matchLabel = `${match.home_team} vs ${match.away_team}`;
    const valuePercent = Math.round(pick.offer.edge);
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
    trackEvent('share', {
      method: 'whatsapp',
      placement: 'home_value_pick',
      match: matchLabel,
      league: match.league,
      value_percent: valuePercent,
      link_url: shareLink,
    });
  };

  useEffect(() => {
    const cached = getCachedOdds();
    if (cached?.data?.data?.length) {
      applyHomeData(cached.data.data);
      clearOddsCacheMemory();
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

  const digestEnabled = Boolean(digestPrefs?.notifications?.dailyDigest);
  const pushEnabled = Boolean(digestPrefs?.notifications?.push);

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
              <span className="stat-value">2-3m</span>
              <span className="stat-label">Fast updates</span>
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
          <span className="section-subtitle">Best edges across Ghana and Nigeria bookmakers</span>
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
                  <div className="value-actions">
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
                    <button
                      type="button"
                      className="value-share"
                      onClick={() => handleShareValuePick(pick)}
                      aria-label={`Share ${matchLabel} value pick`}
                    >
                      Share
                    </button>
                  </div>
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

      {/* Daily Digest */}
      <section className="home-section digest-section">
        <div className="section-header">
          <h2>Daily Odds Digest</h2>
          <span className="section-subtitle">Copy or share the daily draft and grow the community</span>
        </div>
        <div className="digest-grid">
          <div className="digest-card">
            <div className="digest-preview">
              <span className="digest-date">Digest for {digestDateLabel}</span>
              {valuePicks.length > 0 ? (
                <ol className="digest-list">
                  {valuePicks.slice(0, 5).map((pick, idx) => {
                    const match = pick.match;
                    const offer = pick.offer;
                    const config = getBookmakerConfig(offer.bookmaker);
                    const valuePercent = Math.round(offer.edge);
                    return (
                      <li key={`${match.home_team}-${match.away_team}-${idx}`}>
                        <strong>{match.home_team} vs {match.away_team}</strong> ({match.league}) - {offer.label} @ {config.name} +{valuePercent}%
                      </li>
                    );
                  })}
                </ol>
              ) : (
                <p className="digest-empty">No value picks right now. Check back later.</p>
              )}
            </div>
            <div className="digest-actions">
              <button type="button" className="digest-action whatsapp" onClick={handleShareDigest}>
                Share to WhatsApp
              </button>
              <button type="button" className="digest-action" onClick={handleCopyDigest}>
                {digestCopied ? 'Copied!' : 'Copy Digest'}
              </button>
              <a className="digest-action link" href="/news/value-picks">
                View value picks
              </a>
            </div>
          </div>
          <div className="digest-card digest-signup">
            <h3>Daily digest reminders</h3>
            <p className="digest-note">Saved on this device only. No emails or SMS are sent.</p>
            {digestEnabled ? (
              <div className="digest-success">
                Digest saved for {digestUser?.email || digestUser?.phone || 'this device'} on this device.
              </div>
            ) : (
              <form className="digest-form" onSubmit={handleDigestSignup}>
                <input
                  type="text"
                  value={digestIdentifier}
                  onChange={(e) => {
                    setDigestIdentifier(e.target.value);
                    if (digestError) setDigestError('');
                  }}
                  placeholder="Email or phone (local only)"
                  aria-label="Email or phone for local digest"
                  className="digest-input"
                />
                <button type="submit" className="digest-submit">
                  Save daily digest
                </button>
              </form>
            )}
            {digestError && <p className="digest-error">{digestError}</p>}
            <div className="digest-alerts">
              <button
                type="button"
                className="digest-action secondary"
                onClick={handleEnablePush}
                disabled={pushEnabled}
              >
                {pushEnabled ? 'Browser alerts enabled' : 'Enable browser alerts'}
              </button>
              {pushStatus === 'unsupported' && (
                <span className="digest-status">Browser alerts not supported here.</span>
              )}
              {pushStatus === 'denied' && (
                <span className="digest-status">Browser alerts blocked in settings.</span>
              )}
            </div>
            <p className="digest-footnote">Alerts only appear while this page is open in this browser.</p>
          </div>
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
            item.external ? (
              <a key={idx} href={item.to} className="seo-link-pill">
                {item.label}
              </a>
            ) : (
              <Link key={idx} to={item.to} className="seo-link-pill">
                {item.label}
              </Link>
            )
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
              Fast updates run every few minutes, with a full refresh about every 15 minutes.
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
