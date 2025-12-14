import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { TeamLogo } from '../components/TeamLogo';
import { BookmakerLogo } from '../components/BookmakerLogo';
import { LeagueLogo } from '../components/LeagueLogo';
import { BOOKMAKER_AFFILIATES, BOOKMAKER_ORDER } from '../config/affiliates';

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
    icon: '📈',
    title: 'Track Line Movements',
    description: 'Watch for "steam" moves (shortening odds) which often indicate smart money. Our sparklines show you the trends.',
  },
  {
    icon: '🎯',
    title: 'Bankroll Management',
    description: 'Never bet more than 2-5% of your bankroll on a single bet. Consistent staking leads to long-term success.',
  },
];

// Popular leagues for navigation
const POPULAR_LEAGUES = [
  { id: 'premier', name: 'Premier League', matches: 10, slug: 'premier' },
  { id: 'laliga', name: 'La Liga', matches: 10, slug: 'laliga' },
  { id: 'ghana', name: 'Ghana Premier', matches: 9, slug: 'ghana' },
  { id: 'ucl', name: 'Champions League', matches: 8, slug: 'champions' },
  { id: 'seriea', name: 'Serie A', matches: 10, slug: 'seriea' },
  { id: 'bundesliga', name: 'Bundesliga', matches: 9, slug: 'bundesliga' },
];

function HomePage() {
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMatches();
  }, []);

  const loadMatches = async () => {
    try {
      // Try to load from API
      const response = await fetch('/api/odds');
      if (response.ok) {
        const data = await response.json();
        setMatches(data.matches || []);
      }
    } catch (error) {
      console.log('Using demo data');
      // Generate demo data
      setMatches(generateDemoMatches());
    } finally {
      setLoading(false);
    }
  };

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

  // Featured matches (top leagues)
  const featuredMatches = useMemo(() => {
    const topLeagues = ['Premier League', 'England', 'La Liga', 'Spain', 'Champions'];
    return matches
      .filter(m => topLeagues.some(kw => m.league?.toLowerCase().includes(kw.toLowerCase())))
      .slice(0, 6);
  }, [matches]);

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
              <span className="stat-value">5+</span>
              <span className="stat-label">Bookmakers</span>
            </div>
            <div className="stat">
              <span className="stat-value">{matches.length || '100+'}+</span>
              <span className="stat-label">Live Matches</span>
            </div>
            <div className="stat">
              <span className="stat-value">24/7</span>
              <span className="stat-label">Updated</span>
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
            <Link to={`/odds?league=${league.slug}`} key={league.slug} className="league-card">
              <LeagueLogo leagueId={league.id} size={40} />
              <span className="league-name">{league.name}</span>
              <span className="league-count">{league.matches} matches</span>
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
                <span className="bookmaker-bonus">{config.bonus || 'Sign Up Bonus'}</span>
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
              OddsWize compares odds from licensed bookmakers in Ghana including Betway, Sportybet,
              1xBet, Betika, and Supabets. All featured bookmakers are licensed to operate in Ghana
              and offer mobile money deposits.
            </p>
          </details>
          <details className="faq-item">
            <summary>How often are the odds updated?</summary>
            <p>
              Our odds are updated every 5-15 minutes to ensure you see the most current prices.
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

// Generate demo matches for display
function generateDemoMatches() {
  const demoMatches = [
    { home_team: 'Liverpool', away_team: 'Manchester City', league: 'England. Premier League' },
    { home_team: 'Real Madrid', away_team: 'Barcelona', league: 'Spain. La Liga' },
    { home_team: 'Arsenal', away_team: 'Chelsea', league: 'England. Premier League' },
    { home_team: 'Bayern Munich', away_team: 'Dortmund', league: 'Germany. Bundesliga' },
    { home_team: 'PSG', away_team: 'Marseille', league: 'France. Ligue 1' },
    { home_team: 'Inter Milan', away_team: 'AC Milan', league: 'Italy. Serie A' },
  ];

  return demoMatches.map((match, idx) => ({
    ...match,
    start_time: Math.floor(Date.now() / 1000) + (idx + 1) * 3600 * 4,
    odds: [
      { bookmaker: 'betway', home_odds: 1.8 + Math.random() * 0.5, draw_odds: 3.2 + Math.random() * 0.5, away_odds: 2.8 + Math.random() * 0.5 },
      { bookmaker: 'sportybet', home_odds: 1.75 + Math.random() * 0.5, draw_odds: 3.1 + Math.random() * 0.5, away_odds: 2.9 + Math.random() * 0.5 },
    ],
  }));
}

export default HomePage;
