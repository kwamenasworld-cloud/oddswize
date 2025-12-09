#!/bin/bash
# OddsWize - Oracle Cloud VPS Setup Script
# Run this on a fresh Ubuntu 22.04 instance

set -e

echo "=========================================="
echo "OddsWize Scraper - Oracle Cloud Setup"
echo "=========================================="

# Update system
echo "[1/7] Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
echo "[2/7] Installing Python and dependencies..."
sudo apt install -y python3 python3-pip python3-venv git chromium-browser chromium-chromedriver

# Create app directory
echo "[3/7] Setting up application directory..."
sudo mkdir -p /opt/oddswize
sudo chown $USER:$USER /opt/oddswize
cd /opt/oddswize

# Clone repository (or copy files)
echo "[4/7] Cloning repository..."
if [ -d ".git" ]; then
    git pull
else
    git clone https://github.com/kwamenasworld-cloud/oddswize.git .
fi

# Create virtual environment
echo "[5/7] Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install requests beautifulsoup4 lxml selenium webdriver-manager

# Create environment file
echo "[6/7] Creating environment configuration..."
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# Cloudflare Worker API
CLOUDFLARE_WORKER_URL=https://oddswize-api.YOUR_SUBDOMAIN.workers.dev
CLOUDFLARE_API_KEY=your-api-key-here

# Scraper settings
SCRAPE_INTERVAL_MINUTES=15
LOG_LEVEL=INFO
EOF
    echo "Created .env file - EDIT THIS FILE with your Cloudflare credentials!"
fi

# Set up systemd service
echo "[7/7] Setting up systemd service..."
sudo cp deploy/oddswize-scraper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable oddswize-scraper

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit /opt/oddswize/.env with your Cloudflare credentials"
echo "2. Test the scraper: cd /opt/oddswize && source venv/bin/activate && python run_scanner.py"
echo "3. Start the service: sudo systemctl start oddswize-scraper"
echo "4. Check logs: sudo journalctl -u oddswize-scraper -f"
echo ""
