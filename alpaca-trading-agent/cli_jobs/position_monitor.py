"""
Periodic position monitoring and risk limit alerting module using the Alpaca CLI.

This module provides the `PositionMonitor` class to continuously evaluate open positions,
detect positions exceeding unrealized loss thresholds, and emit risk alerts.
"""

import asyncio
import json
import logging
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class PositionMonitor:
    """
    Position monitoring agent for tracking unrealized losses against risk thresholds.

    Attributes:
        check_interval (int): Time interval in seconds between monitoring cycles.
        max_loss_pct (float): Maximum allowable percentage loss for a position before flagging an alert.
    """

    def __init__(self, check_interval: int = 300, max_loss_pct: float = 5.0) -> None:
        """
        Initialize the PositionMonitor.

        Args:
            check_interval: Frequency in seconds to check positions (default: 300 seconds).
            max_loss_pct: Threshold percentage loss for risk alert trigger (default: 5.0%).
        """
        self.check_interval = check_interval
        self.max_loss_pct = abs(float(max_loss_pct))

    def _run_cli(self, args: List[str]) -> Dict[str, Any]:
        """
        Execute an `alpaca` CLI command and parse JSON output.

        Args:
            args: Command arguments to pass to the `alpaca` binary.

        Returns:
            Dict[str, Any]: Parsed result dictionary with execution success flag.
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
                return {"success": True, "data": []}

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
                "error": f"JSON decode error: {str(exc)}",
            }
        except Exception as exc:
            logger.exception("Unexpected error executing CLI command.")
            return {"success": False, "error": str(exc)}

    def _check_risk_limits(self, positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Evaluate open positions against max loss risk limits.

        Args:
            positions: List of position dictionaries returned by Alpaca API/CLI.

        Returns:
            List[Dict[str, Any]]: List of alert dictionaries for positions exceeding loss thresholds.
        """
        alerts: List[Dict[str, Any]] = []

        for pos in positions:
            symbol = pos.get("symbol", "UNKNOWN")
            
            # Extract unrealized profit/loss percentage
            # Note: Alpaca API returns unrealized_plpc as a decimal string (e.g., "-0.065" for -6.5%)
            raw_plpc = pos.get("unrealized_plpc") or pos.get("unrealized_plpc_pct", "0")
            try:
                plpc_val = float(raw_plpc)
                # Convert decimal to percentage if returned as decimal (e.g. abs(-0.065) -> 6.5%)
                loss_pct = abs(plpc_val * 100.0) if abs(plpc_val) <= 1.0 and plpc_val != 0 else abs(plpc_val)
            except (ValueError, TypeError):
                loss_pct = 0.0
                plpc_val = 0.0

            unrealized_pl = pos.get("unrealized_pl", "0.0")

            # Trigger alert if loss is negative and loss percentage exceeds max threshold
            if plpc_val < 0 and loss_pct > self.max_loss_pct:
                alert = {
                    "symbol": symbol,
                    "qty": pos.get("qty"),
                    "market_value": pos.get("market_value"),
                    "cost_basis": pos.get("cost_basis"),
                    "current_price": pos.get("current_price"),
                    "unrealized_pl": unrealized_pl,
                    "unrealized_loss_pct": round(loss_pct, 2),
                    "max_loss_pct_threshold": self.max_loss_pct,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "severity": "HIGH",
                }
                alerts.append(alert)
                logger.warning(
                    "RISK ALERT: Position %s unrealized loss (-%.2f%%) exceeds threshold (-%.2f%%)",
                    symbol,
                    loss_pct,
                    self.max_loss_pct,
                )

        return alerts

    async def monitor(self) -> Dict[str, Any]:
        """
        Execute a position monitoring check cycle.

        Queries positions via `alpaca position list`, evaluates risk limits,
        and generates alerts for positions exceeding loss thresholds.

        Returns:
            Dict[str, Any]: Monitoring report dictionary containing timestamp, total positions scanned,
                and list of triggered risk alerts.
        """
        logger.info("Executing position risk monitoring check...")
        timestamp = datetime.now(timezone.utc).isoformat()

        cli_response = await asyncio.to_thread(self._run_cli, ["position", "list", "--format", "json"])

        if not cli_response.get("success"):
            logger.error("Failed to list positions during monitor cycle: %s", cli_response.get("error"))
            return {
                "timestamp": timestamp,
                "status": "error",
                "error": cli_response.get("error"),
                "positions_scanned": 0,
                "alerts": [],
            }

        positions_data = cli_response.get("data", [])
        if isinstance(positions_data, dict):
            positions_data = positions_data.get("positions", [])

        alerts = self._check_risk_limits(positions_data)

        return {
            "timestamp": timestamp,
            "status": "success",
            "positions_scanned": len(positions_data),
            "alerts_count": len(alerts),
            "alerts": alerts,
        }
