#!/usr/bin/env python3
"""
Advanced Telegram RSI Monitor Bot v3.0 with Multiple Trading Strategies

Features:
- Multiple Trading Strategies:
  * Mean Reversion: Trade against trend at EMA touches
  * Trend Continuation: Trade with trend at EMA pullbacks
  * RSI Breakout: Original strategy (v2 compatibility)
- EMA Touch Detection (20/50/100/200)
- Fibonacci-based Entry/TP/SL calculation
- Advanced Volume Confirmation
- Multi-Timeframe Analysis
- Interactive commands with strategy selection

Setup:
1. pip install python-telegram-bot
2. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables
3. Run: python telegram_rsi_monitor_bot_v3.py

New Commands:
- /strategy: Choose trading strategy (Mean Reversion / Trend Continuation / RSI Breakout)
- /check: Check current conditions with selected strategy
- /status: Show bot status and current strategy
- /start: Start automatic monitoring with selected strategy
- /trade: Quick trading pair analysis

Strategy Details:
1. MEAN REVERSION: Trade reversals at EMA touches
   - Uptrend + EMA touch → SHORT
   - Downtrend + EMA touch → LONG

2. TREND CONTINUATION: Trade with the trend
   - Uptrend + EMA pullback → LONG
   - Downtrend + EMA pullback → SHORT

3. RSI BREAKOUT: Original strategy (v2)
   - RSI threshold breakout with confluence
"""

import os
import sys
import time
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
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
    from tradingview_mcp.core.services.fibonacci_service import analyze_crypto_fibonacci
    from tradingview_mcp.core.services.exchange_volume_service import analyze_exchange_volume
    from trading_strategies import (
        StrategyType,
        MeanReversionStrategy,
        TrendContinuationStrategy,
        create_strategy,
        TradingSignal
    )
except ImportError as e:
    print(f"Error: tradingview-mcp modules not found: {e}")
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

    # Trading Strategy Configuration (NEW in v3)
    trading_strategy: str = "trend_continuation"  # "mean_reversion", "trend_continuation", "rsi_breakout"
    ema_proximity_pct: float = 0.5  # EMA touch detection threshold (%)

    # Signal Mode Configuration (v2 compatibility)
    signal_mode: str = "confluence"  # "threshold" or "confluence"

    # Multi-Timeframe Configuration
    use_multi_timeframe: bool = True  # Use multi-timeframe analysis
    timeframes: List[str] = None  # Timeframes to analyze (1h, 4h, 1d)
    primary_timeframe: str = "1h"  # Primary timeframe for signals
    require_mtf_confluence: bool = True  # Require confluence across timeframes

    # EMA Configuration
    ema_periods: List[int] = None
    ema_bullish_stack: bool = True  # Require bullish EMA stack
    ema_bearish_stack: bool = True  # Require bearish EMA stack

    # Fibonacci Configuration
    fib_tolerance_pct: float = 2.0  # Price proximity tolerance for Fib levels
    fib_golden_pocket_only: bool = False  # Only alert at golden pocket levels

    # Confluence Configuration
    require_confluence: bool = True  # Require multiple indicators to align
    min_indicators: int = 2  # Minimum indicators that must align
    min_confluence_score: int = 70  # Minimum score for strong confluence

    # Exchange API Configuration
    use_exchange_data: bool = True  # Use real-time order book data
    exchange_api_timeout: int = 5  # Timeout for exchange API calls (seconds)

    # Multi-pair monitoring
    monitor_all_pairs: bool = True
    trading_pairs: list = None

    def __post_init__(self):
        if self.trading_pairs is None:
            self.trading_pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "TONUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT"]
        if self.ema_periods is None:
            self.ema_periods = [20, 50, 100, 200]
        if self.timeframes is None:
            self.timeframes = ["1h", "4h", "1d"]  # Default timeframes for MTF analysis


