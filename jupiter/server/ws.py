"""WebSocket handling for Jupiter."""

from __future__ import annotations

import logging
import json
from typing import List, Union, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from jupiter.core.events import JupiterEvent

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket connection established.")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info("WebSocket connection closed.")

    async def broadcast(self, message: Union[str, Dict[str, Any], JupiterEvent]):
        """Broadcast a message to all connected clients.
        
        Args:
            message: Can be a string, a dict, or a JupiterEvent object.
        """
        if isinstance(message, JupiterEvent):
            payload = json.dumps(message.to_dict())
        elif isinstance(message, dict):
            payload = json.dumps(message)
        else:
            payload = str(message)

        to_remove = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception:
                logger.warning("Failed to send message to a client. Removing connection.")
                to_remove.append(connection)
        
        for connection in to_remove:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
