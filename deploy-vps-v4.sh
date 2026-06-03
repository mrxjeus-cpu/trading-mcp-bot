#!/bin/bash
# Deploy Trading Bot v4 to VPS
# EMA Alignment Strategy - 30min monitoring interval

set -e

VPS_HOST="${VPS_HOST:-root@your-vps-ip}"
VPS_PATH="/tmp/trading-mcp-bot"
BOT_NAME="tradingview-bot-v4"

echo "🚀 Deploying Bot v4 to VPS..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Stop current bot
echo "🛑 Stopping current bot..."
ssh $VPS_HOST "cd $VPS_PATH && pm2 delete $BOT_NAME || true"

# 2. Pull latest code
echo "📥 Pulling latest code from GitHub..."
ssh $VPS_HOST "cd $VPS_PATH && git pull origin main"

# 3. Copy v4 config
echo "📝 Copying v4 PM2 config..."
scp ecosystem.config.v4.js $VPS_HOST:$VPS_PATH/ecosystem.config.js

# 4. Start bot v4
echo "▶️  Starting Bot v4..."
ssh $VPS_HOST "cd $VPS_PATH && pm2 start ecosystem.config.js --name $BOT_NAME"

# 5. Save PM2 config
echo "💾 Saving PM2 configuration..."
ssh $VPS_HOST "pm2 save"

# 6. Show status
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Bot v4 Deployed Successfully!"
echo ""
echo "📊 Current Status:"
ssh $VPS_HOST "pm2 status $BOT_NAME"

echo ""
echo "📋 Available Commands:"
echo "• pm2 logs $BOT_NAME --lines 50     - View logs"
echo "• pm2 restart $BOT_NAME             - Restart bot"
echo "• pm2 stop $BOT_NAME                - Stop bot"
echo "• pm2 delete $BOT_NAME              - Delete bot"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 Bot v4 Features:"
echo "• EMA Alignment Strategy (20/50/100/200)"
echo "• 30-minute monitoring interval"
echo "• UPTREND/DOWNTREND/AUTO modes"
echo "• /trend command to switch modes"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
