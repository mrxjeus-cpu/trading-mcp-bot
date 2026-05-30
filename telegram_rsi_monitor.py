#!/usr/bin/env python3
"""
Telegram RSI Monitor Bot for BTC/USDT

Monitors 1H RSI and sends Telegram alerts when conditions are met:
- RSI breaks above 60 (Bullish signal)
- RSI breaks below 50 (Bearish signal)

Setup:
1. Create Telegram Bot: @BotFather on Telegram
2. Get BOT_TOKEN and CHAT_ID
3. Install dependencies: pip install python-telegram-bot requests
4. Run: python telegram_rsi_monitor.py

Or use as library:
    from telegram_rsi_monitor import RSIMonitor
    monitor = RSIMonitor(bot_token="...", chat_id="...")
    monitor.check_and_alert()
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from tradingview_mcp.core.services.screener_service import analyze_coin
    from tradingview_mcp.core.services.yahoo_finance_service import get_price
except ImportError:
    print("Error: tradingview-mcp not found. Run: uv tool install tradingview-mcp-server")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TelegramRSIMonitor:
    """Monitor RSI and send Telegram alerts on breakouts."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        symbol: str = "BTCUSDT",
        exchange: str = "BINANCE",
        timeframe: str = "1h",
        rsi_bullish_threshold: float = 60.0,
        rsi_bearish_threshold: float = 50.0,
        check_interval: int = 300  # 5 minutes
    ):
        """
        Initialize the RSI Monitor.

        Args:
            bot_token: Telegram bot token (or set TELEGRAM_BOT_TOKEN env var)
            chat_id: Telegram chat ID (or set TELEGRAM_CHAT_ID env var)
            symbol: Trading symbol (default: BTCUSDT)
            exchange: Exchange name (default: BINANCE)
            timeframe: Timeframe for RSI (default: 1h)
            rsi_bullish_threshold: RSI level for bullish alert (default: 60)
            rsi_bearish_threshold: RSI level for bearish alert (default: 50)
            check_interval: Check interval in seconds (default: 300)
        """
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.symbol = symbol
        self.exchange = exchange
        self.timeframe = timeframe
        self.rsi_bullish_threshold = rsi_bullish_threshold
        self.rsi_bearish_threshold = rsi_bearish_threshold
        self.check_interval = check_interval

        # State tracking
        self.last_rsi: Optional[float] = None
        self.last_alert_time: Optional[datetime] = None
        self.alert_cooldown = 3600  # 1 hour cooldown between alerts

        # Validate configuration
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials not set. Alerts will be logged only.")

    def get_rsi_data(self) -> Dict[str, Any]:
        """Fetch current RSI data for the configured symbol."""
        try:
            result = analyze_coin(self.symbol, self.exchange, self.timeframe)
            rsi = result.get('rsi', {})

            # Get current price
            price_data = get_price(f"{self.symbol.replace('USDT', '-USD')}")

            return {
                'symbol': self.symbol,
                'exchange': self.exchange,
                'timeframe': self.timeframe,
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
            return "OVERBOUGHT"
        elif rsi_value >= 60:
            return "BULLISH"
        elif rsi_value >= 40:
            return "NEUTRAL"
        elif rsi_value >= 30:
            return "BEARISH"
        else:
            return "OVERSOLD"

    def check_conditions(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Check if alert conditions are met.

        Returns:
            Alert message if conditions met, None otherwise
        """
        if not data:
            return None

        rsi_value = data.get('rsi_value')
        if rsi_value is None:
            return None

        rsi_direction = data.get('rsi_direction', '')
        is_rising = 'Rising' in rsi_direction
        is_falling = 'Falling' in rsi_direction

        # Bullish breakout: RSI crosses above threshold with rising momentum
        if rsi_value > self.rsi_bullish_threshold and is_rising:
            # Check if this is a new breakout (previous RSI was below threshold)
            if self.last_rsi and self.last_rsi <= self.rsi_bullish_threshold:
                return self._create_bullish_alert(data)

        # Bearish breakdown: RSI crosses below threshold with falling momentum
        if rsi_value < self.rsi_bearish_threshold and is_falling:
            # Check if this is a new breakdown (previous RSI was above threshold)
            if self.last_rsi and self.last_rsi >= self.rsi_bearish_threshold:
                return self._create_bearish_alert(data)

        return None

    def _create_bullish_alert(self, data: Dict[str, Any]) -> str:
        """Create bullish alert message."""
        rsi_value = data['rsi_value']
        zone = self.determine_zone(rsi_value)
        price = data['price']
        change_pct = data['price_change_pct']

        message = f"""
🚀 BULLISH SIGNAL ALERT 🚀

📊 Symbol: {data['symbol']} ({data['timeframe']})
💰 Price: ${price:,.2f} ({change_pct:+.2f}%)
📈 RSI: {rsi_value:.2f} - {zone}
⬆️ Direction: {data['rsi_direction']}

🎯 Analysis:
• RSI crossed above {self.rsi_bullish_threshold} with rising momentum
• Previous RSI: {self.last_rsi:.2f} → Current: {rsi_value:.2f}
• Potential LONG entry opportunity

⚡ Trading Plan:
Entry: Consider LONG position
Target: RSI 65-70 (overbought zone)
Stop Loss: Below recent support

⏰ Time: {data['timestamp']}

🔔 Monitor for follow-through
"""
        return message.strip()

    def _create_bearish_alert(self, data: Dict[str, Any]) -> str:
        """Create bearish alert message."""
        rsi_value = data['rsi_value']
        zone = self.determine_zone(rsi_value)
        price = data['price']
        change_pct = data['price_change_pct']

        message = f"""
🔻 BEARISH SIGNAL ALERT 🔻

📊 Symbol: {data['symbol']} ({data['timeframe']})
💰 Price: ${price:,.2f} ({change_pct:+.2f}%)
📉 RSI: {rsi_value:.2f} - {zone}
⬇️ Direction: {data['rsi_direction']}

🎯 Analysis:
• RSI crossed below {self.rsi_bearish_threshold} with falling momentum
• Previous RSI: {self.last_rsi:.2f} → Current: {rsi_value:.2f}
• Potential SHORT entry opportunity

⚡ Trading Plan:
Entry: Consider SHORT position
Target: RSI 40 (bearish zone)
Stop Loss: Above recent resistance

⏰ Time: {data['timestamp']}

🔔 Monitor for follow-through
"""
        return message.strip()

    def send_telegram_message(self, message: str) -> bool:
        """Send message to Telegram."""
        if not self.bot_token or not self.chat_id:
            logger.info("Telegram credentials not set. Message logged only:")
            logger.info(message)
            return True  # Log as "sent" for testing

        try:
            import requests

            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }

            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            logger.info("Message sent to Telegram successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def check_and_alert(self) -> bool:
        """
        Check conditions and send alert if needed.

        Returns:
            True if alert was sent, False otherwise
        """
        # Get current RSI data
        data = self.get_rsi_data()
        if not data:
            logger.warning("Failed to get RSI data")
            return False

        rsi_value = data.get('rsi_value')
        if rsi_value is None:
            logger.warning("RSI value not available")
            return False

        logger.info(f"RSI Check: {rsi_value:.2f} ({data.get('rsi_signal')}) - {data.get('rsi_direction')}")

        # Check if cooldown period has passed
        if self.last_alert_time:
            time_since_last = (datetime.now() - self.last_alert_time).total_seconds()
            if time_since_last < self.alert_cooldown:
                logger.debug(f"In cooldown period. {time_since_last:.0f}s since last alert")
                return False

        # Check conditions
        alert_message = self.check_conditions(data)

        if alert_message:
            # Send alert
            if self.send_telegram_message(alert_message):
                self.last_alert_time = datetime.now()
                logger.info("Alert sent successfully")
                return True
            else:
                logger.error("Failed to send alert")
                return False

        # Update last RSI for next comparison
        if rsi_value is not None:
            self.last_rsi = rsi_value

        return False

    def run_once(self) -> None:
        """Run a single check and exit."""
        logger.info(f"Checking {self.symbol} RSI on {self.timeframe} timeframe...")
        self.check_and_alert()

    def run_continuous(self) -> None:
        """Run continuous monitoring loop."""
        logger.info(f"Starting continuous monitoring for {self.symbol}")
        logger.info(f"Bullish threshold: {self.rsi_bullish_threshold} | Bearish threshold: {self.rsi_bearish_threshold}")
        logger.info(f"Check interval: {self.check_interval}s")

        try:
            while True:
                self.check_and_alert()
                logger.debug(f"Waiting {self.check_interval}s for next check...")
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")


def main():
    """Main entry point for CLI usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Telegram RSI Monitor for Trading")
    parser.add_argument("--symbol", default="BTCUSDT", help="Trading symbol (default: BTCUSDT)")
    parser.add_argument("--exchange", default="BINANCE", help="Exchange (default: BINANCE)")
    parser.add_argument("--timeframe", default="1h", help="Timeframe (default: 1h)")
    parser.add_argument("--bullish-threshold", type=float, default=60.0, help="RSI bullish threshold (default: 60)")
    parser.add_argument("--bearish-threshold", type=float, default=50.0, help="RSI bearish threshold (default: 50)")
    parser.add_argument("--interval", type=int, default=300, help="Check interval in seconds (default: 300)")
    parser.add_argument("--once", action="store_true", help="Run single check and exit")
    parser.add_argument("--bot-token", help="Telegram bot token (or set TELEGRAM_BOT_TOKEN env var)")
    parser.add_argument("--chat-id", help="Telegram chat ID (or set TELEGRAM_CHAT_ID env var)")

    args = parser.parse_args()

    # Create monitor
    monitor = TelegramRSIMonitor(
        bot_token=args.bot_token,
        chat_id=args.chat_id,
        symbol=args.symbol,
        exchange=args.exchange,
        timeframe=args.timeframe,
        rsi_bullish_threshold=args.bullish_threshold,
        rsi_bearish_threshold=args.bearish_threshold,
        check_interval=args.interval
    )

    # Run
    if args.once:
        monitor.run_once()
    else:
        monitor.run_continuous()


if __name__ == "__main__":
    main()
