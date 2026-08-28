"""
Alpaca MCP Client Package.

This package provides configuration utilities and a programmatic client wrapper
for interacting with the Alpaca Model Context Protocol (MCP) server.
"""

from mcp_client.client import AlpacaMCPClient
from mcp_client.config import (
    ALPACA_TOOLSETS,
    MCP_SERVER_ARGS,
    MCP_SERVER_COMMAND,
    get_mcp_config,
    get_mcp_env,
)

__all__ = [
    "AlpacaMCPClient",
    "get_mcp_env",
    "get_mcp_config",
    "ALPACA_TOOLSETS",
    "MCP_SERVER_COMMAND",
    "MCP_SERVER_ARGS",
]
