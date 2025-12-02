# Changelog

## 1.8.2 – Plugin Bridge System & Log Path Setting

### Added
- **Plugin Bridge** (`jupiter/plugins/bridge_plugin.py`):
  - Core services gateway providing stable API access for plugins
  - Decouples plugins from Jupiter internals for future-proof architecture
  - **Service Registry**: Central registry with lazy-loaded service instantiation
  - **Built-in Services**:
    - `events`: Event emission and creation (JupiterEvent)
    - `config`: Configuration access (project root, plugin config)
    - `scanner`: Filesystem scanning operations
    - `cache`: Report caching (get, save, clear)
    - `history`: Snapshot management and diff
    - `logging`: Structured logging for plugins
  - **Capability System**:
    - Services declare their capabilities declaratively
    - Plugins can search services by capability
    - Generic invocation via `bridge.invoke(capability, *args)`
    - Versioned API (`BRIDGE_API_VERSION = 1.0`)
  - Settings-only UI showing:
    - API version and plugin version
    - Number of available/loaded services
    - Service list with categories and capabilities
    - All capabilities across services
  - **Global Access Functions**:
    - `get_bridge()`: Get BridgeContext from any plugin
    - `has_bridge()`: Check if Bridge is available

- **Bridge API Endpoints**:
  - `GET /plugins/bridge/status`: Full Bridge status
  - `GET /plugins/bridge/services`: List available services
  - `GET /plugins/bridge/capabilities`: List all capabilities
  - `GET /plugins/bridge/service/{name}`: Service details

- **Plugin System Enhancements**:
  - Added `get_bridge()` and `has_bridge()` exports to `jupiter.plugins`
  - Bridge context accessible from any plugin

- **Log File Path Setting**:
  - Added log file path input in Settings > Security section
  - Default value: `logs/jupiter.log` (file logging enabled by default)
  - Leave empty to disable file output
  - Persisted in configuration

### Changed
- Updated `jupiter/server/routers/system.py` to v1.5.0 with Bridge endpoints
- Changed `LoggingConfig.path` default from `None` to `"logs/jupiter.log"`

### Documentation
- Added `changelogs/jupiter_plugins_bridge.md`
- Updated `changelogs/jupiter_config_config.md` to v1.2.0
- Updated `README.md` with Bridge feature
- Updated `Manual.md` with Bridge plugin documentation

---

## 1.8.1 – Plugin Watchdog & Logging Improvements

### Added
- **Plugin Watchdog** (`jupiter/plugins/watchdog_plugin.py`):
  - System plugin for automatic plugin hot-reload during development
  - Monitors all plugin files for modifications (mtime-based)
  - Auto-reloads modified plugins without Jupiter restart
  - Settings-only UI (no sidebar view) accessible in Settings > Plugins
  - Configurable options:
    - Enable/disable monitoring
    - Check interval (0.5-10 seconds)
    - Auto-reload toggle
  - Status panel showing:
    - Monitoring state (active/stopped)
    - Watched files count
    - Total reload count
    - Last reload timestamp
  - Force check and refresh status buttons
  - List of all watched files

- **Watchdog API Endpoints**:
  - `GET /plugins/watchdog/config`: Get configuration
  - `POST /plugins/watchdog/config`: Save configuration
  - `GET /plugins/watchdog/status`: Get current status
  - `POST /plugins/watchdog/check`: Force immediate check

- **Live Map Logging** (v0.2.2):
  - Comprehensive logging throughout the plugin
  - GraphBuilder logs: file count, index sizes, build mode
  - Import resolution logs: each attempt and result
  - Per-file processing: imports found/resolved, functions
  - Resolution rate statistics (% resolved)
  - Node/link type breakdown in debug mode

- **i18n**: Added watchdog translation keys (en, fr)

### Changed
- Live Map plugin version bumped to 0.2.2
- Improved Live Map import resolution for JS/TS imports

---

## 1.8.0 – Live Map Plugin Migration

