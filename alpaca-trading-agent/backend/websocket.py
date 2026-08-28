"""
WebSocket connection manager for real-time streaming in the Alpaca Trading Agent.

Handles active connections, disconnections, unicast messaging, and broadcasting
events such as market data updates, order fills, and agent decisions.
"""

import logging
from typing import List
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections for streaming real-time data."""

    def __init__(self) -> None:
        """Initialize the connection manager with an empty connection list."""
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept an incoming WebSocket connection and register it.

        Args:
            websocket: The FastAPI WebSocket connection instance.
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            f"WebSocket client connected. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from the active tracking list.

        Args:
            websocket: The FastAPI WebSocket connection instance to remove.
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(
                f"WebSocket client disconnected. Total connections: {len(self.active_connections)}"
            )

    async def send_personal(self, websocket: WebSocket, data: dict) -> None:
        """Send a JSON payload to a specific connected WebSocket client.

        Args:
            websocket: Target WebSocket connection.
            data: Dictionary payload to send as JSON.
        """
        try:
            await websocket.send_json(data)
        except Exception as e:
            logger.warning(f"Error sending personal message over WebSocket: {e}")
            self.disconnect(websocket)

    async def broadcast(self, data: dict) -> None:
        """Broadcast a JSON payload to all active WebSocket clients.

        Args:
            data: Dictionary payload to broadcast as JSON.
        """
        disconnected: List[WebSocket] = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.warning(f"Error broadcasting to WebSocket client: {e}")
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(connection)