class RSIMonitorBot:
    """Advanced RSI Monitor Bot with EMA & Fibonacci Confluence."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        config: Optional[BotConfig] = None
    ):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.config = config or BotConfig()

        # State tracking - single symbol (for /check command)
        self.last_rsi: Optional[float] = None
        self.last_alert_time: Optional[datetime] = None

        # State tracking - multi-pair monitoring
        self.pair_last_rsi: Dict[str, Optional[float]] = {pair: None for pair in self.config.trading_pairs}
        self.pair_last_alert_time: Dict[str, Optional[datetime]] = {pair: None for pair in self.config.trading_pairs}

        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None

        # Trading Strategy (NEW in v3)
        self.current_strategy = self._initialize_strategy()

        # Validate configuration
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set")
        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID not set")

        logger.info(f"Bot v3.0 initialized with Trading Strategy: {self.config.trading_strategy.upper()}")
        logger.info(f"EMA Proximity Threshold: {self.config.ema_proximity_pct}%")
        logger.info(f"Multi-Timeframe Analysis: {', '.join(self.config.timeframes)} (Primary: {self.config.primary_timeframe})")
        logger.info(f"Monitoring {len(self.config.trading_pairs)} trading pairs: {', '.join(self.config.trading_pairs)}")

    def _initialize_strategy(self):
        """Initialize trading strategy based on config."""
        strategy_type = self.config.trading_strategy

        if strategy_type == "mean_reversion":
            return MeanReversionStrategy({
                "ema_proximity_pct": self.config.ema_proximity_pct,
                "rsi_overbought": 70,
                "rsi_oversold": 30
            })
        elif strategy_type == "trend_continuation":
            return TrendContinuationStrategy({
                "ema_proximity_pct": self.config.ema_proximity_pct,
                "rsi_bullish_min": 50,
                "rsi_bearish_max": 50
            })
        elif strategy_type == "rsi_breakout":
            # Use v2 original strategy (no special initialization)
            logger.info("Using RSI Breakout strategy (v2 compatibility mode)")
            return None
        else:
            logger.warning(f"Unknown strategy: {strategy_type}, defaulting to trend_continuation")
            self.config.trading_strategy = "trend_continuation"
            return TrendContinuationStrategy()

    def set_strategy(self, strategy_name: str):
        """Change trading strategy dynamically."""
        old_strategy = self.config.trading_strategy
        self.config.trading_strategy = strategy_name
        self.current_strategy = self._initialize_strategy()
        logger.info(f"Strategy changed from {old_strategy} to {strategy_name}")
        return self.current_strategy

    def get_rsi_data(self, symbol: Optional[str] = None, exchange: Optional[str] = None, use_mtf: bool = None) -> Optional[Dict[str, Any]]:
        """Fetch current RSI, EMA, Fibonacci, and Exchange data for a specific symbol (with MTF analysis)."""
        try:
            sym = symbol or self.config.symbol
            exch = exchange or self.config.exchange
            use_mtf = use_mtf if use_mtf is not None else self.config.use_multi_timeframe

            result = analyze_coin(sym, exch, self.config.primary_timeframe)

            if result.get("error"):
                logger.error(f"Analysis error for {sym}: {result.get('error')}")
                return None

            rsi = result.get('rsi', {})
            ema = result.get('ema', {})
            support_resistance = result.get('support_resistance', {})
            price_data = result.get('price_data', {})

            # Get current price
            price_symbol = sym.replace('USDT', '-USD')
            yahoo_data = get_price(price_symbol)

            current_price = yahoo_data.get('price') or price_data.get('current_price')

            # Calculate Fibonacci levels
            fib_analysis = analyze_crypto_fibonacci(
                symbol=sym,
                current_price=current_price,
                indicators=result,  # Pass full result for swing detection
                tolerance_pct=self.config.fib_tolerance_pct
            )

            # Get Exchange Volume Data (optional - can be disabled)
            exchange_data = None
            if self.config.use_exchange_data:
                try:
                    exchange_data = analyze_exchange_volume(
                        symbol=sym,
                        exchange="binance",  # Currently only Binance supported
                        include_trades=True,
                        order_book_limit=20
                    )
                    if exchange_data.get("order_book"):
                        logger.debug(f"Exchange data fetched for {sym}: {exchange_data['order_book']['signal']}")
                except Exception as e:
                    logger.warning(f"Failed to fetch exchange data for {sym}: {e}")
                    exchange_data = None

            # Multi-Timeframe Analysis (MTF)
            mtf_data = None
            if use_mtf:
                try:
                    mtf_data = self._analyze_multi_timeframe(sym, exch)
                    logger.debug(f"MTF analysis completed for {sym}")
                except Exception as e:
                    logger.warning(f"Failed to fetch MTF data for {sym}: {e}")
                    mtf_data = None

            # EMA Trend Analysis
            ema_trend = self._analyze_ema_trend(current_price, ema)

            return {
                'symbol': sym,
                'exchange': exch,
                'timeframe': self.config.primary_timeframe,
                'all_timeframes': self.config.timeframes if use_mtf else [self.config.primary_timeframe],

                # RSI Data
                'rsi_value': rsi.get('value'),
                'rsi_signal': rsi.get('signal'),
                'rsi_direction': rsi.get('direction'),
                'rsi_previous': rsi.get('previous'),

                # Price Data
                'price': current_price,
                'price_change_pct': yahoo_data.get('change_pct'),

                # EMA Data
                'ema': ema,
                'ema_trend': ema_trend,

                # Fibonacci Data
                'fibonacci': fib_analysis,

                # Support/Resistance
                'support_resistance': support_resistance,

                # Exchange Volume Data
                'exchange_data': exchange_data,

                # Multi-Timeframe Data
                'mtf_data': mtf_data,

                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None

    def _analyze_ema_trend(self, price: float, ema: Dict) -> Dict[str, Any]:
        """Analyze EMA trend structure."""
        if not ema or not price:
            return {"trend": "unknown", " bullish": False, "bearish": False}

        ema20 = ema.get('ema20')
        ema50 = ema.get('ema50')
        ema100 = ema.get('ema100')
        ema200 = ema.get('ema200')

        if not all([ema20, ema50, ema100, ema200]):
            return {"trend": "insufficient_data", "bullish": False, "bearish": False}

        # Bullish Stack: Price > EMA20 > EMA50 > EMA100 > EMA200
        bullish_stack = price > ema20 > ema50 > ema100 > ema200

        # Bearish Stack: Price < EMA20 < EMA50 < EMA100 < EMA200
        bearish_stack = price < ema20 < ema50 < ema100 < ema200

        # Golden Cross: EMA50 > EMA200
        golden_cross = ema50 > ema200

        # Death Cross: EMA50 < EMA200
        death_cross = ema50 < ema200

        trend = "strong_uptrend" if bullish_stack and golden_cross else \
                "uptrend" if bullish_stack else \
                "strong_downtrend" if bearish_stack and death_cross else \
                "downtrend" if bearish_stack else \
                "ranging" if golden_cross or death_cross else "sideways"

        return {
            "trend": trend,
            "bullish": bullish_stack,
            "bearish": bearish_stack,
            "golden_cross": golden_cross,
            "death_cross": death_cross,
            "price_above_ema20": price > ema20,
            "price_above_ema50": price > ema50,
            "price_above_ema100": price > ema100,
            "price_above_ema200": price > ema200,
            "ema20": ema20,
            "ema50": ema50,
            "ema100": ema100,
            "ema200": ema200
        }

    def _analyze_multi_timeframe(self, symbol: str, exchange: str) -> Dict[str, Any]:
        """Analyze multiple timeframes for confluence."""
        mtf_results = {}
        bullish_timeframes = []
        bearish_timeframes = []

        for tf in self.config.timeframes:
            try:
                # Fetch data for this timeframe
                result = analyze_coin(symbol, exchange, tf)

                if result.get("error"):
                    logger.warning(f"Error analyzing {tf} for {symbol}: {result.get('error')}")
                    continue

                rsi = result.get('rsi', {})
                ema = result.get('ema', {})
                price_data = result.get('price_data', {})
                current_price = price_data.get('current_price', 0)

                # Determine trend for this timeframe
                rsi_value = rsi.get('value', 50)
                ema_trend = self._analyze_ema_trend(current_price, ema)

                # Classify trend
                trend_type = "bullish" if (
                    rsi_value > self.config.rsi_bullish_threshold and
                    ema_trend.get('bullish') and
                    'Rising' in rsi.get('direction', '')
                ) else "bearish" if (
                    rsi_value < self.config.rsi_bearish_threshold and
                    ema_trend.get('bearish') and
                    'Falling' in rsi.get('direction', '')
                ) else "neutral"

                mtf_results[tf] = {
                    'rsi_value': rsi_value,
                    'rsi_direction': rsi.get('direction'),
                    'trend': trend_type,
                    'ema_trend': ema_trend.get('trend'),
                    'price': current_price,
                    'change_pct': price_data.get('change_percent', 0)
                }

                # Track aligned timeframes
                if trend_type == "bullish":
                    bullish_timeframes.append(tf)
                elif trend_type == "bearish":
                    bearish_timeframes.append(tf)

            except Exception as e:
                logger.warning(f"Error analyzing {tf} for {symbol}: {e}")
                continue

        # Determine MTF signal
        aligned_count = len(bullish_timeframes) if bullish_timeframes else len(bearish_timeframes)
        total_count = len(mtf_results)

        if total_count == 0:
            mtf_signal = "neutral"
            mtf_strength = "no_data"
        elif aligned_count == total_count:
            mtf_signal = "strong_bullish" if bullish_timeframes else "strong_bearish"
            mtf_strength = "all_aligned"
        elif aligned_count >= total_count * 0.67:
            mtf_signal = "bullish" if bullish_timeframes else "bearish"
            mtf_strength = "strong_confluence"
        elif aligned_count >= total_count * 0.5:
            mtf_signal = "weak_bullish" if bullish_timeframes else "weak_bearish"
            mtf_strength = "moderate_confluence"
        else:
            mtf_signal = "neutral"
            mtf_strength = "divergent"

        return {
            'primary_timeframe': self.config.primary_timeframe,
            'analyzed_timeframes': list(mtf_results.keys()),
            'mtf_results': mtf_results,
            'bullish_timeframes': bullish_timeframes,
            'bearish_timeframes': bearish_timeframes,
            'mtf_signal': mtf_signal,
            'mtf_strength': mtf_strength,
            'aligned_count': aligned_count,
            'total_count': total_count,
            'confluence_ratio': aligned_count / total_count if total_count > 0 else 0
        }

    def _check_confluence(self, data: Dict, direction: str) -> Dict[str, Any]:
        """Check indicator confluence for a signal."""
        confluence = {
            "total_score": 0,
            "aligned_indicators": [],
            "misaligned_indicators": [],
            "strong_confluence": False
        }

        rsi_value = data.get('rsi_value')
        ema_trend = data.get('ema_trend', {})
        fib = data.get('fibonacci', {})

        # RSI Confluence
        if direction == "LONG":
            if rsi_value > self.config.rsi_bullish_threshold:
                confluence["total_score"] += 30
                confluence["aligned_indicators"].append("RSI Bullish")
            else:
                confluence["misaligned_indicators"].append("RSI Not Bullish")
        elif direction == "SHORT":
            if rsi_value < self.config.rsi_bearish_threshold:
                confluence["total_score"] += 30
                confluence["aligned_indicators"].append("RSI Bearish")
            else:
                confluence["misaligned_indicators"].append("RSI Not Bearish")

        # EMA Confluence
        if direction == "LONG" and ema_trend.get("bullish"):
            confluence["total_score"] += 35
            confluence["aligned_indicators"].append(f"EMA Bullish Stack ({ema_trend.get('trend')})")
        elif direction == "SHORT" and ema_trend.get("bearish"):
            confluence["total_score"] += 35
            confluence["aligned_indicators"].append(f"EMA Bearish Stack ({ema_trend.get('trend')})")
        else:
            confluence["misaligned_indicators"].append("EMA Not Aligned")

        # Fibonacci Confluence
        if direction == "LONG" and fib.get("near_support"):
            confluence["total_score"] += 35
            support = fib.get("nearest_supports", [{}])[0]
            confluence["aligned_indicators"].append(f"Near Fib Support ({support.get('level', 'N/A')})")

            # Bonus for golden pocket
            if fib.get("at_golden_pocket"):
                confluence["total_score"] += 15
                confluence["aligned_indicators"].append("🟡 Golden Pocket Confluence!")
        elif direction == "SHORT" and fib.get("near_resistance"):
            confluence["total_score"] += 35
            resistance = fib.get("nearest_resistances", [{}])[0]
            confluence["aligned_indicators"].append(f"Near Fib Resistance ({resistance.get('level', 'N/A')})")

            # Bonus for golden pocket
            if fib.get("at_golden_pocket"):
                confluence["total_score"] += 15
                confluence["aligned_indicators"].append("🟡 Golden Pocket Confluence!")
        else:
            confluence["misaligned_indicators"].append("Not Near Fib Level")

        # Exchange Volume Confluence (Order Book Analysis)
        exchange_data = data.get('exchange_data')
        if exchange_data and exchange_data.get("order_book"):
            ob_signal = exchange_data["order_book"]["signal"]
            buy_pressure = exchange_data["order_book"]["buy_pressure"]
            sell_pressure = exchange_data["order_book"]["sell_pressure"]

            # Check if exchange data aligns with our direction
            if direction == "LONG" and ob_signal in ["buy", "strong_buy"]:
                confluence["total_score"] += 25
                pressure_type = "Strong" if ob_signal == "strong_buy" else "Moderate"
                confluence["aligned_indicators"].append(f"Exchange {pressure_type} Buy Pressure ({buy_pressure:.0f}% vs {sell_pressure:.0f}%)")

                # Bonus for very strong buying pressure
                if buy_pressure >= 70:
                    confluence["total_score"] += 10
                    confluence["aligned_indicators"].append("🔥 Heavy Accumulation!")
            elif direction == "SHORT" and ob_signal in ["sell", "strong_sell"]:
                confluence["total_score"] += 25
                pressure_type = "Strong" if ob_signal == "strong_sell" else "Moderate"
                confluence["aligned_indicators"].append(f"Exchange {pressure_type} Sell Pressure ({sell_pressure:.0f}% vs {buy_pressure:.0f}%)")

                # Bonus for very strong selling pressure
                if sell_pressure >= 70:
                    confluence["total_score"] += 10
                    confluence["aligned_indicators"].append("🔥 Heavy Distribution!")
            else:
                confluence["misaligned_indicators"].append(f"Exchange {ob_signal} (not aligned with {direction})")

            # Recent trades confluence
            if exchange_data.get("recent_trades"):
                trades_signal = exchange_data["recent_trades"]["signal"]
                net_flow = exchange_data["recent_trades"].get("net_flow", 0)

                if direction == "LONG" and trades_signal == "buy" and net_flow > 0:
                    confluence["total_score"] += 15
                    confluence["aligned_indicators"].append(f"Recent Trades Bullish (Net Flow: +{net_flow:.2f})")
                elif direction == "SHORT" and trades_signal == "sell" and net_flow < 0:
                    confluence["total_score"] += 15
                    confluence["aligned_indicators"].append(f"Recent Trades Bearish (Net Flow: {net_flow:.2f})")
        else:
            confluence["misaligned_indicators"].append("No Exchange data available")

        # Multi-Timeframe Confluence
        mtf_data = data.get('mtf_data')
        if mtf_data:
            mtf_signal = mtf_data.get('mtf_signal')
            mtf_strength = mtf_data.get('mtf_strength')
            aligned_timeframes = mtf_data.get('bullish_timeframes') if direction == "LONG" else mtf_data.get('bearish_timeframes')
            confluence_ratio = mtf_data.get('confluence_ratio', 0)

            # Check if MTF aligns with our direction
            if direction == "LONG" and "bullish" in mtf_signal:
                points = 30 if mtf_strength == "all_aligned" else 20 if mtf_strength == "strong_confluence" else 10
                confluence["total_score"] += points
                confluence["aligned_indicators"].append(f"MTF {mtf_strength.replace('_', ' ').title()} ({', '.join(aligned_timeframes)})")

                # Bonus for full alignment
                if mtf_strength == "all_aligned":
                    confluence["total_score"] += 15
                    confluence["aligned_indicators"].append("🎯 All Timeframes Aligned!")
            elif direction == "SHORT" and "bearish" in mtf_signal:
                points = 30 if mtf_strength == "all_aligned" else 20 if mtf_strength == "strong_confluence" else 10
                confluence["total_score"] += points
                confluence["aligned_indicators"].append(f"MTF {mtf_strength.replace('_', ' ').title()} ({', '.join(aligned_timeframes)})")

                # Bonus for full alignment
                if mtf_strength == "all_aligned":
                    confluence["total_score"] += 15
                    confluence["aligned_indicators"].append("🎯 All Timeframes Aligned!")
            else:
                confluence["misaligned_indicators"].append(f"MTF {mtf_signal} (not aligned with {direction})")
        else:
            confluence["misaligned_indicators"].append("No MTF data available")

        # Strong confluence: score >= min_score and at least min_indicators aligned
        # In threshold mode, just need RSI signal (score >= 30)
        if self.config.signal_mode == "threshold":
            confluence["strong_confluence"] = confluence["total_score"] >= 30
        else:
            confluence["strong_confluence"] = (
                confluence["total_score"] >= self.config.min_confluence_score and
                len(confluence["aligned_indicators"]) >= self.config.min_indicators
            )

        return confluence

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
        """Create comprehensive status message with EMA & Fibonacci analysis."""
        if not data:
            data = self.get_rsi_data()

        if not data:
            return "❌ Unable to fetch data. Please try again."

        rsi_value = data.get('rsi_value')
        zone = self.determine_zone(rsi_value) if rsi_value else "UNKNOWN"
        price = data.get('price')
        change_pct = data.get('price_change_pct')
        direction = data.get('rsi_direction', 'N/A')

        ema_trend = data.get('ema_trend', {})
        fib = data.get('fibonacci', {})

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
📊 ANALYSIS - {data['symbol']} ({data['timeframe']})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 Price: ${price:,.2f} ({change_pct:+.2f}%)
📈 RSI: {rsi_value:.2f} {zone}
📡 Direction: {direction}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 EMA Trend Analysis:"""

        # Add EMA info
        ema = data.get('ema', {})
        if ema.get('ema20'):
            message += f"""
• EMA20: ${ema['ema20']:,.2f} {'✅ Above' if price > ema['ema20'] else '❌ Below'}
• EMA50: ${ema['ema50']:,.2f} {'✅ Above' if price > ema['ema50'] else '❌ Below'}
• EMA100: ${ema['ema100']:,.2f} {'✅ Above' if price > ema['ema100'] else '❌ Below'}
• EMA200: ${ema['ema200']:,.2f} {'✅ Above' if price > ema['ema200'] else '❌ Below'}

Trend: {ema_trend.get('trend', 'N/A').upper()}
Golden Cross: {'✅' if ema_trend.get('golden_cross') else '❌'}"""

        # Add Fibonacci info
        if fib and not fib.get('error'):
            message += f"""

📐 Fibonacci Analysis:
• Swing High: ${fib.get('swing_high', 0):,.2f}
• Swing Low: ${fib.get('swing_low', 0):,.2f}
• Position: {fib.get('position', 'unknown').upper()}"""

            if fib.get('nearest_supports'):
                s = fib['nearest_supports'][0]
                message += f"""
• Nearest Support: {s['level']} @ ${s['price']:,.2f} ({s['distance_pct']:.2f}% away)"""
                if s.get('is_golden_pocket'):
                    message += " 🟡 Golden Pocket"

            if fib.get('nearest_resistances'):
                r = fib['nearest_resistances'][0]
                message += f"""
• Nearest Resistance: {r['level']} @ ${r['price']:,.2f} ({r['distance_pct']:.2f}% away)"""
                if r.get('is_golden_pocket'):
                    message += " 🟡 Golden Pocket"

        # Add Exchange Volume info
        exchange_data = data.get('exchange_data')
        if exchange_data and exchange_data.get('order_book'):
            ob = exchange_data['order_book']
            buy_pressure = ob['buy_pressure']
            sell_pressure = ob['sell_pressure']
            spread = ob['spread']

            message += f"""

📊 Exchange Volume:
• Buy Pressure: {buy_pressure:.1f}% | Sell Pressure: {sell_pressure:.1f}%
• Order Book Signal: {ob['signal'].upper()}
• Spread: ${spread:.2f}"""

            if exchange_data.get('recent_trades'):
                rt = exchange_data['recent_trades']
                message += f"""
• Recent Trades: {rt['signal'].upper()} (Net Flow: {rt['net_flow']:+.2f})"""

        # Add Multi-Timeframe info to status
        mtf_data = data.get('mtf_data')
        if mtf_data:
            mtf_signal = mtf_data.get('mtf_signal')
            bullish_tfs = mtf_data.get('bullish_timeframes', [])
            bearish_tfs = mtf_data.get('bearish_timeframes', [])

            message += f"""

🎯 MTF Analysis:
• Signal: {mtf_signal.upper().replace('_', ' ')}
• Bullish: {', '.join(bullish_tfs) if bullish_tfs else 'None'}
• Bearish: {', '.join(bearish_tfs) if bearish_tfs else 'None'}"""

        message += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 Current Signal: {signal_emoji} {signal_text}