### Added
- **Live Map Plugin** (`jupiter/plugins/livemap.py`):
  - New `LiveMapPlugin` class implementing UIPlugin protocol
  - Interactive D3.js dependency graph visualization
  - Support for simplified mode (group by directory)
  - Auto-simplification for large projects (> max_nodes)
  - Two-column layout: graph + contextual help panel
  - Settings section with dedicated Save button:
    - Enable/disable toggle
    - Simplify by default option
    - Max nodes slider
    - Show functions toggle
    - Link distance slider
    - Charge strength slider
  - Reset Zoom button for easier navigation

- **New API Endpoints**:
  - `GET /plugins/livemap/graph`: Generate dependency graph
  - `GET /plugins/livemap/config`: Get plugin configuration
  - `POST /plugins/livemap/config`: Save plugin configuration

- **i18n**: Added livemap translation keys (en, fr)
  - Help panel translations
  - Settings section translations

### Changed
- Removed hardcoded "Live Map" button from sidebar (now auto-injected by plugin)
- Removed old graph view section from index.html

### Deprecated
- `jupiter/core/graph.py`: Use `jupiter.plugins.livemap` instead
- `GET /graph` endpoint: Use `/plugins/livemap/graph` instead
- `renderGraph()` in app.js: Use plugin's D3 visualization instead

### Migration Notes
- The Live Map functionality now uses the plugin system
- The old endpoint `/graph` will log a deprecation warning
- Update API calls from `/graph` to `/plugins/livemap/graph`

---

## 1.7.0 – Autodiag Runner (Autodiag Phase 4)

### Added
- **AutoDiagRunner**: Automated self-analysis class (`jupiter/core/autodiag.py`)
  - Compares static analysis with dynamic runtime observations
  - Identifies false positives in unused function detection
  - Generates actionable recommendations

- **Test Scenarios**: Automatic execution of:
  - CLI commands (scan, analyze, ci, snapshots, server)
  - API endpoints (when server is running)
  - Plugin hooks (on_scan, on_analyze, on_ci)

- **AutoDiagReport**: Comprehensive result model with:
  - Static analysis summary (total, unused, possibly_unused, likely_used)
  - Dynamic validation results (scenarios run/passed/failed)
  - False positive detection (count, rate, details)
  - Recommendations for improvement

- **CLI Command**: `jupiter autodiag`
  - `--json`: Output as JSON
  - `--api-url`: Override main API URL
  - `--diag-url`: Override diag API URL
  - `--skip-cli`: Skip CLI scenario tests
  - `--skip-api`: Skip API scenario tests
  - `--skip-plugins`: Skip plugin hook tests
  - `--timeout`: Timeout per scenario (default: 30s)

- **API Endpoint**: `POST /diag/run`
  - Trigger autodiag from the diag server
  - Query params: skip_cli, skip_api, skip_plugins, timeout
  - Returns AutoDiagReport as JSON

- **Tests**: New `tests/test_autodiag_runner.py` with 15 tests
  - Model serialization tests
  - Runner initialization tests
  - Scenario execution tests (mocked)
  - Comparison logic tests
  - Recommendation generation tests

### Usage
```bash
# Run autodiag on current project
jupiter autodiag

# Run with JSON output
jupiter autodiag --json

# Skip specific scenarios for faster testing
jupiter autodiag --skip-api --skip-plugins

# Via API (when autodiag server is running on port 8081)
curl -X POST http://127.0.0.1:8081/diag/run?skip_cli=true
```

### Technical
- `jupiter/core/autodiag.py` version 1.0.0
- `jupiter/cli/main.py` version bumped to 1.2.0
- `jupiter/cli/command_handlers.py` updated with `handle_autodiag`
- `jupiter/server/routers/autodiag.py` version bumped to 1.1.0

### Documentation
- Updated `docs/autodiag.md`: Phase 4 marked as complete
- Updated `Manual.md` with autodiag command documentation

## 1.6.0 – Dual-Port Architecture (Autodiag Phase 3)

