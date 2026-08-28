"""Pairs Trading Strategy module.

Implements statistical arbitrage between two correlated equity/ETF assets based on mean-reverting price spreads.
"""

from typing import Any, Dict, List, Tuple
import numpy as np

from .base_strategy import BaseStrategy


class PairsTradingStrategy(BaseStrategy):
    """Pairs trading statistical arbitrage strategy.

    Monitors the price spread between two correlated assets (symbol_a and symbol_b),
    calculating a rolling z-score. Triggers long/short position pairs when spread diverges
    beyond `entry_zscore` and closes positions when spread reverts within `exit_zscore`.
    """

    def __init__(
        self,
        symbol_a: str = "SPY",
        symbol_b: str = "QQQ",
        lookback_period: int = 20,
        entry_zscore: float = 2.0,
        exit_zscore: float = 0.5,
        position_size_pct: float = 0.1,
    ) -> None:
        """Initialize PairsTradingStrategy parameters.

        Args:
            symbol_a: Ticker symbol for the primary asset in the pair.
            symbol_b: Ticker symbol for the secondary asset in the pair.
            lookback_period: Rolling window bar length for statistical calculations.
            entry_zscore: Z-score magnitude threshold to trigger trade entries.
            exit_zscore: Z-score magnitude threshold to trigger position exits.
            position_size_pct: Percentage of portfolio equity allocated to pair trade.
        """
        self.symbol_a = symbol_a.upper()
        self.symbol_b = symbol_b.upper()
        self.lookback_period = int(lookback_period)
        self.entry_zscore = float(entry_zscore)
        self.exit_zscore = float(exit_zscore)
        self.position_size_pct = float(position_size_pct)

    @property
    def name(self) -> str:
        """Return strategy name."""
        return "Pairs Trading"

    @property
    def description(self) -> str:
        """Return strategy description."""
        return "Statistical arbitrage between correlated assets"

    def _extract_prices(self, market_data: Dict[str, Any], symbol: str) -> List[float]:
        """Extract closing prices for a given symbol from various market_data dictionary formats.

        Args:
            market_data: Data dictionary containing bars or prices.
            symbol: Ticker symbol to extract.

        Returns:
            List of price floats.
        """
        raw = None
        if symbol in market_data:
            raw = market_data[symbol]
        elif "prices" in market_data and symbol in market_data["prices"]:
            raw = market_data["prices"][symbol]
        elif "bars" in market_data and symbol in market_data["bars"]:
            raw = market_data["bars"][symbol]

        if not raw:
            return []

        prices = []
        for item in raw:
            if isinstance(item, (int, float)):
                prices.append(float(item))
            elif isinstance(item, dict):
                p = item.get("c") if "c" in item else item.get("close")
                if p is not None:
                    prices.append(float(p))
        return prices

    def _calculate_spread(
        self, prices_a: List[float], prices_b: List[float]
    ) -> Tuple[float, float, float]:
        """Calculate current price spread, rolling mean, and rolling standard deviation.

        Args:
            prices_a: Historical prices for symbol_a.
            prices_b: Historical prices for symbol_b.

        Returns:
            Tuple of (current_spread, mean_spread, std_spread).

        Raises:
            ValueError: If input price lists are empty or have unequal lengths.
        """
        arr_a = np.asarray(prices_a, dtype=np.float64)
        arr_b = np.asarray(prices_b, dtype=np.float64)

        if len(arr_a) == 0 or len(arr_b) == 0:
            raise ValueError("Price arrays must not be empty.")

        if len(arr_a) != len(arr_b):
            raise ValueError(
                f"Price array length mismatch: len({self.symbol_a})={len(arr_a)}, len({self.symbol_b})={len(arr_b)}"
            )

        if len(arr_a) > self.lookback_period:
            arr_a = arr_a[-self.lookback_period :]
            arr_b = arr_b[-self.lookback_period :]

        spread_series = arr_a - arr_b
        current_spread = float(spread_series[-1])
        mean = float(np.mean(spread_series))
        std = float(np.std(spread_series, ddof=1 if len(spread_series) > 1 else 0))

        return current_spread, mean, std

    def _calculate_zscore(self, spread: float, mean: float, std: float) -> float:
        """Calculate standard score (z-score) of current spread relative to mean and std dev.

        Args:
            spread: Current price spread value.
            mean: Historical mean of spread series.
            std: Historical standard deviation of spread series.

        Returns:
            Z-score float. Returns 0.0 if standard deviation is zero.
        """
        if std == 0.0 or np.isnan(std):
            return 0.0
        return float((spread - mean) / std)

    async def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market data for pair assets and calculate spread z-score signals.

        Args:
            market_data: Dict containing price history or bars for symbol_a and symbol_b.

        Returns:
            Dict containing signal_type, strength, and calculation metadata.
        """
        prices_a = self._extract_prices(market_data, self.symbol_a)
        prices_b = self._extract_prices(market_data, self.symbol_b)

        min_required = min(self.lookback_period, 2)
        if len(prices_a) < min_required or len(prices_b) < min_required:
            return {
                "signal_type": "NEUTRAL",
                "strength": 0.0,
                "metadata": {
                    "reason": "Insufficient price data",
                    "available_a": len(prices_a),
                    "available_b": len(prices_b),
                    "required": self.lookback_period,
                },
            }

        # Align length if minor discrepancy exists
        common_len = min(len(prices_a), len(prices_b))
        prices_a = prices_a[-common_len:]
        prices_b = prices_b[-common_len:]

        current_spread, mean, std = self._calculate_spread(prices_a, prices_b)
        z_score = self._calculate_zscore(current_spread, mean, std)

        signal_type = "NEUTRAL"
        strength = 0.0

        if z_score >= self.entry_zscore:
            # Asset A overvalued relative to B -> Short A, Long B
            signal_type = "SHORT_A_LONG_B"
            strength = min(1.0, abs(z_score) / (self.entry_zscore * 2.0))
        elif z_score <= -self.entry_zscore:
            # Asset A undervalued relative to B -> Long A, Short B
            signal_type = "LONG_A_SHORT_B"
            strength = min(1.0, abs(z_score) / (self.entry_zscore * 2.0))
        elif abs(z_score) <= self.exit_zscore:
            # Mean reversion achieved -> Exit/Flat signal
            signal_type = "EXIT"
            strength = max(0.0, 1.0 - (abs(z_score) / self.exit_zscore))

        return {
            "signal_type": signal_type,
            "strength": round(float(strength), 4),
            "metadata": {
                "z_score": round(float(z_score), 4),
                "spread": round(float(current_spread), 4),
                "mean": round(float(mean), 4),
                "std": round(float(std), 4),
                "symbol_a": self.symbol_a,
                "symbol_b": self.symbol_b,
                "last_price_a": prices_a[-1],
                "last_price_b": prices_b[-1],
            },
        }

    async def get_market_data_requirements(self) -> Dict[str, Any]:
        """Return required data payload properties for pairs trading analysis."""
        return {
            "symbols": [self.symbol_a, self.symbol_b],
            "timeframe": "1Day",
            "bars_needed": self.lookback_period,
            "data_types": ["bars"],
        }

    async def generate_orders(
        self, signal: Dict[str, Any], account_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Convert trading signals into paired leg orders based on account balance.

        Args:
            signal: Output signal dictionary from `analyze()`.
            account_info: Account dictionary containing equity, buying power, and positions.

        Returns:
            List of order specifications for pair leg execution.
        """
        signal_type = signal.get("signal_type", "NEUTRAL")
        if signal_type == "NEUTRAL":
            return []

        metadata = signal.get("metadata", {})
        price_a = metadata.get("last_price_a", 1.0)
        price_b = metadata.get("last_price_b", 1.0)

        portfolio_value = float(
            account_info.get(
                "portfolio_value",
                account_info.get("equity", account_info.get("buying_power", 100000.0)),
            )
        )

        total_allocation = portfolio_value * self.position_size_pct
        allocation_per_leg = total_allocation / 2.0

        qty_a = max(1, int(allocation_per_leg / price_a)) if price_a > 0 else 1
        qty_b = max(1, int(allocation_per_leg / price_b)) if price_b > 0 else 1

        orders: List[Dict[str, Any]] = []

        if signal_type == "LONG_A_SHORT_B":
            orders.append(
                {
                    "symbol": self.symbol_a,
                    "qty": qty_a,
                    "side": "buy",
                    "type": "market",
                    "time_in_force": "gtc",
                }
            )
            orders.append(
                {
                    "symbol": self.symbol_b,
                    "qty": qty_b,
                    "side": "sell",
                    "type": "market",
                    "time_in_force": "gtc",
                }
            )
        elif signal_type == "SHORT_A_LONG_B":
            orders.append(
                {
                    "symbol": self.symbol_a,
                    "qty": qty_a,
                    "side": "sell",
                    "type": "market",
                    "time_in_force": "gtc",
                }
            )
            orders.append(
                {
                    "symbol": self.symbol_b,
                    "qty": qty_b,
                    "side": "buy",
                    "type": "market",
                    "time_in_force": "gtc",
                }
            )
        elif signal_type == "EXIT":
            # Generate liquidating exit orders for both legs
            existing_positions = account_info.get("positions", {})
            
            # Helper to find position quantity if passed in dict or list form
            def get_pos_qty(symbol: str) -> int:
                if isinstance(existing_positions, dict):
                    pos = existing_positions.get(symbol, {})
                    return int(pos.get("qty", 0)) if isinstance(pos, dict) else int(pos)
                elif isinstance(existing_positions, list):
                    for item in existing_positions:
                        if item.get("symbol") == symbol:
                            return int(item.get("qty", 0))
                return 0

            qty_pos_a = get_pos_qty(self.symbol_a)
            qty_pos_b = get_pos_qty(self.symbol_b)

            if qty_pos_a != 0:
                side_a = "sell" if qty_pos_a > 0 else "buy"
                orders.append(
                    {
                        "symbol": self.symbol_a,
                        "qty": abs(qty_pos_a),
                        "side": side_a,
                        "type": "market",
                        "time_in_force": "gtc",
                    }
                )

            if qty_pos_b != 0:
                side_b = "sell" if qty_pos_b > 0 else "buy"
                orders.append(
                    {
                        "symbol": self.symbol_b,
                        "qty": abs(qty_pos_b),
                        "side": side_b,
                        "type": "market",
                        "time_in_force": "gtc",
                    }
                )

        return orders

    def get_parameters(self) -> Dict[str, Any]:
        """Return current strategy parameters dict."""
        return {
            "symbol_a": self.symbol_a,
            "symbol_b": self.symbol_b,
            "lookback_period": self.lookback_period,
            "entry_zscore": self.entry_zscore,
            "exit_zscore": self.exit_zscore,
            "position_size_pct": self.position_size_pct,
        }

    def set_parameters(self, params: Dict[str, Any]) -> None:
        """Update strategy parameters dynamically."""
        if "symbol_a" in params:
            self.symbol_a = str(params["symbol_a"]).upper()
        if "symbol_b" in params:
            self.symbol_b = str(params["symbol_b"]).upper()
        if "lookback_period" in params:
            self.lookback_period = int(params["lookback_period"])
        if "entry_zscore" in params:
            self.entry_zscore = float(params["entry_zscore"])
        if "exit_zscore" in params:
            self.exit_zscore = float(params["exit_zscore"])
        if "position_size_pct" in params:
            self.position_size_pct = float(params["position_size_pct"])
