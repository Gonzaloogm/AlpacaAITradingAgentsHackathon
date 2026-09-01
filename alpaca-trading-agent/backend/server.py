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

# Environment setup
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Package imports for agent, strategy, and MCP client modules
try:
    from agent.decision_engine import DecisionEngine  # type: ignore
except ImportError:
    DecisionEngine = None

try:
    from strategy.pairs_trading import PairsTradingStrategy  # type: ignore
except ImportError:
    PairsTradingStrategy = None

try:
    from mcp_client.client import AlpacaMCPClient  # type: ignore
except ImportError:
    AlpacaMCPClient = None

logger = logging.getLogger("alpaca_agent_server")
logging.basicConfig(level=logging.INFO)


def _flatten_list_result(res: Any) -> List[Dict[str, Any]]:
    """Unwrap ``[{"result": [...]}]`` or ``{"result": [...]}`` MCP envelopes.

    The Alpaca MCP server may return results wrapped in a single-element list
    whose only item is ``{"result": <actual_list>}``.  This helper normalises
    the response to a plain list so the frontend always receives a flat array.
    """
    # Pattern A: [{"result": [...]}]
    if (
        isinstance(res, list)
        and len(res) == 1
        and isinstance(res[0], dict)
        and "result" in res[0]
        and isinstance(res[0]["result"], list)
    ):
        return res[0]["result"]

    # Pattern B: {"result": [...]}
    if isinstance(res, dict) and "result" in res and isinstance(res["result"], list):
        return res["result"]

    # Already a plain list
    if isinstance(res, list):
        return res

    return [res] if res else []