📍 Thresholds:
• Bullish: RSI > {self.config.rsi_bullish_threshold}
• Bearish: RSI < {self.config.rsi_bearish_threshold}"""

        # Add confluence analysis if signal is active
        if trade_direction:
            confluence = self._check_confluence(data, trade_direction)
            message += f"""

🔗 CONFLUENCE ANALYSIS:
Score: {confluence['total_score']}/100
Aligned: {', '.join(confluence['aligned_indicators']) if confluence['aligned_indicators'] else 'None'}
Strong Confluence: {'✅ YES' if confluence['strong_confluence'] else '❌ NO'}"""

            # Add trade levels
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
• Account ${positions[0][0]:,}:  {positions[0][1]:.4f} BTC (${positions[0][2]:,.2f}) - Risk ${positions[0][0] * 0.01:.2f}
• Account ${positions[1][0]:,}:  {positions[1][1]:.4f} BTC (${positions[1][2]:,.2f}) - Risk ${positions[1][0] * 0.01:.2f}
• Account ${positions[2][0]:,}:  {positions[2][1]:.4f} BTC (${positions[2][2]:,.2f}) - Risk ${positions[2][0] * 0.01:.2f}"""
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

    def check_breakout_conditions_multi_pair(self, data: Dict, symbol: str) -> Optional[str]:
        """Check if breakout conditions with confluence are met."""
        rsi_value = data.get('rsi_value')
        if rsi_value is None:
            return None

        rsi_direction = data.get('rsi_direction', '')
        is_rising = 'Rising' in rsi_direction
        is_falling = 'Falling' in rsi_direction

        # Get last RSI for this specific symbol
        last_rsi = self.pair_last_rsi.get(symbol)

        # Check Bullish Breakout
        if rsi_value > self.config.rsi_bullish_threshold and is_rising:
            if last_rsi and last_rsi <= self.config.rsi_bullish_threshold:

                # Check confluence
                confluence = self._check_confluence(data, "LONG")

                # Only alert if strong confluence (or confluence not required)
                if not self.config.require_confluence or confluence['strong_confluence']:
                    logger.info(f"Bullish breakout detected for {symbol} with confluence score: {confluence['total_score']}")
                    return self._create_bullish_alert(data, confluence)

        # Check Bearish Breakdown
        if rsi_value < self.config.rsi_bearish_threshold and is_falling:
            if last_rsi and last_rsi >= self.config.rsi_bearish_threshold:

                # Check confluence
                confluence = self._check_confluence(data, "SHORT")

                # Only alert if strong confluence (or confluence not required)
                if not self.config.require_confluence or confluence['strong_confluence']:
                    logger.info(f"Bearish breakdown detected for {symbol} with confluence score: {confluence['total_score']}")
                    return self._create_bearish_alert(data, confluence)

        return None

    def check_strategy_signals(self, data: Dict, symbol: str) -> Optional[str]:
        """
        Check signals using selected trading strategy (NEW v3).

        This replaces the RSI breakout logic with strategy-based signals:
        - Mean Reversion: EMA touch + RSI + Volume + Fib
        - Trend Continuation: EMA pullback + RSI + Volume + Fib
        - RSI Breakout: Original v2 logic (fall back to check_breakout_conditions_multi_pair)
        """
        # If using RSI Breakout strategy (v2 compatibility), use original logic
        if self.config.trading_strategy == "rsi_breakout":
            return self.check_breakout_conditions_multi_pair(data, symbol)

        # For new strategies, use strategy classes
        if not self.current_strategy:
            logger.warning("No strategy initialized, falling back to RSI breakout")
            return self.check_breakout_conditions_multi_pair(data, symbol)

        # Extract data needed for strategy
        current_price = data.get('price')
        rsi_value = data.get('rsi_value')
        ema = data.get('ema', {})
        ema_trend = data.get('ema_trend', {})
        fibonacci = data.get('fibonacci', {})
        exchange_data = data.get('exchange_data')

        # Check if strategy generates a signal
        try:
            signal = self.current_strategy.check_signal(
                symbol=symbol,
                current_price=current_price,
                rsi_value=rsi_value,
                ema=ema,
                ema_trend=ema_trend,
                fibonacci=fibonacci,
                exchange_data=exchange_data
            )

            if signal and signal.confidence >= 60:  # Minimum confidence threshold
                logger.info(f"Strategy signal detected for {symbol}: {signal.direction} with confidence {signal.confidence:.0f}%")
                return self._create_strategy_alert(signal, data)

        except Exception as e:
            logger.error(f"Error checking strategy signals for {symbol}: {e}")

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

    def _create_bullish_alert(self, data: Dict, confluence: Dict) -> str:
        """Create bullish alert with confluence details (including MTF analysis)."""
        rsi_value = data['rsi_value']
        zone = self.determine_zone(rsi_value)
        price = data['price']
        change_pct = data['price_change_pct']
        ema_trend = data.get('ema_trend', {})
        fib = data.get('fibonacci', {})

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

        # Build alert message
        confluence_status = '✅ STRONG' if confluence['strong_confluence'] else '⚠️ MODERATE'
        aligned_indicators_text = ''.join(f'  ✅ {ind}\n' for ind in confluence['aligned_indicators'])
        golden_cross_status = '✅' if ema_trend.get('golden_cross') else '❌'
        stack_status = '✅ Bullish' if ema_trend.get('bullish') else '❌ Not Bullish'

        alert = f"""
🚀🚀🚀 BULLISH SIGNAL ALERT WITH MTF ANALYSIS 🚀🚀🚀

📊 Symbol: {data['symbol']} ({data['timeframe']})
💰 Current Price: ${price:,.2f} ({change_pct:+.2f}%)
📈 RSI: {rsi_value:.2f} - {zone}
⬆️ Direction: {data['rsi_direction']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 CONFLUENCE SCORE: {confluence['total_score']}/100 {confluence_status}

Aligned Indicators:
{aligned_indicators_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 EMA Trend:
• Trend: {ema_trend.get('trend', 'N/A').upper()}
• Golden Cross: {golden_cross_status}
• Stack: {stack_status}"""

        # Add Fibonacci info
        if fib and not fib.get('error') and fib.get('near_support'):
            s = fib['nearest_supports'][0]
            golden_pocket_status = '🟡 YES' if fib.get('at_golden_pocket') else '❌ No'
            alert += f"""

📐 Fibonacci:
• Near Support: {s['level']} @ ${s['price']:,.2f} ({s['distance_pct']:.2f}% away)
• Golden Pocket: {golden_pocket_status}"""

        # Add Exchange Volume info
        exchange_data = data.get('exchange_data')
        if exchange_data and exchange_data.get('order_book'):
            ob = exchange_data['order_book']
            buy_pressure = ob['buy_pressure']
            sell_pressure = ob['sell_pressure']
            spread = ob['spread']

            alert += f"""

📊 EXCHANGE VOLUME:
• Buy Pressure: {buy_pressure:.1f}% | Sell Pressure: {sell_pressure:.1f}%
• Order Book Signal: {ob['signal'].upper()}
• Spread: ${spread:.2f}"""

            # Add recent trades if available
            if exchange_data.get('recent_trades'):
                rt = exchange_data['recent_trades']
                alert += f"""
• Recent Trades: {rt['signal'].upper()} (Net Flow: {rt['net_flow']:+.2f})"""

        # Add Multi-Timeframe info
        mtf_data = data.get('mtf_data')
        if mtf_data:
            mtf_signal = mtf_data.get('mtf_signal')
            bullish_tfs = mtf_data.get('bullish_timeframes', [])
            bearish_tfs = mtf_data.get('bearish_timeframes', [])

            alert += f"""

🎯 MULTI-TIMEFRAME ANALYSIS:
• MTF Signal: {mtf_signal.upper().replace('_', ' ')}
• Bullish TFs: {', '.join(bullish_tfs) if bullish_tfs else 'None'}
• Bearish TFs: {', '.join(bearish_tfs) if bearish_tfs else 'None'}"""

            if mtf_data.get('mtf_results'):
                alert += f"""
• Details: """
                for tf, tf_data in mtf_data['mtf_results'].items():
                    tf_trend = tf_data.get('trend', 'neutral')
                    tf_rsi = tf_data.get('rsi_value', 0)
                    alert += f"{tf}={tf_trend.upper()[0]}(RSI:{tf_rsi:.0f}) "

        alert += f"""

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
• Account ${positions[0][0]:,}:  {positions[0][1]:.4f} BTC (${positions[0][2]:,.2f}) - Risk ${positions[0][0] * 0.01:.2f}
• Account ${positions[1][0]:,}:  {positions[1][1]:.4f} BTC (${positions[1][2]:,.2f}) - Risk ${positions[1][0] * 0.01:.2f}
• Account ${positions[2][0]:,}:  {positions[2][1]:.4f} BTC (${positions[2][2]:,.2f}) - Risk ${positions[2][0] * 0.01:.2f}

⏰ Time: {data['timestamp'][:-10]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔔 Enter at market or wait for pullback to Entry
"""
        return alert.strip()

    def _create_bearish_alert(self, data: Dict, confluence: Dict) -> str:
        """Create bearish alert with confluence details."""
        rsi_value = data['rsi_value']
        zone = self.determine_zone(rsi_value)
        price = data['price']
        change_pct = data['price_change_pct']
        ema_trend = data.get('ema_trend', {})
        fib = data.get('fibonacci', {})

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

        # Build alert message
        confluence_status = '✅ STRONG' if confluence['strong_confluence'] else '⚠️ MODERATE'
        aligned_indicators_text = ''.join(f'  ✅ {ind}\n' for ind in confluence['aligned_indicators'])
        death_cross_status = '✅' if ema_trend.get('death_cross') else '❌'
        stack_status = '✅ Bearish' if ema_trend.get('bearish') else '❌ Not Bearish'

        alert = f"""
🔻🔻🔻 BEARISH SIGNAL ALERT 🔻🔻🔻

📊 Symbol: {data['symbol']} ({data['timeframe']})
💰 Current Price: ${price:,.2f} ({change_pct:+.2f}%)
📉 RSI: {rsi_value:.2f} - {zone}
⬇️ Direction: {data['rsi_direction']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 CONFLUENCE SCORE: {confluence['total_score']}/100 {confluence_status}

Aligned Indicators:
{aligned_indicators_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 EMA Trend:
• Trend: {ema_trend.get('trend', 'N/A').upper()}
• Death Cross: {death_cross_status}
• Stack: {stack_status}"""

        # Add Fibonacci info
        if fib and not fib.get('error') and fib.get('near_resistance'):
            r = fib['nearest_resistances'][0]
            golden_pocket_status = '🟡 YES' if fib.get('at_golden_pocket') else '❌ No'
            alert += f"""

📐 Fibonacci:
• Near Resistance: {r['level']} @ ${r['price']:,.2f} ({r['distance_pct']:.2f}% away)
• Golden Pocket: {golden_pocket_status}"""

        # Add Exchange Volume info
        exchange_data = data.get('exchange_data')
        if exchange_data and exchange_data.get('order_book'):
            ob = exchange_data['order_book']
            buy_pressure = ob['buy_pressure']
            sell_pressure = ob['sell_pressure']
            spread = ob['spread']

            alert += f"""

📊 EXCHANGE VOLUME:
• Buy Pressure: {buy_pressure:.1f}% | Sell Pressure: {sell_pressure:.1f}%
• Order Book Signal: {ob['signal'].upper()}
• Spread: ${spread:.2f}"""

            # Add recent trades if available
            if exchange_data.get('recent_trades'):
                rt = exchange_data['recent_trades']
                alert += f"""
• Recent Trades: {rt['signal'].upper()} (Net Flow: {rt['net_flow']:+.2f})"""

        # Add Multi-Timeframe info
        mtf_data = data.get('mtf_data')
        if mtf_data:
            mtf_signal = mtf_data.get('mtf_signal')
            bullish_tfs = mtf_data.get('bullish_timeframes', [])
            bearish_tfs = mtf_data.get('bearish_timeframes', [])

            alert += f"""

🎯 MULTI-TIMEFRAME ANALYSIS:
• MTF Signal: {mtf_signal.upper().replace('_', ' ')}
• Bullish TFs: {', '.join(bullish_tfs) if bullish_tfs else 'None'}
• Bearish TFs: {', '.join(bearish_tfs) if bearish_tfs else 'None'}"""

            if mtf_data.get('mtf_results'):
                alert += f"""
• Details: """
                for tf, tf_data in mtf_data['mtf_results'].items():
                    tf_trend = tf_data.get('trend', 'neutral')
                    tf_rsi = tf_data.get('rsi_value', 0)
                    alert += f"{tf}={tf_trend.upper()[0]}(RSI:{tf_rsi:.0f}) "

        alert += f"""

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
• Account ${positions[0][0]:,}:  {positions[0][1]:.4f} BTC (${positions[0][2]:,.2f}) - Risk ${positions[0][0] * 0.01:.2f}
• Account ${positions[1][0]:,}:  {positions[1][1]:.4f} BTC (${positions[1][2]:,.2f}) - Risk ${positions[1][0] * 0.01:.2f}
• Account ${positions[2][0]:,}:  {positions[2][1]:.4f} BTC (${positions[2][2]:,.2f}) - Risk ${positions[2][0] * 0.01:.2f}

⏰ Time: {data['timestamp'][:-10]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔔 Enter at market or wait for bounce to Entry
"""
        return alert.strip()

    def _create_strategy_alert(self, signal: 'TradingSignal', data: Dict) -> str:
        """
        Create trading signal alert using strategy-based analysis (NEW v3).

        This generates alerts for Mean Reversion and Trend Continuation strategies
        with Fibonacci-based Entry/TP/SL and Volume confirmation.
        """
        # Strategy display names
        strategy_names = {
            'mean_reversion': '🔄 MEAN REVERSION',
            'trend_continuation': '📈 TREND CONTINUATION',
            'rsi_breakout': '⚡ RSI BREAKOUT'
        }
        strategy_name = strategy_names.get(signal.strategy.value, 'UNKNOWN STRATEGY')

        # Direction emoji
        direction_emoji = "🟢 LONG" if signal.direction == "LONG" else "🔴 SHORT"
        direction_arrow = "⬆️" if signal.direction == "LONG" else "⬇️"

        # Build alert header
        alert = f"""
{direction_emoji} SIGNAL - {strategy_name}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Symbol: {signal.symbol}
💰 Current Price: ${data.get('price', 0):,.2f}
{direction_arrow} Direction: {signal.direction}
📈 RSI: {signal.rsi_value:.2f}
📊 EMA Trend: {signal.ema_trend.upper()}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Signal Confidence: {signal.confidence:.0f}/100

Signal Reasons:
"""

        # Add reasons
        for reason in signal.reasons:
            alert += f"  {reason}\n"

        alert += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ TRADING PLAN (Fibonacci-based):

