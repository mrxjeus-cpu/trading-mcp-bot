#!/usr/bin/env python3
"""
Exchange Volume Analysis Service

Fetches real-time buy/sell volume and order book data from exchanges
to provide more accurate trading signals.

Supports:
- Binance (REST API)
- Order book depth analysis
- Buy/Sell pressure calculation
- Volume profile analysis
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OrderBookData:
    """Order book data structure."""
    symbol: str
    bids: List[tuple]  # [(price, volume), ...]
    asks: List[tuple]  # [(price, volume), ...]
    last_update: str

    # Calculated metrics
    total_bid_volume: float
    total_ask_volume: float
    bid_ask_ratio: float
    buy_pressure: float  # 0-100
    sell_pressure: float  # 0-100

    # Price levels
    best_bid: float
    best_ask: float
    spread: float
    spread_pct: float


class ExchangeVolumeAnalyzer:
    """Analyze volume and order book data from exchanges."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 TradingView-MCP-Bot'
        })

    def get_binance_order_book(
        self,
        symbol: str,
        limit: int = 20
    ) -> Optional[OrderBookData]:
        """
        Fetch order book from Binance.

        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            limit: Number of bid/ask levels (default: 20)

        Returns:
            OrderBookData object or None
        """
        try:
            url = "https://api.binance.com/api/v3/depth"
            params = {
                'symbol': symbol,
                'limit': limit
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            return self._parse_order_book(symbol, data)

        except Exception as e:
            logger.error(f"Error fetching Binance order book for {symbol}: {e}")
            return None

    def _parse_order_book(self, symbol: str, data: Dict) -> OrderBookData:
        """Parse order book response data."""
        bids = [[float(price), float(volume)] for price, volume in data.get('bids', [])]
        asks = [[float(price), float(volume)] for price, volume in data.get('asks', [])]

        # Calculate total volumes
        total_bid_volume = sum([bid[1] for bid in bids]) if bids else 0
        total_ask_volume = sum([ask[1] for ask in asks]) if asks else 0

        # Calculate bid/ask ratio
        if total_ask_volume > 0:
            bid_ask_ratio = total_bid_volume / total_ask_volume
        else:
            bid_ask_ratio = 0

        # Calculate buy/sell pressure (0-100 scale)
        total_volume = total_bid_volume + total_ask_volume
        if total_volume > 0:
            buy_pressure = (total_bid_volume / total_volume) * 100
            sell_pressure = (total_ask_volume / total_volume) * 100
        else:
            buy_pressure = sell_pressure = 50

        # Get best bid/ask
        best_bid = bids[0][0] if bids else 0
        best_ask = asks[0][0] if asks else 0

        # Calculate spread
        if best_bid > 0 and best_ask > 0:
            spread = best_ask - best_bid
            spread_pct = (spread / best_bid) * 100
        else:
            spread = spread_pct = 0

        return OrderBookData(
            symbol=symbol,
            bids=bids,
            asks=asks,
            last_update=datetime.now().isoformat(),
            total_bid_volume=total_bid_volume,
            total_ask_volume=total_ask_volume,
            bid_ask_ratio=bid_ask_ratio,
            buy_pressure=buy_pressure,
            sell_pressure=sell_pressure,
            best_bid=best_bid,
            best_ask=best_ask,
            spread=spread,
            spread_pct=spread_pct
        )

    def analyze_buy_sell_pressure(self, order_book: OrderBookData) -> Dict[str, Any]:
        """
        Analyze buy/sell pressure from order book.

        Returns:
            Dict with pressure analysis
        """
        if not order_book:
            return {"error": "No order book data available"}

        # Determine signal based on pressure
        buy_pressure = order_book.buy_pressure
        sell_pressure = order_book.sell_pressure
        bid_ask_ratio = order_book.bid_ask_ratio

        # Signal determination
        signal = "neutral"
        signal_strength = "weak"

        if buy_pressure >= 60:
            signal = "strong_buy" if buy_pressure >= 75 else "buy"
            signal_strength = "strong" if buy_pressure >= 70 else "moderate"
        elif sell_pressure >= 60:
            signal = "strong_sell" if sell_pressure >= 75 else "sell"
            signal_strength = "strong" if sell_pressure >= 70 else "moderate"

        # Wall detection (large orders)
        bid_walls = []
        ask_walls = []

        for i, (price, volume) in enumerate(order_book.bids[:5]):
            if volume > 0 and order_book.total_bid_volume > 0:
                if volume / order_book.total_bid_volume > 0.15:  # >15% of total bid volume
                    bid_walls.append({"level": i+1, "price": price, "volume": volume, "pct": (volume / order_book.total_bid_volume) * 100})

        for i, (price, volume) in enumerate(order_book.asks[:5]):
            if volume > 0 and order_book.total_ask_volume > 0:
                if volume / order_book.total_ask_volume > 0.15:  # >15% of total ask volume
                    ask_walls.append({"level": i+1, "price": price, "volume": volume, "pct": (volume / order_book.total_ask_volume) * 100})

        return {
            "symbol": order_book.symbol,
            "signal": signal,
            "signal_strength": signal_strength,
            "buy_pressure": round(buy_pressure, 2),
            "sell_pressure": round(sell_pressure, 2),
            "bid_ask_ratio": round(bid_ask_ratio, 2),
            "interpretation": self._interpret_pressure(buy_pressure, sell_pressure),
            "bid_walls": bid_walls,
            "ask_walls": ask_walls,
            "spread": round(order_book.spread, 2),
            "spread_pct": round(order_book.spread_pct, 4),
            "timestamp": order_book.last_update
        }

    def _interpret_pressure(self, buy_pressure: float, sell_pressure: float) -> str:
        """Interpret buy/sell pressure."""
        diff = buy_pressure - sell_pressure

        if diff >= 30:
            return "🟢 Strong Buying Pressure - Accumulation detected"
        elif diff >= 15:
            return "🟡 Moderate Buying Pressure - Buyers in control"
        elif diff <= -30:
            return "🔴 Strong Selling Pressure - Distribution detected"
        elif diff <= -15:
            return "🟡 Moderate Selling Pressure - Sellers in control"
        else:
            return "⚪ Balanced Pressure - No clear direction"

    def get_recent_trades(
        self,
        symbol: str,
        limit: int = 100
    ) -> Optional[Dict]:
        """
        Fetch recent trades from Binance to analyze buy/sell flow.

        Args:
            symbol: Trading pair
            limit: Number of recent trades (max 1000)

        Returns:
            Dict with trade analysis
        """
        try:
            url = "https://api.binance.com/api/v3/trades"
            params = {
                'symbol': symbol,
                'limit': min(limit, 1000)
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            trades = response.json()

            # Analyze trades
            buy_trades = []
            sell_trades = []
            total_volume = 0

            for trade in trades:
                price = float(trade['price'])
                qty = float(trade['qty'])
                is_buyer_maker = trade['isBuyerMaker']

                total_volume += qty

                # isBuyerMaker = True means sell order (maker was buyer)
                # isBuyerMaker = False means buy order (taker bought)
                if not is_buyer_maker:
                    buy_trades.append(qty)
                else:
                    sell_trades.append(qty)

            total_buy_volume = sum(buy_trades)
            total_sell_volume = sum(sell_trades)

            if total_volume > 0:
                buy_ratio = (total_buy_volume / total_volume) * 100
                sell_ratio = (total_sell_volume / total_volume) * 100
            else:
                buy_ratio = sell_ratio = 50

            return {
                "symbol": symbol,
                "total_trades": len(trades),
                "total_volume": round(total_volume, 4),
                "buy_volume": round(total_buy_volume, 4),
                "sell_volume": round(total_sell_volume, 4),
                "buy_ratio": round(buy_ratio, 2),
                "sell_ratio": round(sell_ratio, 2),
                "net_flow": round(total_buy_volume - total_sell_volume, 4),
                "signal": "buy" if buy_ratio >= 60 else "sell" if sell_ratio >= 60 else "neutral",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error fetching recent trades for {symbol}: {e}")
            return None

    def get_ticker_24h(self, symbol: str) -> Optional[Dict]:
        """
        Get 24h ticker data from Binance.

        Args:
            symbol: Trading pair

        Returns:
            Dict with 24h statistics
        """
        try:
            url = "https://api.binance.com/api/v3/ticker/24hr"
            params = {'symbol': symbol}

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            return {
                "symbol": symbol,
                "price_change": float(data['priceChange']),
                "price_change_pct": float(data['priceChangePercent']),
                "high": float(data['highPrice']),
                "low": float(data['lowPrice']),
                "volume": float(data['volume']),
                "quote_volume": float(data['quoteVolume']),
                "trades": int(data['count']),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error fetching 24h ticker for {symbol}: {e}")
            return None


# Singleton instance
_analyzer = None

def get_exchange_analyzer() -> ExchangeVolumeAnalyzer:
    """Get singleton analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = ExchangeVolumeAnalyzer()
    return _analyzer


def analyze_exchange_volume(
    symbol: str,
    exchange: str = "binance",
    include_trades: bool = True,
    order_book_limit: int = 20
) -> Dict[str, Any]:
    """
    Complete exchange volume analysis for a symbol.

    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        exchange: Exchange name (default: binance)
        include_trades: Include recent trades analysis
        order_book_limit: Number of order book levels

    Returns:
        Dict with complete volume analysis
    """
    result = {
        "symbol": symbol,
        "exchange": exchange,
        "timestamp": datetime.now().isoformat(),
        "order_book": None,
        "recent_trades": None,
        "ticker_24h": None,
        "signal": None
    }

    analyzer = get_exchange_analyzer()

    # Get order book
    order_book = analyzer.get_binance_order_book(symbol, order_book_limit)
    if order_book:
        result["order_book"] = analyzer.analyze_buy_sell_pressure(order_book)

    # Get recent trades
    if include_trades:
        trades = analyzer.get_recent_trades(symbol)
        if trades:
            result["recent_trades"] = trades

    # Get 24h ticker
    ticker = analyzer.get_ticker_24h(symbol)
    if ticker:
        result["ticker_24h"] = ticker

    # Generate overall signal
    result["signal"] = _generate_overall_signal(result)

    return result


def _generate_overall_signal(analysis: Dict) -> Dict:
    """Generate overall signal from all exchange data."""
    signals = []
    confidence = 0

    # Order book signal
    if analysis.get("order_book"):
        ob_signal = analysis["order_book"]["signal"]
        ob_strength = analysis["order_book"]["signal_strength"]
        signals.append(ob_signal)

        if ob_signal == "strong_buy":
            confidence += 30 if ob_strength == "strong" else 20
        elif ob_signal == "buy":
            confidence += 20
        elif ob_signal == "strong_sell":
            confidence -= 30 if ob_strength == "strong" else 20
        elif ob_signal == "sell":
            confidence -= 20

    # Recent trades signal
    if analysis.get("recent_trades"):
        trades_signal = analysis["recent_trades"]["signal"]
        signals.append(trades_signal)

        if trades_signal == "buy":
            confidence += 15
        elif trades_signal == "sell":
            confidence -= 15

    # 24h trend
    if analysis.get("ticker_24h"):
        price_change_pct = analysis["ticker_24h"]["price_change_pct"]
        if price_change_pct > 2:
            signals.append("uptrend")
            confidence += 10
        elif price_change_pct < -2:
            signals.append("downtrend")
            confidence -= 10

    # Determine final signal
    if confidence >= 40:
        final_signal = "strong_buy"
    elif confidence >= 20:
        final_signal = "buy"
    elif confidence <= -40:
        final_signal = "strong_sell"
    elif confidence <= -20:
        final_signal = "sell"
    else:
        final_signal = "neutral"

    return {
        "final_signal": final_signal,
        "confidence": abs(confidence),
        "components": signals,
        "interpretation": f"Overall: {final_signal.upper()} (confidence: {abs(confidence)})"
    }


# Quick test
if __name__ == "__main__":
    # Test with BTCUSDT
    result = analyze_exchange_volume("BTCUSDT")

    print(f"Exchange Volume Analysis for BTCUSDT")
    print(f"=" * 50)

    if result.get("order_book"):
        ob = result["order_book"]
        print(f"\n📊 Order Book Analysis:")
        print(f"  Signal: {ob['signal'].upper()} ({ob['signal_strength']})")
        print(f"  Buy Pressure: {ob['buy_pressure']:.2f}%")
        print(f"  Sell Pressure: {ob['sell_pressure']:.2f}%")
        print(f"  Bid/Ask Ratio: {ob['bid_ask_ratio']:.2f}")
        print(f"  Spread: {ob['spread']:.2f} ({ob['spread_pct']:.4f}%)")
        print(f"  {ob['interpretation']}")

    if result.get("recent_trades"):
        rt = result["recent_trades"]
        print(f"\n📈 Recent Trades (last {rt['total_trades']}):")
        print(f"  Signal: {rt['signal'].upper()}")
        print(f"  Buy Volume: {rt['buy_volume']:,.4f} ({rt['buy_ratio']:.2f}%)")
        print(f"  Sell Volume: {rt['sell_volume']:,.4f} ({rt['sell_ratio']:.2f}%)")
        print(f"  Net Flow: {rt['net_flow']:+,.4f}")

    if result.get("ticker_24h"):
        t = result["ticker_24h"]
        print(f"\n📊 24H Statistics:")
        print(f"  Change: {t['price_change_pct']:+.2f}%")
        print(f"  High: ${t['high']:,.2f}")
        print(f"  Low: ${t['low']:,.2f}")
        print(f"  Volume: {t['volume']:,.0f}")

    print(f"\n🎯 Overall Signal: {result['signal']['final_signal'].upper()}")
    print(f"   Confidence: {result['signal']['confidence']}")
