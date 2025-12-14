import { useParams, Link, Navigate } from 'react-router-dom';
import { ARTICLES } from './NewsPage';

function ArticlePage() {
  const { slug } = useParams();
  const article = ARTICLES.find((a) => a.slug === slug);

  if (!article) {
    return <Navigate to="/news" replace />;
  }

  return (
    <div className="article-page">
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
        <div className={`article-hero-image news-image-${article.image}`}></div>

        <h1>{article.title}</h1>

        <div className="article-meta">
          <span className="article-date">{article.date}</span>
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
          {ARTICLES.filter((a) => a.id !== article.id)
            .slice(0, 3)
            .map((related) => (
              <Link to={`/news/${related.slug}`} key={related.id} className="related-card">
                <div className={`related-image news-image-${related.image}`}></div>
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