### Added
- **AutodiagConfig**: New configuration section for autodiag dual-port architecture
  - `enabled`: Enable/disable autodiag server (default: false)
  - `port`: Port for autodiag API (default: 8081, localhost only)
  - `introspect_api`: Enable API introspection endpoint
  - `validate_handlers`: Enable handler validation endpoint
  - `collect_runtime_stats`: Enable runtime statistics collection

- **Dedicated Autodiag Server**: Separate FastAPI app running on localhost only
  - Security: No authentication required (localhost access only)
  - Isolation: Does not affect main API performance
  - When enabled, Jupiter runs two servers concurrently

- **New Autodiag Router** (`jupiter/server/routers/autodiag.py`):
  - `GET /diag/introspect`: Return all registered endpoints from main API
  - `GET /diag/handlers`: Aggregate handlers (API, CLI, plugins)
  - `GET /diag/functions`: Function usage with confidence scores
  - `POST /diag/validate-unused`: Validate if functions are truly unused
  - `GET /diag/stats`: Runtime statistics (uptime, memory, route count)
  - `GET /diag/health`: Simple health check

- **Tests**: New `tests/test_autodiag.py` with comprehensive test coverage
  - AutodiagConfig tests
  - Router endpoint tests
  - CLI handlers integration tests

### Configuration
```yaml
# <project>.jupiter.yaml
autodiag:
  enabled: true
  port: 8081
  introspect_api: true
  validate_handlers: true
  collect_runtime_stats: false
```

### Technical
- `jupiter/config/config.py` version bumped to 1.1.0
- `jupiter/server/api.py` version bumped to 1.1.0
- New `_create_diag_app()` method in `JupiterAPIServer`
- New `_run_dual_servers()` async method for concurrent server startup

### Documentation
- Updated `docs/autodiag.md`: Phase 3 marked as complete

## 1.5.0 – Confidence Scoring & Handler Introspection (Autodiag Phase 2)

### Added
- **Function Usage Confidence Scoring**: Functions now have a confidence score (0.0-1.0)
  - `FunctionUsageStatus` enum: `USED`, `LIKELY_USED`, `POSSIBLY_UNUSED`, `UNUSED`
  - `FunctionUsageInfo` dataclass with status, confidence, and reasons
  - `compute_function_confidence()` helper function with detailed scoring logic

- **Enhanced Python Summary**: `PythonProjectSummary` now includes:
  - `function_usage_details`: List of non-USED functions with confidence scores
  - `usage_summary`: Count per usage status

- **API Handler Introspection**: `/api/endpoints` now includes:
  - `handlers`: List of FastAPI route handlers with function names and modules
  - `get_registered_handlers()` helper function

- **New Diagnostic Endpoints**:
  - `GET /diag/handlers`: Lists all handlers (API, CLI, plugins)
  - `GET /diag/functions`: Returns function usage details with confidence scores

- **CLI Handler Registry**: `jupiter/cli/main.py` now exposes:
  - `CLI_HANDLERS`: Dict mapping command names to handler functions
  - `get_cli_handlers()`: Function returning handler info for introspection

### Technical
- `jupiter/core/analyzer.py` version bumped to 1.1.0
- `jupiter/server/routers/scan.py` version bumped to 1.1.0
- `jupiter/server/routers/system.py` version bumped to 1.1.0
- `jupiter/cli/main.py` version bumped to 1.1.0
- New helper functions: `_collect_api_handlers()`, `_collect_cli_handlers()`, `_collect_plugin_handlers()`

### Documentation
- Updated `docs/autodiag.md`: Phase 2 marked as complete

## 1.4.1 – Type Fix

### Fixed
- **Pyright Type Error**: Fixed `run_ci_check` parameter type in `server/routers/analyze.py`
  - Changed `ci_req: CIRequest = None` to `ci_req: Optional[CIRequest] = None`
  - Resolves reportArgumentType error for nullable parameter with non-optional type hint

## 1.4.0 – Improved Unused Function Detection (Autodiag Phase 1)

