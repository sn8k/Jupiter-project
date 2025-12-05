# Changelog - jupiter/web/js/jupiter_bridge.js

## v0.1.0
- Initial creation of JupiterBridge module
- Window-global API (`window.jupiterBridge`) for plugin frontend communication
- REST API wrapper with GET/POST/PUT/DELETE methods
- WebSocket connection management with auto-reconnect
- Event subscription system for real-time updates
- Plugin-specific API methods (list, get, enable, disable, configure)
- Notification system with toast display
- Project management API integration
- Scan and analysis API wrappers
- Connection state tracking and retry logic
- Error handling and notification

## v0.1.1
- Default API base now maps GUI/diag ports (8050/8081) to API port 8000 when no base is injected.
- Plugin metrics calls now target `/plugins/v2/{id}/metrics` (legacy autodiag kept) to eliminate 404s.

## v0.1.2
- Expose `api.baseUrl` so plugin UIs (e.g., Metrics Manager logs SSE) use the API port instead of the GUI port, preventing 404 on `/metrics_manager/logs/stream`.
