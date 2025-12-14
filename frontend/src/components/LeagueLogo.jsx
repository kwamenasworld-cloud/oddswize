import { useState } from 'react';

// League logo URLs from public sources
const LEAGUE_LOGOS = {
  all: null, // No logo for "All"
  premier: 'https://media.api-sports.io/football/leagues/39.png',
  championship: 'https://media.api-sports.io/football/leagues/40.png',
  laliga: 'https://media.api-sports.io/football/leagues/140.png',
  bundesliga: 'https://media.api-sports.io/football/leagues/78.png',
  seriea: 'https://media.api-sports.io/football/leagues/135.png',
  ligue1: 'https://media.api-sports.io/football/leagues/61.png',
  ucl: 'https://media.api-sports.io/football/leagues/2.png',
  uel: 'https://media.api-sports.io/football/leagues/3.png', // Europa League
  ghana: 'https://media.api-sports.io/football/leagues/304.png',
  nigeria: 'https://media.api-sports.io/football/leagues/332.png',
  africa: 'https://media.api-sports.io/football/leagues/6.png', // CAF Champions League
};

// Fallback icons (simple SVG paths)
const FALLBACK_ICONS = {
  all: '⚽',
  premier: 'PL',
  championship: 'CH',
  laliga: 'LL',
  bundesliga: 'BL',
  seriea: 'SA',
  ligue1: 'L1',
  ucl: 'UCL',
  uel: 'UEL',
  ghana: 'GH',
  nigeria: 'NG',
  africa: 'AF',
};

export function LeagueLogo({ leagueId, size = 16, className = '' }) {
  const [error, setError] = useState(false);
  const logoUrl = LEAGUE_LOGOS[leagueId];
  const fallback = FALLBACK_ICONS[leagueId] || '⚽';

  // For "all" league, show soccer ball emoji
  if (leagueId === 'all' || !logoUrl || error) {
    return (
      <span
        className={`league-logo-fallback ${className}`}
        style={{
          fontSize: size * 0.8,
          lineHeight: 1,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: size,
          height: size,
        }}
      >
        {leagueId === 'all' ? '⚽' : fallback}
      </span>
    );
  }

  return (
    <img
      src={logoUrl}
      alt={`${leagueId} logo`}
      className={`league-logo ${className}`}
      style={{
        width: size,
        height: size,
        objectFit: 'contain',
      }}
      onError={() => setError(true)}
      loading="lazy"
    />
  );
}

export default LeagueLogo;