### Added
- **Framework Decorator Detection**: The Python analyzer now recognizes ~50 framework decorators
  - FastAPI/Starlette: `@router.get/post/put/delete/patch`, `@app.on_event`, etc.
  - Flask: `@route`, `@before_request`, `@errorhandler`, etc.
  - Click/Typer: `@click.command`, `@click.group`, etc.
  - pytest: `@pytest.fixture`, `@pytest.mark.*`
  - Django, Celery, Pydantic decorators

- **Known Patterns Whitelist**: ~80 method patterns automatically excluded from "unused"
  - Dunder methods: `__init__`, `__str__`, `__enter__`, `__exit__`, etc.
  - Serialization: `to_dict`, `from_json`, `serialize`, etc.
  - Plugin hooks: `on_scan`, `on_analyze`, `setup`, `teardown`, etc.
  - Test patterns: `setUp`, `tearDown`, etc.

- **Dynamic Registration Tracking**: Detects functions passed to registration methods
  - `parser.set_defaults(func=handler)` (argparse CLI)
  - `app.add_command(cmd)` (CLI frameworks)
  - `emitter.on("event", callback)` (event systems)
  - `signal.connect(handler)` (Django signals)

- **New Analysis Fields**: `analyze_python_source()` returns additional data
  - `decorated_functions`: Functions with framework decorators
  - `dynamically_registered`: Functions registered dynamically

### Changed
- **Reduced False Positives**: Estimated 60-80% reduction in false positive "unused" functions
  - FastAPI route handlers: No longer flagged as unused
  - CLI command handlers: No longer flagged as unused
  - Plugin methods: No longer flagged as unused
  - Magic methods: No longer flagged as unused

### Technical
- `jupiter/core/language/python.py` version bumped to 1.1.0
- New constants: `FRAMEWORK_DECORATORS`, `KNOWN_USED_PATTERNS`, `DYNAMIC_REGISTRATION_METHODS`
- New `PythonCodeAnalyzer` methods: `_analyze_decorators()`, `_get_decorator_name()`, `_is_framework_decorator()`, `_check_dynamic_registration()`, `_track_function_arguments()`
- New helper function: `is_likely_used(func_name: str) -> bool`

### Documentation
- Added `docs/autodiag.md`: Comprehensive autodiagnostic analysis and proposals
- Updated `docs/dev_guide.md`: Python analyzer features section
- New changelog: `changelogs/jupiter_core_language_python.md`

## 1.3.3 – Settings Save Fix & PATCH Endpoint
### Fixed
- **Settings Save Buttons**: All Settings page Save buttons now work correctly
  - Added `PATCH /config` endpoint for partial configuration updates
  - Changed JS save functions from POST to PATCH method
  - Network, Interface, Security, and Performance settings save independently

- **Code Quality Plugin Save**: The Save button in the Code Quality plugin settings now works
  - Fixed JavaScript injection: separated `get_settings_js()` from `get_settings_html()`
  - Scripts inserted via `innerHTML` don't execute; now properly injected via script element

### Technical
- New `PartialConfigModel` in `models.py` with all fields optional
- New `PATCH /config` endpoint applies only provided fields to existing config
- Code Quality plugin now has separate `get_settings_html()` and `get_settings_js()` methods

## 1.3.2 – Log Level Setting Restoration
### Fixed
- **Log Level Setting Restored**: The global log level setting was accidentally removed during the Settings UX refactor. It has been restored in the Security section of the Settings page.
  - Log level dropdown with DEBUG, INFO, WARNING, ERROR, CRITICAL options
  - Settings are saved with the Security section save button
  - Log level is applied immediately upon save

### Technical
- Updated `saveSecuritySettings()` to include `log_level` in the config payload
- Uses existing i18n keys `settings_log_level_label` and `settings_log_level_hint`

## 1.3.1 – Settings UX Refactor & Project Performance
### Changed
- **Settings Page Refactor**: Each settings section now has its own Save button
  - Network, Interface, and Security sections save independently
  - Removed global "Save Settings" button for better UX
  - Immediate feedback with status indicators (✓ / ✗)

