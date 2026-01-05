import { BOOKMAKER_AFFILIATES, BOOKMAKER_ORDER } from '../config/affiliates';

const LOCAL_BOOKMAKERS = ['SoccaBet Ghana', 'Betfox Ghana'];
const PREMIER_BOOKMAKERS = ['Betway Ghana', 'SportyBet Ghana'];
const EUROPE_BOOKMAKERS = ['1xBet Ghana', '22Bet Ghana'];
const BONUS_BOOKMAKERS = ['SportyBet Ghana', 'Betway Ghana'];

const normalize = (value) => (value || '').toString().toLowerCase();

const resolveRecommendation = (names, reason, count) => (
  names
    .filter((name) => BOOKMAKER_AFFILIATES[name])
    .slice(0, count)
    .map((name) => ({
      ...BOOKMAKER_AFFILIATES[name],
      name,
      reason,
    }))
);

const getTopRatedBookmakers = (count) => {
  const sorted = [...BOOKMAKER_ORDER]
    .map((name) => ({
      ...BOOKMAKER_AFFILIATES[name],
      name,
    }))
    .sort((a, b) => (b.rating || 0) - (a.rating || 0));
  return sorted.slice(0, count).map((item) => ({
    ...item,
    reason: 'Top rated in Ghana',
  }));
};

export const getRecommendedBookmakers = ({
  league,
  category,
  count = 2,
} = {}) => {
  const leagueName = normalize(league);
  const categoryName = normalize(category);

  if (leagueName.includes('ghana') || categoryName.includes('ghana')) {
    return resolveRecommendation(LOCAL_BOOKMAKERS, 'Strong Ghana coverage', count);
  }

  if (leagueName.includes('premier') || categoryName.includes('premier')) {
    return resolveRecommendation(PREMIER_BOOKMAKERS, 'Great EPL coverage', count);
  }

  if (
    leagueName.includes('champions') ||
    leagueName.includes('europa') ||
    categoryName.includes('champions') ||
    categoryName.includes('europe')
  ) {
    return resolveRecommendation(EUROPE_BOOKMAKERS, 'Deep European markets', count);
  }

  if (categoryName.includes('guide') || categoryName.includes('betting')) {
    return resolveRecommendation(BONUS_BOOKMAKERS, 'Popular bonuses and payouts', count);
  }

  return getTopRatedBookmakers(count);
};
