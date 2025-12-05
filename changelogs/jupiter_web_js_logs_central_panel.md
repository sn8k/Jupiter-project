# Changelog - jupiter/web/js/logs_central_panel.js

## v0.1.0
- Initial creation of CentralLogsPanel module
- Multi-plugin log filtering with dropdown selector
- Level filter dropdown (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Time range picker with presets (last 5min, 15min, 1h, 24h, all)
- Search functionality with debounce
- WebSocket streaming for real-time logs
- Log entry rendering with timestamp, level badge, plugin tag
- Export filtered logs to JSON or TXT
- Clear all logs functionality
- Auto-scroll to latest logs (configurable)
- Connection status indicator
- Responsive layout with CSS grid
- i18n support via jupiterBridge.i18n.t()
- Singleton pattern with window.jupiterCentralLogsPanel