- **Performance Settings Moved to Projects**: Performance configuration (parallel scan, workers, timeout, graph settings) is now in the active project section of the Projects view, as these are project-specific settings

### Fixed
- **Project API Config Restoration**: Project API connector settings (connector type, app variable, path) are now properly restored on startup
- **Code Quality Plugin Save**: Fixed the plugin config API endpoint to properly accept JSON body (`Body(...)` annotation)
- **Performance Settings Loading**: Performance settings are now loaded when switching to the Projects view

### Technical
- New individual save functions: `saveNetworkSettings()`, `saveUISettings()`, `saveSecuritySettings()`, `saveProjectPerformanceSettings()`
- New `loadProjectPerformanceConfig()` function to restore performance settings
- Added new i18n keys for performance labels in both French and English

## 1.3.0 – Dynamic i18n & Fun Language Packs
### Added
- **Dynamic Language Discovery**: The language selector now auto-detects available translations from `lang/*.json` files
  - Each language file contains a `_meta` block with `lang_code`, `lang_name`, and `version`
  - Version info displayed in the selector: `Français (v1.0.0)`
  - Current language version shown below the selector

- **Fun Language Packs** (for entertainment):
  - 🖖 **Klingon** (`klingon.json`): Full tlhIngan Hol translation for Star Trek fans
  - 🧝 **Sindarin** (`elvish.json`): Elvish translation inspired by Tolkien's Lord of the Rings
  - 🏴‍☠️ **Pirate French** (`pirate.json`): French pirate speak with "arrr", "moussaillon", "mille sabords!"

- **Translation Audit**: Comprehensive review and completion of all i18n keys
  - Both `en.json` and `fr.json` now have 729 keys with perfect parity
  - Added missing keys for CI, snapshots, scan options, license details, and more

### Technical
- New `discoverLanguages()` function scans and caches language metadata at startup
- New `populateLanguageSelector()` dynamically fills the language dropdown
- Language files now have versioned `_meta` structure for future compatibility tracking
- Selector prioritizes `fr` and `en`, then sorts others alphabetically

## 1.2.1 – Settings UX Improvements & User Management
### Added
- **User Management CRUD**: Complete user editing workflow with inline edit, save, cancel buttons
  - Edit mode shows input fields for username, token (masked), and role dropdown
  - Token visibility toggle with show/hide functionality
  - API endpoint `PUT /users/{name}` for user updates
  - Visual action buttons grouped with proper styling

- **Meeting License Panel**:
  - Added Save button to persist Meeting configuration changes
  - License details grid populated from Meeting service response
  - Removed popup alerts for license check operations

### Changed
- **Settings Page Layout**: Reorganized into two-column layout
  - Left column: Interface, Users sections
  - Right column: Meeting License (reduced width for better proportions)
- **Interface Section**: Moved "Allow Run Command" toggle from Security to Interface section
- **Security Section**: Removed standalone section (toggle moved to Interface)

### Fixed
- Fixed duplicate translation key in en.json
- Fixed user table layout and action button styling

### Technical
- Added 20+ new i18n keys for user management and meeting operations
- Added `.users-table`, `.user-edit-row`, `.btn-action-group` CSS classes

## 1.2.0 – WebUI Feature Parity (CI, Snapshots, License Details)
### Added
- **CI / Quality Gates View**: New navigation tab with complete quality gates workflow
  - CI metrics dashboard: avg complexity, max lines/function, doc coverage, duplications
  - Configurable thresholds with localStorage persistence
  - Violations list with file and message details
  - CI history table tracking pass/fail status over time
  - Export CI report functionality
  - New `POST /ci` API endpoint for programmatic CI checks

- **Enhanced Scan Modal**:
  - "No cache" option to force full scan (skip incremental cache)
  - "Don't save snapshot" option to disable snapshot persistence
  - "Snapshot label" text input for custom snapshot naming

