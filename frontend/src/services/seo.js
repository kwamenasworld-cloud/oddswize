import { useEffect } from 'react';

const DEFAULT_META = {
  title: 'OddsWize - Compare Betting Odds in Ghana | Best Odds Comparison',
  description: "Ghana's #1 betting odds comparison site. Compare odds from Betway, SportyBet, 1xBet, 22Bet & SoccaBet. Find the best odds, value bets, and maximize your winnings.",
  image: 'https://oddswize.com/og-image.png',
  url: 'https://oddswize.com/',
  type: 'website',
  twitterCard: 'summary_large_image',
};

const resolveUrl = (value, baseUrl) => {
  if (!value) return '';
  try {
    return new URL(value, baseUrl).toString();
  } catch (error) {
    return value;
  }
};

const setMetaTag = ({ name, property }, content) => {
  if (typeof document === 'undefined' || !content) return;
  const selector = name
    ? `meta[name="${name}"]`
    : `meta[property="${property}"]`;
  let tag = document.head.querySelector(selector);
  if (!tag) {
    tag = document.createElement('meta');
    if (name) tag.setAttribute('name', name);
    if (property) tag.setAttribute('property', property);
    document.head.appendChild(tag);
  }
  tag.setAttribute('content', content);
};

const setLinkTag = (rel, href) => {
  if (typeof document === 'undefined' || !href) return;
  let tag = document.head.querySelector(`link[rel="${rel}"]`);
  if (!tag) {
    tag = document.createElement('link');
    tag.setAttribute('rel', rel);
    document.head.appendChild(tag);
  }
  tag.setAttribute('href', href);
};

export const applyPageMeta = (meta) => {
  if (typeof document === 'undefined') return;
  const merged = { ...DEFAULT_META, ...meta };
  const url = resolveUrl(merged.url, DEFAULT_META.url);
  const image = resolveUrl(merged.image, DEFAULT_META.url);

  document.title = merged.title;
  setMetaTag({ name: 'description' }, merged.description);
  setMetaTag({ property: 'og:title' }, merged.title);
  setMetaTag({ property: 'og:description' }, merged.description);
  setMetaTag({ property: 'og:type' }, merged.type);
  setMetaTag({ property: 'og:url' }, url);
  setMetaTag({ property: 'og:image' }, image);
  setMetaTag({ name: 'twitter:card' }, merged.twitterCard || DEFAULT_META.twitterCard);
  setMetaTag({ name: 'twitter:title' }, merged.title);
  setMetaTag({ name: 'twitter:description' }, merged.description);
  setMetaTag({ name: 'twitter:image' }, image);
  setLinkTag('canonical', url);
};

export const usePageMeta = (meta) => {
  const title = meta?.title;
  const description = meta?.description;
  const image = meta?.image;
  const url = meta?.url;
  const type = meta?.type;

  useEffect(() => {
    applyPageMeta({ ...DEFAULT_META, ...meta });
    return () => applyPageMeta(DEFAULT_META);
  }, [title, description, image, url, type]);
};

export default {
  applyPageMeta,
  usePageMeta,
};
