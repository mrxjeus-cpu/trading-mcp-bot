#!/bin/bash
# Telegram RSI Monitor Bot v2.0 - Launcher Script
# Advanced bot with interactive commands

# Telegram Bot Credentials
export TELEGRAM_BOT_TOKEN="7747661668:AAEDXP6EGeDw87eeNZiF5xNwGo8u8x0ah-k"
export TELEGRAM_CHAT_ID="1827491548"

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🤖 Telegram RSI Monitor Bot v2.0"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Configuration:"
echo "  Symbol: BTCUSDT"
echo "  Timeframe: 1H"
echo "  Bullish: RSI > 60"
echo "  Bearish: RSI < 50"
echo ""
echo "🚀 Starting bot..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Available Commands in Telegram:"
echo "  /check-now - Check RSI now"
echo "  /status - Bot status"
echo "  /config - Configuration menu"
echo "  /start - Start auto monitoring"
echo "  /stop - Stop auto monitoring"
echo "  /help - Show all commands"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Press Ctrl+C to stop the bot"
echo ""

# Run the bot
uv run python telegram_rsi_monitor_bot.py \
  --bot-token "$TELEGRAM_BOT_TOKEN" \
  --chat-id "$TELEGRAM_CHAT_ID"
