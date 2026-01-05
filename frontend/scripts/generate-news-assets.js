import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ARTICLES } from '../src/data/articles.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SITE_URL = 'https://oddswize.com';
const PUBLIC_DIR = path.resolve(__dirname, '../public');

const toDate = (value) => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date;
};

const toIsoDate = (value, fallback) => {
  const date = toDate(value) || fallback || new Date();
  return date.toISOString().slice(0, 10);
};

const toRfc822 = (value, fallback) => {
  const date = toDate(value) || fallback || new Date();
  return date.toUTCString();
};

const escapeXml = (value) => {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
};

const sortedArticles = [...ARTICLES].sort(
  (a, b) => (toDate(b.publishedAt)?.getTime() || 0) - (toDate(a.publishedAt)?.getTime() || 0)
);

const now = new Date();
const latestArticleDate = sortedArticles[0]?.publishedAt;
const latestIso = toIsoDate(latestArticleDate, now);

const sitemapEntries = [
  {
    loc: `${SITE_URL}/`,
    lastmod: toIsoDate(now, now),
    changefreq: 'daily',
    priority: '1.0',
  },
  {
    loc: `${SITE_URL}/odds`,
    lastmod: toIsoDate(now, now),
    changefreq: 'hourly',
    priority: '0.9',
  },
  {
    loc: `${SITE_URL}/bookmakers`,
    lastmod: toIsoDate(now, now),
    changefreq: 'weekly',
    priority: '0.8',
  },
  {
    loc: `${SITE_URL}/news`,
    lastmod: latestIso,
    changefreq: 'daily',
    priority: '0.8',
  },
  ...sortedArticles.map((article) => ({
    loc: `${SITE_URL}/news/${article.slug}`,
    lastmod: toIsoDate(article.publishedAt, now),
    changefreq: 'weekly',
    priority: '0.7',
  })),
];

const sitemapXml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${sitemapEntries.map((entry) => `  <url>
    <loc>${escapeXml(entry.loc)}</loc>
    <lastmod>${escapeXml(entry.lastmod)}</lastmod>
    <changefreq>${escapeXml(entry.changefreq)}</changefreq>
    <priority>${escapeXml(entry.priority)}</priority>
  </url>`).join('\n')}
</urlset>
`;

const rssItems = sortedArticles.map((article) => {
  const link = `${SITE_URL}/news/${article.slug}`;
  const title = escapeXml(article.title);
  const description = escapeXml(article.excerpt);
  const category = escapeXml(article.category);
  const pubDate = toRfc822(article.publishedAt, now);
  const content = article.content ? `<![CDATA[${article.content.trim()}]]>` : '';

  return `    <item>
      <title>${title}</title>
      <link>${escapeXml(link)}</link>
      <guid>${escapeXml(link)}</guid>
      <pubDate>${escapeXml(pubDate)}</pubDate>
      <category>${category}</category>
      <description>${description}</description>
      <content:encoded>${content}</content:encoded>
    </item>`;
});

const rssXml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:atom="http://www.w3.org/2005/Atom"
  xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>OddsWize News</title>
    <link>${SITE_URL}/news</link>
    <atom:link href="${SITE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <description>Betting news, odds analysis, and guides for Ghanaian bettors.</description>
    <language>en-GH</language>
    <lastBuildDate>${toRfc822(latestArticleDate, now)}</lastBuildDate>
${rssItems.join('\n')}
  </channel>
</rss>
`;

await fs.writeFile(path.join(PUBLIC_DIR, 'sitemap.xml'), sitemapXml, 'utf8');
await fs.writeFile(path.join(PUBLIC_DIR, 'rss.xml'), rssXml, 'utf8');

console.log('Generated sitemap.xml and rss.xml');
