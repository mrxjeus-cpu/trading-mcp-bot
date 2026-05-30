#!/bin/bash
################################################################################
# TradingView MCP Bot - VPS Deployment with PM2
# For Ubuntu/Debian servers with 2GB+ RAM
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🚀 TradingView Bot - PM2 Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Please run as root${NC}"
    exit 1
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

################################################################################
# Step 1: System Update
################################################################################
echo -e "${YELLOW}[1/8]${NC} Updating system..."
apt update && apt upgrade -y
echo -e "${GREEN}✓${NC} Updated"
echo ""

################################################################################
# Step 2: Install Node.js & PM2
################################################################################
echo -e "${YELLOW}[2/8]${NC} Installing Node.js & PM2..."

# Install Node.js 18.x
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt install -y nodejs

# Install PM2 globally
npm install -g pm2

# Install PM2 logrotate
pm2 install pm2-logrotate

echo -e "${GREEN}✓${NC} PM2 installed: $(pm2 --version)"
echo ""

################################################################################
# Step 3: Install Python & UV
################################################################################
echo -e "${YELLOW}[3/8]${NC} Installing Python & UV..."
apt install -y python3 python3-venv python3-pip git curl

curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

echo -e "${GREEN}✓${NC} Python & UV installed"
echo ""

################################################################################
# Step 4: Setup Project
################################################################################
echo -e "${YELLOW}[4/8]${NC} Setting up project..."

INSTALL_DIR="/opt/tradingview-bot"
mkdir -p "$INSTALL_DIR"
cp -r "$PROJECT_DIR"/* "$INSTALL_DIR/"
cd "$INSTALL_DIR"

# Create virtual environment
echo "  Creating virtual environment..."
export PATH="$HOME/.local/bin:$PATH"
uv venv

# Install dependencies
echo "  Installing dependencies..."
uv pip install -r "$INSTALL_DIR/deploy/requirements.txt" || uv pip install \
    mcp[cli] requests tradingview-screener tradingview-ta \
    feedparser python-telegram-bot pandas

echo -e "${GREEN}✓${NC} Project setup complete"
echo ""

################################################################################
# Step 5: Setup Logs Directory
################################################################################
echo -e "${YELLOW}[5/8]${NC} Setting up logs..."
mkdir -p "$INSTALL_DIR/logs"
chown -R tradingbot:tradingbot "$INSTALL_DIR/logs" 2>/dev/null || true
echo -e "${GREEN}✓${NC} Logs directory created"
echo ""

################################################################################
# Step 6: Configure PM2
################################################################################
echo -e "${YELLOW}[6/8]${NC} Configuring PM2..."

# Copy ecosystem config
cp "$INSTALL_DIR/ecosystem.config.js" "$INSTALL_DIR/ecosystem.pm2.config.js"

echo -e "${GREEN}✓${NC} PM2 configured"
echo ""

################################################################################
# Step 7: Create Bot User
################################################################################
echo -e "${YELLOW}[7/8]${NC} Creating bot user..."

if ! id -u tradingbot &> /dev/null; then
    useradd -r -s /bin/bash -d "$INSTALL_DIR" tradingbot
    echo "  Created user: tradingbot"
fi

chown -R tradingbot:tradingbot "$INSTALL_DIR"
echo -e "${GREEN}✓${NC} User created"
echo ""

################################################################################
# Step 8: Start with PM2
################################################################################
echo -e "${YELLOW}[8/8]${NC} Starting bot with PM2..."

cd "$INSTALL_DIR"

# Stop existing if running
pm2 stop tradingview-bot 2>/dev/null || true
pm2 delete tradingview-bot 2>/dev/null || true

# Start with PM2
pm2 start ecosystem.config.js

# Save PM2 process list
pm2 save

# Setup PM2 startup script
pm2 startup systemd -u tradingbot --hp /opt/tradingview-bot --write /etc/systemd/system/pm2-tradingbot.service
systemctl enable pm2-tradingbot

echo -e "${GREEN}✓${NC} Bot started with PM2"
echo ""

################################################################################
# Complete
################################################################################
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ DEPLOYMENT COMPLETE!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 PM2 Commands:"
echo "  pm2 list              - List all processes"
echo "  pm2 logs tradingview-bot -f        - View logs"
echo "  pm2 restart tradingview-bot       - Restart bot"
echo "  pm2 stop tradingview-bot          - Stop bot"
echo "  pm2 monit            - Monitor dashboard"
echo ""
echo "🌐 PM2 Monitor: http://localhost:9615"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
