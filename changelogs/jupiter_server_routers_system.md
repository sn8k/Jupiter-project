# Changelog – jupiter/server/routers/system.py

## Version 1.6.2 (2025-12-03) – Plugin Restart Protection

### Added
- Restart protection check in `POST /plugins/{name}/restart` endpoint
- Returns HTTP 403 Forbidden for plugins with `restartable = False`
- Bridge plugin cannot be restarted by users, only by Watchdog/system

### Fixed
- Watchdog config POST endpoint now properly uses `Body(...)` for JSON parsing
- Bridge config POST endpoint added for potential future config changes

## Version 1.5.0 (2025-12-02) – Plugin Bridge API
- Added `GET /plugins/bridge/status` endpoint to get Bridge status
  - Returns API version, plugin version, services count, loaded count
  - Lists all available services with descriptors
  - Lists all capabilities across services
  - Initializes Bridge if needed
- Added `GET /plugins/bridge/services` endpoint to list available services
  - Returns service list with full descriptors
  - Includes API version
- Added `GET /plugins/bridge/capabilities` endpoint to list all capabilities
  - Returns flattened capability list from all services
- Added `GET /plugins/bridge/service/{name}` endpoint for service details
  - Returns full service descriptor including capabilities
  - Returns 404 if service not found

## Version 1.4.0 (2025-12-02) – Plugin Watchdog API
- Added `GET /plugins/watchdog/config` endpoint to retrieve watchdog configuration
- Added `POST /plugins/watchdog/config` endpoint to save watchdog settings
  - Injects plugin_manager reference for reload functionality
  - Handles enabled/disabled state
- Added `GET /plugins/watchdog/status` endpoint to get watchdog status
  - Returns monitoring state, watched files count, reload count, last reload
- Added `POST /plugins/watchdog/check` endpoint to force immediate file check
  - Ensures plugin_manager is set before checking
  - Returns check results (files checked, reloads triggered)

## Version 1.3.0 (2025-12-02) – Live Map Settings API
- Updated `GET /plugins/livemap/config` to use `plugin_obj.get_config()` if available
  - Now returns all config fields: `enabled`, `simplify`, `max_nodes`, `show_functions`, `link_distance`, `charge_strength`
- Added `POST /plugins/livemap/config` endpoint to save Live Map plugin settings
  - Accepts configuration payload and calls `plugin_obj.configure()`
  - Handles enabled/disabled state via plugin manager
  - Logs configuration updates

## Version 1.2.0 (2025-12-02) – Live Map Plugin Support
- Added `GET /plugins/livemap/graph` endpoint for dependency graph visualization
  - Supports `simplify` and `max_nodes` query parameters
  - Uses cached scan data or triggers fresh scan via connector
- Added `GET /plugins/livemap/config` endpoint to retrieve plugin settings

## Version 1.1.0 (2025-12-02) – Phase 2: Diagnostic Endpoints
- Added `GET /diag/handlers` endpoint to list all registered handlers:
  - `api_handlers`: FastAPI route handlers
  - `cli_handlers`: CLI command handlers
  - `plugin_handlers`: Plugin hook handlers
- Added `GET /diag/functions` endpoint for function usage details with confidence scores
- Added helper functions:
  - `_collect_api_handlers(app)`: Extract FastAPI handlers
  - `_collect_cli_handlers()`: Extract CLI handlers via `get_cli_handlers()`
  - `_collect_plugin_handlers(app)`: Extract plugin hook handlers
- Added version docstring header

## Previous Changes
- Replaced ad-hoc root/config wiring with the shared `SystemState` helper for metrics, config reads, and runtime rebuilds.
- Root updates now preserve Meeting keys, refresh Meeting adapter/project manager/plugin manager in one place, and reset the history manager only when needed.
- Config updates call the same helper, ensuring WebSocket clients receive consistent `CONFIG_UPDATED` payloads.
- API `/config` now reads/writes `log_level`, normalizes user-provided aliases, and forwards the value to the runtime rebuild.
- Raw config endpoints and project initialization now resolve the project config path via the new `<project>.jupiter.yaml` naming (with legacy support), so the UI edits the correct file even after the rename.
- Settings API now exposes `log_path` to allow configuring the destination log file path from the UI.
- Added `/projects/{id}/ignore` to persist per-project ignore globs in the global registry and serve them to the UI/projects list.
- Added `/projects/{id}/api_config` (GET/POST) to read/update API inspection settings per project without touching unrelated config fields.
- Added `/project/root-entries` endpoint to list all files/folders at the project root for the interactive exclusion panel, returning entries with `is_dir`, `is_hidden` flags and current ignore patterns.