# Global Application Instance & Configuration
app = FastAPI(
    title="Alpaca AI Trading Agent",
    description="AI-powered trading agent using Claude/Gemini + Alpaca MCP",
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

# Initialized client instances
decision_engine: Any = None
alpaca_client: Any = None


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize agent components and client connections on FastAPI startup."""
    global decision_engine, alpaca_client
    logger.info("Initializing Alpaca AI Trading Agent Server...")

    api_key = os.getenv("ALPACA_API_KEY", "")
    secret_key = os.getenv("ALPACA_SECRET_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    paper_trading = os.getenv("ALPACA_PAPER", "true").lower() == "true"

    if AlpacaMCPClient and api_key and secret_key:
        try:
            alpaca_client = AlpacaMCPClient(
                api_key=api_key, secret_key=secret_key, paper=paper_trading
            )
            await alpaca_client.start()
            logger.info("AlpacaMCPClient subprocess started successfully.")
        except Exception as e:
            logger.warning("Could not start AlpacaMCPClient subprocess: %s", e)
            logger.warning(
                "\n"
                "╔══════════════════════════════════════════════════════════════╗\n"
                "║  ⚠️  MOCK-FALLBACK MODE ACTIVE — NOT REAL ALPACA DATA  ⚠️   ║\n"
                "║                                                              ║\n"
                "║  MCP subprocess failed to start (see error above).          ║\n"
                "║  /api/positions and /api/orders will return HARDCODED MOCK  ║\n"
                "║  data from server.py — NOT your real Alpaca account.        ║\n"
                "║                                                              ║\n"
                "║  /health will show: mock_fallback_mode: true                ║\n"
                "╚══════════════════════════════════════════════════════════════╝"
            )
    else:
        if not (api_key and secret_key):
            logger.warning(
                "\n"
                "╔══════════════════════════════════════════════════════════════╗\n"
                "║  ⚠️  MOCK-FALLBACK MODE ACTIVE — NO CREDENTIALS SET  ⚠️     ║\n"
                "║  ALPACA_API_KEY / ALPACA_SECRET_KEY not in environment.     ║\n"
                "║  All API endpoints return hardcoded mock data.              ║\n"
                "╚══════════════════════════════════════════════════════════════╝"
            )

    if DecisionEngine:
        primary_provider = "gemini" if gemini_key else ("claude" if anthropic_key else "gemini")
        try:
            decision_engine = DecisionEngine(
                gemini_api_key=gemini_key,
                anthropic_api_key=anthropic_key,
                primary=primary_provider,
            )
            logger.info("DecisionEngine initialized with primary provider: %s", primary_provider)
        except Exception as e:
            logger.warning("Could not initialize DecisionEngine: %s", e)

    mcp_ok = bool(alpaca_client and getattr(alpaca_client, "is_connected", False))
    if mcp_ok:
        logger.info("Server startup complete. MCP=CONNECTED  paper=%s", paper_trading)
    else:
        logger.warning("Server startup complete. MCP=DISCONNECTED  paper=%s  *** MOCK DATA MODE ***", paper_trading)



@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up resources on FastAPI shutdown."""
    global alpaca_client, agent_running, strategy_task
    logger.info("Shutting down Alpaca AI Trading Agent Server...")
    agent_running = False
    if strategy_task and not strategy_task.done():
        strategy_task.cancel()

    if alpaca_client and hasattr(alpaca_client, "stop"):
        try:
            await alpaca_client.stop()
            logger.info("AlpacaMCPClient stopped cleanly.")
        except Exception as e:
            logger.error("Error stopping AlpacaMCPClient: %s", e)


# -----------------------------------------------------------------------------
# Health Check Endpoint
# -----------------------------------------------------------------------------


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint to verify server availability.

    Returns:
        Dictionary containing server status, version, UTC timestamp, and integration states.
        ``mock_fallback_mode`` is ``True`` when MCP is disconnected and all endpoints
        return hardcoded demo data instead of real Alpaca account data.
    """
    mcp_connected = bool(alpaca_client and getattr(alpaca_client, "is_connected", False))
    engine_ready = bool(decision_engine is not None)
    mock_mode = not mcp_connected
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": app.version,
        "mcp_connected": mcp_connected,
        "engine_ready": engine_ready,
        "mock_fallback_mode": mock_mode,
        "data_source": "real_alpaca_account" if mcp_connected else "HARDCODED_MOCK_DATA",
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
    if alpaca_client and getattr(alpaca_client, "is_connected", False):
        try:
            res = await alpaca_client.get_account()
            return res
        except Exception as e:
            logger.error("Error fetching account via AlpacaMCPClient: %s", e)

    # Placeholder / mock fallback if MCP is disconnected
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
    if alpaca_client and getattr(alpaca_client, "is_connected", False):
        try:
            res = await alpaca_client.get_positions()
            return _flatten_list_result(res)
        except Exception as e:
            logger.error("Error fetching positions via AlpacaMCPClient: %s", e)


    # Placeholder / mock data fallback — MCP not connected
    logger.warning(
        "⚠️  /api/positions returning MOCK DATA (MCP disconnected) — "
        "check /health for mock_fallback_mode status"
    )
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
    if alpaca_client and getattr(alpaca_client, "is_connected", False):
        try:
            res = await alpaca_client.get_orders(status=status, limit=limit)
            return _flatten_list_result(res)
        except Exception as e:
            logger.error("Error fetching orders via AlpacaMCPClient: %s", e)


    # Placeholder / mock data fallback — MCP not connected
    logger.warning(
        "⚠️  /api/orders returning MOCK DATA (MCP disconnected) — "
        "check /health for mock_fallback_mode status"
    )
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
    if alpaca_client and getattr(alpaca_client, "is_connected", False):
        try:
            res = await alpaca_client.get_portfolio_history(period=period, timeframe=timeframe)
            return res
        except Exception as e:
            logger.error("Error fetching portfolio history via AlpacaMCPClient: %s", e)

    # Placeholder / mock data fallback
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
# Autonomous Strategy Background Loop
# -----------------------------------------------------------------------------


async def _run_strategy_loop(strategy_name: str) -> None:
    """Autonomous background loop evaluating market signals and executing decisions."""
    global agent_running, last_decision, total_trades, total_pnl
    logger.info("Starting autonomous strategy loop for '%s'...", strategy_name)

    strategy = PairsTradingStrategy(symbol_a="SPY", symbol_b="QQQ") if PairsTradingStrategy else None

    while agent_running:
        try:
            cycle_id = len(reasoning_log.get_entries(limit=10000)) + 1
            logger.info("Executing strategy cycle #%d for %s", cycle_id, strategy_name)

            market_data: Dict[str, Any] = {}
            if alpaca_client and getattr(alpaca_client, "is_connected", False):
                try:
                    data_spy = await alpaca_client.get_market_data("SPY")
                    data_qqq = await alpaca_client.get_market_data("QQQ")
                    market_data = {"SPY": data_spy.get("snapshot", data_spy), "QQQ": data_qqq.get("snapshot", data_qqq)}
                except Exception as err:
                    logger.warning("Could not fetch real snapshot via MCP: %s", err)

            if not market_data:
                # Generate synthetic mock price data for strategy analysis if offline
                import random
                market_data = {
                    "SPY": [500.0 + random.uniform(-2, 2) for _ in range(20)],
                    "QQQ": [430.0 + random.uniform(-2, 2) for _ in range(20)],
                }

            # 2. Compute quantitative signal
            signal = {}
            if strategy:
                signal = await strategy.analyze(market_data)

            # 3. Decision Engine evaluation
            decision = {
                "action": "hold",
                "confidence": 0.5,
                "reasoning": "Standard monitoring turn — spread within normal bounds.",
                "parameters": {},
                "provider": getattr(decision_engine, "primary", "none") if decision_engine else "none",
            }
            if decision_engine:
                try:
                    decision = await decision_engine.analyze_market(
                        market_data=market_data,
                        strategy_context={
                            "strategy_name": strategy_name,
                            "signal": signal,
                            "symbol_a": "SPY",
                            "symbol_b": "QQQ",
                        },
                    )
                except Exception as err:
                    logger.error("DecisionEngine evaluation error: %s", err)

            last_decision = decision
            action = str(decision.get("action", "hold")).lower()
            tool_calls = []

            # 4. Execute order if action is buy or sell
            if action in ("buy", "sell") and alpaca_client and getattr(alpaca_client, "is_connected", False):
                params = decision.get("parameters", {})
                symbol = params.get("symbol", "SPY")
                qty = float(params.get("qty", 1.0))
                try:
                    order_res = await alpaca_client.place_order(
                        symbol=symbol, qty=qty, side=action, type="market", time_in_force="day"
                    )
                    tool_calls.append({
                        "name": "place_stock_order",
                        "args": {"symbol": symbol, "qty": qty, "side": action},
                        "result": order_res,
                    })
                    total_trades += 1
                except Exception as err:
                    logger.error("Order placement error via MCP: %s", err)

            # 5. Log cycle to Reasoning Transparency Log
            log_entry = reasoning_log.add_entry(
                cycle_id=cycle_id,
                market_data=market_data,
                llm_reasoning=str(decision.get("reasoning", "")),
                decision=decision,
                mcp_tools_called=tool_calls,
                orders_placed=[tc.get("result") for tc in tool_calls if "result" in tc],
                result={"pnl": total_pnl, "total_trades": total_trades, "status": "completed"},
            )

            # 6. Broadcast event over WebSockets
            await ws_manager.broadcast({
                "type": "reasoning_log_entry",
                "data": log_entry,
            })
            await ws_manager.broadcast({
                "type": "agent_state_update",
                "data": {
                    "is_running": agent_running,
                    "last_decision": last_decision,
                    "total_trades": total_trades,
                    "total_pnl": total_pnl,
                },
            })

        except asyncio.CancelledError:
            logger.info("Autonomous strategy loop cancelled.")
            break
        except Exception as e:
            logger.error("Error in strategy loop cycle: %s", e)

        # Loop pacing (sleep 30s per turn)
        await asyncio.sleep(30)


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
    strategy_task = asyncio.create_task(_run_strategy_loop(current_strategy))

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
    """Retrieve paginated audit entries from the transparent reasoning log."""
    return reasoning_log.get_entries(limit=limit, offset=offset)


@app.get("/api/reasoning-log/summary")
async def get_reasoning_log_summary() -> Dict[str, Any]:
    """Retrieve aggregate summary statistics for all decision cycles."""
    return reasoning_log.get_summary()


@app.get("/api/reasoning-log/{cycle_id}")
async def get_reasoning_log_entry(cycle_id: int) -> Dict[str, Any]:
    """Retrieve a specific reasoning log entry by cycle_id."""
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
    """Send a user message to the AI agent for analysis or execution."""
    session_id = request.session_id or str(uuid.uuid4())
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []

    chat_sessions[session_id].append({"role": "user", "content": request.message})

    tool_calls: List[Dict[str, Any]] = []
    response_text: str = ""

    if decision_engine:
        try:
            available_tools = []
            if alpaca_client and getattr(alpaca_client, "is_connected", False):
                try:
                    available_tools = await alpaca_client.list_tools()
                except Exception as err:
                    logger.warning("Could not list tools from AlpacaMCPClient: %s", err)

            response_text, tool_calls_made = await decision_engine.chat(
                user_message=request.message,
                conversation_history=chat_sessions[session_id],
                available_tools=available_tools,
            )

            # If tools were called and MCP client is connected, execute tool calls
            if alpaca_client and getattr(alpaca_client, "is_connected", False) and tool_calls_made:
                for tc in tool_calls_made:
                    t_name = tc.get("name", "")
                    t_args = tc.get("input", {})
                    try:
                        res = await alpaca_client.call_tool(t_name, t_args)
                        tool_calls.append({"name": t_name, "args": t_args, "result": res})
                    except Exception as err:
                        logger.error("Error calling MCP tool '%s': %s", t_name, err)
                        tool_calls.append({"name": t_name, "args": t_args, "result": f"Error: {err}"})
            else:
                tool_calls = tool_calls_made

        except Exception as err:
            logger.error("Error in decision_engine.chat: %s", err)
            response_text = f"An error occurred while processing your request: {err}"
    else:
        response_text = (
            f"Received message: '{request.message}'. AI DecisionEngine is not initialized (check API keys)."
        )

    chat_sessions[session_id].append({"role": "assistant", "content": response_text})

    return ChatResponse(
        response=response_text,
        session_id=session_id,
        tool_calls=tool_calls,
    )


@app.post("/api/session/new")
async def create_chat_session() -> Dict[str, Any]:
    """Create a new chat conversation session."""
    session_id = str(uuid.uuid4())
    chat_sessions[session_id] = []
    return {
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/session/{session_id}/history")
async def get_session_history(session_id: str) -> Dict[str, Any]:
    """Retrieve message history for a specific chat session."""
    if session_id not in chat_sessions:
        raise HTTPException(
            status_code=404, detail=f"Session '{session_id}' not found"
        )
    return {"session_id": session_id, "history": chat_sessions[session_id]}


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str) -> Dict[str, Any]:
    """Delete a chat session and purge its message history."""
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
    """WebSocket endpoint for real-time data and event streaming."""
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
