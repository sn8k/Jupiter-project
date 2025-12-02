# Changelog – jupiter/web/app.py
- Added `JupiterWebUI` static HTTP server backed by `ThreadingTCPServer`.
- Added `WebUISettings` dataclass to configure host, port, and project root.
- Exposed `launch_web_ui` helper to start the GUI with minimal boilerplate.
- Context payload now includes `api_base_url` (configurable via `JUPITER_API_BASE`) so the frontend can target the correct API host.

# Changelog – jupiter/web/app.js

## 2025-12-03 – Plugin Restart Protection

### Changed
- Restart button in Plugins page now checks `plugin.restartable` property
- Plugins with `restartable = false` (like Bridge) don't show restart button
- Preserves backward compatibility: restart button shown by default for existing plugins

## 2024-12-01 – Meeting License Integration
- Added complete Meeting license management section in Settings page.
- New functions: `refreshMeetingStatus()`, `checkMeetingLicense()`, `updateMeetingStatusUI()`.
- Meeting status box with colored indicators (valid=green, invalid=red, network_error=orange, config_error=purple).
- Device Key and Auth Token input fields for Meeting configuration.
- "Check license" and "Refresh" buttons for manual license verification.
- Last Meeting API response display panel with JSON preview.
- Added i18n support for all Meeting-related texts (fr.json, en.json).

# Changelog – jupiter/web/index.html (2024-12-01)
- Split "Interface & Meeting" section into separate "Interface" and "Meeting License" sections.
- New Meeting License panel with status indicator, device key input, auth token input.
- Meeting actions buttons for license verification.
- Last response display area showing raw API response data.

# Changelog – jupiter/web/styles.css (2024-12-01)
- Added `.meeting-section` styles for full-width Meeting panel.
- Added `.meeting-status-box` with colored state variants (status-valid, status-invalid, etc.).
- Added `.meeting-status-indicator` for icon + text status display.
- Added `.meeting-actions` button group styles.
- Added `.meeting-last-response` panel for API response display.
