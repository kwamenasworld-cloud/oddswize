import { useState } from 'react';

// League logo URLs from public sources
const LEAGUE_LOGOS = {
  all: null, // No logo for "All"
  premier: 'https://media.api-sports.io/football/leagues/39.png',
  championship: 'https://media.api-sports.io/football/leagues/40.png',
  league1: 'https://media.api-sports.io/football/leagues/41.png',
  league2: 'https://media.api-sports.io/football/leagues/42.png',
  laliga: 'https://media.api-sports.io/football/leagues/140.png',
  laliga2: 'https://media.api-sports.io/football/leagues/141.png',
  bundesliga: 'https://media.api-sports.io/football/leagues/78.png',
  bundesliga2: 'https://media.api-sports.io/football/leagues/79.png',
  seriea: 'https://media.api-sports.io/football/leagues/135.png',
  serieb: 'https://media.api-sports.io/football/leagues/136.png',
  ligue1: 'https://media.api-sports.io/football/leagues/61.png',
  ligue2: 'https://media.api-sports.io/football/leagues/62.png',
  eredivisie: 'https://media.api-sports.io/football/leagues/88.png',
  primeira: 'https://media.api-sports.io/football/leagues/94.png',
  ucl: 'https://media.api-sports.io/football/leagues/2.png',
  uel: 'https://media.api-sports.io/football/leagues/3.png',
  conference: 'https://media.api-sports.io/football/leagues/848.png',
  facup: 'https://media.api-sports.io/football/leagues/45.png',
  eflcup: 'https://media.api-sports.io/football/leagues/48.png',
  ghana: 'https://media.api-sports.io/football/leagues/304.png',
  nigeria: 'https://media.api-sports.io/football/leagues/332.png',
  africa: 'https://media.api-sports.io/football/leagues/6.png',
};

// Fallback icons (simple SVG paths)
const FALLBACK_ICONS = {
  all: '⚽',
  premier: 'PL',
  championship: 'CH',
  league1: 'L1',
  league2: 'L2',
  laliga: 'LL',
  laliga2: 'LL2',
  bundesliga: 'BL',
  bundesliga2: 'BL2',
  seriea: 'SA',
  serieb: 'SB',
  ligue1: 'FL1',
  ligue2: 'FL2',
  eredivisie: 'ED',
  primeira: 'PL',
  ucl: 'UCL',
  uel: 'UEL',
  conference: 'UECL',
  facup: 'FAC',
  eflcup: 'EFL',
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
