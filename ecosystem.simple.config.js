module.exports = {
  apps: [{
    name: 'tradingview-bot',
    script: 'telegram_rsi_monitor_bot.py',
    interpreter: 'uv',
    interpreter_args: 'run',
    cwd: '/opt/tradingview-bot',

    // Environment variables
    env: {
      TELEGRAM_BOT_TOKEN: '6201562127:AAF7ktbBYfljTvMEi0ZDXekIPHiElkaSRSM',
      TELEGRAM_CHAT_ID: '1827491548',
      PATH: '/root/.local/bin:/usr/bin:/bin'
    },

    // Auto-restart
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',

    // Logging
    log_file: '/opt/tradingview-bot/logs/pm2.log',
    error_file: '/opt/tradingview-bot/logs/pm2-error.log',
    out_file: '/opt/tradingview-bot/logs/pm2-out.log',
    merge_logs: true,

    // Process management
    min_uptime: '10s',
    restart_delay: 4000
  }]
};
