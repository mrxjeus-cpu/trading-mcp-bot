#!/bin/bash
################################################################################
# TradingView Bot - Update Script
# Updates the bot to the latest version
################################################################################

set -e

INSTALL_DIR="/opt/tradingview-bot"
SERVICE_NAME="tradingview-bot"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🔄 TradingView Bot - Update"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Stop service
echo "⏹️  Stopping service..."
systemctl stop $SERVICE_NAME

# Backup current version
echo "💾 Creating backup..."
BACKUP_DIR="$INSTALL_DIR.backup.$(date +%Y%m%d_%H%M%S)"
cp -r "$INSTALL_DIR" "$BACKUP_DIR"

# Pull latest changes (if git repo)
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "📥 Pulling latest changes..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "⚠️  Not a git repository, skipping update"
fi

# Update dependencies
echo "📦 Updating dependencies..."
cd "$INSTALL_DIR"
export PATH="$HOME/.local/bin:$PATH"
uv pip install -r deploy/requirements.txt --upgrade

# Set ownership
echo "🔒 Setting ownership..."
chown -R tradingbot:tradingbot "$INSTALL_DIR"

# Start service
echo "▶️  Starting service..."
systemctl start $SERVICE_NAME

# Check status
echo "📊 Service status:"
systemctl status $SERVICE_NAME --no-pager

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Update complete!"
echo ""
echo "💡 View logs: journalctl -u $SERVICE_NAME -f"
echo "💡 Backup saved to: $BACKUP_DIR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
