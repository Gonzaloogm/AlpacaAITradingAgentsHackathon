"""
Main FastAPI server for the Alpaca AI Trading Agent.

Serves REST endpoints for account/portfolio management, strategy execution control,
chat interactions with the AI agent, transparent reasoning audit log access,
and real-time WebSocket event streaming.
"""

import asyncio
from datetime import datetime, timezone
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Relative/Package imports from backend modules
from backend.models import (
    AgentState,
    ChatRequest,
    ChatResponse,
    OrderRequest,
    StrategyConfig,
)
from backend.reasoning_log import ReasoningLog
from backend.websocket import ConnectionManager

# Optional environment setup
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Optional imports for agent, strategy, and MCP client modules
try:
    from agent.decision_engine import DecisionEngine  # type: ignore
except ImportError:
    DecisionEngine = None  # TODO: Wire actual DecisionEngine once available

try:
    from strategy.pairs_trading import PairsTradingStrategy  # type: ignore
except ImportError:
    PairsTradingStrategy = None  # TODO: Wire actual Strategy module once available

try:
    from mcp_client.alpaca import AlpacaMCPClient  # type: ignore
except ImportError:
    AlpacaMCPClient = None  # TODO: Wire actual Alpaca MCP Client once available

logger = logging.getLogger("alpaca_agent_server")
logging.basicConfig(level=logging.INFO)

# Global Application Instance & Configuration
app = FastAPI(
    title="Alpaca AI Trading Agent",
    description="AI-powered trading agent using Claude + Alpaca MCP",
    version="1.0.0",
)

# CORS Middleware setup (allow all origins for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State Variables
start_time: float = time.time()
reasoning_log: ReasoningLog = ReasoningLog(max_entries=1000)
ws_manager: ConnectionManager = ConnectionManager()

agent_running: bool = False
current_strategy: str = "pairs_trading"
strategy_task: Optional[asyncio.Task] = None
chat_sessions: Dict[str, List[Dict[str, str]]] = {}
last_decision: Optional[Dict[str, Any]] = None
total_trades: int = 0
total_pnl: float = 0.0

# Initialized client instances (placeholders or real if imported)
decision_engine: Any = None
alpaca_client: Any = None


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize agent components and client connections on FastAPI startup."""
    global decision_engine, alpaca_client
    logger.info("Initializing Alpaca AI Trading Agent Server...")

    api_key = os.getenv("ALPACA_API_KEY", "")
    secret_key = os.getenv("ALPACA_SECRET_KEY", "")
    paper_trading = os.getenv("ALPACA_PAPER", "true").lower() == "true"

    if AlpacaMCPClient:
        # TODO: Initialize real AlpacaMCPClient with environment variables
        alpaca_client = AlpacaMCPClient(
            api_key=api_key, secret_key=secret_key, paper=paper_trading
        )

    if DecisionEngine:
        # TODO: Initialize real DecisionEngine with Alpaca client and LLM configuration
        decision_engine = DecisionEngine(alpaca_client=alpaca_client)

    logger.info("Server startup complete. Environment: paper=%s", paper_trading)


# -----------------------------------------------------------------------------
# Health Check Endpoint
# -----------------------------------------------------------------------------


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint to verify server availability.

    Returns:
        Dictionary containing server status, version, and UTC timestamp.
    """
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": app.version,
    }


# -----------------------------------------------------------------------------
# Account & Portfolio Endpoints
# -----------------------------------------------------------------------------


@app.get("/api/account")
async def get_account() -> Dict[str, Any]:
    """Retrieve Alpaca account information.

    Returns:
        Account details including buying power, cash balance, and portfolio value.
    """
    if alpaca_client and hasattr(alpaca_client, "get_account"):
        # TODO: Replace with real call: return await alpaca_client.get_account()
        pass

    # Placeholder / mock data until Alpaca MCP integration is connected
    return {
        "id": "mock-account-123",
        "account_number": "PA31415926",
        "status": "ACTIVE",
        "currency": "USD",
        "buying_power": 100000.0,
        "cash": 50000.0,
        "portfolio_value": 105230.50,
        "pattern_day_trader": False,
        "trading_blocked": False,
        "transfers_blocked": False,
        "account_blocked": False,
        "created_at": "2026-01-01T00:00:00Z",
    }