- **Snapshot Detail Panel** (History View):
  - View button to open detailed snapshot info
  - Export button to download individual snapshots as JSON
  - Summary display: files, functions, lines, timestamp, label

- **License Details** (Settings View):
  - License details grid showing type, status, device key, session ID, expiry, features
  - Refresh button to update license information from Meeting service

### Technical
- Added 60+ new i18n keys (en.json, fr.json)
- Added CI models: `CIRequest`, `CIResponse`, `CIMetrics`, `CIThresholds`, `CIViolation`
- Updated `startScanWithOptions()` to handle new scan parameters

## 1.1.13 – Manual Duplication Linking
- Code Quality plugin duplication tab now lets you select overlapping detector clusters and merge them into a single linked block with a custom label. Linked blocks display verification badges (verified / missing / diverged) and can be rechecked without rerunning a scan.
- Linked definitions are persisted to `.jupiter/manual_duplication_links.json` (and optionally via config) so they survive restarts and are injected into `/analyze` responses without inflating duplication percentages.
- Added admin-only endpoints to automate this workflow: `POST /plugins/code_quality/manual-links`, `DELETE /plugins/code_quality/manual-links/{link_id}`, and `POST /plugins/code_quality/manual-links/recheck`.
- Duplication detector now records `end_line` for every occurrence, enabling accurate block spans when manual links are recomputed and tightening UI previews.
- Updated README, Manual, and API docs to describe the new workflow and storage format.

## 1.1.12 – Meeting License WebUI & Heartbeat
- Added complete Meeting license management section in Settings page.
- Meeting status box with colored indicators based on license status (valid=green, invalid=red, network_error=orange, config_error=purple).
- Device Key and Auth Token input fields for Meeting configuration.
- "Check license" and "Refresh" buttons for manual license verification against Meeting API.
- Last Meeting API response display panel with JSON preview and timestamp.
- Added i18n support for all Meeting-related UI texts (fr.json, en.json).
- Split Settings "Interface & Meeting" section into separate panels for better organization.
- **Heartbeat implementation**: Jupiter now sends a POST to `/api/devices/{device_key}/online` on every license check to signal presence to Meeting.

## 1.1.11 – Meeting License Verification
- Implemented full Meeting license verification via the Meeting backend API.
- Added `MeetingLicenseStatus` enum and `MeetingLicenseCheckResult` dataclass for detailed license status.
- License validation checks: `authorized == true`, `device_type == "Jupiter"`, `token_count > 0`.
- Added new API endpoints:
  - `GET /license/status` – Returns detailed license verification status
  - `POST /license/refresh` – Forces a license re-check (admin only)
- Added CLI command: `jupiter meeting check-license [--json]` with appropriate exit codes.
- Extended `MeetingConfig` with new parameters: `base_url`, `device_type`, `timeout_seconds`, `auth_token`.
- Server startup now verifies license automatically with graceful degradation to restricted mode.
- Updated global_config.yaml with full Meeting configuration section.
- Added comprehensive unit tests in `tests/test_meeting_adapter.py`.

## 1.1.10 – Internal Deduplication
- CLI scan/analyze commands now reuse a shared service builder to remove repeated argument blocks.
- API routers reuse a common history manager helper (SystemState) instead of duplicated local implementations.
- Remote connector HTTP calls are centralized to avoid repeated request/raise patterns.
- Web UI project actions share a single mutation helper to reduce copy/paste error handling.
- Projects page now lets you edit per-project ignore globs, stored in the global registry and applied by default to scans/analyses.
- Project API connector settings moved to the Projects page with dedicated save endpoints (`/projects/{id}/api_config`).

## 1.1.9 – Detailed Duplication Evidence
- Duplication refactoring hints now embed file:line occurrences so AI suggestions explicitly list where duplicated blocks live.
- `/analyze` responses and the Suggestions tab surface these locations (with line numbers), the nearest function name, and a code excerpt to make the report actionable without hunting through duplication clusters.

# Changelog

