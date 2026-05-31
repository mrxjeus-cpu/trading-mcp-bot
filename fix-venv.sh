#!/bin/bash
# Fix VPS venv and dependencies

cd /tmp/trading-mcp-bot

echo "🔧 Step 1: Remove old venv if exists"
rm -rf .venv

echo "🔧 Step 2: Create new venv with system python"
python3 -m venv .venv

echo "🔧 Step 3: Activate venv and install packages"
source .venv/bin/activate

echo "🔧 Step 4: Upgrade pip"
pip install --upgrade pip

echo "🔧 Step 5: Install dependencies"
pip install tradingview-ta tradingview-screener
pip install python-telegram-bot requests pandas

echo "🔧 Step 6: Test import"
python3 -c "from tradingview_ta import TA_Handler; print('✅ tradingview_ta OK')"

echo "✅ Complete! Now restart PM2:"
echo "pm2 restart tradingview-bot"
echo "pm2 logs tradingview-bot --lines 30"
