#!/usr/bin/env python3
"""
Advanced Telegram RSI Monitor Bot with Interactive Commands

Features:
- Automatic RSI monitoring and alerts
- Interactive commands: /check-now, /status, /help, /config
- Real-time trading signals
- Configurable thresholds and timeframes

Setup:
1. pip install python-telegram-bot
2. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables
3. Run: python telegram_rsi_monitor_bot.py

Commands:
- /check-now: Check current conditions immediately
- /status: Show bot status and configuration
- /config: View or update configuration
- /start: Start automatic monitoring
- /stop: Stop automatic monitoring
- /help: Show all available commands
"""

import os
import sys
import time
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

try:
    from tradingview_mcp.core.services.screener_service import analyze_coin
    from tradingview_mcp.core.services.yahoo_finance_service import get_price
except ImportError:
    print("Error: tradingview-mcp not found.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class BotConfig:
    """Bot configuration."""
    symbol: str = "BTCUSDT"
    exchange: str = "BINANCE"
    timeframe: str = "1h"
    rsi_bullish_threshold: float = 60.0
    rsi_bearish_threshold: float = 50.0
    check_interval: int = 300  # 5 minutes
    alert_cooldown: int = 3600  # 1 hour


class RSIMonitorBot:
    """Advanced RSI Monitor Bot with interactive commands."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        config: Optional[BotConfig] = None
    ):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.config = config or BotConfig()

        # State tracking
        self.last_rsi: Optional[float] = None
        self.last_alert_time: Optional[datetime] = None
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None

        # Validate configuration
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set")
        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID not set")

        logger.info(f"Bot initialized for {self.config.symbol} ({self.config.timeframe})")

    def get_rsi_data(self) -> Optional[Dict[str, Any]]:
        """Fetch current RSI data."""
        try:
            result = analyze_coin(self.config.symbol, self.config.exchange, self.config.timeframe)
            rsi = result.get('rsi', {})

            # Get current price
            price_symbol = self.config.symbol.replace('USDT', '-USD')
            price_data = get_price(price_symbol)

            return {
                'symbol': self.config.symbol,
                'exchange': self.config.exchange,
                'timeframe': self.config.timeframe,
                'rsi_value': rsi.get('value'),
                'rsi_signal': rsi.get('signal'),
                'rsi_direction': rsi.get('direction'),
                'rsi_previous': rsi.get('previous'),
                'price': price_data.get('price'),
                'price_change_pct': price_data.get('change_pct'),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching RSI data: {e}")
            return None

    def determine_zone(self, rsi_value: float) -> str:
        """Determine RSI zone."""
        if rsi_value >= 70:
            return "🔴 OVERBOUGHT"
        elif rsi_value >= 60:
            return "🟢 BULLISH"
        elif rsi_value >= 40:
            return "⚪ NEUTRAL"
        elif rsi_value >= 30:
            return "🔵 BEARISH"
        else:
            return "🟡 OVERSOLD"

    def create_status_message(self, data: Optional[Dict] = None) -> str:
        """Create comprehensive status message with trade levels."""
        if not data:
            data = self.get_rsi_data()

        if not data:
            return "❌ Unable to fetch RSI data. Please try again."

        rsi_value = data.get('rsi_value')
        zone = self.determine_zone(rsi_value) if rsi_value else "UNKNOWN"
        price = data.get('price')
        change_pct = data.get('price_change_pct')
        direction = data.get('rsi_direction', 'N/A')

        # Determine signal
        signal_emoji = "⏳"
        signal_text = "WAIT"
        trade_direction = None
        if rsi_value:
            if rsi_value > self.config.rsi_bullish_threshold and 'Rising' in direction:
                signal_emoji = "🚀"
                signal_text = "LONG"
                trade_direction = "LONG"
            elif rsi_value < self.config.rsi_bearish_threshold and 'Falling' in direction:
                signal_emoji = "🔻"
                signal_text = "SHORT"
                trade_direction = "SHORT"

        message = f"""
📊 RSI STATUS - {data['symbol']} ({data['timeframe']})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 Price: ${price:,.2f} ({change_pct:+.2f}%)
📈 RSI: {rsi_value:.2f}
{zone}
📡 Direction: {direction}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 Current Signal: {signal_emoji} {signal_text}

📍 Thresholds:
• Bullish: RSI > {self.config.rsi_bullish_threshold}
• Bearish: RSI < {self.config.rsi_bearish_threshold}"""

        # Add trade levels if signal is active
        if trade_direction:
            trade = self.calculate_trade_levels(price, trade_direction)

            # Calculate position sizes
            risk_per_btc = trade['risk_amount']
            positions = []
            for account in [1000, 5000, 10000]:
                risk_amount = account * 0.01  # 1% risk
                btc_size = risk_amount / risk_per_btc
                position_value = btc_size * price
                positions.append((account, btc_size, position_value))

            message += f"""

⚡ TRADING LEVELS (R:R = 1:2):

✅ ENTRY PRICE:     ${trade['entry']:,.2f}
🎯 TAKE PROFIT:     ${trade['take_profit']:,.2f}
🛡️ STOP LOSS:      ${trade['stop_loss']:,.2f}

💰 Risk:            ${trade['risk_amount']:,.2f} per BTC
📈 Reward:          ${trade['reward_amount']:,.2f} per BTC
⚖️ Ratio:           {trade['risk_reward_ratio']}

📊 Position Sizing (1% Account Risk):
• Account ${positions[0][0]:,}:  {positions[0][1]:.4f} BTC (${positions[0][1] * price:,.2f}) - Risk ${positions[0][0] * 0.01:.2f}
• Account ${positions[1][0]:,}:  {positions[1][1]:.4f} BTC (${positions[1][1] * price:,.2f}) - Risk ${positions[1][0] * 0.01:.2f}
• Account ${positions[2][0]:,}:  {positions[2][1]:.4f} BTC (${positions[2][1] * price:,.2f}) - Risk ${positions[2][0] * 0.01:.2f}"""
        else:
            message += f"""

⚡ Trading Plan:
• Wait for clear signal
• No trade at current level"""

        message += f"""

⏰ Updated: {data['timestamp'][:-10]}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return message.strip()

    def check_breakout_conditions(self, data: Dict) -> Optional[str]:
        """Check if breakout conditions are met."""
        rsi_value = data.get('rsi_value')
        if rsi_value is None:
            return None

        rsi_direction = data.get('rsi_direction', '')
        is_rising = 'Rising' in rsi_direction
        is_falling = 'Falling' in rsi_direction

        # Bullish breakout
        if rsi_value > self.config.rsi_bullish_threshold and is_rising:
            if self.last_rsi and self.last_rsi <= self.config.rsi_bullish_threshold:
                return self._create_bullish_alert(data)

        # Bearish breakdown
        if rsi_value < self.config.rsi_bearish_threshold and is_falling:
            if self.last_rsi and self.last_rsi >= self.config.rsi_bearish_threshold:
                return self._create_bearish_alert(data)

        return None

    def calculate_trade_levels(self, current_price: float, direction: str) -> Dict:
        """Calculate entry, TP, SL levels with 1:2 R:R ratio."""
        # Risk percentage (1% of price for SL)
        risk_pct = 0.01

        if direction == "LONG":
            entry = current_price
            sl_distance = current_price * risk_pct
            stop_loss = entry - sl_distance
            take_profit = entry + (sl_distance * 2)  # 1:2 R:R ratio
        else:  # SHORT
            entry = current_price
            sl_distance = current_price * risk_pct
            stop_loss = entry + sl_distance
            take_profit = entry - (sl_distance * 2)  # 1:2 R:R ratio

        return {
            'entry': entry,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_amount': sl_distance,
            'reward_amount': sl_distance * 2,
            'risk_reward_ratio': '1:2'
        }

    def _create_bullish_alert(self, data: Dict) -> str:
        """Create bullish alert with trade levels."""
        rsi_value = data['rsi_value']
        zone = self.determine_zone(rsi_value)
        price = data['price']
        change_pct = data['price_change_pct']

        # Calculate trade levels
        trade = self.calculate_trade_levels(price, "LONG")

        # Calculate position sizes
        risk_per_btc = trade['risk_amount']
        positions = []
        for account in [1000, 5000, 10000]:
            risk_amount = account * 0.01  # 1% risk
            btc_size = risk_amount / risk_per_btc
            position_value = btc_size * price
            positions.append((account, btc_size, position_value))

        return f"""
🚀🚀🚀 BULLISH SIGNAL ALERT 🚀🚀🚀

📊 Symbol: {data['symbol']} ({data['timeframe']})
💰 Current Price: ${price:,.2f} ({change_pct:+.2f}%)
📈 RSI: {rsi_value:.2f} - {zone}
⬆️ Direction: {data['rsi_direction']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 BREAKOUT CONFIRMED!

📈 Analysis:
• RSI crossed above {self.config.rsi_bullish_threshold} with rising momentum
• Previous RSI: {self.last_rsi:.2f} → Current: {rsi_value:.2f}
• Strong bullish signal

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ TRADING PLAN (R:R = 1:2):

✅ ENTRY PRICE:     ${trade['entry']:,.2f}
🎯 TAKE PROFIT:     ${trade['take_profit']:,.2f}
🛡️ STOP LOSS:      ${trade['stop_loss']:,.2f}

💰 Risk:            ${trade['risk_amount']:,.2f} per BTC
📈 Reward:          ${trade['reward_amount']:,.2f} per BTC
⚖️ Ratio:           {trade['risk_reward_ratio']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Position Sizing (1% Account Risk):
• Account ${positions[0][0]:,}:  {positions[0][1]:.4f} BTC (${positions[0][1] * price:,.2f}) - Risk ${positions[0][0] * 0.01:.2f}
• Account ${positions[1][0]:,}:  {positions[1][1]:.4f} BTC (${positions[1][1] * price:,.2f}) - Risk ${positions[1][0] * 0.01:.2f}
• Account ${positions[2][0]:,}:  {positions[2][1]:.4f} BTC (${positions[2][1] * price:,.2f}) - Risk ${positions[2][0] * 0.01:.2f}

⏰ Time: {data['timestamp'][:-10]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔔 Enter at market or wait for pullback to Entry
"""

    def _create_bearish_alert(self, data: Dict) -> str:
        """Create bearish alert with trade levels."""
        rsi_value = data['rsi_value']
        zone = self.determine_zone(rsi_value)
        price = data['price']
        change_pct = data['price_change_pct']

        # Calculate trade levels
        trade = self.calculate_trade_levels(price, "SHORT")

        # Calculate position sizes
        risk_per_btc = trade['risk_amount']
        positions = []
        for account in [1000, 5000, 10000]:
            risk_amount = account * 0.01  # 1% risk
            btc_size = risk_amount / risk_per_btc
            position_value = btc_size * price
            positions.append((account, btc_size, position_value))

        return f"""
🔻🔻🔻 BEARISH SIGNAL ALERT 🔻🔻🔻

📊 Symbol: {data['symbol']} ({data['timeframe']})
💰 Current Price: ${price:,.2f} ({change_pct:+.2f}%)
📉 RSI: {rsi_value:.2f} - {zone}
⬇️ Direction: {data['rsi_direction']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 BREAKDOWN CONFIRMED!

📉 Analysis:
• RSI crossed below {self.config.rsi_bearish_threshold} with falling momentum
• Previous RSI: {self.last_rsi:.2f} → Current: {rsi_value:.2f}
• Strong bearish signal

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ TRADING PLAN (R:R = 1:2):

✅ ENTRY PRICE:     ${trade['entry']:,.2f}
🎯 TAKE PROFIT:     ${trade['take_profit']:,.2f}
🛡️ STOP LOSS:      ${trade['stop_loss']:,.2f}

💰 Risk:            ${trade['risk_amount']:,.2f} per BTC
📈 Reward:          ${trade['reward_amount']:,.2f} per BTC
⚖️ Ratio:           {trade['risk_reward_ratio']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Position Sizing (1% Account Risk):
• Account ${positions[0][0]:,}:  {positions[0][1]:.4f} BTC (${positions[0][1] * price:,.2f}) - Risk ${positions[0][0] * 0.01:.2f}
• Account ${positions[1][0]:,}:  {positions[1][1]:.4f} BTC (${positions[1][1] * price:,.2f}) - Risk ${positions[1][0] * 0.01:.2f}
• Account ${positions[2][0]:,}:  {positions[2][1]:.4f} BTC (${positions[2][1] * price:,.2f}) - Risk ${positions[2][0] * 0.01:.2f}

⏰ Time: {data['timestamp'][:-10]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔔 Enter at market or wait for bounce to Entry
"""

    async def send_message(self, message: str) -> bool:
        """Send message to Telegram."""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }

            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            logger.info("Message sent successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    # ========== Command Handlers ==========

    async def cmd_check_now(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check current conditions immediately."""
        logger.info("Command: /check-now")

        await update.message.reply_text("🔍 Checking current RSI conditions...")

        data = self.get_rsi_data()
        if data:
            # Update last RSI for comparison
            if data.get('rsi_value'):
                self.last_rsi = data.get('rsi_value')

            message = self.create_status_message(data)
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("❌ Failed to fetch RSI data. Please try again.")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot status and configuration."""
        logger.info("Command: /status")

        status_text = f"""
🤖 Bot Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Configuration:
• Symbol: {self.config.symbol}
• Exchange: {self.config.exchange}
• Timeframe: {self.config.timeframe}
• Bullish Threshold: {self.config.rsi_bullish_threshold}
• Bearish Threshold: {self.config.rsi_bearish_threshold}
• Check Interval: {self.config.check_interval}s

⚙️ Monitoring: {'🟢 Active' if self.monitoring_active else '🔴 Inactive'}
📡 Last RSI: {self.last_rsi if self.last_rsi else 'N/A'}
⏰ Last Alert: {self.last_alert_time.strftime('%H:%M:%S') if self.last_alert_time else 'Never'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await update.message.reply_text(status_text.strip())

    async def cmd_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show configuration menu."""
        logger.info("Command: /config")

        keyboard = [
            [
                InlineKeyboardButton("📊 Check Now", callback_data="check_now"),
                InlineKeyboardButton("📈 Status", callback_data="status"),
            ],
            [
                InlineKeyboardButton("⚙️ Change Symbol", callback_data="change_symbol"),
                InlineKeyboardButton("⏱️ Change Timeframe", callback_data="change_tf"),
            ],
            [
                InlineKeyboardButton("🔼 Bullish Thresh", callback_data="bullish_thresh"),
                InlineKeyboardButton("🔽 Bearish Thresh", callback_data="bearish_thresh"),
            ],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "⚙️ Configuration Menu:\nSelect an option:",
            reply_markup=reply_markup
        )

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start automatic monitoring."""
        logger.info("Command: /start")

        if self.monitoring_active:
            await update.message.reply_text("⚠️ Monitoring is already active!")
            return

        self.monitoring_active = True
        await update.message.reply_text(f"🚀 Automatic monitoring STARTED\n\nChecking every {self.config.check_interval}s")

        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stop automatic monitoring."""
        logger.info("Command: /stop")

        if not self.monitoring_active:
            await update.message.reply_text("⚠️ Monitoring is not active!")
            return

        self.monitoring_active = False

        if self.monitoring_task:
            self.monitoring_task.cancel()
            self.monitoring_task = None

        await update.message.reply_text("🛑 Automatic monitoring STOPPED")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help message."""
        logger.info("Command: /help")

        help_text = """
🤖 RSI Monitor Bot - Commands

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Monitoring Commands:
/check or /checknow - Check current conditions immediately
/status - Show bot status and configuration
/config - Configuration menu

⚙️ Control Commands:
/start - Start automatic monitoring
/stop - Stop automatic monitoring

❓ Help:
/help - Show this help message

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Tips:
• Use /check to get instant RSI analysis
• Use /start to enable automatic alerts
• Use /config to customize settings

⚠️ Note: Automatic monitoring checks RSI every 5 minutes and sends alerts when breakout conditions are met.
"""
        await update.message.reply_text(help_text.strip())

    # ========== Callback Handler ==========

    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks."""
        query = update.callback_query
        await query.answer()

        callback_data = query.data

        if callback_data == "check_now":
            data = self.get_rsi_data()
            if data:
                message = self.create_status_message(data)
                await query.edit_message_text(message)
            else:
                await query.edit_message_text("❌ Failed to fetch data")

        elif callback_data == "status":
            await self.cmd_status(update, context)
            # Delete the config menu message
            await query.message.delete()

        elif callback_data in ["change_symbol", "change_tf", "bullish_thresh", "bearish_thresh"]:
            await query.edit_message_text(
                f"⚠️ Feature coming soon!\n\n"
                f"To change {callback_data}, edit the config in the script or use command-line arguments."
            )

    # ========== Monitoring Loop ==========

    async def _monitoring_loop(self):
        """Automatic monitoring loop."""
        logger.info("Monitoring loop started")

        while self.monitoring_active:
            try:
                # Get current data
                data = self.get_rsi_data()

                if data and data.get('rsi_value'):
                    rsi_value = data['rsi_value']
                    logger.info(f"RSI Check: {rsi_value:.2f} ({data.get('rsi_signal')})")

                    # Check cooldown
                    if self.last_alert_time:
                        time_since_last = (datetime.now() - self.last_alert_time).total_seconds()
                        if time_since_last < self.config.alert_cooldown:
                            logger.debug("In cooldown period")
                        else:
                            # Check for breakout conditions
                            alert = self.check_breakout_conditions(data)
                            if alert:
                                await self.send_message(alert)
                                self.last_alert_time = datetime.now()

                    # Update last RSI
                    self.last_rsi = rsi_value

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

            # Wait for next check
            await asyncio.sleep(self.config.check_interval)

    # ========== Run ==========

    def run(self):
        """Run the bot."""
        # Create application
        application = Application.builder().token(self.bot_token).build()

        # Add command handlers
        # Note: Bot commands must be lowercase letters, numbers, and underscores only
        application.add_handler(CommandHandler("check", self.cmd_check_now))
        application.add_handler(CommandHandler("checknow", self.cmd_check_now))
        application.add_handler(CommandHandler("status", self.cmd_status))
        application.add_handler(CommandHandler("config", self.cmd_config))
        application.add_handler(CommandHandler("start", self.cmd_start))
        application.add_handler(CommandHandler("stop", self.cmd_stop))
        application.add_handler(CommandHandler("help", self.cmd_help))

        # Add callback handler
        application.add_handler(CallbackQueryHandler(self.callback_handler))

        # Start bot
        logger.info("Bot started. Send /help to see available commands")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Telegram RSI Monitor Bot with Interactive Commands")
    parser.add_argument("--bot-token", help="Telegram bot token")
    parser.add_argument("--chat-id", help="Telegram chat ID")
    parser.add_argument("--symbol", default="BTCUSDT", help="Trading symbol")
    parser.add_argument("--exchange", default="BINANCE", help="Exchange")
    parser.add_argument("--timeframe", default="1h", help="Timeframe")
    parser.add_argument("--bullish-threshold", type=float, default=60.0, help="RSI bullish threshold")
    parser.add_argument("--bearish-threshold", type=float, default=50.0, help="RSI bearish threshold")
    parser.add_argument("--interval", type=int, default=300, help="Check interval in seconds")

    args = parser.parse_args()

    # Create config
    config = BotConfig(
        symbol=args.symbol,
        exchange=args.exchange,
        timeframe=args.timeframe,
        rsi_bullish_threshold=args.bullish_threshold,
        rsi_bearish_threshold=args.bearish_threshold,
        check_interval=args.interval
    )

    # Create and run bot
    bot = RSIMonitorBot(
        bot_token=args.bot_token,
        chat_id=args.chat_id,
        config=config
    )

    bot.run()


if __name__ == "__main__":
    main()
