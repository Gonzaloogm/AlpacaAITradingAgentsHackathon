"""Strategy orchestrator tying decision engine with market data and Alpaca trade execution."""

from datetime import datetime, timezone
import asyncio
import logging
from typing import Any, Dict, List, Optional

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest

from agent.base_agent import AgentConfig
from agent.decision_engine import DecisionEngine

logger = logging.getLogger(__name__)

# Placeholder import for strategy.base_strategy.BaseStrategy
try:
    from strategy.base_strategy import BaseStrategy
except ImportError:
    from abc import ABC, abstractmethod

    class BaseStrategy(ABC):  # type: ignore[no-redef]
        """Placeholder interface for BaseStrategy if not yet implemented."""

        @abstractmethod
        async def get_market_data(self) -> Dict[str, Any]:
            """Fetch latest market data and indicators."""
            pass

        @abstractmethod
        async def get_context(self) -> Dict[str, Any]:
            """Fetch strategy context and portfolio parameters."""
            pass


class StrategyOrchestrator:
    """Orchestrates market data collection, LLM analysis, and Alpaca trade execution."""

    def __init__(
        self,
        config: AgentConfig,
        strategy: BaseStrategy,
        decision_engine: DecisionEngine,
    ) -> None:
        """Initialize StrategyOrchestrator.

        Args:
            config: AgentConfig instance with Alpaca API credentials.
            strategy: BaseStrategy instance for fetching market data and context.
            decision_engine: DecisionEngine instance for market decision analysis.
        """
        self.config = config
        self.strategy = strategy
        self.decision_engine = decision_engine

        self.trading_client = TradingClient(
            api_key=config.alpaca_api_key,
            secret_key=config.alpaca_secret_key,
            paper=config.paper_trading,
        )

        self.is_running = False
        self.last_decision: Optional[Dict[str, Any]] = None
        self.reasoning_log: List[Dict[str, Any]] = []

    async def run_loop(self, interval_seconds: int = 30) -> None:
        """Main execution loop - fetch market data, analyze with LLM, execute if approved.

        Args:
            interval_seconds: Time interval between analysis cycles in seconds.
        """
        self.is_running = True
        logger.info(
            "Starting StrategyOrchestrator loop with interval of %d seconds", interval_seconds
        )

        while self.is_running:
            cycle_time = datetime.now(timezone.utc).isoformat()
            try:
                market_data = await self.strategy.get_market_data()
                strategy_context = await self.strategy.get_context()

                decision = await self.decision_engine.analyze_market(
                    market_data=market_data,
                    strategy_context=strategy_context,
                )
                self.last_decision = decision

                execution_result = None
                action = str(decision.get("action", "")).lower()
                confidence = float(decision.get("confidence", 0.0))

                if action in ("buy", "sell") and confidence >= 0.5:
                    execution_result = await self.execute_trade(decision)
                else:
                    execution_result = {
                        "status": "skipped",
                        "reason": f"Action '{action}' or confidence {confidence} below threshold",
                    }

                log_entry = {
                    "timestamp": cycle_time,
                    "market_data": market_data,
                    "strategy_context": strategy_context,
                    "decision": decision,
                    "execution": execution_result,
                }
                self.reasoning_log.append(log_entry)
                logger.info("Cycle completed at %s. Action: %s", cycle_time, action)

            except Exception as err:
                logger.error("Error in StrategyOrchestrator cycle: %s", err)
                self.reasoning_log.append({
                    "timestamp": cycle_time,
                    "error": str(err),
                })

            await asyncio.sleep(interval_seconds)

    async def execute_trade(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trade on Alpaca based on LLM decision.

        Args:
            decision: Decision dictionary containing action, parameters, and confidence.

        Returns:
            Dictionary containing trade execution results or error info.
        """
        action = str(decision.get("action", "")).lower()
        if action not in ("buy", "sell"):
            return {
                "status": "skipped",
                "reason": f"Action '{action}' does not require execution",
            }

        params = decision.get("parameters", {})
        symbol = params.get("symbol")
        qty = params.get("qty")

        if not symbol or not qty:
            return {
                "status": "failed",
                "reason": "Missing required order parameters (symbol, qty)",
            }

        try:
            side = OrderSide.BUY if action == "buy" else OrderSide.SELL
            order_type = str(params.get("order_type", "market")).lower()

            if order_type == "limit" and "limit_price" in params:
                order_req = LimitOrderRequest(
                    symbol=symbol,
                    qty=float(qty),
                    side=side,
                    time_in_force=TimeInForce.GTC,
                    limit_price=float(params["limit_price"]),
                )
            else:
                order_req = MarketOrderRequest(
                    symbol=symbol,
                    qty=float(qty),
                    side=side,
                    time_in_force=TimeInForce.GTC,
                )

            order = self.trading_client.submit_order(order_req)
            result = {
                "status": "executed",
                "order_id": str(getattr(order, "id", "")),
                "symbol": symbol,
                "side": action,
                "qty": qty,
                "order_type": order_type,
            }
            logger.info("Trade executed successfully: %s", result)
            return result

        except Exception as err:
            logger.error("Failed to execute trade via Alpaca: %s", err)
            return {"status": "failed", "error": str(err)}

    def stop(self) -> None:
        """Stop the execution loop."""
        self.is_running = False
        logger.info("StrategyOrchestrator stop signal received.")

    def get_state(self) -> Dict[str, Any]:
        """Get current state of orchestrator including running status, positions, and PnL.

        Returns:
            Dictionary with keys: running, last_decision, reasoning_log_count, positions, pnl.
        """
        positions = []
        pnl = {"equity": "0.00", "unrealized_pnl": "0.00"}

        try:
            acct = self.trading_client.get_account()
            pnl["equity"] = str(getattr(acct, "equity", "0.00"))
            pnl["unrealized_pnl"] = str(getattr(acct, "unrealized_pl", "0.00"))

            raw_positions = self.trading_client.get_all_positions()
            for pos in raw_positions:
                positions.append({
                    "symbol": getattr(pos, "symbol", ""),
                    "qty": getattr(pos, "qty", "0"),
                    "market_value": getattr(pos, "market_value", "0.00"),
                    "unrealized_pl": getattr(pos, "unrealized_pl", "0.00"),
                })
        except Exception as err:
            logger.warning("Could not fetch Alpaca positions/account state: %s", err)

        return {
            "running": self.is_running,
            "last_decision": self.last_decision,
            "reasoning_log_count": len(self.reasoning_log),
            "positions": positions,
            "pnl": pnl,
        }


__all__ = ["StrategyOrchestrator"]
