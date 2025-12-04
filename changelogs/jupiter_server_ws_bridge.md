# Changelog - jupiter/server/ws_bridge.py

## Version 0.1.0
- Initial implementation of Bridge-to-WebSocket event propagation
- Created `init_ws_bridge()` to connect EventBus to WebSocket manager
- Created `shutdown_ws_bridge()` to disconnect on server shutdown
- Created `is_ws_bridge_active()` status check
- Created `get_propagated_event_count()` placeholder for metrics
- Automatic event forwarding using EventBus `add_websocket_hook()`
- Events forwarded with type "bridge_event" for WebUI consumption
- Integrated into api.py lifespan for automatic startup/shutdown
