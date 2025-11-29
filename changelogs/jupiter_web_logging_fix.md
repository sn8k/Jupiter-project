# Changelog - Web Interface Logging & Cache Fixes

## Fixed
- **Cache Issues**: Disabled server-side caching in `jupiter/web/app.py` and added version query parameter to `app.js` in `index.html` to prevent stale code execution.
- **WebUI Frozen**: Confirmed fix for ES Module scope isolation (from previous iteration) will now be correctly loaded.

## Added
- **Log Filtering**: Added a dropdown in the WebUI to filter logs by level (ALL, INFO, WARN, ERROR).
- **Rich Logging**: Updated `addLog` to support log levels and styled log entries accordingly (colors, borders).
- **Error Visibility**: Critical errors (Scan, Language load, WebSocket) are now logged as `ERROR` level for better visibility.
