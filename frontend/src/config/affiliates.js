// Affiliate Configuration - Replace with your actual affiliate tracking URLs
// These URLs should include your affiliate ID/tracking parameters

export const BOOKMAKER_AFFILIATES = {
  'Betway Ghana': {
    id: 'betway',
    name: 'Betway',
    logo: '/logos/betway.png',
    color: '#00a826',
    // Replace YOUR_AFFILIATE_ID with your actual Betway affiliate tracking ID
    affiliateUrl: 'https://www.betway.com.gh/?btag=YOUR_AFFILIATE_ID',
    signupBonus: 'Get 50% up to GHS 200',
  },
  'SportyBet Ghana': {
    id: 'sportybet',
    name: 'SportyBet',
    logo: '/logos/sportybet.png',
    color: '#1a1a1a',
    affiliateUrl: 'https://www.sportybet.com/gh/?affiliate=YOUR_AFFILIATE_ID',
    signupBonus: 'Get 300% Welcome Bonus',
  },
  '1xBet Ghana': {
    id: '1xbet',
    name: '1xBet',
    logo: '/logos/1xbet.png',
    color: '#1b5da8',
    affiliateUrl: 'https://1xbet.com/gh/?refId=YOUR_AFFILIATE_ID',
    signupBonus: 'Get 200% up to GHS 750',
  },
  '22Bet Ghana': {
    id: '22bet',
    name: '22Bet',
    logo: '/logos/22bet.png',
    color: '#282828',
    affiliateUrl: 'https://22bet.com.gh/?refCode=YOUR_AFFILIATE_ID',
    signupBonus: 'Get 100% up to GHS 750',
  },
  'SoccaBet Ghana': {
    id: 'soccabet',
    name: 'SoccaBet',
    logo: '/logos/soccabet.png',
    color: '#e31837',
    affiliateUrl: 'https://www.soccabet.com/?ref=YOUR_AFFILIATE_ID',
    signupBonus: 'Get 100% First Deposit Bonus',
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
    color: '#666',
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
