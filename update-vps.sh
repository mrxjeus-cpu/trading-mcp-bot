#!/bin/bash
################################################################################
# Update TradingView Bot v2 on VPS
# Run this on your VPS to update to the latest version
################################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🔄 TradingView Bot v2 - Update Script"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Installation directory
BOT_DIR="/tmp/trading-mcp-bot"

echo -e "${YELLOW}[1/6]${NC} Stopping PM2 bot..."
pm2 stop tradingview-bot || echo "Bot not running"

echo -e "${YELLOW}[2/6]${NC} Pulling latest code from GitHub..."
cd "$BOT_DIR"
git pull origin main

echo -e "${YELLOW}[3/6]${NC} Checking for new files..."
ls -la telegram_rsi_monitor_bot_v2.py
ls -la src/tradingview_mcp/core/services/fibonacci_service.py
ls -la src/tradingview_mcp/core/services/exchange_volume_service.py

echo -e "${YELLOW}[4/6]${NC} Copying ecosystem config..."
cp ecosystem.config.js "$BOT_DIR/ecosystem.config.js"

echo -e "${YELLOW}[5/6]${NC} Restarting PM2..."
cd "$BOT_DIR"
pm2 restart tradingview-bot

echo -e "${YELLOW}[6/6]${NC} Checking status..."
sleep 3
pm2 status tradingview-bot
pm2 logs tradingview-bot --lines 20 --nostream

echo ""
echo -e "${GREEN}✅ Update Complete!${NC}"
echo ""
echo "Check logs with:"
echo "  pm2 logs tradingview-bot"
echo ""
echo "Check status with:"
echo "  pm2 status"
echo ""
