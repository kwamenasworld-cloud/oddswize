const DEFAULT_SITEMAP_URL = 'https://oddswize.com/sitemap.xml';
const shouldPing = ['1', 'true', 'yes'].includes((process.env.PING_SITEMAP || '').toLowerCase());

if (!shouldPing) {
  console.log('[sitemap] PING_SITEMAP not set; skipping ping.');
  process.exit(0);
}

const sitemapUrl = process.env.SITEMAP_URL || DEFAULT_SITEMAP_URL;
const timeoutMs = Number(process.env.SITEMAP_PING_TIMEOUT_MS) || 8000;

const endpoints = [
  `https://www.google.com/ping?sitemap=${encodeURIComponent(sitemapUrl)}`,
  `https://www.bing.com/ping?sitemap=${encodeURIComponent(sitemapUrl)}`,
];

const ping = async (url) => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return true;
  } catch (error) {
    const message = error?.message || 'unknown error';
    console.warn(`[sitemap] Ping failed: ${url} (${message})`);
    return false;
  } finally {
    clearTimeout(timeoutId);
  }
};

const results = await Promise.all(endpoints.map(ping));
if (results.every(Boolean)) {
  console.log(`[sitemap] Pinged search engines for ${sitemapUrl}`);
} else {
  console.log('[sitemap] Some ping requests failed; build will continue.');
}
