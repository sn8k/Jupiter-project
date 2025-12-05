# Changelog – jupiter/web/app.py
- Added `JupiterWebUI` static HTTP server backed by `ThreadingTCPServer`.
- Added `WebUISettings` dataclass to configure host, port, and project root.
- Exposed `launch_web_ui` helper to start the GUI with minimal boilerplate.
- Context payload now includes `api_base_url` (configurable via `JUPITER_API_BASE`) so the frontend can target the correct API host.

## Version 1.1.2 - Version placeholder injection
- `index.html` is now rendered with the current Jupiter version injected into placeholders so the footer badge and `app.js?v=` cache-busting reflect the running build.

## 2025-12-03 - Cache hardening
- Enforced HTTP/1.1 responses with `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` plus `Pragma`/`Expires`/`Surrogate-Control` on every asset.
- Stripped `If-Modified-Since` and `If-None-Match` headers from incoming requests to avoid 304 responses and force fresh payloads.
- Added a version note (1.1.1) in the module docstring for traceability.

# Changelog – jupiter/web/app.js

## v1.6.2 - Plugin Menu Fixes

### Fixed
- Fixed double icon issue on plugin menu items during cold start
  - Plugin buttons now use separate `<span>` elements for icon and label
  - `translateUI()` now preserves icons when translating plugin button labels
- Improved startup performance for plugin menu display
  - `loadPluginMenus()` now starts early in init and runs in parallel with other fetches
  - Reduced time to display plugin menu items by ~50%

## v1.6.1 - Fixed v2 plugin settings display

### Fixed
- `loadPluginSettings()` now reloads `settingsPlugins` list if empty (fixes settings not showing when auth was delayed)
- Added debug logging for plugin settings loading

# Changelog – jupiter/web/styles.css

## v2 Plugin Settings Styling
- Added `.plugin-v2-settings` styles for auto-generated settings forms
- Form groups with proper labels, inputs, selects, checkboxes
- Save button styling with accent color
- Responsive form layout

## v1.6.0 - V2 Plugin UI Integration

### Added
- `createPluginBridge(pluginName)` - Creates the bridge object for v2 plugin mount()
  - Provides i18n.t(), api.fetch/get/post, state access, events on/emit
  - Config get/save to /plugins/v2/{name}/config
  - Plugin-prefixed logging (debug, info, warn, error)

- V2 plugin detection in `injectPluginMenuItems()`
  - Stores `data-v2="true"` and `data-route` on plugin nav buttons
  - Passed to `loadPluginViewContent()`

- ES module loading in `loadPluginViewContent(pluginName, viewId, isV2)`
  - For v2 plugins: creates Blob URL, dynamic imports, calls mount(container, bridge)
  - Fallback to legacy script injection on module load failure
  - Uses `loadKey = "${pluginName}:${viewId}"` to allow multiple panels per plugin

- Auto-generated settings forms for v2 plugins
  - `initializeV2SettingsForm()` parses JSON schema from data-schema
  - `generateFormFromSchema()` creates inputs for boolean, number, enum, array, text
  - `saveV2PluginSettings()` collects form data and PUTs to /plugins/v2/{name}/config

### Fixed
- Multiple panels per plugin now tracked correctly (ai_helper main + suggestions)

## 2025-12-03 - No-store browser requests
- Wrapped `window.fetch` to inject `cache: "no-store"` and cache-busting headers on every request while preserving auth headers.
- `apiFetch` now normalizes headers via `Headers` and forces `cache: "no-store"` for all API calls.

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