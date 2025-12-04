# Changelog

## 1.8.38 - Phase 6 Plugin Migration: ai_helper Complete

### Added
- **AI Helper Plugin v1.1.0** - Complete Bridge v2 compliance:
  - **Server Module** (`server/api.py`):
    - FastAPI router with `/ai_helper` prefix
    - Standard endpoints: `/health`, `/metrics`, `/logs`, `/logs/stream`
    - Job management: `/jobs` (GET, POST), `/jobs/{id}` (GET, DELETE)
    - AI-specific: `/suggestions`, `/suggestions/file`, `/config`
    - Settings reset and changelog endpoints
    - `register_api_contribution(app, bridge)` for Bridge registration
  
  - **CLI Module** (`cli/commands.py`):
    - `jupiter ai suggest`: Generate suggestions with type/severity filters
    - `jupiter ai analyze-file <path>`: Analyze specific file
    - `jupiter ai status|health|config`: Plugin management commands
    - `register_cli_contribution(subparsers)` for Bridge registration
  
  - **WebUI Panel** (`web/panels/main.js`):
    - Full-featured panel per plugins_architecture.md
    - Suggestions list with type/severity filters
    - JSON export and AI context export
    - Real-time logs panel with pause/resume/download
    - Usage statistics (executions, suggestions, errors)
    - Help sidebar with documentation links
    - `mount(container, bridge)` and `unmount(container)` exports
  
  - **Unit Tests** (`tests/test_plugin.py`):
    - Lifecycle tests (init, health, metrics, reset_settings)
    - Business logic tests (suggestion generation)
    - Hook tests (on_scan, on_analyze)
    - MockBridge for isolated testing
  
  - **Business Logic** (`core/logic.py`):
    - Added `analyze_single_file()` for targeted file analysis
  
  - **i18n Updates**: 50+ new translation keys for panel

### Changed
- Updated `plugin.yaml` with complete entrypoints (server, cli, reset_settings)
- API routes now use `/ai_helper/*` prefix convention
- Version bump to 1.8.38

### Fixed
- Plugin now fully conforms to `docs/plugin_model/` reference structure
- All entrypoints properly declared for Bridge registration

## 1.8.37 - Phase 6 Plugin Migration: ai_helper

### Added
- **AI Helper Plugin v1.0.0** - Migrated to Bridge v2 architecture:
  - Full `plugin.yaml` manifest with JSON Schema configuration
  - Package structure (`jupiter/plugins/ai_helper/`)
  - Bridge v2 lifecycle: `init()`, `health()`, `metrics()`
  - Enhanced configuration schema:
    - `suggestion_types`: Select which types (refactoring, doc, security, etc.)
    - `severity_threshold`: Filter by minimum severity level
    - `large_file_threshold_kb`: Configurable large file detection
    - `max_functions_threshold`: Configurable God Object detection
  - i18n support (English and French translations)
  - Metrics tracking (execution count, errors, suggestions)
  - Declared permissions (fs_read, network_outbound)
  - UI panels and widgets declarations

### Changed
- AI Helper now uses function-based module API instead of class-based
- Configuration via `init()` instead of `configure()` method
- Internal state managed via `PluginState` dataclass singleton
- Version bump to 1.8.37

### Migration Note
- Legacy `AIHelperPlugin` class remains for backward compatibility
- New plugins should follow the Bridge v2 pattern demonstrated in `ai_helper/`

## 1.8.36 - Phase 5 WebUI Components Completion

### Added
- **Help Panel v0.1.0** (`jupiter/web/js/help_panel.js`):
  - Contextual help panel with slide-in animation
  - Collapsible sections with toggle icons
  - Search filtering for help content
  - i18n integration for multilingual support
  - Markdown-like text formatting (bold, code, lists)
  - Keyboard shortcuts: F1, ?, Escape
  - Built-in feedback dialog
  - Documentation links support

- **Data Export v0.1.0** (`jupiter/web/js/data_export.js`):
  - AI agent data export following pylance analyzer model
  - Multiple formats: JSON, NDJSON, CSV, Markdown
  - Data source selection (scan, analysis, functions, files, metrics, history)
  - Field selection with checkboxes
  - Filter system (eq, ne, gt, lt, contains, startswith)
  - Preview with size estimation
  - Copy to clipboard and file download

- **UX Utilities v0.1.0** (`jupiter/web/js/ux_utils.js`):
  - Progress indicators: ring, bar, step wizard
  - Task status badges (pending, running, success, error, cancelled)
  - Skeleton loaders (text, circle, rectangle)
  - Timing utilities: debounce, throttle
  - Focus management: trapFocus, saveFocus
  - Keyboard navigation for lists
  - Responsive breakpoint utilities
  - Animation helpers: fadeIn/Out, slideUp/Down
  - Clipboard utilities

- **Styles v1.2.0** (`jupiter/web/styles.css`):
  - Help panel slide-in styles
  - Data export panel styles
  - UX utility component styles
  - Spinner and skeleton animations

### Changed
- Updated `index.html` to include new JS modules with version tags
- Version bump to 1.8.36

## 1.8.35 - Plugin Type-Safety Maintenance

### Fixed
- Developer mode watchdog handler now overrides `on_modified` with the base filesystem event type, eliminating Pyright override errors while continuing to ignore directory events.
- Plugin signature details rely on `VerificationResult.signature_info` and UTC timestamp conversion, and circuit breaker badges now read through `JobManager` public accessors instead of private fields.

### Changed
- Version bump to 1.8.35

## 1.8.34 - WebUI Plugin Enhancements

