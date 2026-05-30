#!/bin/bash
# Telegram RSI Monitor - Launcher Script
# Usage: ./start_telegram_monitor.sh [once|continuous]

# Telegram Bot Credentials
export TELEGRAM_BOT_TOKEN="7747661668:AAEDXP6EGeDw87eeNZiF5xNwGo8u8x0ah-k"
export TELEGRAM_CHAT_ID="1827491548"

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Mode selection
MODE="${1:-continuous}"

case $MODE in
    once)
        echo "🔍 Running single RSI check..."
        uv run python telegram_rsi_monitor.py --once
        ;;
    continuous|*)
        echo "🚀 Starting continuous RSI monitoring..."
        echo "Press Ctrl+C to stop"
        echo ""
        uv run python telegram_rsi_monitor.py
        ;;
esac
