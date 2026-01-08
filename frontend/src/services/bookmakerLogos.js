/**
 * Bookmaker Logo Service
 * Automatically fetches bookmaker logos from various free APIs
 */

// DuckDuckGo Icons API (free, no auth required, good quality)
const DUCKDUCKGO_ICON_API = 'https://icons.duckduckgo.com/ip3';

// Google Favicon API as fallback
const GOOGLE_FAVICON_API = 'https://t1.gstatic.com/faviconV2';

// Local cache for bookmaker logos
const CACHE_KEY = 'oddswize_bookmaker_logos_v1';
const CACHE_EXPIRY = 30 * 24 * 60 * 60 * 1000; // 30 days

// Bookmaker domain mappings
const BOOKMAKER_DOMAINS = {
  'betway ghana': 'betway.com',
  'betway': 'betway.com',
  'sportybet ghana': 'sportybet.com',
  'sportybet': 'sportybet.com',
  '1xbet ghana': '1xbet.com',
  '1xbet': '1xbet.com',
  '22bet ghana': '22bet.com',
  '22bet': '22bet.com',
  'soccabet ghana': 'soccabet.com.gh',
  'soccabet': 'soccabet.com.gh',
  'betfox ghana': 'betfox.com.gh',
  'betfox': 'betfox.com.gh',
  'bet365': 'bet365.com',
  'betking': 'betking.com',
  'betwinner': 'betwinner.com',
  'melbet': 'melbet.com',
  'parimatch': 'parimatch.com',
  'betano': 'betano.com',
  'unibet': 'unibet.com',
  'william hill': 'williamhill.com',
  'ladbrokes': 'ladbrokes.com',
  'coral': 'coral.co.uk',
  'paddy power': 'paddypower.com',
  'betfair': 'betfair.com',
  'sky bet': 'skybet.com',
  'bwin': 'bwin.com',
  '888sport': '888sport.com',
  'pinnacle': 'pinnacle.com',
};

// Load cache from localStorage
const loadCache = () => {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (cached) {
      const data = JSON.parse(cached);
      if (Date.now() - data.timestamp < CACHE_EXPIRY) {
        return data.logos;
      }
    }
  } catch (e) {
    console.log('[BookmakerLogos] Cache load error:', e);
  }
  return {};
};

// Save cache to localStorage
const saveCache = (logos) => {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({
      timestamp: Date.now(),
      logos
    }));
  } catch (e) {
    console.log('[BookmakerLogos] Cache save error:', e);
  }
};

// In-memory cache
let logoCache = loadCache();

const LOGO_CONCURRENCY_LIMIT = 4;
let activeLogoFetches = 0;
const logoFetchQueue = [];
const pendingLogoPromises = new Map();

const runNextLogoFetch = () => {
  if (activeLogoFetches >= LOGO_CONCURRENCY_LIMIT) return;
  const next = logoFetchQueue.shift();
  if (!next) return;
  activeLogoFetches += 1;
  next.task()
    .then(next.resolve)
    .catch(next.reject)
    .finally(() => {
      activeLogoFetches -= 1;
      runNextLogoFetch();
    });
};

const enqueueLogoFetch = (task) => new Promise((resolve, reject) => {
  logoFetchQueue.push({ task, resolve, reject });
  runNextLogoFetch();
});

/**
 * Get domain for a bookmaker
 */
const getBookmakerDomain = (bookmakerName) => {
  const normalized = bookmakerName.toLowerCase().trim();
  return BOOKMAKER_DOMAINS[normalized] || null;
};

/**
 * Test if a logo URL is valid (returns an image)
 */
const testLogoUrl = async (url) => {
  try {
    const response = await fetch(url, { method: 'HEAD' });
    const contentType = response.headers.get('content-type');
    return response.ok && contentType && contentType.startsWith('image/');
  } catch {
    return false;
  }
};

/**
 * Fetch bookmaker logo
 */
const fetchBookmakerLogo = async (bookmakerName) => {
  const domain = getBookmakerDomain(bookmakerName);
  const cacheKey = bookmakerName.toLowerCase().trim();

  // Check memory cache first
  if (logoCache[cacheKey]) {
    return logoCache[cacheKey];
  }

  if (!domain) {
    return null;
  }

  if (pendingLogoPromises.has(cacheKey)) {
    return pendingLogoPromises.get(cacheKey);
  }

  const queuedPromise = enqueueLogoFetch(async () => {
    // Try DuckDuckGo Icons API first (good quality, always works)
    const duckduckgoUrl = `${DUCKDUCKGO_ICON_API}/${domain}.ico`;

    try {
      const isValid = await testLogoUrl(duckduckgoUrl);
      if (isValid) {
        logoCache[cacheKey] = duckduckgoUrl;
        saveCache(logoCache);
        return duckduckgoUrl;
      }
    } catch (e) {
      // DuckDuckGo failed, fallback to Google
    }

    // Fall back to Google Favicon API
    const googleUrl = `${GOOGLE_FAVICON_API}?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://${domain}&size=128`;

    logoCache[cacheKey] = googleUrl;
    saveCache(logoCache);
    return googleUrl;
  });

  pendingLogoPromises.set(cacheKey, queuedPromise);
  try {
    return await queuedPromise;
  } finally {
    pendingLogoPromises.delete(cacheKey);
  }
};

/**
 * Get bookmaker logo (from cache or fetch)
 */
export const getBookmakerLogo = async (bookmakerName) => {
  if (!bookmakerName) return null;

  const cacheKey = bookmakerName.toLowerCase().trim();

  // Return cached value if exists
  if (logoCache[cacheKey]) {
    return logoCache[cacheKey];
  }

  // Fetch logo
  return await fetchBookmakerLogo(bookmakerName);
};

/**
 * Get cached logo (sync, returns null if not cached)
 */
export const getCachedBookmakerLogo = (bookmakerName) => {
  if (!bookmakerName) return null;
  const cacheKey = bookmakerName.toLowerCase().trim();
  return logoCache[cacheKey] || null;
};

/**
 * Preload logos for multiple bookmakers
 */
export const preloadBookmakerLogos = async (bookmakerNames) => {
  const uniqueNames = [...new Set(bookmakerNames.filter(Boolean))];
  const uncached = uniqueNames.filter(name => {
    const key = name.toLowerCase().trim();
    return !(key in logoCache);
  });

  console.log(`[BookmakerLogos] Preloading ${uncached.length} logos`);

  // Fetch in parallel (small number so no rate limiting needed)
  await Promise.all(uncached.map(name => fetchBookmakerLogo(name)));
};

/**
 * Clear logo cache
 */
export const clearBookmakerLogoCache = () => {
  logoCache = {};
  localStorage.removeItem(CACHE_KEY);
  console.log('[BookmakerLogos] Cache cleared');
};

/**
 * Get logo stats for debugging
 */
export const getBookmakerLogoStats = () => {
  const total = Object.keys(logoCache).length;
  return { total, cached: logoCache };
};

export default {
  getBookmakerLogo,
  getCachedBookmakerLogo,
  preloadBookmakerLogos,
  clearBookmakerLogoCache,
  getBookmakerLogoStats
};
