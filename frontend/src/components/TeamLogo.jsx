import { useState, useEffect, useRef } from 'react';
import { getTeamLogo, getCachedLogo } from '../services/teamLogos';

/**
 * Team Logo Component
 * Displays team badge/logo with automatic fetching and fallback
 */
export function TeamLogo({ teamName, size = 24, className = '' }) {
  const [logoUrl, setLogoUrl] = useState(getCachedLogo(teamName));
  const [loading, setLoading] = useState(!logoUrl);
  const [error, setError] = useState(false);
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
    setError(false);

    const loadLogo = async () => {
      // Check cache first
      const cached = getCachedLogo(teamName);
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
        const url = await getTeamLogo(teamName);
        if (mounted) {
          setLogoUrl(url);
          setLoading(false);
        }
      } catch (e) {
        if (mounted) {
          setLoading(false);
          setError(true);
        }
      }
    };

    loadLogo();

    return () => {
      mounted = false;
    };
  }, [teamName, isVisible]);

  // Generate initials for fallback
  const getInitials = (name) => {
    if (!name) return '?';
    const words = name.split(/\s+/).filter(w => w.length > 0);
    if (words.length >= 2) {
      return (words[0][0] + words[1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  };

  // Generate consistent color from team name
  const getColor = (name) => {
    const colors = [
      '#1a73e8', '#e63946', '#2e7d32', '#f57c00',
      '#7b1fa2', '#00838f', '#c62828', '#283593',
      '#00695c', '#4527a0', '#bf360c', '#1565c0'
    ];
    let hash = 0;
    for (let i = 0; i < (name || '').length; i++) {
      hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
  };

  const initials = getInitials(teamName);
  const color = getColor(teamName);

  // Loading placeholder
  if (loading) {
    return (
      <div
        ref={logoRef}
        className={`team-logo team-logo-loading ${className}`}
        style={{
          width: size,
          height: size,
          borderRadius: '50%',
          background: '#e0e0e0',
          animation: 'pulse 1.5s ease-in-out infinite',
        }}
      />
    );
  }

  // Show logo if available
  if (logoUrl && !error) {
    return (
      <img
        ref={logoRef}
        src={logoUrl}
        alt={`${teamName} logo`}
        className={`team-logo ${className}`}
        style={{
          width: size,
          height: size,
          objectFit: 'contain',
          borderRadius: '4px',
        }}
        onError={() => setError(true)}
        loading="lazy"
      />
    );
  }

  // Fallback to initials
  return (
    <div
      ref={logoRef}
      className={`team-logo team-logo-fallback ${className}`}
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        background: `linear-gradient(135deg, ${color}, ${color}dd)`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'white',
        fontSize: size * 0.4,
        fontWeight: 600,
        flexShrink: 0,
      }}
      title={teamName}
    >
      {initials}
    </div>
  );
}

/**
 * Match Teams Display Component
 * Shows both team logos with names
 */
export function MatchTeams({ homeTeam, awayTeam, logoSize = 28, showVs = true }) {
  return (
    <div className="match-teams-display" style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    }}>
      <div className="team home-team" style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
      }}>
        <TeamLogo teamName={homeTeam} size={logoSize} />
        <span className="team-name">{homeTeam}</span>
      </div>

      {showVs && (
        <span className="vs-badge" style={{
          padding: '0.15rem 0.4rem',
          background: '#f0f0f0',
          borderRadius: '4px',
          fontSize: '0.7rem',
          fontWeight: 600,
          color: '#666',
        }}>
          vs
        </span>
      )}

      <div className="team away-team" style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
      }}>
        <TeamLogo teamName={awayTeam} size={logoSize} />
        <span className="team-name">{awayTeam}</span>
      </div>
    </div>
  );
}

export default TeamLogo;
