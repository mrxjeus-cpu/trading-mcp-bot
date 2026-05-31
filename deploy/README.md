# 🚀 TradingView MCP Bot v2 - VPS Deployment Guide

Advanced Telegram Trading Bot with Multi-Timeframe Analysis, EMA, Fibonacci, and Exchange Volume Analysis.

---

## 🎯 Bot Features v2

### Technical Indicators
- **RSI (Relative Strength Index)** - Momentum detection & breakout signals
- **EMA (20/50/100/200)** - Trend analysis & stack detection
- **Fibonacci Retracement** - Support/Resistance levels & Golden Pocket
- **Exchange Volume** - Real-time buy/sell pressure from Binance
- **Multi-Timeframe Analysis** - 1h, 4h, 1d confluence confirmation

### Signal Modes
1. **Threshold Mode (RSI-only)**
   - More signals (20-30/month)
   - RSI > 60 = Bullish, RSI < 50 = Bearish
   - Min score: 30 points

2. **Confluence Mode (Multi-indicator)**
   - Quality signals (5-10/month)
   - 3+ indicators aligned
   - RSI + EMA + Fibonacci + Exchange + MTF
   - Min score: 100 points

### Trading Signals Include
- Entry price, Take Profit (TP), Stop Loss (SL)
- 1:2 Risk-Reward ratio
- Position sizing for $1K, $5K, $10K accounts
- Multi-timeframe confirmation
- Exchange volume analysis

---

## 📋 Prerequisites

### Server Requirements
- **OS:** Ubuntu 20.04+ / Debian 11+ (Recommended: Ubuntu 22.04 LTS)
- **RAM:** 2GB+ (1GB works with swap)
- **Disk:** 10GB+ free space
- **Network:** Internet access for TradingView & Telegram APIs

### Before You Start
- ✅ SSH access to your VPS
- ✅ Root or sudo privileges
- ✅ Telegram Bot Token (from @BotFather)
- ✅ Telegram Chat ID (from @getidsbot or @userinfobot)

---

## ⚡ Quick Deploy (5 Minutes)

### Step 1: Connect to VPS
```bash
ssh root@your-vps-ip
```

### Step 2: Get Bot Token & Chat ID
```bash
# In Telegram, message @BotFather:
/newbot
# Follow instructions to get token: 123456:ABC-DEF...

# Message @getidsbot in your group:
# Get group ID: -100xxxxxxxxxx
```

### Step 3: Download & Run Deploy Script
```bash
# Download the project
cd /tmp
git clone https://github.com/atilaahmettaner/tradingview-mcp.git
cd tradingview-mcp

# Run deployment
chmod +x deploy/deploy.sh
sudo ./deploy/deploy.sh
```

### Step 4: Configure Bot
```bash
# Edit service file with your credentials
sudo nano /etc/systemd/system/tradingview-bot.service

# Replace:
# YOUR_BOT_TOKEN_HERE with your actual bot token
# YOUR_CHAT_ID_HERE with your actual chat ID (e.g., -1003923788619)
```

### Step 5: Start Bot
```bash
sudo systemctl daemon-reload
sudo systemctl enable tradingview-bot
sudo systemctl start tradingview-bot
```

### Step 6: Verify
```bash
# Check status
sudo systemctl status tradingview-bot

# View logs
sudo journalctl -u tradingview-bot -f
```

---

## 📦 Deployment Files

### `deploy/deploy.sh`
Main deployment script that:
- Updates system packages
- Installs dependencies (Python, UV, etc.)
- Sets up project directory in `/opt/tradingview-bot`
- Configures systemd service
- Sets up firewall with UFW

### `deploy/.env.example`
Environment configuration template:
```bash
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=-100xxxxxxxxxx  # Group ID format
BOT_SIGNAL_MODE=confluence
BOT_USE_MULTI_TIMEFRAME=true
```

### `deploy/update.sh`
Update script to pull latest changes from GitHub and restart service.

---

## 📱 Telegram Commands

| Command | Description |
|---------|-------------|
| `/trade` | Quick trading pairs check (BTC, ETH, SOL, TON, BNB, ADA, XRP) |
| `/check` | Check current market conditions immediately |
| `/status` | Show bot status and configuration |
| `/config` | Configuration menu |
| `/mode` | Switch signal mode (Threshold/Confluence) |
| `/start` | Start auto monitoring (every 5 min) |
| `/stop` | Stop auto monitoring |
| `/info` | Bot features introduction |
| `/menu` | Command menu |
| `/help` | Detailed help |

---

## 🔧 Manual Installation

If deploy script fails, install manually:

