"""
End-of-Day (EOD) portfolio rebalancing module using the Alpaca CLI interface.

This module provides the `EODRebalancer` class, which fetches current portfolio
positions and account equity via the `alpaca` CLI command, compares current holdings
against target asset allocations, and submits rebalancing orders.
"""

import asyncio
import json
import logging
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EODRebalancer:
    """
    End-of-Day portfolio rebalancer driven by Alpaca CLI commands.

    Attributes:
        target_allocations (Dict[str, float]): Target portfolio allocations where keys
            are symbol tickers and values are fractional weights (summing to 1.0).
    """

    def __init__(self, target_allocations: Optional[Dict[str, float]] = None) -> None:
        """
        Initialize the EODRebalancer.

        Args:
            target_allocations: Target portfolio allocations (e.g., {'SPY': 0.5, 'QQQ': 0.5}).
                Defaults to 50% SPY and 50% QQQ if not specified.
        """
        if target_allocations is None:
            self.target_allocations = {"SPY": 0.5, "QQQ": 0.5}
        else:
            self.target_allocations = target_allocations

        # Validate total allocation weight sum
        total_weight = sum(self.target_allocations.values())
        if not (0.99 <= total_weight <= 1.01):
            logger.warning(
                "Target allocation weights sum to %.4f (expected ~1.0). "
                "Calculations will proceed based on provided ratios.",
                total_weight,
            )

    def _run_cli(self, args: List[str]) -> Dict[str, Any]:
        """
        Execute an `alpaca` CLI command and parse the JSON output.

        Args:
            args: Subcommands and flags to pass to the `alpaca` binary (e.g., ['position', 'list']).

        Returns:
            Dict[str, Any]: Parsed JSON response dictionary or error details.
        """
        command = ["alpaca"] + args
        logger.debug("Executing CLI command: %s", " ".join(command))

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.error(
                    "Alpaca CLI command failed (exit code %d): %s",
                    result.returncode,
                    result.stderr.strip(),
                )
                return {
                    "success": False,
                    "error": result.stderr.strip(),
                    "returncode": result.returncode,
                }

            stdout_str = result.stdout.strip()
            if not stdout_str:
                return {"success": True, "data": {}}

            parsed_data = json.loads(stdout_str)
            return {"success": True, "data": parsed_data}

        except FileNotFoundError:
            logger.exception("The 'alpaca' CLI binary was not found on PATH.")
            return {
                "success": False,
                "error": "CLI executable 'alpaca' not found on PATH",
            }
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse JSON from CLI output: %s", exc)
            return {
                "success": False,
                "raw_output": result.stdout if 'result' in locals() else "",
                "error": f"JSON decode error: {str(exc)}",
            }
        except Exception as exc:
            logger.exception("Unexpected error executing CLI command.")
            return {"success": False, "error": str(exc)}

    def _calculate_rebalance_orders(
        self,
        current_positions: Dict[str, Dict[str, Any]],
        target: Dict[str, float],
        equity: float,
    ) -> List[Dict[str, Any]]:
        """
        Compute required buy/sell rebalance orders based on current positions and target allocations.

        Args:
            current_positions: Dictionary mapping symbol to position details
                (e.g., {'SPY': {'qty': 10, 'market_value': 4500.0, 'current_price': 450.0}}).
            target: Target allocation weights dictionary (e.g., {'SPY': 0.5, 'QQQ': 0.5}).
            equity: Total account portfolio equity in USD.

        Returns:
            List[Dict[str, Any]]: List of order specifications to execute rebalance.
        """
        orders: List[Dict[str, Any]] = []

        if equity <= 0:
            logger.error("Account equity must be greater than zero to calculate rebalance orders.")
            return orders

        # Process all targeted assets
        all_symbols = set(target.keys()).union(set(current_positions.keys()))

        for symbol in all_symbols:
            target_weight = target.get(symbol, 0.0)
            target_value = equity * target_weight

            pos_info = current_positions.get(symbol, {})
            current_val = float(pos_info.get("market_value", 0.0))
            current_qty = float(pos_info.get("qty", 0.0))
            current_price = float(pos_info.get("current_price", 0.0))

            # Infer price if missing from market value and quantity
            if current_price <= 0 and current_qty > 0:
                current_price = current_val / current_qty

            val_diff = target_value - current_val

            if current_price > 0:
                shares_delta = int(val_diff / current_price)
            else:
                # If price is unavailable for a new position, defer quantity calculation or log warning
                logger.warning(
                    "Current market price for %s is unknown; skipping order calculation.",
                    symbol,
                )
                continue

            if shares_delta > 0:
                orders.append({
                    "symbol": symbol,
                    "qty": abs(shares_delta),
                    "side": "buy",
                    "type": "market",
                    "time_in_force": "day",
                    "target_value": target_value,
                    "current_value": current_val,
                })
            elif shares_delta < 0:
                orders.append({
                    "symbol": symbol,
                    "qty": abs(shares_delta),
                    "side": "sell",
                    "type": "market",
                    "time_in_force": "day",
                    "target_value": target_value,
                    "current_value": current_val,
                })

        return orders

    async def run(self) -> Dict[str, Any]:
        """
        Execute end-of-day portfolio rebalancing.

        Steps:
        1. Query account equity and active positions via `alpaca position list` / `alpaca account get`.
        2. Calculate difference between current allocations and target weights.
        3. Submit buy/sell orders via `alpaca order submit`.

        Returns:
            Dict[str, Any]: Summary dictionary containing execution status, calculated orders, and order response data.
        """
        logger.info("Starting EOD portfolio rebalance run...")

        # 1. Fetch current positions via CLI
        pos_res = await asyncio.to_thread(self._run_cli, ["position", "list"])
        if not pos_res.get("success"):
            logger.error("Failed to retrieve current positions: %s", pos_res.get("error"))
            return {"status": "failed", "stage": "get_positions", "error": pos_res.get("error")}

        positions_raw = pos_res.get("data", [])
        if isinstance(positions_raw, dict):
            positions_raw = positions_raw.get("positions", [])

        # 2. Fetch account info via CLI to get equity
        acc_res = await asyncio.to_thread(self._run_cli, ["account", "get"])
        if not acc_res.get("success"):
            logger.error("Failed to retrieve account summary: %s", acc_res.get("error"))
            return {"status": "failed", "stage": "get_account", "error": acc_res.get("error")}

        account_data = acc_res.get("data", {})
        equity = float(account_data.get("equity", 0.0))

        # Format current positions lookup map
        current_positions: Dict[str, Dict[str, Any]] = {}
        for pos in positions_raw:
            sym = pos.get("symbol")
            if sym:
                current_positions[sym] = {
                    "qty": float(pos.get("qty", 0)),
                    "market_value": float(pos.get("market_value", 0.0)),
                    "current_price": float(pos.get("current_price", 0.0)),
                }

        # 3. Calculate rebalance orders
        orders_to_submit = self._calculate_rebalance_orders(
            current_positions=current_positions,
            target=self.target_allocations,
            equity=equity,
        )

        logger.info("Calculated %d rebalance orders.", len(orders_to_submit))

        # 4. Submit orders via CLI
        submitted_orders: List[Dict[str, Any]] = []
        failed_orders: List[Dict[str, Any]] = []

        for order in orders_to_submit:
            cmd_args = [
                "order",
                "submit",
                "--symbol", order["symbol"],
                "--qty", str(order["qty"]),
                "--side", order["side"],
                "--type", order["type"],
                "--time-in-force", order["time_in_force"],
            ]
            sub_res = await asyncio.to_thread(self._run_cli, cmd_args)
            if sub_res.get("success"):
                submitted_orders.append({"order": order, "response": sub_res.get("data")})
            else:
                failed_orders.append({"order": order, "error": sub_res.get("error")})

        return {
            "status": "completed",
            "account_equity": equity,
            "orders_calculated": len(orders_to_submit),
            "submitted_orders": submitted_orders,
            "failed_orders": failed_orders,
        }
