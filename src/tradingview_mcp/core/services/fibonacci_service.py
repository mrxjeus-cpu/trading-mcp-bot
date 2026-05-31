#!/usr/bin/env python3
"""
Fibonacci Retracement & Extension Calculator for Crypto

Calculates Fibonacci levels for swing high/low analysis.
Used in conjunction with RSI and EMA for confluence trading signals.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FibonacciCalculator:
    """Calculate and analyze Fibonacci levels for trading."""

    # Fibonacci ratios
    RETRACEMENT_LEVELS = {
        "0%": 0.0,
        "23.6%": 0.236,
        "38.2%": 0.382,  # Golden Pocket
        "50%": 0.5,
        "61.8%": 0.618,  # Golden Pocket
        "78.6%": 0.786,
        "100%": 1.0
    }

    EXTENSION_LEVELS = {
        "-27%": 1.272,
        "-61.8%": 1.618,
        "-100%": 2.0,
        "-161.8%": 2.618,
        "-261.8%": 3.618
    }

    @classmethod
    def calculate_levels(cls, swing_high: float, swing_low: float) -> Dict:
        """
        Calculate Fibonacci retracement and extension levels.

        Args:
            swing_high: The swing high price
            swing_low: The swing low price

        Returns:
            Dict with retracement and extension levels
        """
        if swing_high <= swing_low:
            raise ValueError(f"Invalid swing range: high ({swing_high}) must be > low ({swing_low})")

        diff = swing_high - swing_low
        current_price = swing_low  # Default to swing low for now

        # Calculate retracement levels
        retracement = {}
        for name, ratio in cls.RETRACEMENT_LEVELS.items():
            price = swing_high - (diff * ratio)
            retracement[name] = {
                "ratio": ratio,
                "price": round(price, 2),
                "distance_from_high_pct": round(ratio * 100, 2),
                "is_golden_pocket": name in ["38.2%", "61.8%"]
            }

        # Calculate extension levels
        extension = {}
        for name, ext_ratio in cls.EXTENSION_LEVELS.items():
            price = swing_high + (diff * (ext_ratio - 1)) if ext_ratio > 1 else swing_high - (diff * abs(ext_ratio - 1))
            extension[name] = {
                "ratio": ext_ratio,
                "price": round(price, 2),
                "extension_pct": round((ext_ratio - 1) * 100, 2) if ext_ratio > 1 else round(-(1 - ext_ratio) * 100, 2)
            }

        return {
            "swing_high": round(swing_high, 2),
            "swing_low": round(swing_low, 2),
            "swing_range": round(diff, 2),
            "swing_range_pct": round((diff / swing_low) * 100, 2),
            "retracement_levels": retracement,
            "extension_levels": extension
        }

    @classmethod
    def analyze_price_position(
        cls,
        current_price: float,
        fib_levels: Dict,
        tolerance_pct: float = 2.0
    ) -> Dict:
        """
        Analyze where current price sits relative to Fibonacci levels.

        Args:
            current_price: Current trading price
            fib_levels: Fibonacci levels from calculate_levels()
            tolerance_pct: Price proximity tolerance (default 2%)

        Returns:
            Analysis with nearest supports, resistances, and position
        """
        swing_high = fib_levels["swing_high"]
        swing_low = fib_levels["swing_low"]
        retracement = fib_levels["retracement_levels"]

        current_price = float(current_price)

        # Find nearest supports (Fib levels below price)
        supports = []
        resistances = []

        for level_name, level_data in retracement.items():
            level_price = level_data["price"]
            distance_pct = abs((current_price - level_price) / current_price) * 100

            level_info = {
                "level": level_name,
                "price": level_price,
                "distance_pct": round(distance_pct, 2),
                "is_golden_pocket": level_data["is_golden_pocket"],
                "ratio": level_data["ratio"]
            }

            if level_price < current_price:
                # This is a support level
                supports.append(level_info)
            elif level_price > current_price:
                # This is a resistance level
                resistances.append(level_info)

        # Sort by distance (nearest first)
        supports.sort(key=lambda x: x["distance_pct"])
        resistances.sort(key=lambda x: x["distance_pct"])

        # Filter by tolerance
        nearby_supports = [s for s in supports if s["distance_pct"] <= tolerance_pct]
        nearby_resistances = [r for r in resistances if r["distance_pct"] <= tolerance_pct]

        # Determine position
        position = "unknown"
        if current_price >= swing_high:
            position = "above_swing_high"
        elif current_price <= swing_low:
            position = "below_swing_low"
        elif len(nearby_supports) > 0:
            position = "near_support"
        elif len(nearby_resistances) > 0:
            position = "near_resistance"
        else:
            # Calculate which zone we're in
            sorted_levels = sorted(retracement.items(), key=lambda x: x[1]["price"], reverse=True)
            for i, (level_name, level_data) in enumerate(sorted_levels):
                if current_price <= level_data["price"]:
                    position = f"between_{level_name}_and_{sorted_levels[i+1][0] if i+1 < len(sorted_levels) else 'low'}"
                    break

        return {
            "current_price": round(current_price, 2),
            "position": position,
            "nearest_supports": nearby_supports[:3],  # Top 3 nearest
            "nearest_resistances": nearby_resistances[:3],
            "all_supports": supports,
            "all_resistances": resistances,
            "near_support": len(nearby_supports) > 0,
            "near_resistance": len(nearby_resistances) > 0,
            "at_golden_pocket": any(
                s.get("is_golden_pocket") and s["distance_pct"] <= tolerance_pct
                for s in nearby_supports + nearby_resistances
            )
        }

    @classmethod
    def calculate_swing_from_indicators(cls, indicators: Dict, lookback_period: str = "52W") -> Tuple[Optional[float], Optional[float]]:
        """
        Extract or calculate swing high/low from TradingView indicators.

        Args:
            indicators: TradingView indicators dict
            lookback_period: Period for swing calculation

        Returns:
            Tuple of (swing_high, swing_low) or (None, None)
        """
        # Try to get from pivot points
        high_candidates = [
            indicators.get("Pivot.M.Fibonacci.R3"),
            indicators.get("Pivot.M.Classic.R3"),
            indicators.get("price_52_week_high"),
            indicators.get("High.52W"),
            indicators.get("High.All")
        ]

        low_candidates = [
            indicators.get("Pivot.M.Fibonacci.S3"),
            indicators.get("Pivot.M.Classic.S3"),
            indicators.get("price_52_week_low"),
            indicators.get("Low.52W"),
            indicators.get("Low.All")
        ]

        # Filter None values
        swing_high = max([h for h in high_candidates if h is not None], default=None)
        swing_low = min([l for l in low_candidates if l is not None], default=None)

        # Validate
        if swing_high and swing_low and swing_high > swing_low:
            return float(swing_high), float(swing_low)

        # Fallback: use recent high/low from indicators
        recent_high = indicators.get("high")
        recent_low = indicators.get("low")

        if recent_high and recent_low and recent_high > recent_low:
            # This is less ideal as it's just current candle
            logger.warning("Using current candle high/low as swing (not ideal)")
            return float(recent_high), float(recent_low)

        return None, None


def analyze_crypto_fibonacci(
    symbol: str,
    current_price: float,
    indicators: Optional[Dict] = None,
    swing_high: Optional[float] = None,
    swing_low: Optional[float] = None,
    tolerance_pct: float = 2.0
) -> Dict:
    """
    Complete Fibonacci analysis for crypto trading.

    Args:
        symbol: Trading symbol (e.g., 'BTCUSDT')
        current_price: Current trading price
        indicators: TradingView indicators (optional, used to auto-detect swing)
        swing_high: Manual swing high (optional)
        swing_low: Manual swing low (optional)
        tolerance_pct: Price proximity tolerance for confluence

    Returns:
        Complete Fibonacci analysis with levels and position
    """
    result = {
        "symbol": symbol,
        "timestamp": datetime.now().isoformat(),
        "error": None
    }

    # Determine swing high/low
    if swing_high is None or swing_low is None:
        if indicators:
            swing_high, swing_low = FibonacciCalculator.calculate_swing_from_indicators(indicators)
        else:
            result["error"] = "Must provide either indicators or manual swing_high/swing_low"
            return result

    if swing_high is None or swing_low is None:
        result["error"] = "Could not determine swing high/low"
        return result

    try:
        # Calculate Fibonacci levels
        fib_levels = FibonacciCalculator.calculate_levels(swing_high, swing_low)

        # Analyze price position
        position_analysis = FibonacciCalculator.analyze_price_position(
            current_price, fib_levels, tolerance_pct
        )

        result.update({
            "swing_high": fib_levels["swing_high"],
            "swing_low": fib_levels["swing_low"],
            "swing_range": fib_levels["swing_range"],
            "swing_range_pct": fib_levels["swing_range_pct"],
            "current_price": position_analysis["current_price"],
            "position": position_analysis["position"],
            "retracement_levels": fib_levels["retracement_levels"],
            "extension_levels": fib_levels["extension_levels"],
            "nearest_supports": position_analysis["nearest_supports"],
            "nearest_resistances": position_analysis["nearest_resistances"],
            "near_support": position_analysis["near_support"],
            "near_resistance": position_analysis["near_resistance"],
            "at_golden_pocket": position_analysis["at_golden_pocket"],
            "golden_pocket_support": next(
                (s for s in position_analysis["nearest_supports"] if s["is_golden_pocket"]),
                None
            ),
            "golden_pocket_resistance": next(
                (r for r in position_analysis["nearest_resistances"] if r["is_golden_pocket"]),
                None
            )
        })

        return result

    except Exception as e:
        result["error"] = f"Fibonacci calculation failed: {str(e)}"
        logger.error(f"Fibonacci analysis error for {symbol}: {e}")
        return result


# Quick test function
if __name__ == "__main__":
    # Test with BTC example
    btc_price = 69500
    swing_high = 74000
    swing_low = 60000

    result = analyze_crypto_fibonacci(
        symbol="BTCUSDT",
        current_price=btc_price,
        swing_high=swing_high,
        swing_low=swing_low
    )

    print(f"Fibonacci Analysis for BTCUSDT @ ${btc_price:,}")
    print(f"Swing High: ${swing_high:,} | Swing Low: ${swing_low:,}")
    print(f"\nRetracement Levels:")
    for level, data in result["retracement_levels"].items():
        print(f"  {level:8s}: ${data['price']:>10,.2f} {'🟡 Golden Pocket' if data['is_golden_pocket'] else ''}")

    print(f"\nCurrent Position: {result['position']}")
    if result["nearest_supports"]:
        print(f"Nearest Support: {result['nearest_supports'][0]['level']} @ ${result['nearest_supports'][0]['price']:,}")
    if result["nearest_resistances"]:
        print(f"Nearest Resistance: {result['nearest_resistances'][0]['level']} @ ${result['nearest_resistances'][0]['price']:,}")