```bash
# 1. Install dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git curl

# 2. Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# 3. Clone project
cd /opt
sudo git clone https://github.com/atilaahmettaner/tradingview-mcp.git tradingview-bot
cd tradingview-bot

# 4. Install Python dependencies
uv pip install -r deploy/requirements.txt

# 5. Create user
sudo useradd -r -s /bin/bash -d /opt/tradingview-bot tradingbot
sudo chown -R tradingbot:tradingbot /opt/tradingview-bot

# 6. Create service
sudo nano /etc/systemd/system/tradingview-bot.service
# Paste service file content and edit credentials

# 7. Start
sudo systemctl daemon-reload
sudo systemctl enable tradingview-bot
sudo systemctl start tradingview-bot
```

---

## 🎮 Management Commands

### Service Control
```bash
# Start service
sudo systemctl start tradingview-bot

# Stop service
sudo systemctl stop tradingview-bot

# Restart service
sudo systemctl restart tradingview-bot

# Enable auto-start on boot
sudo systemctl enable tradingview-bot

# Disable auto-start
sudo systemctl disable tradingview-bot
```

### Monitoring
```bash
# Check service status
sudo systemctl status tradingview-bot

# View live logs
sudo journalctl -u tradingview-bot -f

# View last 100 lines
sudo journalctl -u tradingview-bot -n 100

# View logs since today
sudo journalctl -u tradingview-bot --since today
```

### Updates
```bash
# Run update script
cd /opt/tradingview-bot
chmod +x deploy/update.sh
sudo ./deploy/update.sh
```

---

## 🔒 Security Setup

### Firewall
```bash
# Check firewall status
sudo ufw status

# Allow SSH only
sudo ufw allow ssh

# Enable firewall
sudo ufw enable
```

### Fail2Ban (Installed by default)
```bash
# Check status
sudo systemctl status fail2ban

# View banned IPs
sudo fail2ban-client status sshd
```

### SSH Key Authentication (Recommended)
```bash
# On your local machine:
ssh-keygen -t ed25519

# Copy key to VPS
ssh-copy-id root@your-vps-ip

# Disable password login (optional)
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
sudo systemctl restart ssh
```

---

## 📊 Resource Usage

### Expected Usage on 2GB VPS
```
CPU:     1-5% average
RAM:     100-300MB
Disk:     ~500MB (project + logs)
Network:  1-5 MB/day (API calls)
```

### Monitor Resources
```bash
# Real-time monitoring
htop

# Memory usage
free -h

# Disk usage
df -h

# Process details
ps aux | grep tradingview-bot
```

---

## 🐛 Troubleshooting

### Bot won't start
```bash
# Check logs for errors
sudo journalctl -u tradingview-bot -n 50

# Verify Python dependencies
uv pip check

# Test bot manually
cd /opt/tradingview-bot
uv run python telegram_rsi_monitor_bot_v2.py
```

### Can't receive Telegram messages
```bash
# Verify bot token
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe

# Test sending message
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/sendMessage" \
  -d "chat_id=<YOUR_CHAT_ID>" \
  -d "text=Test message"
```

### High memory usage
```bash
# Check memory
free -h

# Restart service
sudo systemctl restart tradingview-bot

# If still high, consider creating swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 🔄 Backup & Restore

### Backup
```bash
# Backup entire installation
sudo tar -czf tradingview-bot-backup.tar.gz /opt/tradingview-bot

# Backup configuration only
sudo tar -czf tradingview-bot-config.tar.gz \
  /etc/systemd/system/tradingview-bot.service
```

### Restore
```bash
# Extract backup
sudo tar -xzf tradingview-bot-backup.tar.gz -C /

# Restore service
sudo systemctl daemon-reload
sudo systemctl start tradingview-bot
```

---

## 🎯 Next Steps

1. ✅ Deploy bot to VPS
2. ✅ Test with `/check` command
3. ✅ Try `/info` to learn features
4. ✅ Use `/menu` to see all commands
5. ✅ Enable auto monitoring with `/start`
6. ✅ Monitor logs for first few hours
7. ✅ Set up monitoring/alerts for VPS

---

## 📞 Support

- **Issues:** https://github.com/atilaahmettaner/tradingview-mcp/issues
- **Docs:** https://github.com/atilaahmettaner/tradingview-mcp#readme

---

## ⚠️ Disclaimer

This bot is for educational purposes only. Not financial advice. Always do your own research before trading.

---

**Deployed on:** 2GB RAM VPS
**OS:** Ubuntu 22.04 LTS
**Bot Version:** 2.0 (with MTF, EMA, Fibonacci, Exchange Volume)
