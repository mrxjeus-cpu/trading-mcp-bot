# 🚀 PM2 Deployment Guide

## What is PM2?

PM2 is a production process manager for Node.js applications, but it can manage **any application type** including Python scripts, with features like:
- Automatic restart on crash
- Log management
- Cluster mode
- Monitoring dashboard

---

## ✅ PM2 vs Systemd

| Feature | PM2 | Systemd |
|---------|-----|----------|
| Auto-restart | ✅ | ✅ |
| Log rotation | ✅ Built-in | ❌ Need setup |
| Monitoring UI | ✅ Web dashboard | ❌ CLI only |
| Cluster mode | ✅ | ❌ |
| Memory limit | ✅ | ❌ |
| Resource monitoring | ✅ | ❌ |

---

## 🚀 Quick Deploy with PM2

### Option 1: Use PM2 Deploy Script

```bash
ssh root@your-vps-ip

cd /tmp
git clone https://github.com/mrxjeus-cpu/trading-mcp-bot.git
cd trading-mcp-bot
chmod +x deploy/deploy-pm2.sh
sudo ./deploy/deploy-pm2.sh
```

### Option 2: Manual PM2 Setup

```bash
# 1. Install PM2
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo bash -
sudo apt install -y nodejs
sudo npm install -g pm2

# 2. Setup project
cd /opt/tradingview-bot
sudo uv venv
sudo uv pip install -r deploy/requirements.txt

# 3. Start with PM2
sudo pm2 start ecosystem.config.js
sudo pm2 save
sudo pm2 startup
```

---

## 📊 PM2 Configuration

### ecosystem.config.js

```javascript
{
  apps: [{
    name: 'tradingview-bot',
    script: 'telegram_rsi_monitor_bot.py',
    interpreter: 'python3',

    env: {
      TELEGRAM_BOT_TOKEN: 'your_token',
      TELEGRAM_CHAT_ID: 'your_chat_id'
    },

    // Auto-restart on crash
    autorestart: true,
    max_memory_restart: '500M',

    // Logging
    log_file: '/opt/tradingview-bot/logs/app.log',
    error_file: '/opt/tradingview-bot/logs/error.log',

    // Process management
    restart_delay: 4000
  }]
}
```

---

## 🎮 PM2 Commands

### Basic Management
```bash
# Start bot
pm2 start ecosystem.config.js

# Stop bot
pm2 stop tradingview-bot

# Restart bot
pm2 restart tradingview-bot

# Delete from PM2
pm2 delete tradingview-bot

# List all processes
pm2 list
```

### Monitoring
```bash
# Real-time logs
pm2 logs tradingview-bot -f

# Clear logs
pm2 flush

# Monitor dashboard
pm2 monit
# Open: http://your-vps-ip:9615
```

### Process Information
```bash
# Show details
pm2 show tradingview-bot

# Resource usage
pm2 ls --monitor

# Description
pm2 describe tradingview-bot
```

### Startup & Persistence
```bash
# Save process list
pm2 save

# Generate startup script
pm2 startup

# Update startup config
pm2 resurrect
```

---

## 🔄 PM2 Log Rotation

PM2 includes built-in log rotation:

```bash
# Install PM2 logrotate module
pm2 install pm2-logrotate

# Configure (optional)
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 7
pm2 set pm2-logrotate:compress true
```

---

## 🔍 Troubleshooting

### Bot won't start
```bash
# Check PM2 logs
pm2 logs tradingview-bot --lines 50

# Check Python path
which python3
which uv

# Verify dependencies
uv pip check
```

### High memory usage
```bash
# Check memory
pm2 ls --monitor

# Restart to free memory
pm2 restart tradingview-bot

# Memory limit is set to 500M in config
```

### PM2 not starting on boot
```bash
# Check if PM2 service is enabled
systemctl status pm2-root

# Enable PM2 startup
pm2 startup systemd

# Verify startup script
cat /etc/systemd/system/pm2-root.service
```

---

## 📈 PM2 Monitoring Dashboard

Access the PM2 monitoring dashboard:

```bash
# On VPS
pm2 web

# Or access directly
http://your-vps-ip:9615
```

Features:
- Real-time CPU/RAM monitoring
- Log viewer
- Process management
- Metrics dashboard

---

## 🆚 PM2 vs Systemd - Quick Comparison

### Use PM2 if you want:
- ✅ Web-based monitoring
- ✅ Built-in log rotation
- ✅ Easy process management
- ✅ Cluster mode (future)
- ✅ Resource limits

### Use Systemd if you want:
- ✅ Native Linux integration
- ✅ No extra dependencies
- ✅ More control over service
- ✅ Standard Linux way

---

## 🎯 Recommendation

**For this bot, PM2 is recommended because:**
1. Easy monitoring and debugging
2. Built-in log management
3. Memory limit protection (500M)
4. Web dashboard for quick status check
5. Simple restart commands

---

## 📝 Switch from Systemd to PM2

```bash
# 1. Stop systemd service
sudo systemctl stop tradingview-bot
sudo systemctl disable tradingview-bot

# 2. Start with PM2
cd /opt/tradingview-bot
sudo pm2 start ecosystem.config.js
sudo pm2 save
sudo pm2 startup

# 3. Verify
sudo pm2 list
```

---

**PM2 makes managing the bot much easier with its monitoring and auto-restart features!**