"""
Pydantic data models for the Alpaca Trading Agent backend.

Defines schemas for API requests, responses, strategy configuration,
agent status, and audit/reasoning log entries.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request payload for agent chat interaction."""

    session_id: Optional[str] = Field(
        default=None, description="Optional session identifier for chat context."
    )
    message: str = Field(..., description="Message text sent to the trading agent.")


class ChatResponse(BaseModel):
    """Response payload for agent chat interaction."""

    response: str = Field(..., description="Agent response message.")
    session_id: str = Field(..., description="Session identifier for tracking history.")
    tool_calls: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of MCP tool calls executed during reasoning."
    )


class OrderRequest(BaseModel):
    """Request payload to place an order via the API."""

    symbol: str = Field(..., description="Ticker symbol for the security (e.g., 'AAPL').")
    side: str = Field(..., description="Order side: 'buy' or 'sell'.")
    qty: float = Field(..., gt=0, description="Quantity of shares/contracts to trade.")
    order_type: str = Field(default="market", description="Order type: 'market', 'limit', etc.")
    time_in_force: str = Field(default="day", description="Time in force: 'day', 'gtc', 'ioc', etc.")
    limit_price: Optional[float] = Field(
        default=None, description="Limit price for limit orders."
    )


class StrategyConfig(BaseModel):
    """Configuration payload for initializing or updating trading strategies."""

    strategy_name: str = Field(default="pairs_trading", description="Name of the strategy to run.")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Strategy-specific parameters and hyperparameter overrides."
    )


class ReasoningLogEntry(BaseModel):
    """Structure of an entry in the transparent reasoning log."""

    timestamp: str = Field(..., description="ISO 8601 timestamp of cycle execution.")
    cycle_id: int = Field(..., description="Unique cycle sequence number.")
    market_data: Dict[str, Any] = Field(..., description="Snapshot of market data evaluated.")
    llm_reasoning: str = Field(..., description="Full LLM reasoning chain or summary.")
    decision: Dict[str, Any] = Field(..., description="Decision made by the engine (e.g., action, target).")
    mcp_tools_called: List[Dict[str, Any]] = Field(..., description="Tools called during execution.")
    orders_placed: List[Dict[str, Any]] = Field(..., description="Orders submitted to Alpaca.")
    result: Dict[str, Any] = Field(..., description="Result status and execution metrics.")


class AgentState(BaseModel):
    """Current operating state of the trading agent."""

    is_running: bool = Field(..., description="Whether the trading loop is active.")
    strategy_name: str = Field(..., description="Active strategy name.")
    last_decision: Optional[Dict[str, Any]] = Field(
        default=None, description="Summary of the most recent trade cycle decision."
    )
    total_trades: int = Field(default=0, description="Total number of trades executed.")
    total_pnl: float = Field(default=0.0, description="Cumulative realized and unrealized P&L in USD.")
    uptime_seconds: float = Field(default=0.0, description="Total running time of the server/agent in seconds.")
