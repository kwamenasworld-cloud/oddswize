import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ARTICLES } from '../src/data/articles.js';
import { LEAGUES, COUNTRIES } from '../src/config/leagues.js';
import { BOOKMAKER_AFFILIATES, BOOKMAKER_ORDER } from '../src/config/affiliates.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SITE_URL = 'https://oddswize.com';
const PUBLIC_DIR = path.resolve(__dirname, '../public');
const VALUE_EDGE_MIN = 5;
const MAX_MATCH_PAGES = 400;
const MATCH_LOOKAHEAD_DAYS = 7;

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

const escapeHtml = escapeXml;

const slugify = (value) => (
  String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
);

const buildMatchSlug = (match) => {
  if (!match?.home_team || !match?.away_team || !Number.isFinite(match.start_time)) return '';
  const date = new Date(match.start_time * 1000);
  if (Number.isNaN(date.getTime())) return '';
  const dateLabel = date.toISOString().slice(0, 10);
  const homeSlug = slugify(match.home_team);
  const awaySlug = slugify(match.away_team);
  if (!homeSlug || !awaySlug) return '';
  return `${homeSlug}-vs-${awaySlug}-${dateLabel}`;
};

const formatKickoff = (timestamp) => {
  if (!Number.isFinite(timestamp)) return 'TBD';
  const date = new Date(timestamp * 1000);
  if (Number.isNaN(date.getTime())) return 'TBD';
  return date.toLocaleString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const renderLandingPage = ({ title, description, canonical, heading, intro, sectionsHtml, ctaLabel, ctaUrl }) => {
  const safeTitle = escapeHtml(title);
  const safeDescription = escapeHtml(description);
  const safeCanonical = escapeHtml(canonical);
  const safeHeading = escapeHtml(heading);
  const safeIntro = escapeHtml(intro);
  const safeCtaLabel = escapeHtml(ctaLabel);
  const safeCtaUrl = escapeHtml(ctaUrl);
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: title,
    description,
    url: canonical,
    publisher: {
      '@type': 'Organization',
      name: 'OddsWize',
      logo: {
        '@type': 'ImageObject',
        url: `${SITE_URL}/logo.png`,
      },
    },
  };

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${safeTitle}</title>
  <meta name="description" content="${safeDescription}" />
  <link rel="canonical" href="${safeCanonical}" />
  <meta property="og:title" content="${safeTitle}" />
  <meta property="og:description" content="${safeDescription}" />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="${safeCanonical}" />
  <meta property="og:image" content="${SITE_URL}/logo.png" />
  <meta name="twitter:card" content="summary" />
  <style>
    :root {
      --primary: #1a73e8;
      --primary-dark: #0f5fc5;
      --ink: #0f172a;
      --muted: #6b7280;
      --card: #ffffff;
      --bg: #f4f6fb;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: 'Lucida Sans', 'Lucida Sans Unicode', 'Lucida Grande', sans-serif;
      background: var(--bg);
      color: var(--ink);
    }
    a { color: inherit; }
    .hero {
      background: linear-gradient(135deg, #0f172a 0%, #1a1a2e 100%);
      color: #fff;
      padding: 3.5rem 1.5rem;
    }
    .hero-inner {
      max-width: 900px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    .brand {
      text-decoration: none;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      font-size: 0.85rem;
      color: rgba(255, 255, 255, 0.7);
    }
    .hero h1 {
      margin: 0;
      font-size: 2.4rem;
      line-height: 1.2;
    }
    .hero p {
      margin: 0;
      font-size: 1.05rem;
      color: rgba(255, 255, 255, 0.75);
    }
    .cta {
      align-self: flex-start;
      background: linear-gradient(135deg, var(--primary), var(--primary-dark));
      color: #fff;
      text-decoration: none;
      padding: 0.75rem 1.5rem;
      border-radius: 10px;
      font-weight: 700;
    }
    .content {
      max-width: 1100px;
      margin: 0 auto;
      padding: 2.5rem 1.5rem 3rem;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }
    .card {
      background: var(--card);
      border-radius: 16px;
      padding: 1.5rem;
      box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
      border: 1px solid #e6e8ee;
    }
    .card h2 {
      margin: 0 0 0.75rem;
      font-size: 1.3rem;
    }
    .card p {
      margin: 0 0 0.75rem;
      color: var(--muted);
      line-height: 1.6;
    }
    .list {
      margin: 0.75rem 0 0;
      padding-left: 1.2rem;
      color: var(--muted);
      line-height: 1.6;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 1rem;
    }
    .pick-card h3 {
      margin: 0 0 0.5rem;
      font-size: 1rem;
    }
    .pick-meta {
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--muted);
      margin-bottom: 0.5rem;
    }
    .pick-edge {
      font-weight: 700;
      color: #16a34a;
    }
    .pick-link {
      display: inline-flex;
      margin-top: 0.5rem;
      color: var(--primary);
      font-weight: 600;
      text-decoration: none;
    }
    .pick-link:hover {
      text-decoration: underline;
    }
    .footer {
      padding: 1.5rem;
      text-align: center;
      color: var(--muted);
      font-size: 0.85rem;
    }
    @media (max-width: 720px) {
      .hero {
        padding: 2.5rem 1.25rem;
      }
      .hero h1 {
        font-size: 1.8rem;
      }
      .cta {
        width: 100%;
        text-align: center;
      }
    }
  </style>
  <script type="application/ld+json">${escapeHtml(JSON.stringify(jsonLd))}</script>
</head>
<body>
  <header class="hero">
    <div class="hero-inner">
      <a class="brand" href="${SITE_URL}/">OddsWize</a>
      <h1>${safeHeading}</h1>
      <p>${safeIntro}</p>
      <a class="cta" href="${safeCtaUrl}">${safeCtaLabel}</a>
    </div>
  </header>
  <main class="content">
    ${sectionsHtml}
  </main>
  <footer class="footer">
    <p>OddsWize compares odds across Ghana and Nigeria bookmakers. Always gamble responsibly.</p>
  </footer>
</body>
</html>`;
};

const renderLeaguePage = (league) => {
  const slug = slugify(league.id || league.name);
  const leagueName = league.name || 'League';
  const countryName = COUNTRIES[league.country]?.name || 'International';
  const title = `${leagueName} Odds in Ghana | Compare ${leagueName} Bookmakers`;
  const description = `Compare ${leagueName} odds from top Ghana bookmakers. Find the best prices for ${leagueName} matches and bet with confidence.`;
  const canonical = `${SITE_URL}/odds/${slug}/`;
  const heading = `${leagueName} Odds Comparison`;
  const intro = `Compare ${leagueName} odds from Ghana bookmakers and spot the best value quickly.`;
  const bookmakersList = BOOKMAKER_ORDER.map((bookie) => {
    const name = BOOKMAKER_AFFILIATES[bookie]?.name || bookie;
    return `<li>${escapeHtml(name)}</li>`;
  }).join('');

  const sectionsHtml = `
    <section class="card">
      <h2>Best ${escapeHtml(leagueName)} odds</h2>
      <p>OddsWize compares ${escapeHtml(leagueName)} markets across Ghana's licensed bookmakers. Use the odds table to find the best price before you place a bet.</p>
      <p>Country focus: ${escapeHtml(countryName)}. We track major fixtures, derbies, and high profile matchups.</p>
    </section>
    <section class="card">
      <h2>Bookmakers we compare</h2>
      <ul class="list">${bookmakersList}</ul>
    </section>
    <section class="card">
      <h2>How to get the best value</h2>
      <ol class="list">
        <li>Compare the top three prices for each outcome.</li>
        <li>Track odds movement close to kickoff.</li>
        <li>Prioritize bookmakers with the strongest bonuses.</li>
      </ol>
    </section>
  `;

  return renderLandingPage({
    title,
    description,
    canonical,
    heading,
    intro,
    sectionsHtml,
    ctaLabel: `View ${leagueName} odds`,
    ctaUrl: `${SITE_URL}/odds?league=${league.id || slug}`,
  });
};

const renderBookmakerPage = (config) => {
  const slug = slugify(config.id || config.name);
  const name = config.name || 'Bookmaker';
  const title = `${name} Ghana Review | Odds and Bonuses`;
  const description = `See ${name} odds and bonus details, plus compare prices against other Ghana bookmakers on OddsWize.`;
  const canonical = `${SITE_URL}/bookmakers/${slug}/`;
  const heading = `${name} Bookmaker Review`;
  const intro = `Learn about ${name} bonuses, odds coverage, and how to compare prices on OddsWize.`;
  const features = Array.isArray(config.features) && config.features.length
    ? config.features
    : ['Competitive odds on top leagues', 'Fast deposits and withdrawals', 'Mobile friendly betting'];
  const featuresHtml = features.map((item) => `<li>${escapeHtml(item)}</li>`).join('');
  const bonusHtml = config.signupBonus
    ? `<p><strong>Signup bonus:</strong> ${escapeHtml(config.signupBonus)}</p>`
    : '<p>Visit the bookmaker to see the latest signup bonus details.</p>';
  const sectionsHtml = `
    <section class="card">
      <h2>Why bettors choose ${escapeHtml(name)}</h2>
      ${bonusHtml}
      <ul class="list">${featuresHtml}</ul>
    </section>
    <section class="card">
      <h2>Compare ${escapeHtml(name)} odds</h2>
      <p>OddsWize lets you compare ${escapeHtml(name)} against other Ghana bookmakers so you can spot the best price quickly.</p>
      <p>Use the odds table to compare 1X2, double chance, and totals markets.</p>
    </section>
  `;
  const ctaUrl = config.affiliateUrl && config.affiliateUrl !== '#'
    ? config.affiliateUrl
    : `${SITE_URL}/bookmakers`;
  const ctaLabel = config.affiliateUrl && config.affiliateUrl !== '#'
    ? `Visit ${name}`
    : 'View bookmakers';

  return renderLandingPage({
    title,
    description,
    canonical,
    heading,
    intro,
    sectionsHtml,
    ctaLabel,
    ctaUrl,
  });
};

const getCountryLeagues = (countryId) => (
  Object.values(LEAGUES)
    .filter((league) => league.country === countryId)
    .sort((a, b) => (a.tier || 9) - (b.tier || 9))
);

const renderCountryOddsPage = ({ countryId, slug, headline, intro, ctaUrl }) => {
  const country = COUNTRIES[countryId];
  const countryName = country?.name || 'Country';
  const title = `${countryName} Odds Comparison | Best Bookmakers in ${countryName}`;
  const description = `Compare odds from ${countryName} bookmakers and find the best prices across top leagues.`;
  const canonical = `${SITE_URL}/${slug}/`;
  const heading = headline || `${countryName} Odds Comparison`;
  const leagueList = getCountryLeagues(countryId)
    .map((league) => {
      const name = league.name === 'Premier League'
        ? `${countryName} Premier League`
        : league.name;
      return `<li>${escapeHtml(name)}</li>`;
    })
    .join('');
  const bookmakersList = BOOKMAKER_ORDER.map((bookie) => {
    const name = BOOKMAKER_AFFILIATES[bookie]?.name || bookie;
    return `<li>${escapeHtml(name)}</li>`;
  }).join('');
  const sectionsHtml = `
    <section class="card">
      <h2>Compare odds in ${escapeHtml(countryName)}</h2>
      <p>OddsWize brings together prices from ${escapeHtml(countryName)}-focused bookmakers so you can see the best value before you bet.</p>
      <p>We cover local fixtures plus the biggest European competitions that Ghanaian and Nigerian bettors follow.</p>
    </section>
    <section class="card">
      <h2>Popular ${escapeHtml(countryName)} leagues</h2>
      <ul class="list">${leagueList || '<li>Premier League fixtures</li>'}</ul>
    </section>
    <section class="card">
      <h2>Bookmakers we track</h2>
      <ul class="list">${bookmakersList}</ul>
    </section>
  `;

  return renderLandingPage({
    title,
    description,
    canonical,
    heading,
    intro: intro || `Compare odds for ${countryName} fixtures and get the best price quickly.`,
    sectionsHtml,
    ctaLabel: `View ${countryName} odds`,
    ctaUrl: ctaUrl || `${SITE_URL}/odds?country=${countryId}`,
  });
};

const renderCountryLeaguePage = ({ countryId, leagueId, slug, leagueName }) => {
  const country = COUNTRIES[countryId];
  const countryName = country?.name || 'Country';
  const league = LEAGUES[leagueId];
  const displayName = leagueName || league?.name || 'League';
  const title = `${displayName} Odds | ${countryName} Bookmakers`;
  const description = `Compare ${displayName} odds from ${countryName} bookmakers. Find the best prices for upcoming fixtures.`;
  const canonical = `${SITE_URL}/${slug}/`;
  const heading = `${displayName} Odds Comparison`;
  const sectionsHtml = `
    <section class="card">
      <h2>Best ${escapeHtml(displayName)} odds</h2>
      <p>Compare ${escapeHtml(displayName)} odds across ${escapeHtml(countryName)} bookmakers and spot value quickly.</p>
      <p>We update frequently to keep odds and coverage fresh.</p>
    </section>
    <section class="card">
      <h2>Get more value from every bet</h2>
      <ol class="list">
        <li>Check at least three bookmakers for each outcome.</li>
        <li>Look for lines that are 5%+ above the market average.</li>
        <li>Move quickly when you see a price gap.</li>
      </ol>
    </section>
  `;

  return renderLandingPage({
    title,
    description,
    canonical,
    heading,
    intro: `Compare ${displayName} fixtures across the top ${countryName} bookmakers.`,
    sectionsHtml,
    ctaLabel: `View ${displayName} odds`,
    ctaUrl: `${SITE_URL}/odds?league=${leagueId}`,
  });
};

const getMarketAverage = (odds, field) => {
  const values = (odds || [])
    .map((bookie) => Number(bookie[field]))
    .filter((value) => Number.isFinite(value) && value > 1);
  if (!values.length) return 0;
  const sum = values.reduce((acc, value) => acc + value, 0);
  return sum / values.length;
};

const buildValuePicks = (matches) => {
  const nowSeconds = Date.now() / 1000;
  const windowEnd = nowSeconds + 24 * 60 * 60;
  const picks = [];

  (matches || []).forEach((match) => {
    const startTime = Number(match.start_time || 0);
    if (!startTime || startTime < nowSeconds || startTime > windowEnd) return;
    if (!Array.isArray(match.odds) || match.odds.length < 2) return;

    const averages = ['home_odds', 'draw_odds', 'away_odds'].map((field) => getMarketAverage(match.odds, field));
    const labels = [
      match.home_team ? `${match.home_team} win` : 'Home win',
      'Draw',
      match.away_team ? `${match.away_team} win` : 'Away win',
    ];

    let best = null;
    match.odds.forEach((bookie) => {
      ['home_odds', 'draw_odds', 'away_odds'].forEach((field, index) => {
        const value = Number(bookie[field]);
        const average = averages[index];
        if (!Number.isFinite(value) || value <= 1 || !average) return;
        const edge = ((value - average) / average) * 100;
        if (edge < VALUE_EDGE_MIN) return;
        if (!best || edge > best.edge) {
          best = {
            bookmaker: bookie.bookmaker,
            odds: value,
            edge,
            label: labels[index],
          };
        }
      });
    });

    if (best) {
      picks.push({
        match,
        offer: best,
      });
    }
  });

  return picks
    .sort((a, b) => b.offer.edge - a.offer.edge)
    .slice(0, 8);
};

const renderValuePicksPage = (picks, updatedAt) => {
  const updatedLabel = updatedAt ? toRfc822(updatedAt) : toRfc822(new Date());
  const cards = picks.map((pick) => {
    const match = pick.match;
    const offer = pick.offer;
    const valuePercent = Math.round(offer.edge);
    const matchSlug = buildMatchSlug(match);
    const matchUrl = matchSlug
      ? `${SITE_URL}/odds/match/${matchSlug}/`
      : `${SITE_URL}/odds?match=${encodeURIComponent(`${match.home_team} vs ${match.away_team}`)}`;

    return `
      <div class="card pick-card">
        <div class="pick-meta">${escapeHtml(match.league || 'Match')}</div>
        <h3>${escapeHtml(match.home_team)} vs ${escapeHtml(match.away_team)}</h3>
        <p>Kickoff: ${escapeHtml(formatKickoff(match.start_time))}</p>
        <p><span class="pick-edge">+${valuePercent}%</span> on ${escapeHtml(offer.label)} at ${escapeHtml(offer.bookmaker)}</p>
        <p>Odds: ${Number.isFinite(offer.odds) ? offer.odds.toFixed(2) : 'N/A'}</p>
        <a class="pick-link" href="${escapeHtml(matchUrl)}">View match odds</a>
      </div>
    `;
  }).join('');

  const sectionsHtml = `
    <section class="card">
      <h2>How we rank picks</h2>
      <p>We compare each bookmaker price to the market average for the same outcome. The biggest positive edges rise to the top.</p>
      <p>Last updated: ${escapeHtml(updatedLabel)}</p>
    </section>
    <section class="grid">
      ${cards || '<div class="card">No value picks available right now. Check back later.</div>'}
    </section>
  `;

  return renderLandingPage({
    title: 'Value Picks Today | OddsWize',
    description: 'Auto-generated value picks based on the largest odds edges across Ghana and Nigeria bookmakers.',
    canonical: `${SITE_URL}/news/value-picks/`,
    heading: 'Value Picks Today',
    intro: 'Auto-generated picks based on the largest odds edges across Ghana and Nigeria bookmakers.',
    sectionsHtml,
    ctaLabel: 'Compare all odds',
    ctaUrl: `${SITE_URL}/odds`,
  });
};

const getBestOddsByField = (odds, field) => {
  const valid = (odds || [])
    .map((bookie) => ({
      bookmaker: bookie.bookmaker,
      value: Number(bookie[field]),
    }))
    .filter((item) => Number.isFinite(item.value) && item.value > 1);
  if (!valid.length) return { value: null, bookmaker: null };
  return valid.reduce((best, item) => (item.value > best.value ? item : best), valid[0]);
};

const renderMatchPage = (match, slug) => {
  const home = match.home_team || 'Home';
  const away = match.away_team || 'Away';
  const league = match.league || 'Match';
  const kickoff = formatKickoff(match.start_time);
  const title = `${home} vs ${away} Odds | ${league}`;
  const description = `Compare ${home} vs ${away} odds across Ghana and Nigeria bookmakers. Find the best prices before kickoff.`;
  const canonical = `${SITE_URL}/odds/match/${slug}/`;
  const heading = `${home} vs ${away} Odds`;
  const intro = `Compare ${home} vs ${away} odds across Ghana and Nigeria bookmakers and spot the best value quickly.`;
  const bestHome = getBestOddsByField(match.odds, 'home_odds');
  const bestDraw = getBestOddsByField(match.odds, 'draw_odds');
  const bestAway = getBestOddsByField(match.odds, 'away_odds');
  const oddsLink = `${SITE_URL}/odds?match=${encodeURIComponent(`${home} vs ${away}`)}&ref=match_page`;
  const bookmakersList = BOOKMAKER_ORDER.map((bookie) => {
    const name = BOOKMAKER_AFFILIATES[bookie]?.name || bookie;
    return `<li>${escapeHtml(name)}</li>`;
  }).join('');
  const bestOddsRows = `
    <ul class="list">
      <li>${escapeHtml(home)} win: ${bestHome.value ? bestHome.value.toFixed(2) : 'N/A'}${bestHome.bookmaker ? ` (${escapeHtml(bestHome.bookmaker)})` : ''}</li>
      <li>Draw: ${bestDraw.value ? bestDraw.value.toFixed(2) : 'N/A'}${bestDraw.bookmaker ? ` (${escapeHtml(bestDraw.bookmaker)})` : ''}</li>
      <li>${escapeHtml(away)} win: ${bestAway.value ? bestAway.value.toFixed(2) : 'N/A'}${bestAway.bookmaker ? ` (${escapeHtml(bestAway.bookmaker)})` : ''}</li>
    </ul>
  `;

  const sectionsHtml = `
    <section class="card">
      <h2>Match details</h2>
      <p>League: ${escapeHtml(league)}</p>
      <p>Kickoff: ${escapeHtml(kickoff)}</p>
    </section>
    <section class="card">
      <h2>Best odds right now</h2>
      ${bestOddsRows}
      <p>Odds change fast near kickoff, so check the live table before placing your bet.</p>
    </section>
    <section class="card">
      <h2>Bookmakers we compare</h2>
      <ul class="list">${bookmakersList}</ul>
    </section>
  `;

  return renderLandingPage({
    title,
    description,
    canonical,
    heading,
    intro,
    sectionsHtml,
    ctaLabel: 'Compare all odds',
    ctaUrl: oddsLink,
  });
};

const writePage = async (relativePath, html) => {
  const targetDir = path.join(PUBLIC_DIR, relativePath);
  await fs.mkdir(targetDir, { recursive: true });
  await fs.writeFile(path.join(targetDir, 'index.html'), html, 'utf8');
};

const readOddsData = async () => {
  try {
    const raw = await fs.readFile(path.join(PUBLIC_DIR, 'data', 'odds_data.json'), 'utf8');
    return JSON.parse(raw);
  } catch (error) {
    return null;
  }
};

const sortedArticles = [...ARTICLES].sort(
  (a, b) => (toDate(b.publishedAt)?.getTime() || 0) - (toDate(a.publishedAt)?.getTime() || 0)
);

const now = new Date();
const latestArticleDate = sortedArticles[0]?.publishedAt;
const latestIso = toIsoDate(latestArticleDate, now);

const leagueEntries = [];
for (const league of Object.values(LEAGUES)) {
  if (!league || !league.id || !league.name) continue;
  const slug = slugify(league.id);
  if (!slug) continue;
  await writePage(`odds/${slug}`, renderLeaguePage(league));
  leagueEntries.push({
    loc: `${SITE_URL}/odds/${slug}/`,
    lastmod: latestIso,
    changefreq: 'weekly',
    priority: '0.6',
  });
}

const bookmakerEntries = [];
for (const config of Object.values(BOOKMAKER_AFFILIATES)) {
  if (!config || (!config.id && !config.name)) continue;
  const slug = slugify(config.id || config.name);
  if (!slug) continue;
  await writePage(`bookmakers/${slug}`, renderBookmakerPage(config));
  bookmakerEntries.push({
    loc: `${SITE_URL}/bookmakers/${slug}/`,
    lastmod: latestIso,
    changefreq: 'weekly',
    priority: '0.6',
  });
}

const COUNTRY_LANDINGS = [
  {
    countryId: 'ghana',
    slug: 'ghana-odds',
    headline: 'Ghana Odds Comparison',
    intro: 'Compare odds from Ghana bookmakers and find the best price fast.',
    ctaUrl: `${SITE_URL}/odds?country=ghana`,
  },
  {
    countryId: 'nigeria',
    slug: 'nigeria-odds',
    headline: 'Nigeria Odds Comparison',
    intro: 'Compare odds from Nigeria bookmakers and track top fixtures daily.',
    ctaUrl: `${SITE_URL}/odds?country=nigeria`,
  },
];

const COUNTRY_LEAGUE_LANDINGS = [
  {
    countryId: 'ghana',
    leagueId: 'ghana',
    slug: 'ghana-premier-league-odds',
    leagueName: 'Ghana Premier League',
  },
  {
    countryId: 'nigeria',
    leagueId: 'nigeria',
    slug: 'npfl-odds',
    leagueName: 'Nigeria Premier League (NPFL)',
  },
];

const countryEntries = [];
for (const landing of COUNTRY_LANDINGS) {
  if (!landing?.countryId || !landing?.slug) continue;
  await writePage(landing.slug, renderCountryOddsPage(landing));
  countryEntries.push({
    loc: `${SITE_URL}/${landing.slug}/`,
    lastmod: latestIso,
    changefreq: 'weekly',
    priority: '0.7',
  });
}

const countryLeagueEntries = [];
for (const landing of COUNTRY_LEAGUE_LANDINGS) {
  if (!landing?.countryId || !landing?.leagueId || !landing?.slug) continue;
  await writePage(landing.slug, renderCountryLeaguePage(landing));
  countryLeagueEntries.push({
    loc: `${SITE_URL}/${landing.slug}/`,
    lastmod: latestIso,
    changefreq: 'weekly',
    priority: '0.7',
  });
}

const oddsData = await readOddsData();
const valuePicks = buildValuePicks(oddsData?.matches || []);
const updatedAt = oddsData?.last_updated || now.toISOString();
await writePage('news/value-picks', renderValuePicksPage(valuePicks, updatedAt));
const valuePicksEntry = {
  loc: `${SITE_URL}/news/value-picks/`,
  lastmod: toIsoDate(updatedAt, now),
  changefreq: 'hourly',
  priority: '0.7',
};

const matchEntries = [];
if (Array.isArray(oddsData?.matches)) {
  const nowSeconds = Date.now() / 1000;
  const cutoff = nowSeconds + MATCH_LOOKAHEAD_DAYS * 24 * 60 * 60;
  const matches = oddsData.matches
    .filter((match) => Number.isFinite(match?.start_time))
    .filter((match) => match.start_time >= nowSeconds - 6 * 60 * 60 && match.start_time <= cutoff)
    .sort((a, b) => (a.start_time || 0) - (b.start_time || 0));

  const seen = new Set();
  for (const match of matches) {
    if (matchEntries.length >= MAX_MATCH_PAGES) break;
    const slug = buildMatchSlug(match);
    if (!slug || seen.has(slug)) continue;
    seen.add(slug);
    await writePage(`odds/match/${slug}`, renderMatchPage(match, slug));
    matchEntries.push({
      loc: `${SITE_URL}/odds/match/${slug}/`,
      lastmod: toIsoDate(match.start_time * 1000, now),
      changefreq: 'daily',
      priority: '0.55',
    });
  }
}

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
  ...(valuePicksEntry ? [valuePicksEntry] : []),
  ...sortedArticles.map((article) => ({
    loc: `${SITE_URL}/news/${article.slug}`,
    lastmod: toIsoDate(article.publishedAt, now),
    changefreq: 'weekly',
    priority: '0.7',
  })),
  ...matchEntries,
  ...countryEntries,
  ...countryLeagueEntries,
  ...leagueEntries,
  ...bookmakerEntries,
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

console.log('Generated sitemap.xml, rss.xml, and landing pages');