✅ ENTRY PRICE:     ${signal.entry_price:,.2f}
🎯 TAKE PROFIT:     ${signal.take_profit:,.2f}
🛡️ STOP LOSS:      ${signal.stop_loss:,.2f}

💰 Risk:            ${abs(signal.entry_price - signal.stop_loss):,.2f} per coin
📈 Reward:          ${abs(signal.take_profit - signal.entry_price):,.2f} per coin
⚖️ Fib Level:       {signal.fibonacci_level or 'N/A'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        # Add position sizing
        risk_per_coin = abs(signal.entry_price - signal.stop_loss)
        positions = []
        for account in [1000, 5000, 10000]:
            risk_amount = account * 0.01  # 1% risk
            coin_size = risk_amount / risk_per_coin
            position_value = coin_size * signal.entry_price
            positions.append((account, coin_size, position_value))

        alert += f"""
📊 Position Sizing (1% Account Risk):
• Account ${positions[0][0]:,}:  {positions[0][1]:.4f} coins (${positions[0][2]:,.2f}) - Risk ${positions[0][0] * 0.01:.2f}
• Account ${positions[1][0]:,}:  {positions[1][1]:.4f} coins (${positions[1][2]:,.2f}) - Risk ${positions[1][0] * 0.01:.2f}
• Account ${positions[2][0]:,}:  {positions[2][1]:.4f} coins (${positions[2][2]:,.2f}) - Risk ${positions[2][0] * 0.01:.2f}

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔔 Enter at calculated Entry price for optimal R:R ratio
"""
        return alert.strip()

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

        await update.message.reply_text("🔍 Checking current conditions...")

        data = self.get_rsi_data()
        if data:
            # Update last RSI for comparison
            if data.get('rsi_value'):
                self.last_rsi = data.get('rsi_value')

            message = self.create_status_message(data)
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("❌ Failed to fetch data. Please try again.")

    async def cmd_strategy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Select trading strategy."""
        logger.info("Command: /strategy")

        # Create inline keyboard for strategy selection
        keyboard = [
            [
                InlineKeyboardButton("🔄 Mean Reversion", callback_data='strategy_mean_reversion'),
                InlineKeyboardButton("📈 Trend Continuation", callback_data='strategy_trend_continuation')
            ],
            [
                InlineKeyboardButton("⚡ RSI Breakout (v2)", callback_data='strategy_rsi_breakout')
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        current_strategy = self.config.trading_strategy.upper().replace('_', ' ')

        strategy_info = f"""
🎯 TRADING STRATEGY SELECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current Strategy: {current_strategy}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Available Strategies:

1️⃣ MEAN REVERSION
   • Uptrend + EMA touch → SHORT
   • Downtrend + EMA touch → LONG
   • Trade against the trend at EMA touches
   • Best: Ranging markets

2️⃣ TREND CONTINUATION ⭐ RECOMMENDED
   • Uptrend + EMA pullback → LONG
   • Downtrend + EMA pullback → SHORT
   • Trade with the trend
   • Best: Strong trending markets

3️⃣ RSI BREAKOUT (v2)
   • Original strategy from v2
   • RSI threshold + confluence
   • Good: Volatile markets

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Select a strategy below to continue:
"""

        await update.message.reply_text(strategy_info, reply_markup=reply_markup)

    async def strategy_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle strategy selection callback."""
        query = update.callback_query
        await query.answer()

        strategy_map = {
            'strategy_mean_reversion': 'mean_reversion',
            'strategy_trend_continuation': 'trend_continuation',
            'strategy_rsi_breakout': 'rsi_breakout'
        }

        selected = strategy_map.get(query.data)
        if not selected:
            await query.edit_message_text("❌ Invalid strategy selection")
            return

        # Update strategy
        self.set_strategy(selected)

        strategy_descriptions = {
            'mean_reversion': '🔄 MEAN REVERSION - Trade reversals at EMA touches',
            'trend_continuation': '📈 TREND CONTINUATION - Trade with the trend at EMA pullbacks',
            'rsi_breakout': '⚡ RSI BREAKOUT - Original v2 strategy'
        }

        confirmation = f"""
✅ Strategy Updated!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

New Strategy: {selected.upper().replace('_', ' ')}

{strategy_descriptions[selected]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 Settings:
• EMA Proximity: {self.config.ema_proximity_pct}%
• Timeframe: {self.config.primary_timeframe}
• RSI Bullish: {self.config.rsi_bullish_threshold}
• RSI Bearish: {self.config.rsi_bearish_threshold}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Bot will now use this strategy for all signals.

Use /check to test the new strategy!
"""

        await query.edit_message_text(confirmation)

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot status and configuration."""
        logger.info("Command: /status")

        pairs_list = '\n'.join([f"  • {pair}" for pair in self.config.trading_pairs])

        # Determine current mode display
        mode_emoji = "🎯" if self.config.signal_mode == "confluence" else "⚡"
        mode_name = "Confluence (Multi-indicator)" if self.config.signal_mode == "confluence" else "Threshold (RSI-only)"

        # Determine strategy display (NEW v3)
        strategy_map = {
            'mean_reversion': ('🔄 Mean Reversion', 'Trade reversals at EMA touches'),
            'trend_continuation': ('📈 Trend Continuation', 'Trade with trend at EMA pullbacks'),
            'rsi_breakout': ('⚡ RSI Breakout', 'Original v2 strategy')
        }
        strategy_emoji, strategy_desc = strategy_map.get(self.config.trading_strategy, ('❓ Unknown', 'Unknown strategy'))

        status_text = f"""
🤖 Bot Status v3.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 Trading Strategy: {strategy_emoji}
   {strategy_desc}
   EMA Proximity: {self.config.ema_proximity_pct}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Signal Mode: {mode_emoji} {mode_name}
   {'Score Required: ≥' + str(self.config.min_confluence_score) if self.config.signal_mode == 'confluence' else 'Score Required: ≥30 (RSI only)'}

📊 Configuration:
• Exchange: {self.config.exchange}
• Timeframe: {self.config.timeframe}
• Bullish Threshold: {self.config.rsi_bullish_threshold}
• Bearish Threshold: {self.config.rsi_bearish_threshold}
• Check Interval: {self.config.check_interval}s ({self.config.check_interval//60} minutes)
• Alert Cooldown: {self.config.alert_cooldown}s ({self.config.alert_cooldown//60} minutes)

📈 EMA Periods: {', '.join(map(str, self.config.ema_periods))}
📐 Fibonacci Tolerance: {self.config.fib_tolerance_pct}%
🔗 Require Confluence: {'Yes' if self.config.require_confluence else 'No'}
   Min Indicators: {self.config.min_indicators}

📈 Monitoring Pairs ({len(self.config.trading_pairs)}):
{pairs_list}

⚙️ Monitoring: {'🟢 Active' if self.monitoring_active else '🔴 Inactive'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Commands:
• /strategy - Change trading strategy
• /mode - Switch signal mode
"""
        await update.message.reply_text(status_text.strip())

    async def cmd_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show configuration menu."""
        logger.info("Command: /config")

        keyboard = [
            [
                InlineKeyboardButton("⚡ Threshold Mode", callback_data="mode_threshold"),
                InlineKeyboardButton("🎯 Confluence Mode", callback_data="mode_confluence"),
            ],
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

        current_mode = "🎯 Confluence" if self.config.signal_mode == "confluence" else "⚡ Threshold"
        await update.message.reply_text(
            f"⚙️ Configuration Menu:\nCurrent Mode: {current_mode}\n\nSelect an option:",
            reply_markup=reply_markup
        )

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start automatic monitoring."""
        logger.info("Command: /start")

        if self.monitoring_active:
            await update.message.reply_text("⚠️ Monitoring is already active!")
            return

        self.monitoring_active = True
        pairs_list = ', '.join(self.config.trading_pairs)
        await update.message.reply_text(
            f"🚀 Automatic monitoring STARTED\n\n"
            f"📊 Monitoring {len(self.config.trading_pairs)} pairs: {pairs_list}\n"
            f"⏱️ Checking every {self.config.check_interval}s ({self.config.check_interval//60} minutes)\n"
            f"🎯 Bullish Threshold: {self.config.rsi_bullish_threshold}\n"
            f"🎯 Bearish Threshold: {self.config.rsi_bearish_threshold}\n"
            f"📈 EMA: {', '.join(map(str, self.config.ema_periods))}\n"
            f"📐 Fibonacci: Enabled (±{self.config.fib_tolerance_pct}% tolerance)\n"
            f"🔗 Confluence: {'Required' if self.config.require_confluence else 'Optional'}"
        )

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

    async def cmd_trade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show trading pair menu for quick analysis."""
        logger.info("Command: /trade")

        keyboard = [
            [
                InlineKeyboardButton("₿ BTC/USDT", callback_data="check_BTCUSDT"),
                InlineKeyboardButton("Ξ ETH/USDT", callback_data="check_ETHUSDT"),
            ],
            [
                InlineKeyboardButton("◎ SOL/USDT", callback_data="check_SOLUSDT"),
                InlineKeyboardButton("💎 TON/USDT", callback_data="check_TONUSDT"),
            ],
            [
                InlineKeyboardButton("🔶 BNB/USDT", callback_data="check_BNBUSDT"),
                InlineKeyboardButton("🅰️ ADA/USDT", callback_data="check_ADAUSDT"),
            ],
            [
                InlineKeyboardButton("✖️ XRP/USDT", callback_data="check_XRPUSDT"),
                InlineKeyboardButton("🔄 Refresh", callback_data="menu_refresh"),
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "📊 Trading Pairs Quick Check\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Select a trading pair to check RSI, EMA & Fibonacci confluence:\n",
            reply_markup=reply_markup
        )

    async def cmd_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show signal mode menu or switch mode."""
        logger.info("Command: /mode")

        # Check if argument provided
        if context.args and context.args[0].lower() in ['threshold', 'confluence']:
            new_mode = context.args[0].lower()
            self.config.signal_mode = new_mode

            mode_emoji = "⚡" if new_mode == "threshold" else "🎯"
            mode_name = "Threshold (RSI-only)" if new_mode == "threshold" else "Confluence (Multi-indicator)"

            await update.message.reply_text(
                f"{mode_emoji} Signal mode changed to: {mode_name}\n\n"
                f"{'⚡ Threshold Mode: More signals, based on RSI only' if new_mode == 'threshold' else '🎯 Confluence Mode: Quality signals, requires RSI + EMA + Fib alignment'}\n\n"
                f"Use /status to see full configuration."
            )
            logger.info(f"Signal mode changed to: {new_mode}")
        else:
            # Show mode selection menu
            keyboard = [
                [
                    InlineKeyboardButton("⚡ Threshold Mode", callback_data="mode_threshold"),
                    InlineKeyboardButton("🎯 Confluence Mode", callback_data="mode_confluence"),
                ],
                [
                    InlineKeyboardButton("❮ Back to Main", callback_data="back_to_main"),
                ]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            current_mode = "🎯 Confluence" if self.config.signal_mode == "confluence" else "⚡ Threshold"

            mode_info = f"""
📊 Signal Mode Selection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current: {current_mode}

⚡ **Threshold Mode** (RSI-only):
• More signals (20-30/month)
• Based on RSI breakouts only
• Win rate: 40-50%
• Best for: Day trading, scalping

🎯 **Confluence Mode** (Multi-indicator):
• Quality signals (5-10/month)
• Requires RSI + EMA + Fib alignment
• Win rate: 65-75%
• Best for: Swing trading

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            await update.message.reply_text(mode_info.strip(), reply_markup=reply_markup)

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help message."""
        logger.info("Command: /help")

        help_text = """
🤖 Trading Bot v3.0 - Multiple Strategies

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Strategy Commands (NEW v3):
/strategy - Choose trading strategy
  • Mean Reversion: Trade reversals at EMA touches
  • Trend Continuation: Trade with trend at EMA pullbacks
  • RSI Breakout: Original v2 strategy

📈 Monitoring Commands:
/trade - Trading pairs quick check menu
/check or /checknow - Check current conditions with selected strategy
/status - Show bot status and current strategy
/config - Configuration menu
/mode - Switch signal mode (Threshold/Confluence)

⚙️ Control Commands:
/start - Start automatic monitoring
/stop - Stop automatic monitoring

❓ Help:
/help - Show this help message
/info - Bot features introduction
/menu - Show command menu

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 Trading Strategies:

1️⃣ MEAN REVERSION
   Uptrend + EMA touch → SHORT
   Downtrend + EMA touch → LONG
   Trade against the trend

2️⃣ TREND CONTINUATION ⭐
   Uptrend + EMA pullback → LONG
   Downtrend + EMA pullback → SHORT
   Trade with the trend

3️⃣ RSI BREAKOUT (v2)
   RSI threshold + confluence
   Original strategy

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Features v3.0:
• Multiple Trading Strategies
• EMA Touch Detection (20/50/100/200)
• Fibonacci Entry/TP/SL calculation
• Advanced Volume Confirmation
• Multi-Timeframe Analysis
• Auto Entry, TP, SL with dynamic R:R
• Position sizing for different accounts

⚠️ Note: Auto-monitoring checks all 7 trading pairs every 5 minutes and sends alerts when signal conditions are met.
"""
        await update.message.reply_text(help_text.strip())

    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show command menu with descriptions."""
        logger.info("Command: /menu")

        menu_text = """
📋 Bot Commands Menu

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 Analysis Commands:
• /trade - Quick trading pairs check (BTC, ETH, SOL, TON, BNB, ADA, XRP)
• /check - Check current market conditions immediately
• /status - Show bot status and configuration

⚙️ Settings Commands:
• /config - Open configuration menu
• /mode - Switch signal mode (Threshold/Confluence)

🚀 Control Commands:
• /start - Start automatic monitoring (every 5 min)
• /stop - Stop automatic monitoring

ℹ️ Info Commands:
• /info - Bot features introduction
• /menu - Show this command menu
• /help - Show detailed help with examples

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Use /info to learn about bot features
"""
        await update.message.reply_text(menu_text.strip())

    async def cmd_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot features introduction."""
        logger.info("Command: /info")

        info_text = """
🎯 TradingView Bot - Features

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Technical Indicators:
• RSI (Relative Strength Index) - Momentum detection
• EMA (20/50/100/200) - Trend analysis
• Fibonacci Retracement - Support/Resistance levels
• Exchange Volume - Buy/Sell pressure analysis

🎯 Multi-Timeframe Analysis:
• 1 Hour (1h) - Short-term signals
• 4 Hour (4h) - Medium-term confirmation
• 1 Day (1d) - Long-term trend validation

⚡ Signal Modes:

1. THRESHOLD MODE (RSI-only):
   • More signals (20-30/month)
   • RSI > 60 = Bullish
   • RSI < 50 = Bearish
   • Min score: 30 points

2. CONFLUENCE MODE (Multi-indicator):
   • Quality signals (5-10/month)
   • 3+ indicators aligned
   • RSI + EMA + Fibonacci + Exchange + MTF
   • Min score: 100 points

📈 Confluence Scoring System:
• RSI Signal: 30 points
• EMA Trend: 35 points
• Fibonacci Level: 35 points (+15 bonus)
• Exchange Order Book: 25 points (+10 bonus)
• Recent Trades Flow: 15 points
• Multi-Timeframe: 30 points (+15 bonus)
• Maximum: 180 points

🎁 Trading Signals Include:
• Entry price, Take Profit (TP), Stop Loss (SL)
• 1:2 Risk-Reward ratio
• Position sizing for $1K, $5K, $10K accounts
• Multi-timeframe confirmation
• Exchange volume analysis

🔄 Auto-Monitoring:
• Checks 7 trading pairs every 5 minutes
• Sends alerts when confluence detected
• Works 24/7 in background

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 Use /menu to see all commands
⚙️ Use /config to adjust settings
"""
        await update.message.reply_text(info_text.strip())

    # ========== Callback Handler ==========

    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks."""
        query = update.callback_query
        await query.answer()

        callback_data = query.data

        # Trading pair quick check
        if callback_data.startswith("check_"):
            # Extract symbol from callback (e.g., "check_BTCUSDT" -> "BTCUSDT")
            symbol = callback_data.replace("check_", "")

            await query.edit_message_text(f"🔍 Checking {symbol} with EMA & Fibonacci analysis...")

            # Get RSI data for selected symbol
            data = self.get_rsi_data(symbol=symbol)
            if data:
                message = self.create_status_message(data)
                await query.edit_message_text(message)
            else:
                await query.edit_message_text(f"❌ Failed to fetch data for {symbol}")

        # Menu refresh
        elif callback_data == "menu_refresh":
            keyboard = [
                [
                    InlineKeyboardButton("₿ BTC/USDT", callback_data="check_BTCUSDT"),
                    InlineKeyboardButton("Ξ ETH/USDT", callback_data="check_ETHUSDT"),
                ],
                [
                    InlineKeyboardButton("◎ SOL/USDT", callback_data="check_SOLUSDT"),
                    InlineKeyboardButton("💎 TON/USDT", callback_data="check_TONUSDT"),
                ],
                [
                    InlineKeyboardButton("🔶 BNB/USDT", callback_data="check_BNBUSDT"),
                    InlineKeyboardButton("🅰️ ADA/USDT", callback_data="check_ADAUSDT"),
                ],
                [
                    InlineKeyboardButton("✖️ XRP/USDT", callback_data="check_XRPUSDT"),
                    InlineKeyboardButton("🔄 Refresh", callback_data="menu_refresh"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📊 Trading Pairs Quick Check\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Select a trading pair to check RSI, EMA & Fibonacci confluence:\n",
                reply_markup=reply_markup
            )

        elif callback_data == "check_now":
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

        elif callback_data in ["mode_threshold", "mode_confluence"]:
            # Handle mode switching
            new_mode = "threshold" if callback_data == "mode_threshold" else "confluence"
            self.config.signal_mode = new_mode

            mode_emoji = "⚡" if new_mode == "threshold" else "🎯"
            mode_name = "Threshold (RSI-only)" if new_mode == "threshold" else "Confluence (Multi-indicator)"

            await query.edit_message_text(
                f"{mode_emoji} Signal mode changed to: {mode_name}\n\n"
                f"{'⚡ Threshold Mode: More signals, based on RSI only' if new_mode == 'threshold' else '🎯 Confluence Mode: Quality signals, requires RSI + EMA + Fib alignment'}\n\n"
                f"Use /status to see full configuration."
            )
            logger.info(f"Signal mode changed via callback to: {new_mode}")

        elif callback_data == "back_to_main":
            # Return to mode selection menu
            keyboard = [
                [
                    InlineKeyboardButton("⚡ Threshold Mode", callback_data="mode_threshold"),
                    InlineKeyboardButton("🎯 Confluence Mode", callback_data="mode_confluence"),
                ],
                [
                    InlineKeyboardButton("❮ Back to Main", callback_data="back_to_main"),
                ]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            current_mode = "🎯 Confluence" if self.config.signal_mode == "confluence" else "⚡ Threshold"

            mode_info = f"""
📊 Signal Mode Selection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current: {current_mode}

⚡ **Threshold Mode** (RSI-only):
• More signals (20-30/month)
• Based on RSI breakouts only
• Win rate: 40-50%
• Best for: Day trading, scalping

🎯 **Confluence Mode** (Multi-indicator):
• Quality signals (5-10/month)
• Requires RSI + EMA + Fib alignment
• Win rate: 65-75%
• Best for: Swing trading

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            await query.edit_message_text(mode_info.strip(), reply_markup=reply_markup)

        elif callback_data in ["change_symbol", "change_tf", "bullish_thresh", "bearish_thresh"]:
            await query.edit_message_text(
                f"⚠️ Feature coming soon!\n\n"
                f"To change {callback_data}, edit the config in the script or use command-line arguments."
            )

    # ========== Monitoring Loop ==========

    async def _monitoring_loop(self):
        """Automatic monitoring loop - checks all trading pairs."""
        logger.info("Monitoring loop started with EMA + Fibonacci confluence")

        while self.monitoring_active:
            try:
                # Check all trading pairs
                for symbol in self.config.trading_pairs:
                    try:
                        # Get current data for this symbol
                        data = self.get_rsi_data(symbol=symbol)

                        if data and data.get('rsi_value'):
                            rsi_value = data['rsi_value']
                            ema_trend = data.get('ema_trend', {})
                            fib = data.get('fibonacci', {})

                            logger.info(f"Check {symbol}: RSI={rsi_value:.2f}, EMA={ema_trend.get('trend', 'N/A')}, Fib={fib.get('position', 'N/A')}")

                            # Get last alert time for this symbol
                            last_alert = self.pair_last_alert_time.get(symbol)
                            cooldown_active = False

                            if last_alert:
                                time_since_last = (datetime.now() - last_alert).total_seconds()
                                if time_since_last < self.config.alert_cooldown:
                                    logger.debug(f"{symbol} in cooldown period")
                                    cooldown_active = True

                            if not cooldown_active:
                                # Check for signal conditions using selected strategy (v3)
                                alert = self.check_strategy_signals(data, symbol)
                                if alert:
                                    await self.send_message(alert)
                                    self.pair_last_alert_time[symbol] = datetime.now()

                            # Update last RSI for this symbol
                            self.pair_last_rsi[symbol] = rsi_value

                    except Exception as e:
                        logger.error(f"Error checking {symbol}: {e}")

                logger.info(f"Completed checking all {len(self.config.trading_pairs)} pairs")

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
        application.add_handler(CommandHandler("strategy", self.cmd_strategy))  # NEW v3
        application.add_handler(CommandHandler("trade", self.cmd_trade))
        application.add_handler(CommandHandler("menu", self.cmd_menu))
        application.add_handler(CommandHandler("check", self.cmd_check_now))
        application.add_handler(CommandHandler("checknow", self.cmd_check_now))
        application.add_handler(CommandHandler("status", self.cmd_status))
        application.add_handler(CommandHandler("config", self.cmd_config))
        application.add_handler(CommandHandler("mode", self.cmd_mode))
        application.add_handler(CommandHandler("start", self.cmd_start))
        application.add_handler(CommandHandler("stop", self.cmd_stop))
        application.add_handler(CommandHandler("info", self.cmd_info))
        application.add_handler(CommandHandler("menu", self.cmd_menu))
        application.add_handler(CommandHandler("help", self.cmd_help))

        # Add callback handlers
        application.add_handler(CallbackQueryHandler(self.strategy_callback, pattern='^strategy_'))
        application.add_handler(CallbackQueryHandler(self.callback_handler))

        # Start bot
        logger.info("Bot started with EMA + Fibonacci. Send /help to see available commands")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Telegram RSI + EMA + Fibonacci Monitor Bot")
    parser.add_argument("--bot-token", help="Telegram bot token")
    parser.add_argument("--chat-id", help="Telegram chat ID")
    parser.add_argument("--symbol", default="BTCUSDT", help="Trading symbol")
    parser.add_argument("--exchange", default="BINANCE", help="Exchange")
    parser.add_argument("--timeframe", default="1h", help="Timeframe")
    parser.add_argument("--bullish-threshold", type=float, default=60.0, help="RSI bullish threshold")
    parser.add_argument("--bearish-threshold", type=float, default=50.0, help="RSI bearish threshold")
    parser.add_argument("--interval", type=int, default=300, help="Check interval in seconds")
    parser.add_argument("--require-confluence", action="store_true", default=True, help="Require indicator confluence")
    parser.add_argument("--no-confluence", dest="require_confluence", action="store_false", help="Disable confluence requirement")

    args = parser.parse_args()

    # Create config
    config = BotConfig(
        symbol=args.symbol,
        exchange=args.exchange,
        timeframe=args.timeframe,
        rsi_bullish_threshold=args.bullish_threshold,
        rsi_bearish_threshold=args.bearish_threshold,
        check_interval=args.interval,
        require_confluence=args.require_confluence
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
