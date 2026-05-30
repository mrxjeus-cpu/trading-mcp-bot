# 🤖 Telegram RSI Monitor Bot

Bot monitoring RSI indicators and sending alerts to Telegram when trading conditions are met.

## ✨ Features

- **Real-time RSI Monitoring**: Tracks RSI on any timeframe (1H, 4H, 1D...)
- **Smart Alerts**: Sends notifications when RSI breaks key levels
- **Configurable Thresholds**: Set your own bullish/bearish RSI levels
- **Multi-Symbol Support**: Monitor BTC, ETH, or any trading pair
- **Cooldown Protection**: Prevents spam alerts with 1-hour cooldown
- **Detailed Messages**: Includes price, RSI, and trading recommendations

---

## 🚀 Setup Instructions

### Step 1: Create Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Follow instructions to name your bot
4. Save the **BOT TOKEN** (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Get Your Chat ID

1. Search for **@userinfobot** on Telegram
2. Send `/start` command
3. Save your **CHAT ID**looks like: `123456789`)

### Step 3: Configure Environment Variables

```bash
# Option A: Set environment variables
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export TELEGRAM_CHAT_ID="your_chat_id_here"

# Option B: Pass as command line arguments
--bot-token "your_bot_token" --chat-id "your_chat_id"
```

---

## 📖 Usage

### Basic Usage (Monitor BTC/USDT 1H RSI)

```bash
# Run single check
uv run python telegram_rsi_monitor.py --once

# Run continuous monitoring (checks every 5 minutes)
uv run python telegram_rsi_monitor.py
```

### Advanced Options

```bash
# Custom symbol and thresholds
uv run python telegram_rsi_monitor.py \
  --symbol ETHUSDT \
  --bullish-threshold 65 \
  --bearish-threshold 45 \
  --interval 600

# Monitor 4H timeframe
uv run python telegram_rsi_monitor.py \
  --timeframe 4h \
  --interval 1800

# Monitor with Telegram credentials
uv run python telegram_rsi_monitor.py \
  --bot-token "123456:ABC" \
  --chat-id "123456789"
```

### All Options

| Option | Description | Default |
|--------|-------------|---------|
| `--symbol` | Trading symbol | BTCUSDT |
| `--exchange` | Exchange | BINANCE |
| `--timeframe` | Timeframe | 1h |
| `--bullish-threshold` | RSI bullish trigger | 60 |
| `--bearish-threshold` | RSI bearish trigger | 50 |
| `--interval` | Check interval (seconds) | 300 |
| `--once` | Run single check | False |
| `--bot-token` | Telegram bot token | env var |
| `--chat-id` | Telegram chat ID | env var |

---

## 📊 Alert Examples

### 🚀 Bullish Alert (RSI > 60)

```
🚀 BULLISH SIGNAL ALERT 🚀

📊 Symbol: BTCUSDT (1h)
💰 Price: $73,866.92 (+0.67%)
📈 RSI: 61.50 - BULLISH
⬆️ Direction: Rising

🎯 Analysis:
• RSI crossed above 60 with rising momentum
• Previous RSI: 59.56 → Current: 61.50
• Potential LONG entry opportunity

⚡ Trading Plan:
Entry: Consider LONG position
Target: RSI 65-70 (overbought zone)
Stop Loss: Below recent support
```

### 🔻 Bearish Alert (RSI < 50)

```
🔻 BEARISH SIGNAL ALERT 🔻

📊 Symbol: BTCUSDT (1h)
💰 Price: $72,500.00 (-1.5%)
📉 RSI: 48.20 - BEARISH
⬇️ Direction: Falling

🎯 Analysis:
• RSI crossed below 50 with falling momentum
• Previous RSI: 51.00 → Current: 48.20
• Potential SHORT entry opportunity

⚡ Trading Plan:
Entry: Consider SHORT position
Target: RSI 40 (bearish zone)
Stop Loss: Above recent resistance
```

---

## 🔧 Background Service Setup

### macOS (using launchd)

Create `~/Library/LaunchAgents/com.tradingview.rsi-monitor.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tradingview.rsi-monitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/macprom1/.local/bin/uv</string>
        <string>run</string>
        <string>--directory</string>
        <string>/Users/macprom1/vuongnd/code/2026/trading/tradingview-mcp</string>
        <string>python</string>
        <string>telegram_rsi_monitor.py</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>TELEGRAM_BOT_TOKEN</key>
        <string>YOUR_BOT_TOKEN</string>
        <key>TELEGRAM_CHAT_ID</key>
        <string>YOUR_CHAT_ID</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/rsi-monitor.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/rsi-monitor-error.log</string>
</dict>
</plist>
```

Load the service:
```bash
launchctl load ~/Library/LaunchAgents/com.tradingview.rsi-monitor.plist
```

### Linux (using systemd)

Create `/etc/systemd/system/rsi-monitor.service`:

```ini
[Unit]
Description=Telegram RSI Monitor
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/tradingview-mcp
Environment="TELEGRAM_BOT_TOKEN=your_token"
Environment="TELEGRAM_CHAT_ID=your_chat_id"
ExecStart=/usr/local/bin/uv run python telegram_rsi_monitor.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable rsi-monitor
sudo systemctl start rsi-monitor
sudo systemctl status rsi-monitor
```

---

## 🔍 Troubleshooting

### "Telegram credentials not set"
- Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` environment variables
- Or pass via `--bot-token` and `--chat-id` arguments

### "Failed to get RSI data"
- TradingView API may be temporarily down
- Check your internet connection
- Try again in a few minutes

### No alerts received
- Check bot can send messages: manually send a message via Telegram API
- Verify chat ID is correct
- Check if you're in cooldown period (1 hour between alerts)

---

## 📝 Notes

- **Check interval**: Default 300 seconds (5 minutes)
- **Alert cooldown**: 1 hour between similar alerts to prevent spam
- **Supported exchanges**: BINANCE, KUCOIN, BYBIT, MEXC, and more
- **Supported timeframes**: 5m, 15m, 1h, 4h, 1D, 1W

---

## ⚠️ Disclaimer

This tool is for educational purposes only. Not financial advice. Always do your own research and consult a licensed professional before trading.
