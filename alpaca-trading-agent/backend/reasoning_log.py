"""
Transparency and audit log for tracking AI trading agent decisions.

Provides in-memory storage of reasoning cycles using a capped deque,
with thread-safe append, query, pagination, filtering, and summary statistics.
"""

from collections import deque
from datetime import datetime, timezone
import threading
from typing import Any, Dict, List, Optional


class ReasoningLog:
    """In-memory audit log for trading agent decision cycles."""

    def __init__(self, max_entries: int = 1000) -> None:
        """Initialize the reasoning log with a maximum capacity.

        Args:
            max_entries: Maximum number of log entries to retain in memory.
        """
        self.max_entries = max_entries
        self._entries: deque = deque(maxlen=max_entries)
        self._lock = threading.Lock()

    def add_entry(
        self,
        cycle_id: int,
        market_data: dict,
        llm_reasoning: str,
        decision: dict,
        mcp_tools_called: list,
        orders_placed: list,
        result: dict,
    ) -> dict:
        """Add a new decision cycle entry to the log.

        Args:
            cycle_id: Sequence number of the reasoning cycle.
            market_data: Snapshot of market parameters analyzed.
            llm_reasoning: Text reasoning or chain-of-thought output from the LLM.
            decision: Final decision dict (action, signal, confidence, etc.).
            mcp_tools_called: List of MCP tools invoked during this cycle.
            orders_placed: List of orders submitted to Alpaca during this cycle.
            result: Result metrics and execution status dictionary.

        Returns:
            The created log entry dictionary.
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cycle_id": cycle_id,
            "market_data": market_data,
            "llm_reasoning": llm_reasoning,
            "decision": decision,
            "mcp_tools_called": mcp_tools_called,
            "orders_placed": orders_placed,
            "result": result,
        }
        with self._lock:
            self._entries.append(entry)
        return entry

    def get_entries(self, limit: int = 50, offset: int = 0) -> List[dict]:
        """Retrieve paginated reasoning log entries (newest first).

        Args:
            limit: Maximum number of entries to return.
            offset: Number of recent entries to skip.

        Returns:
            A list of log entry dictionaries.
        """
        with self._lock:
            entries_list = list(reversed(self._entries))
        return entries_list[offset : offset + limit]

    def get_entry(self, cycle_id: int) -> Optional[dict]:
        """Retrieve a specific reasoning log entry by cycle_id.

        Args:
            cycle_id: Sequence number of the desired cycle.

        Returns:
            Matching log entry dictionary if found, else None.
        """
        with self._lock:
            for entry in self._entries:
                if entry.get("cycle_id") == cycle_id:
                    return entry
        return None

    def get_summary(self) -> dict:
        """Calculate summary statistics across all recorded decision cycles.

        Returns:
            Dictionary containing total_entries, total_trades, total_orders,
            winning_trades, losing_trades, win_rate, avg_pnl, total_pnl,
            and mcp_tool_usage metrics.
        """
        with self._lock:
            entries = list(self._entries)

        total_entries = len(entries)
        total_trades = 0
        total_orders = 0
        total_pnl = 0.0
        winning_trades = 0
        losing_trades = 0
        tool_counts: Dict[str, int] = {}

        for entry in entries:
            orders = entry.get("orders_placed", [])
            total_orders += len(orders)
            if orders:
                total_trades += len(orders)

            res = entry.get("result", {})
            pnl = res.get("pnl", 0.0)
            if pnl != 0.0:
                total_pnl += pnl
                if pnl > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1

            for tool in entry.get("mcp_tools_called", []):
                if isinstance(tool, dict):
                    tool_name = tool.get("name") or tool.get("tool_name") or "unknown"
                else:
                    tool_name = str(tool)
                tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

        total_resolved_trades = winning_trades + losing_trades
        win_rate = (winning_trades / total_resolved_trades) if total_resolved_trades > 0 else 0.0
        avg_pnl = (total_pnl / total_trades) if total_trades > 0 else 0.0

        return {
            "total_entries": total_entries,
            "total_trades": total_trades,
            "total_orders": total_orders,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 4),
            "avg_pnl": round(avg_pnl, 4),
            "total_pnl": round(total_pnl, 4),
            "mcp_tool_usage": tool_counts,
        }

    def clear(self) -> None:
        """Clear all entries from the reasoning log."""
        with self._lock:
            self._entries.clear()
