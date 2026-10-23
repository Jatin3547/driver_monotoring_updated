"""Minimal WebSocket connection manager.

Tracks connected clients and broadcasts JSON messages to all of them.
Used by app/api/routes/ws.py to push GPS updates, safety events,
incidents, and alerts without the frontend needing to poll.
"""

import json
import logging

from fastapi import WebSocket

logger = logging.getLogger("fleet.websocket")


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)
        logger.info("WebSocket connected (%d active)", len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)
        logger.info("WebSocket disconnected (%d active)", len(self._connections))

    async def broadcast(self, event_type: str, payload: dict) -> None:
        message = json.dumps({"type": event_type, "payload": payload})
        stale: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_text(message)
            except Exception:
                stale.append(connection)
        for conn in stale:
            self.disconnect(conn)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()
