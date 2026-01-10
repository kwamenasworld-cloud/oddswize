import { Link } from 'react-router-dom';
import { BookmakerLogo } from '../components/BookmakerLogo';
import { getSortedArticles, formatArticleDate } from '../data/articles';
import { trackAffiliateClick } from '../services/analytics';
import { getRecommendedBookmakers } from '../services/bookmakerRecommendations';

function NewsPage() {
  const articles = getSortedArticles();
  const recommendations = getRecommendedBookmakers({
    category: articles[0]?.category,
    count: 2,
  });
  const topRecommendation = recommendations[0] || null;
  const listJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    itemListElement: articles.map((article, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      url: `https://oddswize.com/news/${article.slug}`,
      name: article.title,
    })),
  };

  return (
    <div className="news-page">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(listJsonLd) }}
      />
      <section className="news-hero">
        <h1>Betting News & Analysis</h1>
        <p>Expert insights, odds analysis, and betting guides for Ghana</p>
        <a className="news-feed-link" href="/rss.xml">Get updates via RSS</a>
      </section>

      <section className="news-auto">
        <div className="news-auto-card">
          <div>
            <h2>Today's Value Picks</h2>
            <p>Auto-generated picks based on the biggest odds edges right now.</p>
          </div>
          <a className="news-auto-link" href="/news/value-picks">View Value Picks</a>
        </div>
      </section>

      {recommendations.length > 0 && (
        <section className="news-recommendations">
          <div className="section-header">
            <h2>Top Bookmakers for This Week</h2>
            <span className="section-subtitle">Trusted options with the best bonuses</span>
          </div>
          <div className="recommended-grid">
            {recommendations.map((bookie) => (
              <div key={bookie.id} className="recommended-card">
                <div className="recommended-card-header">
                  <BookmakerLogo bookmaker={bookie.name} size={36} />
                  <div>
                    <h3>{bookie.name}</h3>
                    <span className="recommended-reason">{bookie.reason}</span>
                  </div>
                </div>
                <div className="recommended-bonus">{bookie.signupBonus}</div>
                <a
                  href={bookie.affiliateUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="recommended-cta"
                  style={{ background: bookie.color }}
                  onClick={() => trackAffiliateClick({
                    bookmaker: bookie.name,
                    placement: 'news_recommendation',
                    url: bookie.affiliateUrl,
                  })}
                >
                  Claim Bonus
                </a>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="news-list">
        {articles.map((article) => (
          <Link to={`/news/${article.slug}`} key={article.id} className="news-list-item">
            <div className="news-list-image">
              <img src={article.image} alt={article.title} loading="lazy" />
              <span className="news-category">{article.category}</span>
            </div>
            <div className="news-list-content">
              <h2>{article.title}</h2>
              <p>{article.excerpt}</p>
              <div className="news-meta">
                <span className="news-date">{formatArticleDate(article.publishedAt)}</span>
                <span className="news-readtime">{article.readTime}</span>
              </div>
            </div>
          </Link>
        ))}
      </section>

      {topRecommendation && (
        <div className="sticky-cta">
          <div className="sticky-cta-text">
            <span className="sticky-cta-title">
              Join {topRecommendation.name} for better odds
            </span>
            <span className="sticky-cta-subtitle">
              {topRecommendation.reason} - {topRecommendation.signupBonus}
            </span>
          </div>
          <a
            href={topRecommendation.affiliateUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="sticky-cta-btn"
            onClick={() => trackAffiliateClick({
              bookmaker: topRecommendation.name,
              placement: 'news_sticky_cta',
              url: topRecommendation.affiliateUrl,
            })}
          >
            Claim Bonus
          </a>
        </div>
      )}
    </div>
  );
}

export default NewsPage;
