# OddsWize Deployment Guide

Complete guide to deploy OddsWize so it runs 24/7 without your PC.

## Architecture Overview

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│   Oracle Cloud VPS  │     │  Cloudflare Workers  │     │  Cloudflare Pages   │
│   (Free Forever)    │────▶│     (Free Tier)      │◀────│    (Free Tier)      │
│                     │     │                      │     │                     │
│  - Python Scraper   │     │  - API Endpoints     │     │  - React Frontend   │
│  - Runs every 15min │     │  - KV Data Cache     │     │  - Static Hosting   │
│  - Auto-restarts    │     │  - Edge Responses    │     │  - Global CDN       │
└─────────────────────┘     └──────────────────────┘     └─────────────────────┘
```

## Cost: $0/month (All Free Tiers)

---

## Step 1: Cloudflare Account Setup

### 1.1 Create Cloudflare Account
1. Go to https://dash.cloudflare.com/sign-up
2. Create a free account
3. Note your **Account ID** (Settings → Account)

### 1.2 Create API Token
1. Go to **My Profile** → **API Tokens**
2. Click **Create Token**
3. Use **Edit Cloudflare Workers** template
4. Add **Cloudflare Pages: Edit** permission
5. Save the token securely

---

## Step 2: Deploy Cloudflare Worker (API)

### 2.1 Install Wrangler CLI
```bash
npm install -g wrangler
wrangler login
```

### 2.2 Create KV Namespaces
```bash
cd worker
npm install

# Create namespaces
wrangler kv:namespace create ODDS_CACHE
wrangler kv:namespace create MATCHES_DATA
```

Copy the IDs from the output and update `worker/wrangler.toml`:
```toml
[[kv_namespaces]]
binding = "ODDS_CACHE"
id = "YOUR_ACTUAL_ID_HERE"

[[kv_namespaces]]
binding = "MATCHES_DATA"
id = "YOUR_ACTUAL_ID_HERE"
```

### 2.3 Deploy Worker
```bash
wrangler deploy
```

Note the Worker URL (e.g., `https://oddswize-api.YOUR_SUBDOMAIN.workers.dev`)

---

## Step 3: Deploy Frontend to Cloudflare Pages

### Option A: Via Cloudflare Dashboard (Easiest)
1. Go to https://dash.cloudflare.com → **Workers & Pages**
2. Click **Create application** → **Pages** → **Connect to Git**
3. Select your GitHub repo
4. Configure build:
   - **Build command**: `cd frontend && npm install && npm run build`
   - **Build output directory**: `frontend/dist`
   - **Environment variable**: `VITE_CLOUDFLARE_API_URL` = your Worker URL
   - (Optional) **Environment variable**: `PING_SITEMAP=1` to auto-ping search engines after build
   - (Optional) **Environment variable**: `SITEMAP_URL=https://oddswize.com/sitemap.xml`
5. Click **Save and Deploy**

### Option B: Via GitHub Actions (Automatic)
1. Go to your GitHub repo → **Settings** → **Secrets**
2. Add these secrets:
   - `CLOUDFLARE_API_TOKEN` - Your API token
   - `CLOUDFLARE_ACCOUNT_ID` - Your account ID
   - `CLOUDFLARE_API_URL` - Your Worker URL
3. Push to master - it auto-deploys

---

## Step 4: Oracle Cloud VPS (Scraper)

### 4.1 Create Oracle Cloud Account
1. Go to https://www.oracle.com/cloud/free/
2. Sign up for **Always Free** tier
3. Complete verification (credit card for verification only, won't be charged)

### 4.2 Create VM Instance
1. Go to **Compute** → **Instances** → **Create Instance**
2. Choose:
   - **Shape**: VM.Standard.E2.1.Micro (Always Free)
   - **Image**: Ubuntu 22.04
   - **Boot volume**: 50GB (free)
3. Download the SSH key
4. Click **Create**

### 4.3 Configure Firewall
1. Go to **Networking** → **Virtual Cloud Networks**
2. Click your VCN → **Security Lists** → **Default Security List**
3. Add **Ingress Rule**:
   - Source: `0.0.0.0/0`
   - Port: `22` (SSH - should be there already)

### 4.4 Connect to VM
```bash
# On Windows (PowerShell)
ssh -i path/to/your-key.key ubuntu@YOUR_VM_IP

# On Mac/Linux
chmod 400 path/to/your-key.key
ssh -i path/to/your-key.key ubuntu@YOUR_VM_IP
```

### 4.5 Run Setup Script
```bash
# On the Oracle VM
git clone https://github.com/kwamenasworld-cloud/oddswize.git
cd oddswize
chmod +x deploy/setup-oracle.sh
./deploy/setup-oracle.sh
```

### 4.6 Configure Environment
```bash
nano /opt/oddswize/.env
```

Update with your Cloudflare details:
```
CLOUDFLARE_WORKER_URL=https://oddswize-api.YOUR_SUBDOMAIN.workers.dev
CLOUDFLARE_API_KEY=your-api-key-here
SCRAPE_INTERVAL_MINUTES=15
```

### 4.7 Start the Scraper
```bash
# Test first
cd /opt/oddswize
source venv/bin/activate
python auto_scanner.py --once

# If successful, start the service
sudo systemctl start oddswize-scraper
sudo systemctl status oddswize-scraper
```

### 4.8 Monitor Logs
```bash
# View live logs
sudo journalctl -u oddswize-scraper -f

# View scanner log file
tail -f /opt/oddswize/scanner.log
```

---

## Step 5: GitHub Secrets Setup

Add these secrets to your GitHub repo for CI/CD:

| Secret Name | Description |
|-------------|-------------|
| `CLOUDFLARE_API_TOKEN` | Cloudflare API token |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account ID |
| `CLOUDFLARE_API_URL` | Worker URL |

---

## Verification Checklist

- [ ] Cloudflare Worker deployed and responding at `/health`
- [ ] KV namespaces created and bound
- [ ] Frontend deployed to Cloudflare Pages
- [ ] Oracle VM running and accessible via SSH
- [ ] Scraper service running (`systemctl status oddswize-scraper`)
- [ ] Data flowing from scraper to Worker to frontend

---

## Troubleshooting

### Worker returns empty data
- Check KV namespaces are correctly configured
- Verify scraper is pushing data: `journalctl -u oddswize-scraper`

### Frontend shows "API unavailable"
- Check CORS settings in `worker/wrangler.toml`
- Verify `VITE_CLOUDFLARE_API_URL` is set correctly

### Scraper failing on Oracle
```bash
# Check service status
sudo systemctl status oddswize-scraper

# View detailed logs
sudo journalctl -u oddswize-scraper -n 100

# Restart service
sudo systemctl restart oddswize-scraper
```

### Oracle VM not accessible
- Check Security List ingress rules
- Verify VM is running in Oracle Console
- Check if IP changed (use reserved public IP)

---

## Maintenance

### Update Scraper Code
```bash
ssh ubuntu@YOUR_VM_IP
cd /opt/oddswize
git pull
sudo systemctl restart oddswize-scraper
```

### Update Worker
```bash
cd worker
wrangler deploy
```

### Update Frontend
Just push to GitHub - it auto-deploys via Cloudflare Pages.

---

## Free Tier Limits

| Service | Limit | Typical Usage |
|---------|-------|---------------|
| Oracle VM | 2 instances, 1GB RAM each | 1 instance |
| Cloudflare Workers | 100k requests/day | ~5k/day |
| Cloudflare KV | 100k reads, 1k writes/day | ~1k reads, 96 writes |
| Cloudflare Pages | Unlimited | N/A |

All well within free tier for a betting odds site!