### Added
- **Plugin Settings Frame v0.2.0** (`jupiter/web/js/plugin_settings_frame.js`):
  - Check for update button with `checkForUpdate()` method
  - Update plugin button with `updatePlugin()` method
  - View changelog button with modal display
  - Debug mode toggle with auto-disable timer
  - Update available badge display

- **Auto Form v0.2.0** (`jupiter/web/js/auto_form.js`):
  - Format validation: email, url, uri, date-time, date, time, ipv4, ipv6, hostname
  - Number validation: exclusiveMinimum, exclusiveMaximum, multipleOf
  - Array validation: uniqueItems
  - Enum validation for any type
  - Custom validation function support via `x-validate`

- **Logs Panel v0.2.0** (`jupiter/web/js/logs_panel.js`):
  - Rate limiting for incoming logs with configurable batch processing
  - Message truncation for long log entries
  - ZIP/Gzip compression for log export (JSZip/CompressionStream)
  - `getLogsPerSecond()` and `getPendingCount()` monitoring methods

- **i18n Loader v0.2.0** (`jupiter/web/js/i18n_loader.js`):
  - Plugin translation loading and merging
  - `loadPluginTranslations()` and `loadAllPluginTranslations()` methods
  - `pt()` shorthand for plugin translations
  - Plugin namespace support (`plugin.<pluginId>.<key>`)

### Changed
- Version bump to 1.8.34

## 1.8.33 - Plugin Integration Module

### Added
- **Plugin Integration** (`jupiter/web/js/plugin_integration.js`):
  - Wires all plugin frontend modules with main app.js
  - Auto-initialization after DOM ready
  - Integration with existing pluginUIState
  - Plugin settings frame injection into settings view
  - Event handling for plugin lifecycle events
  - Modal dialog support with fallback
  - Metric alert notifications

### Changed
- Updated `index.html` to include plugin_integration.js
- Version bump to 1.8.33

## 1.8.32 - WebUI Plugin Bridge Frontend Modules

### Added
- **Plugin Container** (`jupiter/web/js/plugin_container.js`):
  - Dynamic plugin panel mounting with lazy loading
  - Sandboxed iframe support for plugin isolation
  - Event-based communication between host and plugins
  - Panel lifecycle management and visibility tracking

- **Jupiter Bridge** (`jupiter/web/js/jupiter_bridge.js`):
  - Window-global API (`window.jupiterBridge`) for frontend plugins
  - REST API wrapper with full CRUD methods
  - WebSocket connection management with auto-reconnect
  - Event subscription system for real-time updates

- **Auto Form** (`jupiter/web/js/auto_form.js`):
  - JSON Schema-based automatic form generation
  - Support for all JSON Schema types and validation
  - Conditional rendering and nested objects/arrays
  - Live data binding with onChange callbacks

- **Logs Panel** (`jupiter/web/js/logs_panel.js`):
  - Real-time log streaming via WebSocket
  - Log level filtering and text search with highlighting
  - Export logs as JSON or plain text
  - Auto-scroll with pause on user interaction

- **Plugin Settings Frame** (`jupiter/web/js/plugin_settings_frame.js`):
  - Dynamic form generation from plugin manifest
  - Settings validation and dirty state tracking
  - Import/export settings as JSON files
  - Tab-based settings organization

- **i18n Loader** (`jupiter/web/js/i18n_loader.js`):
  - Dynamic language file loading
  - Automatic language detection
  - Pluralization and interpolation support
  - MutationObserver for dynamic content translation

- **Metrics Widget** (`jupiter/web/js/metrics_widget.js`):
  - Real-time metrics dashboard with auto-refresh
  - Sparkline mini-charts for historical data
  - Threshold-based alerting (warning/critical)
  - System and plugin metrics scope switching

### Changed
- Updated `index.html` to load all new JS modules
- Version bump to 1.8.32

## 1.8.7 - Web UI cache hardening

### Changed
- Jupiter Web UI HTTP handler now strips conditional headers and enforces `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` (plus `Pragma`/`Expires`/`Surrogate-Control`) on every response to avoid stale assets.
- The frontend wraps `window.fetch` and `apiFetch` with `cache: "no-store"` and no-cache headers so every request bypasses the browser cache.
- Added cache-control meta tags to `index.html` to align client-side caching with the server policy.

### Documentation
- README and Manual mention that the Web UI disables browser/proxy caching.

## 1.8.6 — Documentation polish (language, examples, roles)

### Updated
- `docs/api.md` with clearer introduction, explicit JSON payload examples for `scan`, `ci`, `simulate`, `run`, and more precise wording for roles and safety constraints.
- `Manual.md` (FR) to fix encoding issues, improve phrasing, and keep the CLI/API summaries aligned with the current endpoints.
- `README.md` wording to clarify the CI/SSH usage of the CLI and point to concrete API examples.
- `docs/index.md` to better describe the scope and audience of each document.

## 1.8.5 — Documentation refresh (API/UI/CLI alignment)

### Updated
- README to highlight GUI-first flow, full CLI matrix, and API overview tied to current routers.
- Manual (FR) with accurate setup, multi-projet registry, snapshots/simulation, sécurité, Meeting, and plugin coverage.
- API reference with real endpoints, roles, and payload summaries (scan/analyze/ci, snapshots, simulate, projects/config, plugins, watch, Meeting, update).
- Docs index to point to up-to-date guides and mention Projects/History in the Web UI.

## 1.8.2 — Plugin Bridge System & Log Path Setting

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

## Older entries

See historical notes in the individual files under `changelogs/` for versions prior to 1.8.2.

