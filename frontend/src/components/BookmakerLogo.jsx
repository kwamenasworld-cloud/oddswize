import { useState, useEffect, useRef } from 'react';
import { BOOKMAKER_AFFILIATES, getBookmakerConfig } from '../config/affiliates';
import { getBookmakerLogo, getCachedBookmakerLogo } from '../services/bookmakerLogos';

// Bookmaker Logo Component with automatic logo fetching
export function BookmakerLogo({ bookmaker, size = 40, showName = false }) {
  const config = BOOKMAKER_AFFILIATES[bookmaker] || getBookmakerConfig(bookmaker);
  const [logoUrl, setLogoUrl] = useState(getCachedBookmakerLogo(bookmaker));
  const [imgError, setImgError] = useState(false);
  const [loading, setLoading] = useState(!logoUrl);
  const [isVisible, setIsVisible] = useState(() => typeof window === 'undefined');
  const logoRef = useRef(null);

  useEffect(() => {
    if (isVisible) return;
    const element = logoRef.current;
    if (!element || typeof window === 'undefined' || !('IntersectionObserver' in window)) {
      setIsVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: '160px' }
    );

    observer.observe(element);

    return () => observer.disconnect();
  }, [isVisible]);

  useEffect(() => {
    let mounted = true;
    setImgError(false);

    const loadLogo = async () => {
      // Check cache first
      const cached = getCachedBookmakerLogo(bookmaker);
      if (cached) {
        setLogoUrl(cached);
        setLoading(false);
        return;
      }

      if (!isVisible) {
        setLogoUrl(null);
        setLoading(true);
        return;
      }

      // Fetch from API
      try {
        const url = await getBookmakerLogo(bookmaker);
        if (mounted && url) {
          setLogoUrl(url);
          setLoading(false);
        }
      } catch (e) {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    loadLogo();

    return () => {
      mounted = false;
    };
  }, [bookmaker, isVisible]);

  // Fallback gradient badge when image fails or not available
  const FallbackBadge = () => (
    <div
      className="bookmaker-logo-icon"
      style={{
        width: `${size}px`,
        height: `${size}px`,
        background: `linear-gradient(135deg, ${config.color} 0%, ${config.colorDark || config.color} 100%)`,
        borderRadius: '10px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'white',
        fontWeight: '700',
        fontSize: `${size * 0.4}px`,
        boxShadow: `0 4px 12px ${config.color}40`,
        letterSpacing: '-0.5px',
      }}
    >
      {config.shortName}
    </div>
  );

  // Loading placeholder
  if (loading) {
    return (
      <div
        ref={logoRef}
        className="bookmaker-logo-wrapper"
        style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}
      >
        <div
          style={{
            width: `${size}px`,
            height: `${size}px`,
            borderRadius: '10px',
            background: '#e0e0e0',
            animation: 'pulse 1.5s ease-in-out infinite',
          }}
        />
        {showName && (
          <span style={{ fontSize: '0.7rem', fontWeight: '600', color: config.color }}>
            {config.name}
          </span>
        )}
      </div>
    );
  }

  return (
    <div
      ref={logoRef}
      className="bookmaker-logo-wrapper"
      style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}
    >
      {logoUrl && !imgError ? (
        <img
          src={logoUrl}
          alt={`${config.name} logo`}
          style={{
            width: `${size}px`,
            height: `${size}px`,
            objectFit: 'contain',
            borderRadius: '8px',
            background: 'white',
          }}
          onError={() => setImgError(true)}
          loading="lazy"
        />
      ) : (
        <FallbackBadge />
      )}
      {showName && (
        <span style={{ fontSize: '0.7rem', fontWeight: '600', color: config.color }}>
          {config.name}
        </span>
      )}
    </div>
  );
}

// Star Rating Component
export function StarRating({ rating, size = 14 }) {
  const fullStars = Math.floor(rating);
  const hasHalfStar = rating % 1 >= 0.5;
  const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
      {[...Array(fullStars)].map((_, i) => (
        <svg key={`full-${i}`} width={size} height={size} viewBox="0 0 24 24" fill="#ffc107">
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
        </svg>
      ))}
      {hasHalfStar && (
        <svg width={size} height={size} viewBox="0 0 24 24">
          <defs>
            <linearGradient id="halfGrad">
              <stop offset="50%" stopColor="#ffc107" />
              <stop offset="50%" stopColor="#e0e0e0" />
            </linearGradient>
          </defs>
          <path fill="url(#halfGrad)" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
        </svg>
      )}
      {[...Array(emptyStars)].map((_, i) => (
        <svg key={`empty-${i}`} width={size} height={size} viewBox="0 0 24 24" fill="#e0e0e0">
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
        </svg>
      ))}
      <span style={{ marginLeft: '4px', fontSize: '0.8rem', fontWeight: '600', color: '#666' }}>
        {rating.toFixed(1)}
      </span>
    </div>
  );
}

// Feature Badge Component
export function FeatureBadge({ text, color = '#1a73e8' }) {
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        background: `${color}15`,
        color: color,
        borderRadius: '12px',
        fontSize: '0.7rem',
        fontWeight: '600',
        whiteSpace: 'nowrap',
      }}
    >
      {text}
    </span>
  );
}

// Live Indicator
export function LiveIndicator() {
  return (
    <span className="live-indicator">
      <span className="live-dot"></span>
      LIVE
    </span>
  );
}

// Odds Movement Arrow
export function OddsMovement({ direction }) {
  if (direction === 'up') {
    return (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="#00c853" style={{ marginLeft: '4px' }}>
        <path d="M7 14l5-5 5 5H7z" />
      </svg>
    );
  }
  if (direction === 'down') {
    return (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="#f44336" style={{ marginLeft: '4px' }}>
        <path d="M7 10l5 5 5-5H7z" />
      </svg>
    );
  }
  return null;
}

export default BookmakerLogo;