## 1.1.8 – Active Project Persistence
- CLI root resolution now uses the active project stored in the global registry (`~/.jupiter/global_config.yaml` or legacy `global.yaml`) and syncs the local state file so restarting the GUI/CLI reopens the last project activated from the Web UI.
- Project activation in the backend now persists the selected root to the shared state file, keeping the registry and CLI defaults aligned.
- Global project registry entries are normalized on load (legacy `jupiter.yaml` -> `<project>.jupiter.yaml`, absolute paths), and Windows event-loop policy is enforced to suppress noisy connection-reset traces on client disconnects.

## 1.1.6 – Config Naming Update
- Global install configuration now targets `global_config.yaml` (with backward-compatible loading of legacy install overrides).
- Project configurations follow the `<project>.jupiter.yaml` naming scheme; legacy `jupiter.yaml` files are still loaded for existing setups.
- Documentation and UI copy have been refreshed to highlight the new naming and the registry path `~/.jupiter/global_config.yaml`.

## 1.1.7 – Log Destination in Settings
- Settings page now exposes a log file path field; the API, CLI, and debug server pass this value to logging setup to attach a file handler.
- Config schema (`logging.path`) persists this path across global/project saves and is exposed via `/config`.

## 1.1.5 – Configurable Logging
- Added centralized logging configuration with a project-level `logging.level` setting applied to CLI, FastAPI, and Uvicorn.
- Settings page now exposes the log level selector (Debug/Info/Warning/Error/Critic) and reuses it to filter dashboard logs.
- API config endpoints normalize and persist the log level while rebuilding runtime services with the updated verbosity.

## 1.1.4 – Projects Control Center
- Projects page is now fully wired to `/projects` (list, activate, delete) with refresh controls and in-place overview updates.
- Documented the Projects API endpoints and the new Web UI dashboard for multi-project management.
- Added a regression test (FastAPI TestClient) covering project create/activate/delete using the provided secondary project path.
- History view now scopes snapshots/diffs to the active project, clearing stale selections when switching.
- Forced context reload on project switch (no-cache) so the top bar and History view update to the newly active project immediately.

## 1.0.4 – Cache Schema & Notification Fallbacks
- Normalized cached scan payloads (plugins serialized as lists) and forced the API to resave the enriched report so `/reports/last` never fails Pydantic validation after upgrading plugins.
- Added a `PLUGIN_NOTIFICATION` event and taught the webhook plugin to emit local Live Events (via WebSocket) whenever no webhook URL is configured instead of logging errors.

## 1.0.3 – CLI Workflow & System Router Service
- Unified `scan`, `analyze`, and `ci` behind a shared CLI workflow (plugins, caching, snapshots) and exposed new helpers for CI gate evaluation.
- Introduced `SystemState` helper to rebuild plugin/project managers, Meeting adapter, and history whenever the API root or config changes.
- Root changes now preserve the last Meeting `deviceKey`, refresh plugin discovery once, and broadcast consistent state updates across WebSocket clients.
- Documentation refreshed (README, Manual) to describe the CI command and the automatic root refresh behavior.
- Fixed the Suggestions IA "Actualiser" button so it now calls the `/analyze` API and refreshes refactoring hints in-place with proper status feedback.

## 1.0.2 – CLI & Config Deduplication
- Refactored CLI scan/analyze setup to share a single options builder and scanner bootstrap, reducing duplicated logic.
- Centralized dynamic analysis cache merging in `CacheManager` and reused it across CLI and local connector flows.
- Consolidated configuration serialization helpers for performance/backends/API sections to avoid drift between project/global saves.

## 1.0.1 – UI Polish & Quality Data
- **Scan Modal**: Rebuilt layout/padding and persisted the previous options automatically.
- **Quality View**: Scan responses now embed complexity/duplication metrics so the Qualité page shows data immediately (even while watching a local backend).

## 0.1.13 – Login UI & Config Fixes
- **Fix**: Resolved "Invalid credentials" error by ensuring the API server receives the correctly loaded configuration.
- **UI**: Improved styling of the Login Modal (backdrop, spacing, inputs).

