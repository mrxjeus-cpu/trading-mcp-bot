# 🚀 TradingView MCP Bot - VPS Deployment Guide

Deploy your TradingView RSI Monitor Bot on a 2GB RAM VPS.

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
- ✅ Telegram Chat ID (from @userinfobot)

---

## ⚡ Quick Deploy (5 Minutes)

### Step 1: Connect to VPS
```bash
ssh root@your-vps-ip
```

### Step 2: Download & Run Deploy Script
```bash
# Download the project
cd /tmp
git clone https://github.com/atilaahmettaner/tradingview-mcp.git
cd tradingview-mcp

# Run deployment
chmod +x deploy/deploy.sh
sudo ./deploy/deploy.sh
```

### Step 3: Configure Bot
```bash
# Edit service file with your credentials
sudo nano /etc/systemd/system/tradingview-bot.service

# Replace:
# YOUR_BOT_TOKEN_HERE with your actual bot token
# YOUR_CHAT_ID_HERE with your actual chat ID
```

### Step 4: Start Bot
```bash
sudo systemctl daemon-reload
sudo systemctl enable tradingview-bot
sudo systemctl start tradingview-bot
```

### Step 5: Verify
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
- Sets up project directory
- Configures systemd service
- Sets up firewall

### `deploy/.env.example`
Environment configuration template:
```bash
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
BOT_SYMBOL=BTCUSDT
BOT_TIMEFRAME=1h
```

### `deploy/tradingview-bot.service`
Systemd service file for running bot as background service.

### `deploy/update.sh`
Update script to pull latest changes and restart service.

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
sudo cp deploy/tradingview-bot.service /etc/systemd/system/
sudo nano /etc/systemd/system/tradingview-bot.service  # Edit credentials

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
uv run python telegram_rsi_monitor_bot.py --help
```

### Can't receive Telegram messages
```bash
# Verify bot token and chat ID
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

### Service crashes frequently
```bash
# Check logs
sudo journalctl -u tradingview-bot -n 100

# Increase restart delay (edit service file)
RestartSec=30

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart tradingview-bot
```

---

## 🔄 Backup & Restore

### Backup
```bash
# Backup entire installation
sudo tar -czf tradingview-bot-backup.tar.gz /opt/tradingview-bot

# Backup configuration only
sudo tar -czf tradingview-bot-config.tar.gz \
  /etc/systemd/system/tradingview-bot.service \
  /opt/tradingview-bot/.env
```

### Restore
```bash
# Extract backup
sudo tar -xzf tradingview-bot-backup.tar.gz -C /

# Restore service
sudo cp tradingview-bot-config.tar.gz /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start tradingview-bot
```

---

## 📱 Telegram Commands

Once deployed, use these commands in Telegram:

| Command | Description |
|---------|-------------|
| `/check` | Check RSI conditions now |
| `/status` | Show bot status |
| `/config` | Configuration menu |
| `/start` | Start auto monitoring |
| `/stop` | Stop auto monitoring |
| `/help` | Show all commands |

---

## 🎯 Next Steps

1. ✅ Deploy bot to VPS
2. ✅ Test with `/check` command
3. ✅ Enable auto monitoring with `/start`
4. ✅ Monitor logs for first few hours
5. ✅ Set up monitoring/alerts for VPS

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
**Bot Version:** 2.0
