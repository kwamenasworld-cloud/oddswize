import { useParams, Link, Navigate } from 'react-router-dom';
import { BookmakerLogo } from '../components/BookmakerLogo';
import { getArticleBySlug, getSortedArticles, formatArticleDate } from '../data/articles';
import { trackAffiliateClick } from '../services/analytics';
import { getRecommendedBookmakers } from '../services/bookmakerRecommendations';
import { usePageMeta } from '../services/seo';

const splitArticleContent = (html) => {
  if (!html) return { introHtml: '', restHtml: '' };
  const marker = '</p>';
  const first = html.indexOf(marker);
  if (first === -1) return { introHtml: html, restHtml: '' };
  const second = html.indexOf(marker, first + marker.length);
  const cutIndex = second !== -1 ? second + marker.length : first + marker.length;
  return {
    introHtml: html.slice(0, cutIndex),
    restHtml: html.slice(cutIndex),
  };
};

function ArticlePage() {
  const { slug } = useParams();
  const article = getArticleBySlug(slug);
  const siteUrl = typeof window !== 'undefined' ? window.location.origin : 'https://oddswize.com';

  if (!article) {
    return <Navigate to="/news" replace />;
  }

  const relatedArticles = getSortedArticles()
    .filter((item) => item.id !== article.id)
    .slice(0, 3);
  const recommendations = getRecommendedBookmakers({
    category: article.category,
    league: article.category,
    count: 2,
  });
  const topRecommendation = recommendations[0] || null;
  const { introHtml, restHtml } = splitArticleContent(article.content);
  const articleUrl = `${siteUrl}/news/${article.slug}`;
  const articleImage = article.image ? new URL(article.image, siteUrl).toString() : `${siteUrl}/og-image.png`;

  usePageMeta({
    title: `${article.title} | OddsWize`,
    description: article.excerpt,
    url: articleUrl,
    image: articleImage,
    type: 'article',
  });

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

        {recommendations.length > 0 && (
          <div className="article-recommended">
            <h3>Recommended Bookmakers</h3>
            <div className="article-recommended-grid">
              {recommendations.map((bookie) => (
                <div key={bookie.id} className="article-recommended-card">
                  <div className="article-recommended-header">
                    <BookmakerLogo bookmaker={bookie.name} size={34} />
                    <div>
                      <span className="article-recommended-name">{bookie.name}</span>
                      <span className="article-recommended-reason">{bookie.reason}</span>
                    </div>
                  </div>
                  <span className="article-recommended-bonus">{bookie.signupBonus}</span>
                  <a
                    href={bookie.affiliateUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="article-recommended-cta"
                    style={{ background: bookie.color }}
                    onClick={() => trackAffiliateClick({
                      bookmaker: bookie.name,
                      placement: 'article_top_recommendation',
                      url: bookie.affiliateUrl,
                    })}
                  >
                    Claim Bonus
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="article-body">
          <div dangerouslySetInnerHTML={{ __html: introHtml }} />
          {topRecommendation && (
            <div className="article-inline-cta">
              <div>
                <h4>Best odds for this story</h4>
                <p>
                  {topRecommendation.name} - {topRecommendation.reason}
                </p>
              </div>
              <a
                href={topRecommendation.affiliateUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="article-inline-cta-btn"
                onClick={() => trackAffiliateClick({
                  bookmaker: topRecommendation.name,
                  placement: 'article_inline_cta',
                  url: topRecommendation.affiliateUrl,
                })}
              >
                Bet Now
              </a>
            </div>
          )}
          {restHtml && <div dangerouslySetInnerHTML={{ __html: restHtml }} />}
        </div>

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
