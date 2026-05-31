#!/bin/bash
# Configure TradingView API rate limit protection for bot

cd /tmp/trading-mcp-bot

echo "🔧 Configuring rate limit settings for PM2..."

# Update ecosystem.config.js with rate limit environment variables
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'tradingview-bot',
    script: 'telegram_rsi_monitor_bot_v2.py',
    interpreter: '.venv/bin/python',
    interpreter_args: '-u',
    cwd: '/tmp/trading-mcp-bot',

    // Environment variables
    env: {
      TELEGRAM_BOT_TOKEN: '7747661668:AAEDXP6EGeDw87eeNZiF5xNwGo8u8x0ah-k',
      TELEGRAM_CHAT_ID: '-1003923788619',
      BOT_SYMBOL: 'BTCUSDT',
      BOT_EXCHANGE: 'BINANCE',
      BOT_TIMEFRAME: '1h',
      BOT_BULLISH_THRESHOLD: '60',
      BOT_BEARISH_THRESHOLD: '50',
      BOT_CHECK_INTERVAL: '300',
      PATH: '/root/.local/bin:/usr/bin:/bin',
      PYTHONPATH: '/tmp/trading-mcp-bot/src:/tmp/trading-mcp-bot',

      // TradingView MCP Rate Limit Protection
      // Cache TTL: Keep data longer to reduce API calls (default: 60s)
      TRADINGVIEW_MCP_CACHE_TTL: '120',

      // Retry delays: Wait longer between retries (default: "0.5,1.5,4.0")
      TRADINGVIEW_MCP_RETRY_DELAYS: '1.0,2.0,5.0,10.0',

      // Max concurrent calls: Reduce parallel requests (default: 4)
      TRADINGVIEW_MCP_MAX_INFLIGHT: '2',

      // Min interval between calls: Slower but safer (default: 0.8s)
      TRADINGVIEW_MCP_MIN_INTERVAL_S: '1.5'
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
EOF

echo "✅ ecosystem.config.js updated with rate limit protection"
echo ""
echo "📊 New settings:"
echo "  • Cache TTL: 120s (reduced API calls by 50%)"
echo "  • Retry delays: 1.0s, 2.0s, 5.0s, 10.0s (more retries with longer waits)"
echo "  • Max concurrent: 2 (fewer parallel requests)"
echo "  • Min interval: 1.5s (slower but safer)"
echo ""
echo "🔄 Restart PM2 to apply changes:"
echo "  pm2 delete tradingview-bot"
echo "  pm2 start ecosystem.config.js"
echo "  pm2 save"
