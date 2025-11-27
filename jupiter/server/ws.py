"""WebSocket handling for Jupiter."""

from __future__ import annotations

import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


async def websocket_endpoint(websocket: WebSocket):
    """Placeholder for WebSocket handling.

    Accepts a connection and waits for messages. In a real implementation,
    this would be used to stream logs or other real-time events.
    """
    await websocket.accept()
    logger.info("WebSocket connection established.")
    try:
        while True:
            # For now, just keep the connection open and ignore received data.
            await websocket.receive_text()
    except Exception:
        logger.info("WebSocket connection closed.")
