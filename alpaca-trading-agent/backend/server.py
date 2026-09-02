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
import random
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
        logger.info("Server startup complete. MCP=DISCONNECTED")
        
    # Start background ticker task
    asyncio.create_task(_price_ticker_loop())



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
# OHLC Candlestick Data Endpoint
# -----------------------------------------------------------------------------


def _normalize_bars(raw_bars: Any, symbol: str) -> List[Dict[str, Any]]:
    """Normalise Alpaca MCP bar data into a clean [{t, o, h, l, c, v}, ...] array.

    The MCP server returns bars in several possible shapes depending on
    whether a single symbol or multi-symbol request was made.  This helper
    handles all observed variants and returns a deterministic list.
    """
    bars_list: List[Any] = []

    if isinstance(raw_bars, list):
        bars_list = raw_bars
    elif isinstance(raw_bars, dict):
        # Multi-symbol envelope: { "SPY": [ ... ] }
        if symbol.upper() in raw_bars:
            bars_list = raw_bars[symbol.upper()]
        # Single-bar dict — wrap
        elif "t" in raw_bars or "timestamp" in raw_bars:
            bars_list = [raw_bars]
        # Nested "bars" key
        elif "bars" in raw_bars:
            nested = raw_bars["bars"]
            if isinstance(nested, dict) and symbol.upper() in nested:
                bars_list = nested[symbol.upper()]
            elif isinstance(nested, list):
                bars_list = nested

    normalised: List[Dict[str, Any]] = []
    for bar in bars_list:
        if not isinstance(bar, dict):
            continue
        entry: Dict[str, Any] = {
            "t": bar.get("t") or bar.get("timestamp") or bar.get("Timestamp", ""),
            "o": float(bar.get("o") or bar.get("open") or bar.get("Open", 0)),
            "h": float(bar.get("h") or bar.get("high") or bar.get("High", 0)),
            "l": float(bar.get("l") or bar.get("low") or bar.get("Low", 0)),
            "c": float(bar.get("c") or bar.get("close") or bar.get("Close", 0)),
            "v": int(float(bar.get("v") or bar.get("volume") or bar.get("Volume", 0))),
        }
        normalised.append(entry)

    return normalised


@app.get("/api/analytics")
async def get_analytics() -> Dict[str, Any]:
    """Compute win rate, Sharpe ratio, and max drawdown from real account data with strict statistical thresholds."""
    if not (alpaca_client and getattr(alpaca_client, "is_connected", False)):
        logger.warning("⚠️  /api/analytics returning MOCK DATA (MCP disconnected)")
        return {
            "win_rate": {"value": 68.5, "insufficient_data": False},
            "sharpe_ratio": {"value": 1.84, "insufficient_data": False},
            "max_drawdown": {"value": -4.2, "insufficient_data": False},
            "is_mock": True,
            "trade_count": 24
        }

    try:
        # 1. Fetch History & Orders
        hist = await alpaca_client.get_portfolio_history(period="1A", timeframe="1D")
        orders_res = await alpaca_client.get_orders(status="all", limit=500)
        orders = _flatten_list_result(orders_res)
        
        # Trade count (completed fills)
        trade_count = len([o for o in orders if o.get("status") == "filled"])
            
        # Win Rate calculation
        # Hard requirement: at least 10 round trips for statistical relevance, but we don't have PnL mapping easily.
        # Fallback gracefully.
        win_rate_obj = {"value": None, "insufficient_data": True}
        
        # 2. Max Drawdown
        # Meaningful even with sparse data, just requires at least 2 equity points to see a drop.
        equity_curve = hist.get("equity", [])
        equity_curve = [e for e in equity_curve if e is not None and e > 0]
        
        max_dd = 0.0
        max_dd_obj = {"value": None, "insufficient_data": True}
        if len(equity_curve) > 1:
            peak = equity_curve[0]
            for eq in equity_curve:
                if eq > peak:
                    peak = eq
                dd = (eq - peak) / peak
                if dd < max_dd:
                    max_dd = dd
            max_dd_obj = {"value": max_dd * 100, "insufficient_data": False}
        
        # 3. Sharpe Ratio
        # Hard requirement: at least 21 equity points (20 returns) for meaningful variance
        sharpe_obj = {"value": None, "insufficient_data": True}
        if len(equity_curve) >= 21:
            import math
            returns = []
            for i in range(1, len(equity_curve)):
                prev = equity_curve[i-1]
                curr = equity_curve[i]
                returns.append((curr - prev) / prev)
            
            mean_ret = sum(returns) / len(returns)
            variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
            std_dev = math.sqrt(variance)
            
            risk_free_daily = 0.04 / 252
            if std_dev > 0:
                sharpe_val = (mean_ret - risk_free_daily) / std_dev * math.sqrt(252)
                sharpe_obj = {"value": sharpe_val, "insufficient_data": False}

        return {
            "win_rate": win_rate_obj,
            "sharpe_ratio": sharpe_obj,
            "max_drawdown": max_dd_obj,
            "trade_count": trade_count,
            "is_mock": False
        }

    except Exception as e:
        logger.error("Error computing analytics: %s", e)
        return {
            "win_rate": {"value": None, "insufficient_data": True},
            "sharpe_ratio": {"value": None, "insufficient_data": True},
            "max_drawdown": {"value": None, "insufficient_data": True},
            "trade_count": 0,
            "is_mock": False
        }


