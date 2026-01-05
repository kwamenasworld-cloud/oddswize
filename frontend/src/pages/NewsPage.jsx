import { Link } from 'react-router-dom';
import { getSortedArticles, formatArticleDate } from '../data/articles';

function NewsPage() {
  const articles = getSortedArticles();
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
    </div>
  );
}

export default NewsPage;
