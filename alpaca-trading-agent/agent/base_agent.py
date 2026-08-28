"""Base agent module for Alpaca Trading Agent.

Provides the abstract BaseAgent class and AgentConfig dataclass for building
Alpaca-integrated trading agents without blockchain dependencies.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging
from typing import Any, Dict, List, Optional

from alpaca.trading.client import TradingClient

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Agent configuration parameters for Alpaca trading agents.

    Attributes:
        agent_id: Unique identifier for the agent.
        name: Human-readable name of the agent.
        alpaca_api_key: Alpaca API key.
        alpaca_secret_key: Alpaca API secret key.
        gemini_api_key: Google Gemini API key (primary AI, free tier via AI Studio).
            Required when ai_primary="gemini" (the default).
        strategy_name: Name of the trading strategy.
        description: Description of the agent.
        paper_trading: Whether to connect to Alpaca paper trading environment.
        ai_primary: Active AI provider — "gemini" (default) or "claude".
        anthropic_api_key: Anthropic API key. Optional — only required when
            ai_primary="claude". Currently $0 balance; kept for future reactivation.
    """

    agent_id: str
    name: str
    alpaca_api_key: str
    alpaca_secret_key: str
    gemini_api_key: str        # Primary AI — free tier, no billing required
    strategy_name: str
    description: str = ""
    paper_trading: bool = True
    ai_primary: str = "gemini"
    anthropic_api_key: Optional[str] = None  # Preserved, inactive (balance: $0)


class BaseAgent(ABC):
    """Abstract base class for Alpaca trading agents.

    Provides:
    - Alpaca TradingClient initialization (alpaca-py)
    - Account state property
    - Extensible plugin system (add_plugin, get_plugin, list_plugins)
    - Abstract event handlers for tasks, market data, and order fills
    """

    def __init__(self, config: AgentConfig) -> None:
        """Initialize the base agent with Alpaca TradingClient.

        Args:
            config: Agent configuration instance.
        """
        self.config = config
        self._plugins: Dict[str, Any] = {}

        self.trading_client = TradingClient(
            api_key=self.config.alpaca_api_key,
            secret_key=self.config.alpaca_secret_key,
            paper=self.config.paper_trading,
        )

        logger.info(
            "Agent '%s' (ID: %s) initialized (Paper trading: %s)",
            self.config.name,
            self.config.agent_id,
            self.config.paper_trading,
        )

    @property
    def account(self) -> Any:
        """Retrieve Alpaca trading account information.

        Returns:
            Alpaca Account object containing balance, buying power, and account status.
        """
        return self.trading_client.get_account()

    # Plugin System
    def add_plugin(self, plugin_name: str, plugin_instance: Any) -> None:
        """Add plugin for extended functionality.

        Args:
            plugin_name: Name of the plugin.
            plugin_instance: Plugin instance.
        """
        self._plugins[plugin_name] = plugin_instance
        logger.info("Plugin '%s' registered for agent '%s'", plugin_name, self.config.name)

    def get_plugin(self, plugin_name: str) -> Optional[Any]:
        """Get registered plugin instance.

        Args:
            plugin_name: Name of the plugin.

        Returns:
            Plugin instance if registered, else None.
        """
        return self._plugins.get(plugin_name)

    def list_plugins(self) -> List[str]:
        """List names of all registered plugins.

        Returns:
            List of registered plugin names.
        """
        return list(self._plugins.keys())

    def get_status(self) -> Dict[str, Any]:
        """Get agent operational status summary.

        Returns:
            Dictionary containing agent metadata, status flags, and registered plugins.
        """
        return {
            "agent_id": self.config.agent_id,
            "name": self.config.name,
            "description": self.config.description,
            "strategy_name": self.config.strategy_name,
            "paper_trading": self.config.paper_trading,
            "plugins": self.list_plugins(),
        }

    # Abstract Methods
    @abstractmethod
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming task - implement agent-specific logic.

        Args:
            task: Task dictionary to process.

        Returns:
            Task processing result dictionary.
        """
        pass

    @abstractmethod
    async def on_market_data(self, data: Dict[str, Any]) -> None:
        """Handle incoming market data updates.

        Args:
            data: Market data payload.
        """
        pass

    @abstractmethod
    async def on_order_fill(self, event: Dict[str, Any]) -> None:
        """Handle order fill or trade execution events.

        Args:
            event: Order execution payload.
        """
        pass


__all__ = ["AgentConfig", "BaseAgent"]
