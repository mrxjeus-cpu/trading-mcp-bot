module.exports = {
  apps: [{
    name: 'tradingview-bot',
    script: 'telegram_rsi_monitor_bot.py',
    interpreter: 'uv',
    interpreter_args: 'run',
    cwd: '/tmp/trading-mcp-bot',

    // Environment variables
    env: {
      TELEGRAM_BOT_TOKEN: '7747661668:AAEDXP6EGeDw87eeNZiF5xNwGo8u8x0ah-k',
      TELEGRAM_CHAT_ID: '1827491548',
      BOT_SYMBOL: 'BTCUSDT',
      BOT_EXCHANGE: 'BINANCE',
      BOT_TIMEFRAME: '1h',
      BOT_BULLISH_THRESHOLD: '60',
      BOT_BEARISH_THRESHOLD: '50',
      BOT_CHECK_INTERVAL: '300',
      PATH: '/root/.local/bin:/usr/bin:/bin'
    },

    // Auto-restart configuration
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',

    // Logging
    log_file: '/tmp/trading-mcp-bot/logs/app.log',
    error_file: '/tmp/trading-mcp-bot/logs/error.log',
    out_file: '/tmp/trading-mcp-bot/logs/out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,

    // Process management
    min_uptime: '10s',
    max_restarts: 10,
    restart_delay: 4000,

    // Execution mode
    exec_mode: 'fork',
    instances: 1,

    // Security
    autorestart: true,
    kill_retry_time: 1000
  }]
};
