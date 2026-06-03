#!/usr/bin/env python3
"""
Trading Strategies Module
Implements 2 trading strategies:
1. Mean Reversion - Trade against the trend at EMA touches
2. Trend Continuation - Trade with the trend at EMA pullbacks
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class StrategyType(Enum):
    """Trading strategy types."""
    MEAN_REVERSION = "mean_reversion"
    TREND_CONTINUATION = "trend_continuation"
    RSI_BREAKOUT = "rsi_breakout"  # Original strategy


@dataclass
class EMATouchSignal:
    """EMA Touch Detection result."""
    touched: bool
    ema_period: int
    ema_price: float
    current_price: float
    distance_pct: float
    touch_type: str  # "support" or "resistance"
    proximity_strength: str  # "strong", "moderate", "weak"


@dataclass
class TradingSignal:
    """Complete trading signal."""
    symbol: str
    strategy: StrategyType
    direction: str  # "LONG" or "SHORT"
    entry_price: float
    take_profit: float
    stop_loss: float
    confidence: float  # 0-100
    reasons: List[str]
    rsi_value: float
    ema_trend: str
    fibonacci_level: Optional[str] = None
    volume_confidence: Optional[float] = None


class EMATouchDetector:
    """Detect when price touches EMA lines."""

    def __init__(self, proximity_threshold: float = 0.5):
        """
        Args:
            proximity_threshold: Maximum % distance to consider as "touch" (default 0.5%)
        """
        self.proximity_threshold = proximity_threshold

    def detect_touch(self, current_price: float, ema: Dict[str, float]) -> List[EMATouchSignal]:
        """
        Detect if price is touching any EMA line.

        Args:
            current_price: Current market price
            ema: Dictionary with ema20, ema50, ema100, ema200 values

        Returns:
            List of EMATouchSignal objects
        """
        signals = []

        for period in [20, 50, 100, 200]:
            ema_value = ema.get(f'ema{period}')
            if not ema_value:
                continue

            # Calculate distance percentage
            distance_pct = abs((current_price - ema_value) / ema_value) * 100

            # Check if price is touching this EMA
            if distance_pct <= self.proximity_threshold:
                # Determine if EMA is acting as support or resistance
                if current_price > ema_value:
                    touch_type = "support"  # Price above EMA, EMA acting as support
                else:
                    touch_type = "resistance"  # Price below EMA, EMA acting as resistance

                # Determine strength based on proximity
                if distance_pct <= 0.2:
                    strength = "strong"
                elif distance_pct <= 0.35:
                    strength = "moderate"
                else:
                    strength = "weak"

                signals.append(EMATouchSignal(
                    touched=True,
                    ema_period=period,
                    ema_price=ema_value,
                    current_price=current_price,
                    distance_pct=distance_pct,
                    touch_type=touch_type,
                    proximity_strength=strength
                ))

        return signals


class FibonacciCalculator:
    """Calculate Entry, TP, SL using Fibonacci levels."""

    # Fibonacci retracement levels
    FIB_LEVELS = {
        "0%": 0.0,
        "23.6%": 0.236,
        "38.2%": 0.382,
        "50%": 0.5,
        "61.8%": 0.618,  # Golden Pocket
        "78.6%": 0.786,
        "100%": 1.0
    }

    # Fibonacci extension levels for TP
    FIB_EXTENSIONS = {
        "127.2%": 1.272,
        "161.8%": 1.618,  # Golden Extension
        "261.8%": 2.618
    }

    def calculate_entry_tp_sl(
        self,
        current_price: float,
        direction: str,
        swing_high: float,
        swing_low: float,
        risk_reward_ratio: float = 2.0
    ) -> Dict[str, Any]:
        """
        Calculate Entry, TP, SL based on Fibonacci levels.

        Args:
            current_price: Current market price
            direction: "LONG" or "SHORT"
            swing_high: Recent swing high
            swing_low: Recent swing low
            risk_reward_ratio: Risk/Reward ratio (default 1:2)

        Returns:
            Dict with entry, take_profit, stop_loss, levels_used
        """
        swing_range = swing_high - swing_low

        if direction == "LONG":
            # For LONG: Entry at Fib support, SL below support, TP at extension
            # Find nearest Fib support level below current price
            fib_61_8 = swing_high - (swing_range * 0.618)
            fib_78_6 = swing_high - (swing_range * 0.786)

            # Choose entry based on which level is closer
            if abs(current_price - fib_78_6) < abs(current_price - fib_61_8):
                entry = fib_78_6
                entry_level = "78.6%"
            else:
                entry = fib_61_8
                entry_level = "61.8% (Golden Pocket)"

            # SL below the next Fib level (78.6% -> 100%)
            sl = swing_low - (swing_range * 0.1)  # 10% below swing low
            sl_level = "Below 100% retracement"

            # TP at Fib extension (127.2% or 161.8%)
            tp = swing_high + (swing_range * 0.618)  # 161.8% extension
            tp_level = "161.8% extension"

        else:  # SHORT
            # For SHORT: Entry at Fib resistance, SL above resistance, TP at extension
            fib_61_8 = swing_low + (swing_range * 0.618)
            fib_78_6 = swing_low + (swing_range * 0.786)

            # Choose entry based on which level is closer
            if abs(current_price - fib_78_6) < abs(current_price - fib_61_8):
                entry = fib_78_6
                entry_level = "78.6%"
            else:
                entry = fib_61_8
                entry_level = "61.8% (Golden Pocket)"

            # SL above the next Fib level
            sl = swing_high + (swing_range * 0.1)  # 10% above swing high
            sl_level = "Above 100% retracement"

            # TP at Fib extension
            tp = swing_low - (swing_range * 0.618)  # 161.8% extension
            tp_level = "161.8% extension"

        # Calculate risk and reward
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        actual_rr = reward / risk if risk > 0 else 0

        return {
            "entry": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "entry_level": entry_level,
            "tp_level": tp_level,
            "sl_level": sl_level,
            "risk_amount": risk,
            "reward_amount": reward,
            "risk_reward_ratio": f"1:{actual_rr:.1f}",
            "swing_high": swing_high,
            "swing_low": swing_low
        }


class VolumeAnalyzer:
    """Analyze volume to confirm trading signals."""

    def __init__(self):
        self.min_volume_ratio = 1.5  # Volume should be 1.5x average for confirmation

    def analyze_volume_confirmation(
        self,
        exchange_data: Dict[str, Any],
        direction: str
    ) -> Dict[str, Any]:
        """
        Analyze volume data to confirm trading signal.

        Args:
            exchange_data: Exchange data with order_book and recent_trades
            direction: "LONG" or "SHORT"

        Returns:
            Dict with volume confirmation result
        """
        if not exchange_data:
            return {
                "confirmed": False,
                "confidence": 0,
                "reasons": ["No exchange data available"]
            }

        confirmation_score = 0
        reasons = []
        order_book = exchange_data.get("order_book", {})
        recent_trades = exchange_data.get("recent_trades", {})

        # 1. Order Book Analysis (40 points max)
        if order_book:
            buy_pressure = order_book.get("buy_pressure", 0)
            sell_pressure = order_book.get("sell_pressure", 0)
            ob_signal = order_book.get("signal", "")

            if direction == "LONG":
                if ob_signal == "strong_buy":
                    confirmation_score += 40
                    reasons.append(f"🔥 Strong buy pressure ({buy_pressure:.0f}%)")
                elif ob_signal == "buy":
                    confirmation_score += 25
                    reasons.append(f"✓ Buy pressure ({buy_pressure:.0f}%)")
                elif buy_pressure > 55:
                    confirmation_score += 15
                    reasons.append(f"⚡ Moderate buy pressure ({buy_pressure:.0f}%)")
                else:
                    reasons.append(f"⚠️ Weak buy pressure ({buy_pressure:.0f}%)")
            else:  # SHORT
                if ob_signal == "strong_sell":
                    confirmation_score += 40
                    reasons.append(f"🔥 Strong sell pressure ({sell_pressure:.0f}%)")
                elif ob_signal == "sell":
                    confirmation_score += 25
                    reasons.append(f"✓ Sell pressure ({sell_pressure:.0f}%)")
                elif sell_pressure > 55:
                    confirmation_score += 15
                    reasons.append(f"⚡ Moderate sell pressure ({sell_pressure:.0f}%)")
                else:
                    reasons.append(f"⚠️ Weak sell pressure ({sell_pressure:.0f}%)")

        # 2. Recent Trades Analysis (30 points max)
        if recent_trades:
            net_flow = recent_trades.get("net_flow", 0)
            trades_signal = recent_trades.get("signal", "")

            if direction == "LONG" and trades_signal == "buy" and net_flow > 0:
                strength = "🔥" if net_flow > 100 else "✓" if net_flow > 50 else "⚡"
                confirmation_score += 30
                reasons.append(f"{strength} Bullish trades flow (+{net_flow:.0f})")
            elif direction == "SHORT" and trades_signal == "sell" and net_flow < 0:
                strength = "🔥" if net_flow < -100 else "✓" if net_flow < -50 else "⚡"
                confirmation_score += 30
                reasons.append(f"{strength} Bearish trades flow ({net_flow:.0f})")
            else:
                reasons.append(f"⚠️ Trades flow not aligned (signal: {trades_signal})")

        # 3. Spread Analysis (20 points max)
        if order_book:
            spread = order_book.get("spread", 0)
            # Tight spread = good liquidity
            if spread < current_price * 0.001:  # < 0.1% spread
                confirmation_score += 20
                reasons.append(f"✓ Tight spread (${spread:.2f})")
            elif spread < current_price * 0.002:  # < 0.2% spread
                confirmation_score += 10
                reasons.append(f"⚡ Moderate spread (${spread:.2f})")
            else:
                reasons.append(f"⚠️ Wide spread (${spread:.2f})")

        # 4. Imbalance Analysis (10 points max)
        if order_book:
            buy_pressure = order_book.get("buy_pressure", 0)
            sell_pressure = order_book.get("sell_pressure", 0)
            imbalance = abs(buy_pressure - sell_pressure)

            if imbalance > 60:
                confirmation_score += 10
                reasons.append(f"✓ Strong imbalance ({imbalance:.0f}%)")
            elif imbalance > 40:
                confirmation_score += 5
                reasons.append(f"⚡ Moderate imbalance ({imbalance:.0f}%)")

        # Determine confirmation
        confirmed = confirmation_score >= 60  # Need at least 60/100 points
        confidence = min(confirmation_score, 100)

        return {
            "confirmed": confirmed,
            "confidence": confidence,
            "score": confirmation_score,
            "reasons": reasons
        }


class MeanReversionStrategy:
    """
    Mean Reversion Strategy:
    - Uptrend → Price touches EMA → SHORT (expect reversal down)
    - Downtrend → Price touches EMA → LONG (expect reversal up)
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.ema_detector = EMATouchDetector(
            proximity_threshold=self.config.get("ema_proximity_pct", 0.5)
        )
        self.fib_calculator = FibonacciCalculator()
        self.volume_analyzer = VolumeAnalyzer()

        # RSI thresholds for mean reversion
        self.rsi_overbought = self.config.get("rsi_overbought", 70)
        self.rsi_oversold = self.config.get("rsi_oversold", 30)

    def check_signal(
        self,
        symbol: str,
        current_price: float,
        rsi_value: float,
        ema: Dict[str, float],
        ema_trend: Dict[str, Any],
        fibonacci: Dict[str, Any],
        exchange_data: Optional[Dict[str, Any]] = None
    ) -> Optional[TradingSignal]:
        """
        Check if mean reversion signal conditions are met.

        Strategy Logic:
        1. Price touches EMA (any of 20, 50, 100, 200)
        2. RSI shows extremity (overbought for SHORT, oversold for LONG)
        3. Volume confirms the reversal
        4. Fibonacci levels define Entry/TP/SL
        """
        # Step 1: Check if price is touching any EMA
        ema_touches = self.ema_detector.detect_touch(current_price, ema)
        if not ema_touches:
            return None

        # Get the most significant touch (closest to EMA)
        primary_touch = min(ema_touches, key=lambda x: x.distance_pct)

        # Step 2: Determine direction based on trend and EMA touch
        current_trend = ema_trend.get("trend", "unknown")

        reasons = [f"📍 Price touching EMA{primary_touch.ema_period} ({primary_touch.touch_type})"]

        # Step 3: Determine signal direction
        if "uptrend" in current_trend or "bullish" in str(ema_trend.get("bullish", "")):
            # Uptrend + touching EMA → Look for SHORT reversal
            direction = "SHORT"
            reasons.append(f"📈 Uptrend ({current_trend}) + EMA touch → Mean Reversion SHORT")

            # RSI confirmation: Need overbought or showing weakness
            if rsi_value >= self.rsi_overbought:
                reasons.append(f"✓ RSI Overbought ({rsi_value:.1f} >= {self.rsi_overbought})")
            elif rsi_value > 50:
                reasons.append(f"⚡ RSI elevated ({rsi_value:.1f}) - showing weakness")
            else:
                # RSI not confirming overbought condition
                reasons.append(f"⚠️ RSI not overbought ({rsi_value:.1f}) - weak signal")

        elif "downtrend" in current_trend or "bearish" in str(ema_trend.get("bearish", "")):
            # Downtrend + touching EMA → Look for LONG reversal
            direction = "LONG"
            reasons.append(f"📉 Downtrend ({current_trend}) + EMA touch → Mean Reversion LONG")

            # RSI confirmation: Need oversold or showing strength
            if rsi_value <= self.rsi_oversold:
                reasons.append(f"✓ RSI Oversold ({rsi_value:.1f} <= {self.rsi_oversold})")
            elif rsi_value < 50:
                reasons.append(f"⚡ RSI depressed ({rsi_value:.1f}) - showing strength")
            else:
                reasons.append(f"⚠️ RSI not oversold ({rsi_value:.1f}) - weak signal")
        else:
            # Ranging market - skip
            return None

        # Step 4: Volume confirmation
        volume_conf = self.volume_analyzer.analyze_volume_confirmation(
            exchange_data, direction
        )
        reasons.extend(volume_conf["reasons"])

        if not volume_conf["confirmed"]:
            reasons.append("⚠️ Volume not confirming reversal - weak signal")
            confidence = 50
        else:
            confidence = volume_conf["confidence"]
            reasons.append(f"✓ Volume confirms reversal ({confidence:.0f}/100)")

        # Step 5: Calculate Fibonacci-based Entry/TP/SL
        swing_high = fibonacci.get("swing_high", current_price * 1.05)
        swing_low = fibonacci.get("swing_low", current_price * 0.95)

        fib_levels = self.fib_calculator.calculate_entry_tp_sl(
            current_price=current_price,
            direction=direction,
            swing_high=swing_high,
            swing_low=swing_low
        )

        reasons.append(f"📐 Entry at Fib {fib_levels['entry_level']}")
        reasons.append(f"🎯 TP at {fib_levels['tp_level']} (RR: {fib_levels['risk_reward_ratio']})")

        # Calculate final confidence (0-100)
        final_confidence = min(confidence, 100)

        return TradingSignal(
            symbol=symbol,
            strategy=StrategyType.MEAN_REVERSION,
            direction=direction,
            entry_price=fib_levels["entry"],
            take_profit=fib_levels["take_profit"],
            stop_loss=fib_levels["stop_loss"],
            confidence=final_confidence,
            reasons=reasons,
            rsi_value=rsi_value,
            ema_trend=current_trend,
            fibonacci_level=fib_levels["entry_level"],
            volume_confidence=volume_conf["confidence"]
        )


