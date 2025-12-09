import { BOOKMAKER_AFFILIATES, BOOKMAKER_ORDER } from '../config/affiliates';

function BookmakersPage() {
  const bookmakers = BOOKMAKER_ORDER.map((name) => ({
    name,
    ...BOOKMAKER_AFFILIATES[name],
  }));

  return (
    <div className="container">
      {/* Hero Banner */}
      <div
        className="promo-banner"
        style={{
          background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
          padding: '2rem',
          marginBottom: '2rem',
        }}
      >
        <div>
          <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>Ghana Betting Sites</h1>
          <p style={{ opacity: 0.8 }}>
            Compare welcome bonuses and sign up with the best bookmakers in Ghana
          </p>
        </div>
      </div>

      {/* Bookmaker Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {bookmakers.map((bookie, idx) => (
          <div key={bookie.id} className="odds-section">
            <div
              className="section-header"
              style={{ background: bookie.color }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <span
                  style={{
                    background: 'rgba(255,255,255,0.2)',
                    padding: '0.25rem 0.75rem',
                    borderRadius: '20px',
                    fontSize: '0.9rem',
                  }}
                >
                  #{idx + 1}
                </span>
                <h2 className="section-title">{bookie.name}</h2>
              </div>
              <a
                href={bookie.affiliateUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="promo-btn"
              >
                Visit Site
              </a>
            </div>

            <div style={{ padding: '1.5rem' }}>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: '1.5rem',
                }}
              >
                {/* Welcome Bonus */}
                <div>
                  <h4 style={{ color: '#888', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                    WELCOME BONUS
                  </h4>
                  <p style={{ fontSize: '1.2rem', fontWeight: '600', color: '#00c853' }}>
                    {bookie.signupBonus}
                  </p>
                </div>

                {/* Features */}
                <div>
                  <h4 style={{ color: '#888', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                    KEY FEATURES
                  </h4>
                  <ul style={{ fontSize: '0.9rem', paddingLeft: '1.2rem', color: '#555' }}>
                    <li>Mobile App Available</li>
                    <li>Live Betting</li>
                    <li>Cash Out Feature</li>
                  </ul>
                </div>

                {/* Payment Methods */}
                <div>
                  <h4 style={{ color: '#888', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                    PAYMENT METHODS
                  </h4>
                  <p style={{ fontSize: '0.9rem', color: '#555' }}>
                    MTN Mobile Money, Vodafone Cash, AirtelTigo Money, Bank Transfer
                  </p>
                </div>

                {/* Rating */}
                <div>
                  <h4 style={{ color: '#888', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                    OUR RATING
                  </h4>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ color: '#ffc107', fontSize: '1.2rem' }}>★★★★★</span>
                    <span style={{ fontWeight: '600' }}>4.{9 - idx}/5</span>
                  </div>
                </div>
              </div>

              {/* CTA */}
              <div
                style={{
                  marginTop: '1.5rem',
                  padding: '1rem',
                  background: '#f8f9fa',
                  borderRadius: '8px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '1rem',
                }}
              >
                <div>
                  <p style={{ fontWeight: '600', marginBottom: '0.25rem' }}>
                    Sign up now and claim your bonus!
                  </p>
                  <p style={{ fontSize: '0.85rem', color: '#666' }}>
                    New customers only. T&Cs apply. 18+
                  </p>
                </div>
                <a
                  href={bookie.affiliateUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    background: bookie.color,
                    color: 'white',
                    padding: '0.75rem 2rem',
                    borderRadius: '25px',
                    fontWeight: '600',
                    transition: 'transform 0.2s',
                  }}
                  onMouseOver={(e) => (e.target.style.transform = 'scale(1.05)')}
                  onMouseOut={(e) => (e.target.style.transform = 'scale(1)')}
                >
                  Claim {bookie.signupBonus.split(' ').slice(1, 3).join(' ')}
                </a>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Comparison Table */}
      <div className="odds-section" style={{ marginTop: '2rem' }}>
        <div className="section-header">
          <h2 className="section-title">Quick Comparison</h2>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="odds-table">
            <thead>
              <tr>
                <th style={{ textAlign: 'left' }}>Bookmaker</th>
                <th>Welcome Bonus</th>
                <th>Min Deposit</th>
                <th>Mobile App</th>
                <th>Live Betting</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {bookmakers.map((bookie) => (
                <tr key={bookie.id}>
                  <td style={{ textAlign: 'left', fontWeight: '600' }}>{bookie.name}</td>
                  <td style={{ color: '#00c853', fontWeight: '600' }}>{bookie.signupBonus}</td>
                  <td>GHS 1</td>
                  <td>✓</td>
                  <td>✓</td>
                  <td>
                    <a
                      href={bookie.affiliateUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="odds-btn best"
                    >
                      Join
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Disclaimer */}
      <div
        style={{
          marginTop: '2rem',
          padding: '1.5rem',
          background: '#fff3cd',
          borderRadius: '8px',
          fontSize: '0.85rem',
          color: '#856404',
        }}
      >
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
