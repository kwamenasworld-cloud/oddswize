// Affiliate Configuration - Replace with your actual affiliate tracking URLs
// These URLs should include your affiliate ID/tracking parameters

export const BOOKMAKER_AFFILIATES = {
  'Betway Ghana': {
    id: 'betway',
    name: 'Betway',
    shortName: 'BW',
    color: '#00a826',
    colorLight: '#e6f7ea',
    colorDark: '#008a1f',
    logo: '/logos/betway.png',
    // Replace YOUR_AFFILIATE_ID with your actual Betway affiliate tracking ID
    affiliateUrl: 'https://www.betway.com.gh/?btag=YOUR_AFFILIATE_ID',
    signupBonus: 'Get 50% up to GHS 200',
    rating: 4.8,
    features: ['Fast Payouts', 'Live Streaming', 'Cash Out'],
  },
  'SportyBet Ghana': {
    id: 'sportybet',
    name: 'SportyBet',
    shortName: 'SB',
    color: '#e63946',
    colorLight: '#fce8ea',
    colorDark: '#c62e3b',
    logo: '/logos/sportybet.png',
    affiliateUrl: 'https://www.sportybet.com/gh/?affiliate=YOUR_AFFILIATE_ID',
    signupBonus: 'Get 300% Welcome Bonus',
    rating: 4.7,
    features: ['300% Bonus', 'Mobile App', 'Fast Odds'],
  },
  '1xBet Ghana': {
    id: '1xbet',
    name: '1xBet',
    shortName: '1X',
    color: '#1a5fb4',
    colorLight: '#e8f0fa',
    colorDark: '#154a8f',
    logo: '/logos/1xbet.png',
    affiliateUrl: 'https://reffpa.com/L?tag=d_5045676m_97c_',
    signupBonus: 'Get 200% up to GHS 750',
    rating: 4.6,
    features: ['High Odds', 'Many Markets', 'Live Betting'],
  },
  '22Bet Ghana': {
    id: '22bet',
    name: '22Bet',
    shortName: '22',
    color: '#f5a623',
    colorLight: '#fef6e6',
    colorDark: '#d4901e',
    logo: '/logos/22bet.png',
    affiliateUrl: 'https://moy.auraodin.com/redirect.aspx?pid=157982&bid=1494&lpid=544',
    signupBonus: 'Get 100% up to GHS 750',
    rating: 4.5,
    features: ['100% Bonus', 'Virtual Sports', 'E-Sports'],
  },
  'SoccaBet Ghana': {
    id: 'soccabet',
    name: 'SoccaBet',
    shortName: 'SC',
    color: '#e31837',
    colorLight: '#fce6ea',
    colorDark: '#c2142e',
    logo: '/logos/soccabet.png',
    affiliateUrl: 'https://www.soccabet.com/?ref=YOUR_AFFILIATE_ID',
    signupBonus: 'Get 100% First Deposit Bonus',
    rating: 4.4,
    features: ['Local Focus', 'Easy Deposit', 'SMS Betting'],
  },
};

// Get affiliate URL for a bookmaker
export const getAffiliateUrl = (bookmakerName) => {
  const config = BOOKMAKER_AFFILIATES[bookmakerName];
  return config?.affiliateUrl || '#';
};

// Get bookmaker config
export const getBookmakerConfig = (bookmakerName) => {
  return BOOKMAKER_AFFILIATES[bookmakerName] || {
    id: 'unknown',
    name: bookmakerName,
    shortName: '??',
    color: '#666',
    colorLight: '#f0f0f0',
    affiliateUrl: '#',
  };
};

// All bookmakers in display order
export const BOOKMAKER_ORDER = [
  'Betway Ghana',
  'SportyBet Ghana',
  '1xBet Ghana',
  '22Bet Ghana',
  'SoccaBet Ghana',
];

// Bookmaker Logo Component
export const BookmakerLogo = ({ bookmaker, size = 40 }) => {
  const config = BOOKMAKER_AFFILIATES[bookmaker] || getBookmakerConfig(bookmaker);

  return `
    <div style="
      width: ${size}px;
      height: ${size}px;
      background: linear-gradient(135deg, ${config.color} 0%, ${config.colorDark || config.color} 100%);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: 700;
      font-size: ${size * 0.35}px;
      box-shadow: 0 2px 8px ${config.color}40;
    ">
      ${config.shortName}
    </div>
  `;
};