## 0.1.12 – Real Login System
- **Auth**: Implemented Username/Password login with "Remember Me".
- **UI**: Login modal now blocks access until authenticated.
- **Backend**: Added `/login` endpoint and updated token verification.

## 0.1.11 – User Management & Update Upload
- **Settings**: Added User Management section (Global config).
- **Update**: Added "Browse" button for uploading update ZIPs.
- **Backend**: Added endpoints for users and file upload.

## 0.1.10 – Split Configuration Architecture
- **Architecture**: Implemented a split configuration system. Global settings (Meeting, UI, Server) are now stored in the installation directory, while Project settings (Performance, CI) are stored in the project directory.
- **Fix**: Resolved issue where Meeting Key was lost when scanning a new project.
- **API**: Updated `JupiterAPIServer` to handle merged configurations.

## 0.1.9 – Launch & Config Persistence Fixes
- **Launch**: `Jupiter UI.cmd` now forces the application to start with the configuration from the installation directory, fixing issues where settings were ignored.
- **Persistence**: Switching projects in the UI now preserves the Meeting license/configuration if the target project doesn't have one.
- **CLI**: Added global `--root` argument.

## 0.1.8 – Configuration Robustness
- **Config**: Added support for `device_key` alias in `jupiter.yaml` to prevent loading issues.
- **UI**: Improved settings loading logic for Meeting configuration.
- **Debug**: Added logging for configuration state.

## 0.1.7 – Settings Enhancements (API & Raw Config)
- **Settings**: Added "API Inspection" configuration (connector, app var, path) to the Settings page.
- **Raw Editor**: Added a "Edit Raw YAML" feature to modify `jupiter.yaml` directly from the UI.
- **UX**: Added tooltips to settings fields for better guidance.
- **Backend**: Updated API endpoints to support new configuration fields and raw file access.

## 0.1.6 – Snapshot history & diff
- Added automatic snapshot persistence for every scan (CLI/API/UI) with metadata-rich JSON stored under `.jupiter/snapshots/`.
- Introduced CLI controls (`--snapshot-label`, `--no-snapshot`, `snapshots list|show|diff`) plus FastAPI endpoints (`/snapshots`, `/snapshots/{id}`, `/snapshots/diff`).
- Extended Web UI with a History view that lists snapshots, renders diffs, and refreshes when scans complete.
- Updated README, Manual, and docs (User Guide, API, Developer Guide) to explain the workflow and new options.

## 0.1.5 – Modal Visibility Fix
- Added global `.hidden` utility class so overlays/modals are truly hidden until opened.
- Removed duplicate `startScan` definition that broke the Web UI script execution.

## 0.1.4 – Web Interface Modal Fixes
- Added `pointer-events: auto` to modal overlay and content to ensure clicks are registered.
- Bumped client version to `0.1.4`.

## 0.1.3 – Web Interface Cache Fixes
- Forced server-side 200 OK for `index.html` and `app.js` to bypass aggressive browser caching.
- Bumped client version to `0.1.3` with visual indicator.
- Added debug logging for action handling.

## 0.1.2 – Web Interface Fixes
- Fixed unresponsive WebUI caused by ES Module scope issues.
- Refactored event handling to use delegation instead of inline handlers.
- Improved robustness of `app.js`.

## 0.1.1 – CLI exclusions and richer analysis
- Added glob-based ignore handling (including `.jupiterignore`) to the scanner and CLI.
- Extended analysis summaries with average size and top N largest files, plus JSON export.
- Documented new CLI flags, exclusion behavior, and report persistence in the README and Manual.

## 0.1.0 – Initial scaffolding
- Established Jupiter Python package with core scanning, analysis, and reporting primitives.
- Added CLI entrypoint supporting `scan`, `analyze`, and server stubs.
- Introduced server placeholders for API hosting and Meeting integration.
- Documented usage in README and Manual; created per-file changelogs.
