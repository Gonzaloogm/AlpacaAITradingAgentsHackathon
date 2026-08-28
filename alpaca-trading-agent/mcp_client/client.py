"""
Programmatic MCP client wrapper for Alpaca MCP server communication.

Provides an async wrapper for stdio-based communication with the Alpaca MCP
server (v2) using the official MCP Python SDK.

The server is launched as a subprocess via `uvx alpaca-mcp-server` and
communicates over stdio using JSON-RPC 2.0. Tool names match confirmed V2
spec-derived operation IDs from:
  https://github.com/alpacahq/alpaca-mcp-server

Key V2 tool names used:
  Account  : get_account, get_account_portfolio_history
  Trading  : get_all_orders, get_all_open_positions, delete_open_position,
             delete_all_open_positions, place_stock_order
  Mkt Data : get_stock_snapshot, get_stock_bars, get_stock_latest_quote
  Clock    : get_clock, get_calendar
"""

import contextlib
import json
import logging
import os
from typing import Any, Dict, List, Optional

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False
    ClientSession = None  # type: ignore[assignment,misc]
    StdioServerParameters = None  # type: ignore[assignment,misc]
    stdio_client = None  # type: ignore[assignment]

from mcp_client.config import (
    MCP_SERVER_ARGS,
    MCP_SERVER_COMMAND,
    get_mcp_env,
)

logger = logging.getLogger(__name__)


def _extract_text(content: Any) -> Any:
    """Pull plain data out of an MCP tool-call result content block list.

    MCP returns a list of TextContent blocks. We JSON-parse the combined text
    and fall back to returning the raw string if parsing fails.
    """
    if not isinstance(content, list):
        return content
    texts = []
    for block in content:
        text = getattr(block, "text", None)
        if text is not None:
            texts.append(text)
    if not texts:
        return content
    combined = "\n".join(texts)
    try:
        return json.loads(combined)
    except (json.JSONDecodeError, TypeError):
        return combined


