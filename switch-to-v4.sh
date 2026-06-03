#!/bin/bash
# Switch from v2 to v4 on VPS
# This script stops v2, updates code, and starts v4

set -e

VPS_HOST="${VPS_HOST:-root@your-vps-ip}"
VPS_PATH="/tmp/trading-mcp-bot"
OLD_BOT="tradingview-bot"
NEW_BOT="tradingview-bot-v4"

echo "🔄 Switching from v2 to v4..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Stop v2 bot
echo "🛑 Stopping Bot v2..."
ssh $VPS_HOST "cd $VPS_PATH && pm2 stop $OLD_BOT || pm2 delete $OLD_BOT || true"

# 2. Pull latest code
echo "📥 Pulling latest code..."
ssh $VPS_HOST "cd $VPS_PATH && git pull origin main"

# 3. Backup old config
echo "💾 Backing up v2 config..."
ssh $VPS_HOST "cd $VPS_PATH && cp ecosystem.config.js ecosystem.config.v2.backup || true"

# 4. Copy v4 config
echo "📝 Installing v4 config..."
scp ecosystem.config.v4.js $VPS_HOST:$VPS_PATH/ecosystem.config.js

# 5. Start v4 bot
echo "▶️  Starting Bot v4..."
ssh $VPS_HOST "cd $VPS_PATH && pm2 start ecosystem.config.js --name $NEW_BOT"

# 6. Save PM2 config
echo "💾 Saving PM2 configuration..."
ssh $VPS_HOST "pm2 save"

# 7. Delete v2 from PM2
echo "🗑️  Removing v2 from PM2..."
ssh $VPS_HOST "pm2 delete $OLD_BOT || true"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Successfully switched to Bot v4!"
echo ""
echo "📊 Current Status:"
ssh $VPS_HOST "pm2 status"

echo ""
echo "🎯 Key Changes v2 → v4:"
echo "• v2: RSI Breakout (5min interval)"
echo "• v4: EMA Alignment (30min interval)"
echo "• v2: Multiple indicators"
echo "• v4: EMA-focused trend following"
echo ""
echo "📝 Use /trend command in Telegram to select mode!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
