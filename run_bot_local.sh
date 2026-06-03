#!/bin/bash
# Run TradingView Bot locally with EMA + Fibonacci confluence

# Set environment variables
export TELEGRAM_BOT_TOKEN="6201562127:AAF7ktbBYfljTvMEi0ZDXekIPHiElkaSRSM"
export TELEGRAM_CHAT_ID="-1003923788619"

echo "🚀 Starting Telegram Bot with EMA + Fibonacci confluence..."
echo "📱 Bot will send signals to group: singal mrx"
echo ""
echo "Available commands:"
echo "  /trade   - Trading pairs quick check"
echo "  /check   - Check current conditions"
echo "  /status  - Show bot status"
echo "  /config  - Configuration menu"
echo "  /mode    - Switch signal mode"
echo "  /start   - Start auto monitoring"
echo "  /stop    - Stop auto monitoring"
echo "  /info    - Bot features introduction"
echo "  /menu    - Show command menu"
echo "  /help    - Show detailed help"
echo ""
echo "Press Ctrl+C to stop the bot"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run the bot from project directory
cd /Users/macprom1/vuongnd/code/2026/trading/tradingview-mcp

# Use uv to run the bot with proper dependencies
if command -v uv &> /dev/null; then
    echo "🔧 Using uv to run bot..."
    uv run python telegram_rsi_monitor_bot_v2.py
else
    echo "🔧 Using system Python..."
    python3 telegram_rsi_monitor_bot_v2.py
fi