@app.get("/api/positions")
async def get_positions() -> List[Dict[str, Any]]:
    """Retrieve current open portfolio positions.

    Returns:
        List of active open position dictionaries.
    """
    if alpaca_client and hasattr(alpaca_client, "get_positions"):
        # TODO: Replace with real call: return await alpaca_client.get_positions()
        pass

    # Placeholder / mock data
    return [
        {
            "asset_id": "904807e2-320e-4c3d-b4d9-61ab8b9a1e34",
            "symbol": "AAPL",
            "exchange": "NASDAQ",
            "asset_class": "us_equity",
            "avg_entry_price": 180.50,
            "qty": 50.0,
            "side": "long",
            "market_value": 9250.0,
            "cost_basis": 9025.0,
            "unrealized_pl": 225.0,
            "unrealized_plpc": 0.0249,
            "current_price": 185.0,
        },
        {
            "asset_id": "84851834-03f1-4f0e-b70d-3fb2e0b57112",
            "symbol": "MSFT",
            "exchange": "NASDAQ",
            "asset_class": "us_equity",
            "avg_entry_price": 410.0,
            "qty": 20.0,
            "side": "long",
            "market_value": 8400.0,
            "cost_basis": 8200.0,
            "unrealized_pl": 200.0,
            "unrealized_plpc": 0.0244,
            "current_price": 420.0,
        },
    ]


@app.get("/api/orders")
async def get_orders(
    status: str = "open", limit: int = 50
) -> List[Dict[str, Any]]:
    """Retrieve recent trade orders.

    Args:
        status: Filter orders by status ('open', 'closed', 'all').
        limit: Max number of orders to return.

    Returns:
        List of order dictionaries.
    """
    if alpaca_client and hasattr(alpaca_client, "get_orders"):
        # TODO: Replace with real call: return await alpaca_client.get_orders(status=status, limit=limit)
        pass

    # Placeholder / mock data
    return [
        {
            "id": "order-001",
            "client_order_id": "pairs_aapl_msft_1",
            "symbol": "AAPL",
            "qty": 10.0,
            "filled_qty": 10.0,
            "side": "buy",
            "type": "market",
            "time_in_force": "day",
            "status": "filled",
            "filled_avg_price": 182.30,
            "submitted_at": "2026-08-12T10:00:00Z",
        }
    ]


@app.get("/api/portfolio-history")
async def get_portfolio_history(
    period: str = "1M", timeframe: str = "1D"
) -> Dict[str, Any]:
    """Retrieve historical portfolio equity performance for P&L visualization.

    Args:
        period: Time window (e.g., '1D', '1W', '1M', '1A').
        timeframe: Candle granularity ('1Min', '5Min', '1D').

    Returns:
        Dictionary containing equity time series, timestamps, and profit/loss arrays.
    """
    if alpaca_client and hasattr(alpaca_client, "get_portfolio_history"):
        # TODO: Replace with real call: return await alpaca_client.get_portfolio_history(period, timeframe)
        pass

    # Placeholder / mock data
    return {
        "timeframe": timeframe,
        "period": period,
        "base_value": 100000.0,
        "timestamp": [1770000000, 1770086400, 1770172800],
        "equity": [100000.0, 102500.0, 105230.50],
        "profit_loss": [0.0, 2500.0, 5230.50],
        "profit_loss_pct": [0.0, 0.025, 0.0523],
    }


# -----------------------------------------------------------------------------
# Strategy Control Endpoints
# -----------------------------------------------------------------------------


@app.post("/api/strategy/start")
async def start_strategy(
    config: Optional[StrategyConfig] = None,
) -> Dict[str, Any]:
    """Start the trading strategy evaluation loop.

    Args:
        config: Optional strategy configuration overrides.

    Returns:
        Status response dictionary indicating loop state.
    """
    global agent_running, current_strategy, strategy_task

    if agent_running:
        return {"status": "already_running", "strategy": current_strategy}

    if config:
        current_strategy = config.strategy_name

    agent_running = True
    # TODO: Start background trading loop task e.g.,
    # strategy_task = asyncio.create_task(_run_strategy_loop(current_strategy))

    await ws_manager.broadcast(
        {
            "type": "strategy_status",
            "data": {"is_running": True, "strategy": current_strategy},
        }
    )

    return {"status": "started", "strategy": current_strategy}


@app.post("/api/strategy/stop")
async def stop_strategy() -> Dict[str, Any]:
    """Stop the active trading strategy evaluation loop.

    Returns:
        Status response dictionary indicating loop termination.
    """
    global agent_running, strategy_task

    if not agent_running:
        return {"status": "not_running", "strategy": current_strategy}

    agent_running = False
    if strategy_task and not strategy_task.done():
        strategy_task.cancel()
        strategy_task = None

    await ws_manager.broadcast(
        {
            "type": "strategy_status",
            "data": {"is_running": False, "strategy": current_strategy},
        }
    )

    return {"status": "stopped", "strategy": current_strategy}


