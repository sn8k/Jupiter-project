"""Bridge-to-WebSocket Event Propagation.

Version: 0.1.0

This module connects the Bridge EventBus to the WebSocket ConnectionManager,
enabling real-time event propagation to WebUI clients.

When initialized, it subscribes to all Bridge events and forwards them
to connected WebSocket clients in a format they can consume.

Usage:
    # During server startup (in lifespan)
    from jupiter.server.ws_bridge import init_ws_bridge, shutdown_ws_bridge
    
    await init_ws_bridge()
    # ... server runs ...
    await shutdown_ws_bridge()
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Global state for the WS bridge
_ws_hook: Optional[Callable] = None
_initialized: bool = False


def _create_ws_event_hook() -> Callable:
    """Create the WebSocket event hook callback.
    
    Returns:
        A callback function that forwards events to WebSocket clients.
    """
    from jupiter.server.ws import manager
    
    def ws_event_hook(event: Any) -> None:
        """Forward Bridge events to WebSocket clients.
        
        Args:
            event: Event object from Bridge EventBus
        """
        try:
            # Convert event to WebSocket-friendly format
            payload = {
                "type": "bridge_event",
                "topic": event.topic,
                "payload": event.payload,
                "timestamp": event.timestamp.isoformat() if hasattr(event, 'timestamp') else None,
                "source_plugin": event.source_plugin,
            }
            
            # Use asyncio to broadcast if there's a running loop
            try:
                loop = asyncio.get_running_loop()
                # Schedule the broadcast in the event loop
                asyncio.create_task(manager.broadcast(payload))
            except RuntimeError:
                # No running event loop - this shouldn't happen in normal server operation
                logger.debug("No event loop available for WebSocket broadcast")
                
        except Exception as e:
            logger.error("Error forwarding event to WebSocket: %s", e)
    
    return ws_event_hook


async def init_ws_bridge() -> bool:
    """Initialize the Bridge-to-WebSocket connection.
    
    This function connects the Bridge EventBus to the WebSocket manager
    so that all Bridge events are automatically forwarded to connected clients.
    
    Returns:
        True if successfully initialized, False otherwise.
    """
    global _ws_hook, _initialized
    
    if _initialized:
        logger.debug("WS Bridge already initialized")
        return True
    
    try:
        from jupiter.core.bridge import get_event_bus, is_initialized as bridge_initialized
        
        if not bridge_initialized():
            logger.debug("Bridge not initialized, skipping WS bridge setup")
            return False
        
        event_bus = get_event_bus()
        if event_bus is None:
            logger.debug("No event bus available")
            return False
        
        # Create and register the WebSocket hook
        _ws_hook = _create_ws_event_hook()
        event_bus.add_websocket_hook(_ws_hook)
        
        _initialized = True
        logger.info("Bridge-to-WebSocket propagation initialized")
        return True
        
    except ImportError as e:
        logger.debug("Bridge module not available: %s", e)
        return False
    except Exception as e:
        logger.warning("Failed to initialize WS bridge: %s", e)
        return False


async def shutdown_ws_bridge() -> None:
    """Shutdown the Bridge-to-WebSocket connection.
    
    Removes the WebSocket hook from the EventBus.
    """
    global _ws_hook, _initialized
    
    if not _initialized:
        return
    
    try:
        from jupiter.core.bridge import get_event_bus
        
        event_bus = get_event_bus()
        if event_bus is not None and _ws_hook is not None:
            event_bus.remove_websocket_hook(_ws_hook)
            logger.debug("WebSocket hook removed from EventBus")
        
    except Exception as e:
        logger.warning("Error during WS bridge shutdown: %s", e)
    
    _ws_hook = None
    _initialized = False
    logger.info("Bridge-to-WebSocket propagation shutdown")


def is_ws_bridge_active() -> bool:
    """Check if the WS bridge is active.
    
    Returns:
        True if the bridge is initialized and active.
    """
    return _initialized


def get_propagated_event_count() -> int:
    """Get approximate count of events propagated to WebSocket.
    
    Note: This is a placeholder for future metrics integration.
    
    Returns:
        Count of propagated events (currently returns 0).
    """
    # TODO: Add metrics tracking when Phase 4.2.1 is implemented
    return 0
