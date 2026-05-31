#!/bin/bash
################################################################################
# TradingView MCP Bot - VPS Deployment Script
# For Ubuntu/Debian servers with 2GB+ RAM
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🚀 TradingView MCP Bot v2 - VPS Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 System Requirements:"
echo "  • OS: Ubuntu 20.04+ / Debian 11+"
echo "  • RAM: 2GB+ (recommended)"
echo "  • Disk: 10GB+ free space"
echo ""
echo "🎯 Features:"
echo "  • Multi-Timeframe Analysis (1h, 4h, 1d)"
echo "  • EMA + Fibonacci Confluence"
echo "  • Exchange Volume Analysis (Binance)"
echo "  • Signal Mode Switching (Threshold/Confluence)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Please run as root (use sudo)${NC}"
    exit 1
fi

# Get current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}✓${NC} Project directory: $PROJECT_DIR"
echo ""

################################################################################
# Step 1: System Update
################################################################################
echo -e "${YELLOW}[1/7]${NC} Updating system packages..."
apt update && apt upgrade -y
echo -e "${GREEN}✓${NC} System updated"
echo ""

################################################################################
# Step 2: Install Dependencies
################################################################################
echo -e "${YELLOW}[2/7]${NC} Installing system dependencies..."
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    fail2ban \
    ufw \
    nginx

echo -e "${GREEN}✓${NC} Dependencies installed"
echo ""

################################################################################
# Step 3: Install UV (Python Package Manager)
################################################################################
echo -e "${YELLOW}[3/7]${NC} Installing UV package manager..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Verify UV installation
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ UV installation failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} UV installed: $(uv --version)"
echo ""

################################################################################
# Step 4: Setup Project Directory
################################################################################
echo -e "${YELLOW}[4/7]${NC} Setting up project directory..."

INSTALL_DIR="/opt/tradingview-bot"
echo -e "  Creating: $INSTALL_DIR"

mkdir -p "$INSTALL_DIR"
cp -r "$PROJECT_DIR"/* "$INSTALL_DIR/"
cd "$INSTALL_DIR"

echo -e "${GREEN}✓${NC} Project copied to $INSTALL_DIR"

# Create virtual environment
echo -e "  Creating virtual environment with UV..."
export PATH="$HOME/.local/bin:$PATH"
uv venv

echo -e "${GREEN}✓${NC} Virtual environment created"
echo ""

################################################################################
# Step 5: Install Python Dependencies
################################################################################
echo -e "${YELLOW}[5/7]${NC} Installing Python dependencies..."
export PATH="$HOME/.local/bin:$PATH"

# Install dependencies using uv
uv pip install -r "$INSTALL_DIR/deploy/requirements.txt"

echo -e "${GREEN}✓${NC} Python dependencies installed"
echo ""

################################################################################
# Step 6: Create Bot User and Service
################################################################################
echo -e "${YELLOW}[6/7]${NC} Creating bot user and service..."

# Create dedicated user
if ! id -u tradingbot &> /dev/null; then
    useradd -r -s /bin/bash -d "$INSTALL_DIR" tradingbot
    echo -e "  Created user: tradingbot"
fi

# Set ownership
chown -R tradingbot:tradingbot "$INSTALL_DIR"

# Create PM2 ecosystem file
cat > "$INSTALL_DIR/ecosystem.config.js" << 'EOF'
module.exports = {
  apps: [{
    name: "tradingview-bot",
    script: "telegram_rsi_monitor_bot_v2.py",
    interpreter: "python3",
    interpreter_args: "-m",
    cwd: "/opt/tradingview-bot",
    env: {
      TELEGRAM_BOT_TOKEN: "YOUR_BOT_TOKEN_HERE",
      TELEGRAM_CHAT_ID: "YOUR_CHAT_ID_HERE",
      PYTHONPATH: "/opt/tradingview-bot:/opt/tradingview-bot/src"
    },
    error_file: "/var/log/tradingview-bot-error.log",
    out_file: "/var/log/tradingview-bot-out.log",
    log_date_format: "YYYY-MM-DD HH:mm:ss",
    merge_logs: true,
    autorestart: true,
    max_restarts: 10,
    min_uptime: "10s",
    max_memory_restart: "500M",
    restart_delay: 4000
  }]
};
EOF

# Create systemd service (alternative to PM2)
cat > /etc/systemd/system/tradingview-bot.service << 'EOF'
[Unit]
Description=TradingView RSI Monitor Bot v2
After=network.target

[Service]
Type=simple
User=tradingbot
Group=tradingbot
WorkingDirectory=/opt/tradingview-bot
Environment="PATH=/root/.local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/opt/tradingview-bot:/opt/tradingview-bot/src"
Environment="TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE"
Environment="TELEGRAM_CHAT_ID=YOUR_CHAT_ID_HERE"
ExecStart=/root/.local/bin/uv run --python /opt/tradingview-bot/.venv/bin/python telegram_rsi_monitor_bot_v2.py
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=tradingview-bot

# Security
NoNewPrivileges=true
PrivateTmp=true
ReadWritePaths=/opt/tradingview-bot

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓${NC} Systemd service created"
echo ""

################################################################################
# Step 7: Configure Firewall
################################################################################
echo -e "${YELLOW}[7/7]${NC} Configuring firewall..."

# Configure UFW
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo -e "${GREEN}✓${NC} Firewall configured"
echo ""

################################################################################
# Complete
################################################################################
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ DEPLOYMENT COMPLETE!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 NEXT STEPS:"
echo ""
echo "1. ⚙️  Edit configuration file:"
echo "   sudo nano /etc/systemd/system/tradingview-bot.service"
echo ""
echo "2. 🔑 Replace YOUR_BOT_TOKEN_HERE and YOUR_CHAT_ID_HERE:"
echo "   • Get Bot Token from @BotFather"
echo "   • Get Chat ID from @getidsbot (group: -100xxxxxxxxxx)"
echo ""
echo "3. 🔄 Reload systemd and start service:"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable tradingview-bot"
echo "   sudo systemctl start tradingview-bot"
echo ""
echo "4. 📊 Check service status:"
echo "   sudo systemctl status tradingview-bot"
echo ""
echo "5. 📝 View logs:"
echo "   sudo journalctl -u tradingview-bot -f"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📱 Available Telegram Commands:"
echo "  /trade  - Trading pairs quick check"
echo "  /check  - Check current conditions"
echo "  /status - Show bot status"
echo "  /config - Configuration menu"
echo "  /mode   - Switch signal mode"
echo "  /start  - Start auto monitoring"
echo "  /stop   - Stop auto monitoring"
echo "  /info   - Bot features introduction"
echo "  /menu   - Command menu"
echo "  /help   - Detailed help"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
