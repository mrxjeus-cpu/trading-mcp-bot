# ⚡ Quick Deploy Guide - 2GB VPS

## 🚀 5-Minute Deployment

### 1. SSH to VPS
```bash
ssh root@your-vps-ip
```

### 2. One-Command Deploy
```bash
cd /tmp && rm -rf tradingview-mcp && \
git clone https://github.com/atilaahmettaner/tradingview-mcp.git && \
cd tradingview-mcp && \
chmod +x deploy/deploy.sh && \
./deploy/deploy.sh
```

### 3. Configure Bot
```bash
# Edit service file
sudo nano /etc/systemd/system/tradingview-bot.service

# Update these lines:
Environment="TELEGRAM_BOT_TOKEN=6201562127:AAF7ktbBYfljTvMEi0ZDXekIPHiElkaSRSM"
Environment="TELEGRAM_CHAT_ID=1827491548"
```

### 4. Start Bot
```bash
sudo systemctl daemon-reload
sudo systemctl enable tradingview-bot
sudo systemctl start tradingview-bot
```

### 5. Verify
```bash
sudo systemctl status tradingview-bot
```

---

## ✅ Done!

Test in Telegram: Send `/check` command

---

## 📁 Files Created

- `deploy/deploy.sh` - Main deployment script
- `deploy/update.sh` - Update script
- `deploy/.env.example` - Config template
- `deploy/tradingview-bot.service` - Systemd service
- `deploy/README.md` - Full documentation
- `deploy/requirements.txt` - Python dependencies

---

## 🎮 Management

```bash
# Status
sudo systemctl status tradingview-bot

# Logs
sudo journalctl -u tradingview-bot -f

# Restart
sudo systemctl restart tradingview-bot

# Update
cd /opt/tradingview-bot && sudo ./deploy/update.sh
```
