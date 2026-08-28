"""
Configuration module for connecting to the Alpaca MCP (Model Context Protocol) Server.

This module provides constants, environment variable formatters, and server configuration
generators for the Alpaca MCP Server v2. The Alpaca MCP Server dynamically exposes over 60
tools derived directly from Alpaca OpenAPI specifications across multiple asset classes and services.

Key Tool Categories and Endpoints:
- Account: get_account_info
- Orders: submit_order, get_orders, cancel_order, replace_order
- Positions: get_positions, close_position, close_all_positions
- Stock Data: get_stock_bars, get_stock_quotes, get_stock_snapshot, get_stock_trades
- Options: get_option_contracts, get_option_quotes
- Crypto: get_crypto_bars, get_crypto_quotes
- Watchlists: get_watchlists, create_watchlist, update_watchlist, delete_watchlist
- Portfolio: get_portfolio_history
- Calendar & Clock: get_market_calendar, get_market_clock
- Assets: get_asset, list_assets
- Docs: search_docs, get_doc
"""

from typing import Any, Dict, List, Optional

# Executable command for launching the Alpaca MCP server via uvx
MCP_SERVER_COMMAND: str = "uvx"

# Default command-line arguments for the MCP server invocation
MCP_SERVER_ARGS: List[str] = ["alpaca-mcp-server"]

# Comprehensive list of supported Alpaca MCP toolsets
ALPACA_TOOLSETS: List[str] = [
    "account",
    "orders",
    "positions",
    "market_data_stock",
    "market_data_options",
    "market_data_crypto",
    "watchlists",
    "portfolio",
    "calendar",
    "assets",
    "docs",
]


def get_mcp_env(api_key: str, secret_key: str, paper: bool = True) -> Dict[str, str]:
    """
    Generate environment variables required by the Alpaca MCP server process.

    Args:
        api_key: Alpaca API key ID.
        secret_key: Alpaca API secret key.
        paper: Whether to operate in paper trading mode. Defaults to True.

    Returns:
        Dict[str, str]: Dictionary containing the environment variables:
            - ALPACA_API_KEY: The API key.
            - ALPACA_SECRET_KEY: The API secret key.
            - ALPACA_PAPER_TRADE: 'true' if paper else 'false'.
    """
    return {
        "ALPACA_API_KEY": api_key,
        "ALPACA_SECRET_KEY": secret_key,
        "ALPACA_PAPER_TRADE": "true" if paper else "false",
    }


def get_mcp_config(
    api_key: str,
    secret_key: str,
    paper: bool = True,
    toolsets: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generate a full MCP server configuration dictionary suitable for Claude Desktop
    or standard MCP client configurations.

    Args:
        api_key: Alpaca API key ID.
        secret_key: Alpaca API secret key.
        paper: Whether to operate in paper trading mode. Defaults to True.
        toolsets: Optional list of toolsets to enable. If provided, appends --toolsets argument.

    Returns:
        Dict[str, Any]: Full MCP server configuration structure:
            {
                "mcpServers": {
                    "alpaca": {
                        "command": "uvx",
                        "args": ["alpaca-mcp-server", ...],
                        "env": {...}
                    }
                }
            }
    """
    args = list(MCP_SERVER_ARGS)
    if toolsets:
        args.extend(["--toolsets", ",".join(toolsets)])

    return {
        "mcpServers": {
            "alpaca": {
                "command": MCP_SERVER_COMMAND,
                "args": args,
                "env": get_mcp_env(api_key, secret_key, paper=paper),
            }
        }
    }
