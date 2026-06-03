#!/bin/bash
# Run Trading Bot v4 Locally
# EMA Alignment Strategy - 4H timeframe, 30min monitoring

# Set environment variables
export TELEGRAM_BOT_TOKEN="6201562127:AAF7ktbBYfljTvMEi0ZDXekIPHiElkaSRSM"
export TELEGRAM_CHAT_ID="-1003923788619"

# Bot v4 Configuration
export TREND_MODE="auto"  # Options: uptrend, downtrend, auto
export EMA_PROXIMITY_PCT="0.8"  # EMA touch threshold (%)

echo "🚀 Starting Trading Bot v4 - EMA Alignment Strategy"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Configuration:"
echo "  • Timeframe: 4H"
echo "  • Check Interval: 30 minutes"
echo "  • Trend Mode: $TREND_MODE"
echo "  • EMA Proximity: $EMA_PROXIMITY_PCT%"
echo "  • Chat ID: $TELEGRAM_CHAT_ID"
echo ""
echo "🎯 Available Setups:"
echo "  UPTREND: Pullback EMA20, EMA50, Golden Cross, Ribbon Expansion"
echo "  DOWNTREND: Pullback EMA20, EMA50, Death Cross, Ribbon Expansion"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Telegram Commands:"
echo "  /trend  - Select trend mode (UPTREND/DOWNTREND/AUTO)"
echo "  /check  - Check current conditions"
echo "  /start  - Start 30min monitoring"
echo "  /status - Show bot status"
echo "  /help   - Show all commands"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Press Ctrl+C to stop the bot"
echo ""

# Run the bot from project directory
cd /Users/macprom1/vuongnd/code/2026/trading/tradingview-mcp

# Use uv to run the bot with proper dependencies
if command -v uv &> /dev/null; then
    echo "🔧 Using uv to run bot v4..."
    uv run python telegram_rsi_monitor_bot_v4.py
else
    echo "🔧 Using system Python..."
    python3 telegram_rsi_monitor_bot_v4.py
fi