class TrendContinuationStrategy:
    """
    Trend Continuation Strategy:
    - Uptrend → Price pulls back to EMA → LONG (trend continues up)
    - Downtrend → Price pulls back to EMA → SHORT (trend continues down)
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.ema_detector = EMATouchDetector(
            proximity_threshold=self.config.get("ema_proximity_pct", 0.8)
        )
        self.fib_calculator = FibonacciCalculator()
        self.volume_analyzer = VolumeAnalyzer()

        # RSI thresholds for trend continuation
        self.rsi_bullish_min = self.config.get("rsi_bullish_min", 50)
        self.rsi_bearish_max = self.config.get("rsi_bearish_max", 50)

    def check_signal(
        self,
        symbol: str,
        current_price: float,
        rsi_value: float,
        ema: Dict[str, float],
        ema_trend: Dict[str, Any],
        fibonacci: Dict[str, Any],
        exchange_data: Optional[Dict[str, Any]] = None
    ) -> Optional[TradingSignal]:
        """
        Check if trend continuation signal conditions are met.

        Strategy Logic:
        1. Strong trend identified (EMA stack aligned)
        2. Price pulls back to EMA (not breaking it)
        3. RSI respects the trend direction
        4. Volume confirms continuation
        5. Fibonacci levels define Entry/TP/SL
        """
        # Step 1: Check trend strength
        is_bullish = ema_trend.get("bullish", False)
        is_bearish = ema_trend.get("bearish", False)
        current_trend = ema_trend.get("trend", "unknown")

        # Need strong trend (not ranging)
        if not (is_bullish or is_bearish):
            return None

        # Step 2: Check if price is near any EMA (pullback)
        ema_touches = self.ema_detector.detect_touch(current_price, ema)
        if not ema_touches:
            return None

        primary_touch = min(ema_touches, key=lambda x: x.distance_pct)

        # For continuation, EMA should act as support (LONG) or resistance (SHORT)
        reasons = [f"📍 Price pulling back to EMA{primary_touch.ema_period}"]

        # Step 3: Determine signal direction
        if is_bullish:
            # Bullish trend + pullback to EMA → LONG continuation
            direction = "LONG"
            reasons.append(f"✓ Strong Uptrend (Price > EMA stack)")

            # Price should be above EMA for support to hold
            if primary_touch.touch_type == "support":
                reasons.append(f"✓ EMA{primary_touch.ema_period} acting as SUPPORT")
            else:
                reasons.append(f"⚠️ Price below EMA - support might break")

            # RSI confirmation for LONG
            if rsi_value > self.rsi_bullish_min:
                reasons.append(f"✓ RSI bullish ({rsi_value:.1f} >= {self.rsi_bullish_min})")
            elif rsi_value > 40:
                reasons.append(f"⚡ RSI neutral-bullish ({rsi_value:.1f})")
            else:
                reasons.append(f"⚠️ RSI weak ({rsi_value:.1f}) - trend might reverse")

        elif is_bearish:
            # Bearish trend + pullback to EMA → SHORT continuation
            direction = "SHORT"
            reasons.append(f"✓ Strong Downtrend (Price < EMA stack)")

            # Price should be below EMA for resistance to hold
            if primary_touch.touch_type == "resistance":
                reasons.append(f"✓ EMA{primary_touch.ema_period} acting as RESISTANCE")
            else:
                reasons.append(f"⚠️ Price above EMA - resistance might break")

            # RSI confirmation for SHORT
            if rsi_value < self.rsi_bearish_max:
                reasons.append(f"✓ RSI bearish ({rsi_value:.1f} <= {self.rsi_bearish_max})")
            elif rsi_value < 60:
                reasons.append(f"⚡ RSI neutral-bearish ({rsi_value:.1f})")
            else:
                reasons.append(f"⚠️ RSI strong ({rsi_value:.1f}) - trend might reverse")

        # Step 4: Volume confirmation
        volume_conf = self.volume_analyzer.analyze_volume_confirmation(
            exchange_data, direction
        )
        reasons.extend(volume_conf["reasons"])

        if not volume_conf["confirmed"]:
            reasons.append("⚠️ Volume not confirming continuation - weak signal")
            confidence = 50
        else:
            confidence = volume_conf["confidence"]
            reasons.append(f"✓ Volume confirms continuation ({confidence:.0f}/100)")

        # Step 5: Calculate Fibonacci-based Entry/TP/SL
        swing_high = fibonacci.get("swing_high", current_price * 1.05)
        swing_low = fibonacci.get("swing_low", current_price * 0.95)

        fib_levels = self.fib_calculator.calculate_entry_tp_sl(
            current_price=current_price,
            direction=direction,
            swing_high=swing_high,
            swing_low=swing_low
        )

        reasons.append(f"📐 Entry at Fib {fib_levels['entry_level']}")
        reasons.append(f"🎯 TP at {fib_levels['tp_level']} (RR: {fib_levels['risk_reward_ratio']})")

        # Calculate final confidence
        final_confidence = min(confidence, 100)

        return TradingSignal(
            symbol=symbol,
            strategy=StrategyType.TREND_CONTINUATION,
            direction=direction,
            entry_price=fib_levels["entry"],
            take_profit=fib_levels["take_profit"],
            stop_loss=fib_levels["stop_loss"],
            confidence=final_confidence,
            reasons=reasons,
            rsi_value=rsi_value,
            ema_trend=current_trend,
            fibonacci_level=fib_levels["entry_level"],
            volume_confidence=volume_conf["confidence"]
        )


# Factory function to create strategy instance
def create_strategy(strategy_type: StrategyType, config: Dict[str, Any] = None):
    """Factory function to create strategy instance."""
    if strategy_type == StrategyType.MEAN_REVERSION:
        return MeanReversionStrategy(config)
    elif strategy_type == StrategyType.TREND_CONTINUATION:
        return TrendContinuationStrategy(config)
    else:
        raise ValueError(f"Unknown strategy type: {strategy_type}")