@app.get("/api/ohlc/{symbol}")
async def get_ohlc(
    symbol: str, timeframe: str = "1Day", limit: int = 60
) -> Dict[str, Any]:
    """Return OHLC candlestick bar data for a symbol.

    Reuses the proven ``get_market_data`` MCP path (``get_stock_bars``).

    Args:
        symbol: Ticker (e.g. 'SPY', 'QQQ').
        timeframe: Bar granularity ('1Min', '5Min', '15Min', '1Hour', '1Day').
        limit: Number of bars to return (max 200).

    Returns:
        Dictionary with ``symbol`` and ``bars`` array of OHLC objects.
    """
    limit = min(limit, 200)

    if alpaca_client and getattr(alpaca_client, "is_connected", False):
        try:
            res = await alpaca_client.get_market_data(
                symbol=symbol.upper(), timeframe=timeframe, limit=limit
            )
            bars = _normalize_bars(res.get("bars", []), symbol)
            return {"symbol": symbol.upper(), "bars": bars, "timeframe": timeframe, "is_mock": False}
        except Exception as e:
            logger.error("Error fetching OHLC for %s via AlpacaMCPClient: %s", symbol, e)

    # Placeholder / mock data fallback — MCP not connected
    logger.warning(
        "⚠️  /api/ohlc/%s returning MOCK DATA (MCP disconnected) — "
        "check /health for mock_fallback_mode status",
        symbol,
    )

    base_price = 550.0 if symbol.upper() == "SPY" else 480.0
    mock_bars = []
    for i in range(limit):
        day_ts = 1770000000 + i * 86400
        o = base_price + random.uniform(-5, 5)
        c = o + random.uniform(-3, 3)
        h = max(o, c) + random.uniform(0, 2)
        l_val = min(o, c) - random.uniform(0, 2)
        mock_bars.append({
            "t": datetime.fromtimestamp(day_ts, tz=timezone.utc).isoformat(),
            "o": round(o, 2),
            "h": round(h, 2),
            "l": round(l_val, 2),
            "c": round(c, 2),
            "v": random.randint(20_000_000, 80_000_000),
        })
        base_price = c
    return {"symbol": symbol.upper(), "bars": mock_bars, "timeframe": timeframe, "is_mock": True}


# -----------------------------------------------------------------------------
# Live Price Ticker Background Task
# -----------------------------------------------------------------------------

async def _price_ticker_loop():
    """Polls latest quotes for the ticker tape and broadcasts via WS."""
    symbols = ["SPY", "QQQ", "AAPL", "MSFT", "TSLA"]
    while True:
        try:
            if alpaca_client and getattr(alpaca_client, "is_connected", False):
                res = await alpaca_client.call_tool("get_stock_latest_quote", {"symbols": ",".join(symbols)})
                logger.info("TICKER RAW RES: %s", res)
                
                # Normalize the response. Usually {"SPY": {"ap": 500, "bp": 499}, ...}
                # Unpack if nested:
                if isinstance(res, list):
                    if res and hasattr(res[0], 'text'):
                        import json
                        try:
                            res = json.loads(res[0].text)
                        except:
                            pass
                    elif res and isinstance(res[0], dict) and 'text' in res[0]:
                        import json
                        try:
                            res = json.loads(res[0]['text'])
                        except:
                            pass
                
                logger.info("TICKER PARSED RES: %s", res)
                quotes = res.get("quotes", res) if isinstance(res, dict) else res
                ticks = []
                
                if isinstance(quotes, dict):
                    for sym in symbols:
                        data = quotes.get(sym)
                        if data and isinstance(data, dict):
                            # Usually ap = ask price, bp = bid price. Let's use mid or just ask/bid
                            ap = float(data.get("ap") or data.get("ask_price", 0))
                            bp = float(data.get("bp") or data.get("bid_price", 0))
                            price = ap if ap > 0 else bp
                            if price > 0:
                                ticks.append({"symbol": sym, "price": price})
                
                if ticks:
                    await ws_manager.broadcast({
                        "type": "price_tick",
                        "data": ticks
                    })
            else:
                # Mock fallback mode ticker
                import random
                ticks = []
                base = {"SPY": 550, "QQQ": 480, "AAPL": 220, "MSFT": 410, "TSLA": 250}
                for sym, val in base.items():
                    price = val + random.uniform(-2, 2)
                    ticks.append({"symbol": sym, "price": round(price, 2)})
                await ws_manager.broadcast({
                    "type": "price_tick",
                    "data": ticks
                })
        except Exception as e:
            logger.error("Error in _price_ticker_loop: %s", e)
        
        await asyncio.sleep(15)


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
                    # Pass the full object (which includes snapshot and bars) so the strategy can extract prices
                    market_data = {"SPY": data_spy, "QQQ": data_qqq}
                except Exception as err:
                    logger.warning("Could not fetch real snapshot via MCP: %s", err)

            if not market_data:
                logger.warning("No market data retrieved from MCP. Skipping strategy cycle.")
                await asyncio.sleep(30)
                continue

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