class AlpacaMCPClient:
    """
    Async client for stdio communication with the Alpaca MCP Server v2.

    Usage (context manager - recommended)::

        async with AlpacaMCPClient(api_key, secret_key) as client:
            account = await client.get_account()

    Usage (manual lifecycle)::

        client = AlpacaMCPClient(api_key, secret_key)
        await client.start()
        account = await client.get_account()
        await client.stop()
    """

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        paper: bool = True,
    ) -> None:
        """
        Initialize the Alpaca MCP Client.

        Args:
            api_key: Alpaca API key ID.
            secret_key: Alpaca API secret key.
            paper: Whether to operate in paper trading mode. Defaults to True.
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.paper = paper
        self._connected: bool = False
        self._session: Optional[Any] = None  # mcp.ClientSession
        self._exit_stack: contextlib.AsyncExitStack = contextlib.AsyncExitStack()

    # ------------------------------------------------------------------
    # Async context-manager support
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "AlpacaMCPClient":
        await self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.stop()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        """True when the MCP JSON-RPC session is active."""
        return self._connected

    async def start(self) -> None:
        """
        Spawn the Alpaca MCP server subprocess and initialise the stdio
        JSON-RPC session.

        Credentials are injected as environment variables:
        ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_PAPER_TRADE.
        """
        if self._connected:
            logger.warning("AlpacaMCPClient is already running.")
            return

        if not _MCP_AVAILABLE:
            raise ImportError(
                "The 'mcp' package is not installed. "
                "Run: pip install 'mcp>=1.0.0'"
            )

        logger.info("Starting Alpaca MCP server subprocess via uvx ...")

        # Merge current environment with Alpaca credentials
        env = {**os.environ, **get_mcp_env(self.api_key, self.secret_key, self.paper)}

        server_params = StdioServerParameters(
            command=MCP_SERVER_COMMAND,   # "uvx"
            args=MCP_SERVER_ARGS,         # ["alpaca-mcp-server"]
            env=env,
        )

        # Spawn the subprocess and enter the stdio transport context
        read_stream, write_stream = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )

        # Initialise the JSON-RPC session over the stdio streams
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self._session.initialize()

        self._connected = True

        # Log available tools at startup
        tools = await self.list_tools()
        tool_names = [t.get("name") for t in tools]
        logger.info(
            "Alpaca MCP server ready - %d tools available: %s",
            len(tool_names),
            tool_names,
        )

    async def stop(self) -> None:
        """Gracefully shut down the MCP session and the server subprocess."""
        if not self._connected:
            logger.warning("AlpacaMCPClient not running - nothing to stop.")
            return
        logger.info("Stopping Alpaca MCP server ...")
        await self._exit_stack.aclose()
        self._session = None
        self._connected = False
        logger.info("Alpaca MCP server stopped.")

    # ------------------------------------------------------------------
    # Low-level tool primitives
    # ------------------------------------------------------------------

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call an Alpaca MCP V2 tool by its snake_case name and return the
        parsed result.

        Args:
            tool_name: V2 tool name (e.g. 'get_account', 'place_stock_order').
            arguments: Keyword arguments dict per the tool input schema.

        Returns:
            Parsed Python object (dict / list / str) from the MCP response.

        Raises:
            RuntimeError: If the client is not connected.
        """
        if not self._connected or self._session is None:
            raise RuntimeError(
                "Client is not connected. Call 'await client.start()' first, "
                "or use 'async with AlpacaMCPClient(...) as client:'."
            )
        logger.debug("Calling MCP tool %r args=%s", tool_name, arguments)
        result = await self._session.call_tool(tool_name, arguments)
        return _extract_text(result.content)

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all tools currently exposed by the Alpaca MCP server.

        Returns:
            List of dicts with keys: name, description, inputSchema.

        Raises:
            RuntimeError: If the client is not connected.
        """
        if not self._connected or self._session is None:
            raise RuntimeError(
                "Client is not connected. Call 'await client.start()' first."
            )
        response = await self._session.list_tools()
        return [
            {
                "name": t.name,
                "description": getattr(t, "description", ""),
                "inputSchema": getattr(t, "inputSchema", {}),
            }
            for t in response.tools
        ]

    # ------------------------------------------------------------------
    # Account helpers  (toolset: account)
    # ------------------------------------------------------------------

    async def get_account(self) -> Dict[str, Any]:
        """Fetch Alpaca account summary (equity, cash, buying_power, status)."""
        return await self.call_tool("get_account", {})

    async def get_portfolio_history(
        self,
        period: str = "1M",
        timeframe: str = "1D",
    ) -> Dict[str, Any]:
        """
        Fetch portfolio equity history for P&L chart data.

        Args:
            period: '1D', '1W', '1M', '6M', '1A', or 'all'.
            timeframe: '1Min', '5Min', '15Min', '1H', '1D'.
        """
        return await self.call_tool(
            "get_account_portfolio_history",
            {"period": period, "timeframe": timeframe},
        )

    # ------------------------------------------------------------------
    # Position helpers  (toolset: trading)
    # ------------------------------------------------------------------

    async def get_positions(self) -> List[Dict[str, Any]]:
        """Fetch all open portfolio positions."""
        result = await self.call_tool("get_all_open_positions", {})
        if isinstance(result, list):
            return result
        return [result] if result else []

    async def close_position(self, symbol: str) -> Dict[str, Any]:
        """Close the open position for the given symbol."""
        return await self.call_tool(
            "delete_open_position", {"symbol_or_asset_id": symbol}
        )

    async def close_all_positions(self, cancel_orders: bool = True) -> Any:
        """Liquidate all open positions, optionally cancelling open orders first."""
        return await self.call_tool(
            "delete_all_open_positions",
            {"cancel_orders": cancel_orders},
        )

    # ------------------------------------------------------------------
    # Order helpers  (toolset: trading)
    # ------------------------------------------------------------------

    async def get_orders(
        self,
        status: str = "open",
        limit: int = 50,
        symbol: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch orders filtered by status.

        Args:
            status: 'open', 'closed', or 'all'.
            limit: Max orders to return (1-500).
            symbol: Optional ticker filter.
        """
        args: Dict[str, Any] = {"status": status, "limit": limit}
        if symbol:
            args["symbols"] = symbol
        result = await self.call_tool("get_all_orders", args)
        if isinstance(result, list):
            return result
        return [result] if result else []

    async def place_order(
        self,
        symbol: str,
        side: str,
        qty: Optional[str] = None,
        notional: Optional[str] = None,
        order_type: str = "market",
        time_in_force: str = "day",
        limit_price: Optional[str] = None,
        client_order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Place a stock/ETF order via the V2 place_stock_order tool.

        Args:
            symbol: Ticker (e.g. 'SPY', 'AAPL').
            side: 'buy' or 'sell'.
            qty: Number of shares as string. Mutually exclusive with notional.
            notional: Dollar amount. Market + day orders only.
            order_type: 'market', 'limit', 'stop', 'stop_limit', 'trailing_stop'.
            time_in_force: 'day', 'gtc', 'opg', 'cls', 'ioc', 'fok'.
            limit_price: Required for limit/stop_limit orders.
            client_order_id: Optional idempotency key.
        """
        args: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "time_in_force": time_in_force,
        }
        if qty is not None:
            args["qty"] = str(qty)
        if notional is not None:
            args["notional"] = str(notional)
        if limit_price is not None:
            args["limit_price"] = str(limit_price)
        if client_order_id is not None:
            args["client_order_id"] = client_order_id
        return await self.call_tool("place_stock_order", args)

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an open order by its UUID."""
        return await self.call_tool(
            "delete_order_by_order_id", {"order_id": order_id}
        )

    # ------------------------------------------------------------------
    # Market data helpers  (toolset: market_data_stock)
    # ------------------------------------------------------------------

    async def get_market_data(
        self,
        symbol: str,
        timeframe: str = "1Day",
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Fetch a stock market snapshot plus recent historical bars.

        Args:
            symbol: Ticker (e.g. 'AAPL', 'SPY').
            timeframe: Bar granularity ('1Min', '1Hour', '1Day').
            limit: Number of historical bars to retrieve.

        Returns:
            Dict with 'snapshot', 'bars', and 'symbol' keys.
        """
        snapshot = await self.call_tool("get_stock_snapshot", {"symbols": symbol})
        bars = await self.call_tool(
            "get_stock_bars",
            {"symbols": symbol, "timeframe": timeframe, "limit": limit},
        )
        return {"snapshot": snapshot, "bars": bars, "symbol": symbol}

    async def get_latest_quote(self, symbol: str) -> Dict[str, Any]:
        """Fetch the latest bid/ask quote for a stock symbol."""
        return await self.call_tool("get_stock_latest_quote", {"symbols": symbol})

    # ------------------------------------------------------------------
    # Clock / Calendar  (toolset: calendar)
    # ------------------------------------------------------------------

    async def get_clock(self) -> Dict[str, Any]:
        """Get current market open/close status and next open/close times."""
        return await self.call_tool("get_clock", {})

    async def get_calendar(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch the market trading calendar.

        Args:
            start: Start date in YYYY-MM-DD format (default: today).
            end: End date in YYYY-MM-DD format (default: today).
        """
        args: Dict[str, Any] = {}
        if start:
            args["start"] = start
        if end:
            args["end"] = end
        result = await self.call_tool("get_calendar", args)
        if isinstance(result, list):
            return result
        return [result] if result else []
