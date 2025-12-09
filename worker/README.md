# OddsWize API - Cloudflare Worker

Backend API for OddsWize betting odds comparison, deployed on Cloudflare Workers.

## Features

- Fast edge responses (global CDN)
- KV storage for caching odds data
- Arbitrage opportunity detection
- CORS support for frontend
- Scheduled data refresh

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` or `/health` | GET | Health check |
| `/api/odds` | GET | Get all odds data |
| `/api/odds/:league` | GET | Get odds for specific league |
| `/api/arbitrage` | GET | Get arbitrage opportunities |
| `/api/match/:id` | GET | Get single match |
| `/api/bookmakers` | GET | Get list of bookmakers |
| `/api/odds/update` | POST | Update odds data (protected) |

## Setup

### Prerequisites

- Node.js 18+
- Cloudflare account
- Wrangler CLI

### Installation

```bash
cd worker
npm install
```

### Create KV Namespaces

```bash
# Create KV namespaces
wrangler kv:namespace create ODDS_CACHE
wrangler kv:namespace create MATCHES_DATA

# Note the IDs and update wrangler.toml
```

### Update Configuration

Edit `wrangler.toml`:

1. Replace `YOUR_KV_NAMESPACE_ID` with actual IDs from above
2. Update `CORS_ORIGIN` with your frontend domain

### Development

```bash
npm run dev
```

This starts a local development server at `http://localhost:8787`

### Deployment

```bash
# Deploy to production
npm run deploy

# Deploy to dev environment
npm run deploy:dev
```

## Data Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Python Scraper │────▶│ Cloudflare Worker │◀────│  React Frontend │
│  (Local/VPS)    │     │  (Edge Network)   │     │  (Cloudflare    │
│                 │     │                   │     │   Pages)        │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │
         │                       ▼
         │              ┌──────────────────┐
         └─────────────▶│   Cloudflare KV  │
                        │   (Data Cache)   │
                        └──────────────────┘
```

1. **Python Scraper** runs locally or on a VPS
2. Scraper POSTs data to `/api/odds/update`
3. Worker stores data in **Cloudflare KV**
4. **Frontend** fetches from Worker API
5. Worker serves cached data with fast edge responses

## Pushing Data from Scraper

Use the `push_to_cloudflare.py` script:

```bash
# Set environment variables
export CLOUDFLARE_WORKER_URL=https://oddswize-api.YOUR_SUBDOMAIN.workers.dev
export CLOUDFLARE_API_KEY=your-api-key

# Run the script
python push_to_cloudflare.py
```

Or automate with cron:

```bash
# Run every 15 minutes
*/15 * * * * cd /path/to/project && python push_to_cloudflare.py
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment name | `production` |
| `CORS_ORIGIN` | Allowed CORS origin | `https://oddswize.com` |

## Scheduled Jobs

The worker runs a scheduled job every 15 minutes (configurable in `wrangler.toml`).
Currently logs execution; can be extended to fetch from external APIs.

## Security

- `/api/odds/update` requires `X-API-Key` header
- CORS restricted to configured origin
- All data validated before storage

## Monitoring

```bash
# View live logs
npm run tail
```

## Cost Estimation

Cloudflare Workers Free Tier:
- 100,000 requests/day
- 10ms CPU time per request
- 1GB KV storage

For a betting odds site, this is typically sufficient for:
- ~1,000 daily users
- ~100 odds updates/hour
