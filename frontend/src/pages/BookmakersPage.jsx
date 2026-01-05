import { BOOKMAKER_AFFILIATES, BOOKMAKER_ORDER } from '../config/affiliates';
import { BookmakerLogo, StarRating, FeatureBadge } from '../components/BookmakerLogo';
import { trackAffiliateClick } from '../services/analytics';

function BookmakersPage() {
  const bookmakers = BOOKMAKER_ORDER.map((name) => ({
    name,
    ...BOOKMAKER_AFFILIATES[name],
  }));

  return (
    <div className="bookmakers-page">
      {/* Hero Banner */}
      <section className="bookmakers-hero">
        <div className="hero-content">
          <h1>Best Betting Sites in Ghana</h1>
          <p>Compare welcome bonuses and sign up with trusted, licensed bookmakers</p>
          <div className="hero-stats-row">
            <div className="stat-item">
              <span className="stat-number">5</span>
              <span className="stat-text">Bookmakers</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">GHS 2,000+</span>
              <span className="stat-text">Total Bonuses</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">100%</span>
              <span className="stat-text">Licensed</span>
            </div>
          </div>
        </div>
      </section>

      {/* Bookmaker Cards */}
      <section className="bookmakers-list">
        {bookmakers.map((bookie, idx) => (
          <article key={bookie.id} className="bookmaker-card-full">
            {/* Rank Badge */}
            <div className="rank-badge" style={{ background: bookie.color }}>
              #{idx + 1}
            </div>

            {/* Header with Logo */}
            <div className="bookmaker-card-header">
              <div className="bookmaker-identity">
                <BookmakerLogo bookmaker={bookie.name} size={56} />
                <div className="bookmaker-info">
                  <h2>{bookie.name}</h2>
                  <StarRating rating={bookie.rating} size={14} />
                </div>
              </div>
              <div className="bonus-highlight" style={{ borderColor: bookie.color }}>
                <span className="bonus-label">Welcome Bonus</span>
                <span className="bonus-value" style={{ color: bookie.color }}>{bookie.signupBonus}</span>
              </div>
            </div>

            {/* Features */}
            <div className="bookmaker-features">
              {bookie.features?.map((feature, i) => (
                <FeatureBadge key={i} text={feature} color={bookie.color} />
              ))}
            </div>

            {/* Details Grid */}
            <div className="bookmaker-details">
              <div className="detail-item">
                <span className="detail-icon">📱</span>
                <div>
                  <span className="detail-label">Mobile App</span>
                  <span className="detail-value">iOS & Android</span>
                </div>
              </div>
              <div className="detail-item">
                <span className="detail-icon">💳</span>
                <div>
                  <span className="detail-label">Min Deposit</span>
                  <span className="detail-value">GHS 1</span>
                </div>
              </div>
              <div className="detail-item">
                <span className="detail-icon">💰</span>
                <div>
                  <span className="detail-label">Payment</span>
                  <span className="detail-value">MoMo, Vodafone, Bank</span>
                </div>
              </div>
              <div className="detail-item">
                <span className="detail-icon">⚡</span>
                <div>
                  <span className="detail-label">Payout Speed</span>
                  <span className="detail-value">Instant - 24hrs</span>
                </div>
              </div>
            </div>

            {/* CTA */}
            <div className="bookmaker-cta">
              <a
                href={bookie.affiliateUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="cta-button"
                style={{ background: bookie.color }}
                onClick={() => trackAffiliateClick({
                  bookmaker: bookie.name,
                  placement: 'bookmakers_card',
                  url: bookie.affiliateUrl,
                })}
              >
                Claim Bonus
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z"/>
                </svg>
              </a>
              <span className="cta-terms">New customers only. T&Cs apply. 18+</span>
            </div>
          </article>
        ))}
      </section>

      {/* Comparison Table */}
      <section className="comparison-section">
        <h2>Quick Comparison</h2>
        <div className="comparison-table-wrapper">
          <table className="comparison-table">
            <thead>
              <tr>
                <th>Bookmaker</th>
                <th>Welcome Bonus</th>
                <th>Rating</th>
                <th>Min Deposit</th>
                <th>Mobile App</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {bookmakers.map((bookie) => (
                <tr key={bookie.id}>
                  <td className="bookmaker-cell">
                    <BookmakerLogo bookmaker={bookie.name} size={28} />
                    <span>{bookie.name}</span>
                  </td>
                  <td className="bonus-cell">{bookie.signupBonus}</td>
                  <td><StarRating rating={bookie.rating} size={12} /></td>
                  <td>GHS 1</td>
                  <td><span className="check-icon">✓</span></td>
                  <td>
                    <a
                      href={bookie.affiliateUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="join-btn"
                      style={{ background: bookie.color }}
                      onClick={() => trackAffiliateClick({
                        bookmaker: bookie.name,
                        placement: 'bookmakers_table',
                        url: bookie.affiliateUrl,
                      })}
                    >
                      Join
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Info Section */}
      <section className="info-section">
        <h2>How We Rate Bookmakers</h2>
        <div className="info-grid">
          <div className="info-card">
            <span className="info-icon">🔒</span>
            <h3>Licensed & Secure</h3>
            <p>All bookmakers are licensed to operate in Ghana with secure payment processing.</p>
          </div>
          <div className="info-card">
            <span className="info-icon">💰</span>
            <h3>Competitive Odds</h3>
            <p>We compare odds daily to ensure you're getting the best value on your bets.</p>
          </div>
          <div className="info-card">
            <span className="info-icon">📱</span>
            <h3>Mobile Experience</h3>
            <p>All featured sites offer excellent mobile apps for betting on the go.</p>
          </div>
          <div className="info-card">
            <span className="info-icon">🎁</span>
            <h3>Best Bonuses</h3>
            <p>Exclusive welcome bonuses and ongoing promotions for new customers.</p>
          </div>
        </div>
      </section>

      {/* Disclaimer */}
      <div className="disclaimer-box">
        <strong>Disclaimer:</strong> OddsWize may receive commission from bookmakers when you sign
        up through our affiliate links. This does not affect the odds or information displayed on
        our site. Gambling can be addictive - please gamble responsibly. You must be 18+ to
        participate. Always check the bookmaker's website for the most up-to-date terms and
        conditions.
      </div>
    </div>
  );
}

export default BookmakersPage;
