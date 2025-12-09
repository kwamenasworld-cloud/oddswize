import { useState, useEffect } from 'react';

// Demo news data - In production, replace with real API calls
const DEMO_NEWS = [
  {
    id: 1,
    title: "Africa Cup of Nations 2025: Ghana Black Stars Squad Announced",
    summary: "Coach Otto Addo reveals 23-man squad for upcoming AFCON tournament with key players from European leagues included.",
    source: "Ghana Football Association",
    category: "Ghana",
    image: "https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=400&h=250&fit=crop",
    date: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    url: "#",
  },
  {
    id: 2,
    title: "Premier League: Arsenal vs Chelsea Preview and Betting Odds",
    summary: "London derby this weekend promises excitement as both teams fight for top 4 finish. Check our odds comparison for best value.",
    source: "OddsWize",
    category: "Premier League",
    image: "https://images.unsplash.com/photo-1522778119026-d647f0596c20?w=400&h=250&fit=crop",
    date: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    url: "#",
  },
  {
    id: 3,
    title: "SportyBet Ghana Launches 300% Welcome Bonus for New Users",
    summary: "Popular bookmaker increases welcome offer for Ghanaian bettors. Sign up through OddsWize to claim your bonus.",
    source: "OddsWize",
    category: "Promotions",
    image: "https://images.unsplash.com/photo-1518133910546-b6c2fb7d79e3?w=400&h=250&fit=crop",
    date: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
    url: "#",
    isPromo: true,
  },
  {
    id: 4,
    title: "La Liga: Real Madrid Extend Lead at the Top After Barcelona Draw",
    summary: "Los Blancos capitalize on Barcelona's slip-up to extend their advantage in the title race to 5 points.",
    source: "La Liga News",
    category: "La Liga",
    image: "https://images.unsplash.com/photo-1489944440615-453fc2b6a9a9?w=400&h=250&fit=crop",
    date: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(),
    url: "#",
  },
  {
    id: 5,
    title: "Betting Tips: Best Value Bets for This Weekend's Matches",
    summary: "Our experts analyze odds across 5 bookmakers to find the best value bets for Premier League and La Liga fixtures.",
    source: "OddsWize Tips",
    category: "Tips",
    image: "https://images.unsplash.com/photo-1606925797300-0b35e9d1794e?w=400&h=250&fit=crop",
    date: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    url: "#",
  },
  {
    id: 6,
    title: "Accra Hearts vs Asante Kotoko: Ghana Premier League Big Match Preview",
    summary: "The biggest rivalry in Ghanaian football returns this weekend. Full odds comparison and betting preview inside.",
    source: "Ghana Premier League",
    category: "Ghana",
    image: "https://images.unsplash.com/photo-1431324155629-1a6deb1dec8d?w=400&h=250&fit=crop",
    date: new Date(Date.now() - 36 * 60 * 60 * 1000).toISOString(),
    url: "#",
  },
];

const CATEGORIES = [
  { id: 'all', name: 'All News', icon: '📰' },
  { id: 'ghana', name: 'Ghana', icon: '🇬🇭' },
  { id: 'premier', name: 'Premier League', icon: '🏴󠁧󠁢󠁥󠁮󠁧󠁿' },
  { id: 'laliga', name: 'La Liga', icon: '🇪🇸' },
  { id: 'tips', name: 'Tips', icon: '💡' },
  { id: 'promos', name: 'Promotions', icon: '🎁' },
];

function NewsSection() {
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [expandedArticle, setExpandedArticle] = useState(null);

  useEffect(() => {
    // Simulate API fetch
    const fetchNews = async () => {
      setLoading(true);
      try {
        // In production, replace with actual API call:
        // const response = await fetch('https://newsapi.org/v2/everything?q=football+ghana+betting&apiKey=YOUR_KEY');
        // const data = await response.json();

        // Using demo data for now
        await new Promise(resolve => setTimeout(resolve, 500));
        setNews(DEMO_NEWS);
      } catch (error) {
        console.error('Error fetching news:', error);
        setNews(DEMO_NEWS);
      } finally {
        setLoading(false);
      }
    };

    fetchNews();
  }, []);

  const formatTimeAgo = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return 'Yesterday';
    return `${diffDays} days ago`;
  };

  const filteredNews = news.filter((article) => {
    if (selectedCategory === 'all') return true;
    if (selectedCategory === 'promos') return article.isPromo;
    return article.category.toLowerCase().includes(selectedCategory);
  });

  if (loading) {
    return (
      <div className="news-section">
        <div className="news-header">
          <h2 className="news-title">
            <span className="news-icon">📰</span>
            Latest Football News
          </h2>
        </div>
        <div className="news-loading">
          <div className="spinner"></div>
          <span>Loading news...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="news-section">
      <div className="news-header">
        <h2 className="news-title">
          <span className="news-icon">📰</span>
          Latest Football News
        </h2>
        <p className="news-subtitle">Stay updated with the latest football news, betting tips, and promotions</p>
      </div>

      {/* Category Filter */}
      <div className="news-categories">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.id}
            className={`news-category-btn ${selectedCategory === cat.id ? 'active' : ''}`}
            onClick={() => setSelectedCategory(cat.id)}
          >
            <span>{cat.icon}</span>
            {cat.name}
          </button>
        ))}
      </div>

      {/* News Grid */}
      <div className="news-grid">
        {filteredNews.map((article, idx) => (
          <article
            key={article.id}
            className={`news-card ${idx === 0 ? 'featured' : ''} ${article.isPromo ? 'promo' : ''}`}
            onClick={() => setExpandedArticle(expandedArticle === article.id ? null : article.id)}
          >
            <div className="news-image">
              <img src={article.image} alt={article.title} loading="lazy" />
              <span className="news-category-badge">{article.category}</span>
              {article.isPromo && <span className="news-promo-badge">Sponsored</span>}
            </div>
            <div className="news-content">
              <div className="news-meta">
                <span className="news-source">{article.source}</span>
                <span className="news-date">{formatTimeAgo(article.date)}</span>
              </div>
              <h3 className="news-card-title">{article.title}</h3>
              <p className="news-summary">{article.summary}</p>
              {expandedArticle === article.id && (
                <div className="news-expanded">
                  <p>Full article content would appear here. In production, this would link to the full article page for better SEO.</p>
                  <a href={article.url} className="read-more-btn">
                    Read Full Article →
                  </a>
                </div>
              )}
            </div>
          </article>
        ))}
      </div>

      {/* SEO-friendly content */}
      <div className="news-seo-content">
        <h3>Ghana Football Betting News & Updates</h3>
        <p>
          OddsWize brings you the latest football news from Ghana Premier League, English Premier League,
          La Liga, and international competitions. Our coverage includes match previews, betting odds comparisons,
          and expert tips to help you make informed betting decisions. We compare odds from top Ghana bookmakers
          including Betway, SportyBet, 1xBet, 22Bet, and SoccaBet to ensure you always get the best value.
        </p>
      </div>
    </div>
  );
}

export default NewsSection;
