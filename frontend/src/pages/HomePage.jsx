import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { TeamLogo } from '../components/TeamLogo';
import { BookmakerLogo } from '../components/BookmakerLogo';
import { LeagueLogo } from '../components/LeagueLogo';
import { BOOKMAKER_AFFILIATES, BOOKMAKER_ORDER } from '../config/affiliates';
import { LEAGUES, matchLeague } from '../config/leagues';
import { getMatchesByLeague } from '../services/api';

// News articles for homepage (links to full articles)
const NEWS_ARTICLES = [
  {
    id: 1,
    slug: 'premier-league-title-race-best-odds',
    title: 'Premier League Title Race Heats Up: Best Odds for Top 4 Finish',
    excerpt: 'With the season reaching its climax, we analyze the best betting odds for the Premier League top 4 race across Ghana\'s bookmakers.',
    category: 'Premier League',
    date: '2 hours ago',
    image: 'epl',
    readTime: '3 min read',
  },
  {
    id: 2,
    slug: 'afcon-2025-ghana-black-stars-odds',
    title: 'AFCON 2025 Qualifiers: Ghana Black Stars Odds Analysis',
    excerpt: 'The Black Stars face crucial qualifiers. Here\'s where to find the best odds on Ghana\'s matches at Betway, Sportybet and more.',
    category: 'Ghana Football',
    date: '5 hours ago',
    image: 'ghana',
    readTime: '4 min read',
  },
  {
    id: 3,
    slug: 'champions-league-predictions-best-value-bets',
    title: 'Champions League Predictions: Best Value Bets This Week',
    excerpt: 'Our experts break down the Champions League matchday odds and highlight the best value picks from Ghanaian sportsbooks.',
    category: 'Champions League',
    date: '1 day ago',
    image: 'ucl',
    readTime: '5 min read',
  },
  {
    id: 4,
    slug: 'how-to-compare-betting-odds-ghana-guide',
    title: 'How to Compare Betting Odds in Ghana: A Complete Guide',
    excerpt: 'Learn how to find the best betting value by comparing odds across Betway, Sportybet, 1xBet and other licensed bookmakers.',
    category: 'Betting Guide',
    date: '2 days ago',
    image: 'guide',
    readTime: '8 min read',
  },
];

// Betting tips for engagement
const BETTING_TIPS = [
  {
    icon: '📊',
    title: 'Compare Before You Bet',
    description: 'Always compare odds across multiple bookmakers. A 0.10 difference can significantly impact your returns.',
  },
  {
    icon: '💰',
    title: 'Understand Value Betting',
    description: 'Value betting means finding odds that are higher than the true probability. Our highlights show you where the value is.',
  },
  {
    icon: '🏆',
    title: 'Bet on What You Know',
    description: 'Focus on leagues and teams you follow closely. Better knowledge leads to better predictions and more informed bets.',
  },
  {
    icon: '🎯',
    title: 'Bankroll Management',
    description: 'Never bet more than 2-5% of your bankroll on a single bet. Consistent staking leads to long-term success.',
  },
];

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
  const [matches, setMatches] = useState([]);
  const [leagueData, setLeagueData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMatches();
  }, []);

  const loadMatches = async () => {
    try {
      // Load grouped league data for accurate counts
      const data = await getMatchesByLeague();

      // Flatten matches for featured matches section
      const allMatches = data.leagues.flatMap(league =>
        league.matches.map(match => ({
          ...match,
          league: league.league
        }))
      );

      setLeagueData(data.leagues);
      setMatches(allMatches);
    } catch (error) {
      console.error('Failed to load matches:', error);
      setMatches([]);
      setLeagueData([]);
    } finally {
      setLoading(false);
    }
  };

  // Simple deep-links to help discoverability/crawling
  const seoLinks = [
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

  // Featured matches (today's matches from top leagues)
  const featuredMatches = useMemo(() => {
    const topLeagueIds = ['premier', 'laliga', 'ucl', 'seriea', 'bundesliga', 'ligue1'];
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

        // Must be from top leagues (using centralized matching)
        const matchedLeague = matchLeague(m.league);
        return matchedLeague && topLeagueIds.includes(matchedLeague.id);
      })
      .sort((a, b) => (a.start_time || 0) - (b.start_time || 0))
      .slice(0, 6);
  }, [matches]);

  // Count matches per league for display (using API's grouped data directly)
  const leagueMatchCounts = useMemo(() => {
    const counts = {};

    POPULAR_LEAGUES.forEach(popularLeague => {
      // Find all API leagues that match this popular league
      const matchingApiLeagues = leagueData.filter(apiLeague => {
        const matched = matchLeague(apiLeague.league);
        return matched && matched.id === popularLeague.id;
      });

      // Sum up matches from all matching leagues
      counts[popularLeague.id] = matchingApiLeagues.reduce(
        (sum, league) => sum + (league.matches?.length || 0),
        0
      );
    });

    return counts;
  }, [leagueData]);

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
                {loading ? 'Loading...' : matches.length > 0 ? `${matches.length}+` : '0'}
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
          <Link to="/odds" className="see-all">View All Matches →</Link>
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
                      <span className="odd-value">{bestHome.value?.toFixed(2) || '-'}</span>
                    </div>
                    <div className="featured-odd">
                      <span className="odd-label">X</span>
                      <span className="odd-value">{bestDraw.value?.toFixed(2) || '-'}</span>
                    </div>
                    <div className="featured-odd">
                      <span className="odd-label">2</span>
                      <span className="odd-value">{bestAway.value?.toFixed(2) || '-'}</span>
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
          {NEWS_ARTICLES.map((article) => (
            <Link to={`/news/${article.slug}`} key={article.id} className="news-card">
              <div className={`news-image news-image-${article.image}`}>
                <span className="news-category">{article.category}</span>
              </div>
              <div className="news-content">
                <h3>{article.title}</h3>
                <p>{article.excerpt}</p>
                <div className="news-meta">
                  <span className="news-date">{article.date}</span>
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
              <span className="tip-icon">{tip.icon}</span>
              <h3>{tip.title}</h3>
              <p>{tip.description}</p>
            </div>
          ))}
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
