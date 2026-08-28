"""Base Strategy module.

Provides the abstract base class for all trading strategies in the Alpaca Trading Agent framework.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseStrategy(ABC):
    """Abstract base class defining the standard interface for trading strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique human-readable name of the strategy."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Return a detailed description of the strategy methodology and logic."""
        pass

    @abstractmethod
    async def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze historical and current market data to generate trading signals.

        Args:
            market_data: Dictionary containing historical market data, quotes, or bars.

        Returns:
            Dict containing:
                - signal_type (str): Signal classification ('LONG_A_SHORT_B', 'SHORT_A_LONG_B', 'EXIT', 'NEUTRAL').
                - strength (float): Signal confidence or magnitude (e.g. 0.0 to 1.0 or normalized z-score).
                - metadata (dict): Calculation details like current spread, z-score, means, stds, etc.
        """
        pass

    @abstractmethod
    async def get_market_data_requirements(self) -> Dict[str, Any]:
        """Return the data requirements needed by this strategy to perform analysis.

        Returns:
            Dict specifying symbols, timeframes, bars_needed, and data_types required.
        """
        pass

    @abstractmethod
    async def generate_orders(
        self, signal: Dict[str, Any], account_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Convert market signal outputs into executable order parameters.

        Args:
            signal: Output dictionary produced by `analyze()`.
            account_info: Account state dictionary containing cash, buying power, equity, and current positions.

        Returns:
            List of order parameters dictionaries formatted for API submission.
        """
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Return current configurable parameters of the strategy.

        Returns:
            Dict of parameter key-value pairs.
        """
        pass

    @abstractmethod
    def set_parameters(self, params: Dict[str, Any]) -> None:
        """Update configurable parameters of the strategy.

        Args:
            params: Dictionary containing parameter overrides.
        """
        pass
