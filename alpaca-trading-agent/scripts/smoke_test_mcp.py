#!/usr/bin/env python3
"""
MCP Smoke Test — scripts/smoke_test_mcp.py

Standalone script that:
1. Connects to the Alpaca MCP server via uvx
2. Calls get_account() and prints the real paper trading balance
3. Calls get_market_data("AAPL") and prints a real quote

Run from the project root:
    python scripts/smoke_test_mcp.py

Requires .env with ALPACA_API_KEY and ALPACA_SECRET_KEY set.
"""

import asyncio
import json
import logging
import os
import sys

# Allow running from project root without installing the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv optional; fall back to env vars already set

from mcp_client.client import AlpacaMCPClient

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _pretty(obj: object) -> str:
    """Pretty-print a dict/list as JSON, or return str() for other types."""
    try:
        return json.dumps(obj, indent=2, default=str)
    except (TypeError, ValueError):
        return str(obj)


async def run_smoke_test() -> None:
    api_key = os.getenv("ALPACA_API_KEY", "")
    secret_key = os.getenv("ALPACA_SECRET_KEY", "")

    if not api_key or not secret_key:
        print("ERROR: ALPACA_API_KEY and ALPACA_SECRET_KEY must be set.")
        print("Copy .env.example to .env and fill in your paper trading credentials.")
        sys.exit(1)

    print("=" * 60)
    print(" Alpaca MCP Smoke Test")
    print("=" * 60)
    print(f"API Key (first 8 chars): {api_key[:8]}...")
    print()

    async with AlpacaMCPClient(api_key=api_key, secret_key=secret_key, paper=True) as client:

        # ----------------------------------------------------------------
        # 1. List available tools
        # ----------------------------------------------------------------
        print("[1] Listing MCP tools ...")
        tools = await client.list_tools()
        print(f"    -> {len(tools)} tools available")
        for t in tools[:5]:
            print(f"       - {t['name']}: {str(t.get('description', ''))[:60]}")
        if len(tools) > 5:
            print(f"       ... and {len(tools) - 5} more")
        print()

        # ----------------------------------------------------------------
        # 2. get_account()
        # ----------------------------------------------------------------
        print("[2] Fetching account (get_account) ...")
        account = await client.get_account()
        print("    -> Raw result:")
        print(_pretty(account))
        print()

        # Extract key fields for a clean summary
        if isinstance(account, dict):
            print("    -> Account Summary:")
            for key in ["id", "status", "currency", "portfolio_value", "cash", "buying_power", "equity"]:
                val = account.get(key, "N/A")
                print(f"       {key}: {val}")
        print()

        # ----------------------------------------------------------------
        # 3. get_market_data("AAPL")
        # ----------------------------------------------------------------
        print("[3] Fetching AAPL market data (get_stock_snapshot) ...")
        market_data = await client.get_market_data("AAPL", timeframe="1Day", limit=3)
        print("    -> Raw result:")
        print(_pretty(market_data))
        print()

        # ----------------------------------------------------------------
        # 4. Market clock
        # ----------------------------------------------------------------
        print("[4] Fetching market clock (get_clock) ...")
        clock = await client.get_clock()
        print("    -> Clock:")
        print(_pretty(clock))
        print()

    print("=" * 60)
    print(" Smoke test PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_smoke_test())
