const getPagePath = () => {
  if (typeof window === 'undefined') return '';
  return window.location?.pathname || '';
};

export const trackEvent = (eventName, params = {}) => {
  if (typeof window === 'undefined') return;
  if (typeof window.gtag === 'function') {
    window.gtag('event', eventName, {
      ...params,
      page_path: params.page_path || getPagePath(),
      transport_type: 'beacon',
    });
    return;
  }
  if (window.dataLayer && typeof window.dataLayer.push === 'function') {
    window.dataLayer.push({
      event: eventName,
      ...params,
      page_path: params.page_path || getPagePath(),
    });
  }
};

export const trackAffiliateClick = ({
  bookmaker,
  placement,
  match,
  league,
  outcome,
  odds,
  valuePercent,
  url,
}) => {
  trackEvent('affiliate_click', {
    bookmaker,
    placement,
    match,
    league,
    outcome,
    odds,
    value_percent: valuePercent,
    link_url: url,
  });
};