@app.get("/api/agent-state", response_model=AgentState)
async def get_agent_state() -> AgentState:
    """Get the current operational state of the trading agent.

    Returns:
        AgentState Pydantic model with runtime metrics.
    """
    uptime = time.time() - start_time
    return AgentState(
        is_running=agent_running,
        strategy_name=current_strategy,
        last_decision=last_decision,
        total_trades=total_trades,
        total_pnl=total_pnl,
        uptime_seconds=round(uptime, 2),
    )


# -----------------------------------------------------------------------------
# Reasoning Log Endpoints (Transparency & Audit)
# -----------------------------------------------------------------------------


@app.get("/api/reasoning-log")
async def get_reasoning_log(
    limit: int = 50, offset: int = 0
) -> List[Dict[str, Any]]:
    """Retrieve paginated audit entries from the transparent reasoning log.

    Args:
        limit: Maximum entries to return.
        offset: Pagination offset.

    Returns:
        List of decision cycle dictionaries.
    """
    return reasoning_log.get_entries(limit=limit, offset=offset)


@app.get("/api/reasoning-log/summary")
async def get_reasoning_log_summary() -> Dict[str, Any]:
    """Retrieve aggregate summary statistics for all decision cycles.

    Returns:
        Summary metrics including total trades, win rate, and tool usage.
    """
    return reasoning_log.get_summary()


@app.get("/api/reasoning-log/{cycle_id}")
async def get_reasoning_log_entry(cycle_id: int) -> Dict[str, Any]:
    """Retrieve a specific reasoning log entry by cycle_id.

    Args:
        cycle_id: Unique cycle identifier.

    Returns:
        Log entry dictionary.
    """
    entry = reasoning_log.get_entry(cycle_id)
    if not entry:
        raise HTTPException(
            status_code=404,
            detail=f"Reasoning log entry for cycle {cycle_id} not found",
        )
    return entry


# -----------------------------------------------------------------------------
# Chat Endpoints
# -----------------------------------------------------------------------------


@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest) -> ChatResponse:
    """Send a user message to the AI agent for analysis or execution.

    Args:
        request: ChatRequest containing user message and optional session_id.

    Returns:
        ChatResponse containing agent text output and tool calls executed.
    """
    session_id = request.session_id or str(uuid.uuid4())
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []

    chat_sessions[session_id].append(
        {"role": "user", "content": request.message}
    )

    if decision_engine and hasattr(decision_engine, "chat"):
        # TODO: Replace placeholder with actual DecisionEngine.chat call
        # response_text, tool_calls = await decision_engine.chat(session_id, request.message)
        pass

    # Placeholder response logic
    response_text = (
        f"Received message: '{request.message}'. The Alpaca AI Agent is observing "
        f"market conditions under the '{current_strategy}' strategy."
    )
    tool_calls = [
        {
            "name": "get_account",
            "args": {},
            "result": {"buying_power": 100000.0},
        }
    ]

    chat_sessions[session_id].append(
        {"role": "assistant", "content": response_text}
    )

    return ChatResponse(
        response=response_text,
        session_id=session_id,
        tool_calls=tool_calls,
    )


@app.post("/api/session/new")
async def create_chat_session() -> Dict[str, Any]:
    """Create a new chat conversation session.

    Returns:
        Dictionary containing new session_id and creation timestamp.
    """
    session_id = str(uuid.uuid4())
    chat_sessions[session_id] = []
    return {
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/session/{session_id}/history")
async def get_session_history(session_id: str) -> Dict[str, Any]:
    """Retrieve message history for a specific chat session.

    Args:
        session_id: Target session identifier.

    Returns:
        Dictionary containing session_id and list of chat messages.
    """
    if session_id not in chat_sessions:
        raise HTTPException(
            status_code=404, detail=f"Session '{session_id}' not found"
        )
    return {"session_id": session_id, "history": chat_sessions[session_id]}


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str) -> Dict[str, Any]:
    """Delete a chat session and purge its message history.

    Args:
        session_id: Target session identifier to delete.

    Returns:
        Confirmation dictionary.
    """
    if session_id in chat_sessions:
        del chat_sessions[session_id]
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(
        status_code=404, detail=f"Session '{session_id}' not found"
    )


# -----------------------------------------------------------------------------
# WebSocket Real-Time Stream Endpoint
# -----------------------------------------------------------------------------


@app.websocket("/api/stream")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time data and event streaming.

    Args:
        websocket: Standard FastAPI WebSocket instance.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await ws_manager.send_personal(
                websocket,
                {"type": "ack", "message": f"Received client signal: {data}"},
            )
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket processing error: {e}")
        ws_manager.disconnect(websocket)
