import { useParams, Link, Navigate } from 'react-router-dom';
import { getArticleBySlug, getSortedArticles, formatArticleDate } from '../data/articles';

function ArticlePage() {
  const { slug } = useParams();
  const article = getArticleBySlug(slug);

  if (!article) {
    return <Navigate to="/news" replace />;
  }

  const relatedArticles = getSortedArticles()
    .filter((item) => item.id !== article.id)
    .slice(0, 3);

  const articleJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    headline: article.title,
    description: article.excerpt,
    image: [article.image],
    datePublished: article.publishedAt,
    dateModified: article.publishedAt,
    author: {
      '@type': 'Organization',
      name: 'OddsWize',
    },
    publisher: {
      '@type': 'Organization',
      name: 'OddsWize',
      logo: {
        '@type': 'ImageObject',
        url: 'https://oddswize.com/logo.png',
      },
    },
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': `https://oddswize.com/news/${article.slug}`,
    },
    articleSection: article.category,
  };

  return (
    <div className="article-page">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(articleJsonLd) }}
      />
      <div className="article-header">
        <Link to="/news" className="back-link">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
          Back to News
        </Link>
        <span className="article-category">{article.category}</span>
      </div>

      <article className="article-content">
        <div className="article-hero-image">
          <img src={article.image} alt={article.title} loading="lazy" />
        </div>

        <h1>{article.title}</h1>

        <div className="article-meta">
          <span className="article-date">{formatArticleDate(article.publishedAt)}</span>
          <span className="article-readtime">{article.readTime}</span>
        </div>

        <div
          className="article-body"
          dangerouslySetInnerHTML={{ __html: article.content }}
        />

        <div className="article-cta">
          <h3>Ready to Compare Odds?</h3>
          <p>Find the best betting odds across Ghana's top bookmakers</p>
          <Link to="/odds" className="cta-button">
            Compare Odds Now
          </Link>
        </div>

        <div className="article-share">
          <span>Share this article:</span>
          <div className="share-buttons">
            <a
              href={`https://twitter.com/intent/tweet?text=${encodeURIComponent(article.title)}&url=${encodeURIComponent(`https://oddswize.com/news/${article.slug}`)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="share-btn twitter"
            >
              Twitter
            </a>
            <a
              href={`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(`https://oddswize.com/news/${article.slug}`)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="share-btn facebook"
            >
              Facebook
            </a>
            <a
              href={`https://wa.me/?text=${encodeURIComponent(`${article.title} - https://oddswize.com/news/${article.slug}`)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="share-btn whatsapp"
            >
              WhatsApp
            </a>
          </div>
        </div>
      </article>

      <section className="related-articles">
        <h2>More Articles</h2>
        <div className="related-grid">
          {relatedArticles.map((related) => (
            <Link to={`/news/${related.slug}`} key={related.id} className="related-card">
              <div className="related-image">
                <img src={related.image} alt={related.title} loading="lazy" />
              </div>
              <div className="related-content">
                <span className="related-category">{related.category}</span>
                <h3>{related.title}</h3>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

export default ArticlePage;
