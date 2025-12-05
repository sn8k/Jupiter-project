# Changelog

## 1.8.69 - Web UI version injection

### Fixed
- **`jupiter/web/index.html`**: Replaced hardcoded `app.js?v=…` and footer version with backend-injected `{{JUPITER_VERSION}}` placeholder to reflect the running build.
- **`jupiter/web/app.py`** (v1.1.2): Server now renders `index.html` by injecting the current Jupiter version into placeholders so GUI footer/cache-busting stay in sync with backend version.

## 1.8.70 - Metrics plugin null guards

### Fixed
- **`jupiter/plugins/metrics_manager/web/panels/main.js`** (v1.0.4): Filters out null/invalid plugin metric entries before rendering and skips non-object gauges to prevent `Object.entries` TypeError in the WebUI.

## 1.8.68 - Plugin Metrics Base Fixes

### Fixed
- **`jupiter/web/app.js`** (v1.7.2): Plugin bridge now exposes `api.baseUrl`, hardens API calls, and routes plugin metrics through `/plugins/v2/{id}/metrics` with autodiag fallback to prevent 404s.
- **`jupiter/plugins/metrics_manager/web/panels/main.js`** (v1.0.3): Log stream resolves the API host/port (8050/8081 → 8000) and guards empty metrics payloads to avoid UI crashes.

## 1.8.67 - Metrics Log Stream & Base URL

### Fixed
- [x] 1.8.67 - Fix bridge metrics URLs and diagnostics log streaming
- **`jupiter/web/app.js`** (v1.7.1): Route plugin metrics to `/plugins/v2/{id}/metrics` with inferred API base (including diag port 8081→8000) to stop 404s in the plugins page.
## 1.8.66 - Metrics Routing Hardening

### Fixed
- **`jupiter/web/js/jupiter_bridge.js`** (v0.1.1): Infer API base URL to default to port 8000 when GUI/diag ports are used; route plugin metrics via `/plugins/v2/{id}/metrics` (keeping autodiag legacy path) to avoid 404s.
- **`jupiter/web/js/metrics_widget.js`** (v0.1.1): Detect API base URL and target `/metrics` and `/metrics/bridge` endpoints instead of invalid `/plugins` path.

## 1.8.65 - Metrics Manager API URL Fix

### Fixed
- **`jupiter/plugins/metrics_manager/web/panels/main.js`** (v1.0.2):
  - Fixed all API URLs to use `bridge.api.get()` and `bridge.api.post()`
  - Changed paths from `/api/v1/plugins/metrics_manager/*` to `/metrics_manager/*`
  - Consistent with Bridge v2 plugin API routing pattern
  - Metrics should now load correctly in the WebUI

## 1.8.64 - Metrics Manager Plugin Fix

### Fixed
- **`jupiter/plugins/metrics_manager/plugin.yaml`** (v1.0.1):
  - Corrected manifest to match Bridge v2 schema
  - Removed non-standard properties (`settings_frame`, `monitoring`, `governance`)
  - Simplified config schema format
  - Plugin now correctly appears in WebUI sidebar menu

## 1.8.63 - Metrics Manager Plugin

### Added

#### New Plugin: Metrics Manager
- **`jupiter/plugins/metrics_manager/`** (v1.0.0):
  - Complete v2 plugin for centralized metrics observation and management
  - Companion to `jupiter.core.bridge.metrics.MetricsCollector`

- **Features**:
  - Real-time system metrics dashboard (uptime, collected metrics, counters)
  - Plugin metrics aggregation and visualization
  - Counter and gauge tables with live updates
  - Metric history charts (pure canvas, no external libs)
  - Configurable alert system with warning/critical thresholds
  - Export to JSON or Prometheus format
  - Live log streaming with filtering

- **API Endpoints** (`/api/v1/plugins/metrics_manager/`):
  - `GET /all` - All collected metrics
  - `GET /system` - System metrics only
  - `GET /plugins` - Plugin metrics only
  - `GET /counters` - Counter metrics
  - `GET /history/{name}` - Metric history
  - `GET /export` - Export metrics (JSON/Prometheus)
  - `POST /record` - Record custom metrics
  - `POST /reset` - Reset all metrics
  - `GET /alerts`, `DELETE /alerts` - Alert management
  - `GET /stream` - SSE real-time metrics
  - Standard endpoints: `/health`, `/metrics`, `/logs`, `/logs/stream`

- **Configuration** (`config.yaml`):
  - Refresh interval, history size, export format
  - Alert thresholds (error rate, response time)
  - Chart type preferences (line/bar/area)
  - Logging settings

- **i18n Support**:
  - English translations (100+ keys)
  - French translations (100+ keys)

### Technical
- Bridge v2 architecture compliant (plugins_architecture.md v0.6.0)
- Lifecycle hooks: init(), shutdown(), health(), metrics()
- Event bus integration for real-time metric events
- Thread-safe metric collection
- Auto-refresh (configurable, default 10s)

## 1.8.58 - Plugin Navigation & Dynamic i18n

### Fixed

#### Plugin Sidebar Navigation Bug
- **`jupiter/core/plugin_manager.py`** (v1.14.0):
  - Fixed view_id collision causing wrong plugin views to be shown when clicking menu items
  - Previously, all plugins with `id: main` in their UI panel config shared the same viewId (`plugin-main`)
  - Now always uses `plugin_info.manifest.id` as view_id (e.g., `plugin-autodiag`, `plugin-livemap`)
  - **Fixed:** clicking "Autodiag" no longer shows Live Map content

### Added

#### Dynamic Plugin Translations System
Each plugin now manages its own translations in its `web/lang/` directory, loaded dynamically at mount time.

- **`jupiter/server/routers/system.py`**:
  - Added `GET /plugins/{name}/lang/{lang_code}` endpoint to serve plugin translations
  - Falls back to English if requested language not available

- **`jupiter/core/plugin_manager.py`** (v1.14.0):
  - Added `get_plugin_translations(plugin_name, lang_code)` method
  - Loads translations from plugin's `web/lang/{lang_code}.json` file
  - Supports both v2 and legacy plugins

- **`jupiter/web/app.js`**:
  - `createPluginBridge(pluginName, pluginTranslations)` now accepts plugin-specific translations
  - `loadPluginViewContent()` fetches plugin translations before mounting
  - Bridge's `i18n.t()` checks plugin translations first, then falls back to global

### Technical Notes
- Plugin translations are loaded via API (`/plugins/{name}/lang/{lang}`) when the plugin view is mounted
- The bridge provides a `t()` function that prioritizes plugin translations over global ones
- Main lang files (`jupiter/web/lang/*.json`) only contain menu/title keys for plugins (`plugin.*.title`)
- All plugin-specific UI strings remain in the plugin's own `web/lang/` directory

### Architecture Change
This implements the i18n pattern described in `docs/plugins_architecture.md`:
- Plugins own their translations in `web/lang/*.json`
- Bridge merges plugin translations at runtime
- No duplication of plugin strings in the main application

## 1.8.57 - V2 Plugin UI Loading Fix

### Fixed

#### Plugin UI Loading for V2 Plugins
- **`jupiter/core/plugin_manager.py`** (v1.13.0):
  - Fixed `get_plugin_ui_html()` and `get_plugin_ui_js()` for v2 plugins
  - Now tries to import `web.ui` module and call `get_ui_html()`/`get_ui_js()` functions
  - Fallbacks to `web/panels/main.js` pattern if module not found
  - Uses `Bridge.get_instance()` instead of `get_bridge()` for reliable access

### Restored Plugin Interfaces
The following v2 plugins now have their UI interfaces working again:
- 🗺️ **Live Map** - Dependency graph visualization
- 🔬 **Autodiag** - Auto-diagnostic tool
- 📊 **Code Quality** - Code quality analysis
- 🔍 **Pylance Analyzer** - Pylance integration

### Technical
- All 4 plugins: HTML and JS content loaded from `web/ui.py` modules
- UI loading via `/plugins/{name}/ui` endpoint now works for v2 plugins

## 1.8.56 - V2 Plugin API Router Support & UI Fixes

### Fixed

#### API Router Support for V2 Plugins
- **`jupiter/core/bridge/manifest.py`** (v0.1.3):
  - Added support for `api.router` format in manifest
  - Plugins can now declare FastAPI router entrypoints: `api: router: "server.api:router"`
  - Parses prefix and tags from manifest `api:` section

- **`jupiter/core/bridge/bridge.py`** (v0.3.1):
  - Added `_resolve_api_router()` method to import and resolve router entrypoints
  - V2 plugins with `api.router` format now properly mount their routers

#### Plugin API Fixes
- **`jupiter/plugins/ai_helper/server/api.py`** (v1.1.1):
  - Removed hardcoded `prefix="/ai_helper"` from router
  - Prefix now correctly applied by server when mounting (avoiding double-prefix)

#### UI Navigation & Translation Fixes (from 1.8.55)
- **`jupiter/web/lang/en.json` & `fr.json`**:
  - Added missing plugin menu translation keys: `plugin.livemap.title`, `plugin.autodiag.title`, `plugin.code_quality.title`, `plugin.pylance_analyzer.title`

- **`jupiter/web/app.js`**:
  - Fixed `setView()` to pass `isV2` parameter correctly for plugin navigation

- **`jupiter/plugins/ai_helper/plugin.yaml`** (v1.1.1):
  - Removed duplicate suggestions panel from UI contributions

### Technical
- AI Helper API endpoints now available at `/ai_helper/*` (health, metrics, suggestions)
- All 9 plugins discovered and API routers properly mounted

## 1.8.55 - Plugin Manifest Schema Compliance Fix

### Fixed

#### Plugin Manifests (Schema Compliance)
- **`jupiter/plugins/autodiag/plugin.yaml`** (v1.1.1):
  - Rewritten for schema compliance
  - Added required `type: tool` and `jupiter_version: ">=1.8.0"`
  - Changed `trust_level: stable` to `trust_level: official`
  - Proper structure for capabilities, entrypoints, ui

- **`jupiter/plugins/code_quality/plugin.yaml`** (v0.8.2):
  - Same schema compliance fixes

- **`jupiter/plugins/livemap/plugin.yaml`** (v0.3.1):
  - Same schema compliance fixes

- **`jupiter/plugins/notifications_webhook/plugin.yaml`** (v1.0.1):
  - Same schema compliance fixes
  - Added missing `id` field

- **`jupiter/plugins/watchdog/plugin.yaml`** (v1.0.1):
  - Same schema compliance fixes

- **`jupiter/plugins/pylance_analyzer/plugin.yaml`** (v1.0.1):
  - Changed `trust_level: stable` to `trust_level: official`
  - Changed `dependencies: []` to `dependencies: {}` (must be object)

#### Test Fix
- **`tests/test_bridge_manifest.py`** (v1.0.1):
  - Fixed `test_load_from_file` assertion
  - `source_path` now correctly expects plugin directory

### Technical
- Pyright: 0 errors, 0 warnings
- pytest: 1516 passed, 10 failed (pre-existing)
- All 9 plugins now load successfully via Bridge

---

## 1.8.54 - Phase 11.2 & 11.3 Documentation & Deprecation

### Added

#### Documentation Updates (Phase 11.2)
- **`docs/plugin_model/`** (v0.4.0):
  - Updated README.md with v0.6.0 architecture features
  - Added CLI commands reference
  - Added monitoring, governance, notifications sections
  - Updated plugin.yaml with new capabilities (health, monitoring, governance)
  - Updated __init__.py and changelog.md

- **`docs/BRIDGE_V2_CHANGELOG.md`**:
  - New comprehensive changelog summarizing all Bridge v2 phases
  - 11 phases documented with test counts
  - Module list with versions
  - Migration checklist

#### Deprecation (Phase 11.3)
- **`jupiter/plugins/__init__.py`** (v0.6.0):
  - Module-level deprecation warning on import
  - `Plugin` Protocol marked deprecated in docstring
  - `UIPlugin` Protocol marked deprecated in docstring
  - References to PLUGIN_MIGRATION_GUIDE.md

- **`jupiter/core/plugin_manager.py`** (v1.12.0):
  - `PluginManager` class deprecated with warning on instantiation
  - References to Bridge v2 architecture

### Changed

#### refonte_plugins.md
- Updated status: Phase 11.2 and 11.3 marked complete
- Total tests updated to 1500+

### Technical
- Pyright: 0 errors, 0 warnings
- pytest: 1513 passed

---

## 1.8.53 - Phase 5.6, 5.7, 5.11 & 7.1 WebUI Enhancements

### Added

#### Central Logs Panel (Phase 5.6)
- **`jupiter/web/js/logs_central_panel.js`** (v0.1.0):
  - Multi-plugin log filtering with dropdown selector
  - Level filter (DEBUG to CRITICAL)
  - Time range picker with presets (last 5min, 15min, 1h, 24h, all)
  - Search functionality with debounce
  - WebSocket streaming for real-time logs
  - Export filtered logs to JSON or TXT

- **`jupiter/web/js/plugin_integration.js`** (v0.2.0):
  - `_initCentralLogsPanel()` auto-injects central logs in settings view
  - `_integrateUxUtilsWithExistingComponents()` enhances scan progress and loading states

#### Dry-Run Settings Support (Phase 5.7)
- **`jupiter/web/js/plugin_settings_frame.js`** (v0.4.0):
  - Dry-run button in settings footer
  - `dryRunSave()` method validates settings without applying
  - API call to `PUT /plugins/{id}/settings?dry_run=true`
  - Success/error feedback with i18n support

#### UX Utils Integration (Phase 5.11)
- **`jupiter/web/js/plugin_integration.js`** (v0.2.0):
  - Auto-enhances #watch-progress with ProgressRing
  - Adds skeleton loading to plugin containers during fetch
  - Keyboard navigation improvements for plugin lists

#### Permissions Preview (Phase 7.1)
- **`jupiter/web/index.html`**:
  - Added #install-plugin-permissions section in install modal
  - Loading state, permissions list, sensitive warnings

- **`jupiter/web/app.js`**:
  - `previewPluginPermissions()` fetches permissions from URL
  - `previewPluginPermissionsFromFile()` reads from uploaded ZIP
  - `renderPermissionsPreview()` displays permissions with icons

#### i18n Translations
- **`jupiter/web/lang/en.json`** & **`jupiter/web/lang/fr.json`**:
  - dry_run, dry_run_preview, dry_run_success, dry_run_error, dry_run_no_changes
  - central_logs_title, central_logs_subtitle, central_logs_all_plugins
  - central_logs_time_range_* (all presets)
  - plugins_install_permissions_*, permission_* (file_read, file_write, network, exec, config, events, meeting)

#### CSS Styles
- **`jupiter/web/styles.css`**:
  - .central-logs-panel, .central-logs-filters, .central-logs-content
  - .logs-mini-panel for compact injection
  - .permissions-list, .permission-item, .permission-sensitive

### Technical
- Pyright: 0 errors, 0 warnings
- pytest: 1513 passed

---

## 1.8.52 - Phase 6.4 Legacy Deprecation & Phase 8.1 Hot Reload WebUI

### Changed

#### Legacy Adapter Deprecation (Phase 6.4)
- **`jupiter/core/bridge/legacy_adapter.py`** (v0.2.0):
  - Module-level deprecation warning on import
  - `is_legacy_plugin()` marked deprecated with warning
  - `is_legacy_ui_plugin()` marked deprecated with warning
  - `LegacyAdapter` class marked deprecated (warning in `__init__`)
  - `LegacyPluginWrapper` class marked deprecated (warning in `__init__`)
  - All warnings reference `docs/PLUGIN_MIGRATION_GUIDE.md` for migration
  - Will be removed in Jupiter 2.0.0

### Added

#### Hot Reload WebUI Button (Phase 8.1)
- **`jupiter/web/js/plugin_settings_frame.js`** (v0.3.0):
  - Hot Reload button in developer mode debug bar
  - Calls `/plugins/v2/{plugin_id}/reload` API endpoint
  - Loading state with spinner during reload
  - Success/error feedback with i18n support
  - Automatic plugin refresh after successful reload

- **`jupiter/web/lang/en.json`**:
  - Added `hot_reload`, `hot_reload_confirm`, `hot_reload_success`, `hot_reload_error`, `hot_reload_dev_mode_required`

- **`jupiter/web/lang/fr.json`**:
  - Added French translations for hot reload keys

### Technical
- All legacy adapter tests pass (50 tests) with expected deprecation warnings
- Integration tests pass (22 tests)
- Total: 1400+ tests

---

## 1.8.51 - Phase 6.3 Plugin Migration Complete

### Added

#### Additional Bridge v2 Migrations
- **`jupiter/plugins/autodiag/`** (v1.1.0):
  - Complete v2 structure: `plugin.yaml`, `__init__.py`, `web/ui.py`, `web/lang/`
  - `AutodiagPluginState` dataclass for state management
  - Communicates with separate autodiag server on port 8081
  - UI type: `both` (sidebar + settings)
  - i18n: `web/lang/en.json`, `web/lang/fr.json`

- **`jupiter/plugins/livemap/`** (v0.3.0):
  - Complete v2 structure: `plugin.yaml`, `__init__.py`, `core/`, `web/`
  - `core/graph.py`: `GraphNode`, `GraphEdge`, `DependencyGraph`, `GraphBuilder`
  - D3.js force-directed interactive visualization
  - Node coloring by file type (py=green, js/ts=blue, etc.)
  - UI type: `both` (sidebar + settings)
  - i18n: `web/lang/en.json`, `web/lang/fr.json`
  - Deprecates `jupiter/core/graph.py` (legacy shim maintained)

- **`jupiter/plugins/code_quality/`** (v0.8.1):
  - Complete v2 structure: `plugin.yaml`, `__init__.py`, `core/`, `web/`
  - `core/models.py`: `QualityIssue`, `FileQualityReport`, `QualitySummary`, `ManualDuplicationLink`
  - `core/analyzer.py`: `CodeQualityAnalyzer` with complexity and duplication analysis
  - `web/ui.py`: Dashboard with score circle, tabbed interface, manual duplication linking
  - UI type: `both` (sidebar + settings)
  - i18n: `web/lang/en.json`, `web/lang/fr.json`

### Technical
- All 6 plugins now use Bridge v2 architecture (pylance_analyzer, notifications_webhook, watchdog, autodiag, livemap, code_quality)
- Pylance/Pyright verification: 0 errors on all plugins
- 1398 tests passed (1 pre-existing unrelated failure)

---

## 1.8.50 - Phase 6.3 Plugin Migration to Bridge v2

### Added

#### Phase 6.3: Plugin Migration to Bridge v2 Architecture
- **`jupiter/plugins/pylance_analyzer/`** (v1.0.0):
  - Complete v2 structure: `plugin.yaml`, `__init__.py`, `core/`, `server/`, `web/`
  - `core/analyzer.py`: `PylanceDiagnostic`, `PylanceFileReport`, `PylanceSummary`, `PylanceAnalyzer`
  - `server/api.py`: FastAPI router with `/status`, `/config`, `/summary`, `/file/{path}`
  - `web/ui.py`: Legacy UI HTML/JS for backward compatibility
  - `web/lang/en.json`, `fr.json`: i18n translations (60+ keys)
  - Bridge lifecycle: `init()`, `shutdown()`, `health()`, `metrics()`, `reset_settings()`
  - Hooks: `on_scan()`, `on_analyze()`

- **`jupiter/plugins/notifications_webhook/`** (v1.0.0):
  - Complete v2 structure with async notification dispatch
  - `plugin.yaml`: permissions (emit_events, ws_broadcast, http_client)
  - Events: scan_complete, analysis_complete, quality_alert, api_connected
  - `web/ui.py`: Settings HTML/JS
  - `web/lang/en.json`, `fr.json`: i18n translations

- **`jupiter/plugins/watchdog/`** (v1.0.0):
  - Complete v2 structure for development tool
  - Background monitoring thread with configurable interval
  - Auto-reload support with plugin_manager integration
  - `web/ui.py`: Settings panel with status grid
  - `web/lang/en.json`, `fr.json`: i18n translations

### Changed
- All migrated plugins maintain backward compatibility via legacy class wrappers
- Plugins now use Bridge-provided logger via `bridge.services.get_logger()`
- Configuration loaded via `bridge.services.get_config()`

### Technical
- Pylance verification passed on all migrated plugins
- Each plugin has dedicated CHANGELOG.md

## 1.8.48 - Phase 9 & 11.1 Test Coverage Complete + Documentation


### Added

#### Phase 9: CLI Command Tests
- **`tests/test_cli_plugin_commands.py` v0.4.0**:
  - 58 tests total, all passing
  - TestInstallComprehensive: 5 tests (source, dry-run, deps, force, combined)
  - TestUninstallComprehensive: 3 tests (not found, success, force)
  - TestUpdateComprehensive: 7 tests (not found, not installed, backup, no-backup, source, deps, rollback)
  - TestCheckUpdates: 3 tests (no plugins, with plugins, json output)
  - TestValidateManifest: 4 tests (valid, missing fields, invalid version, invalid type)
  - TestInstallDependencies: 3 tests (no requirements, with requirements, pip failure)

#### Phase 11.1: Integration Test Scenarios
- **`tests/test_plugin_integration.py` v0.2.0**:
  - TestScenarioInstallFromScratch: 2 tests (install flow, signature verification)
  - TestScenarioFullUsage: 2 tests (CLI command registration, event bus integration)
  - TestScenarioUpdateWithRollback: 2 tests (backup creation, rollback on failure)
  - TestScenarioFailureRecovery: 2 tests (invalid plugin rejection, uninstall preservation)
  - TestScenarioPerformance: 1 test (bulk event emission)
  - **TestScenarioJobsCancellation**: 7 tests (submit, cancel, failure, progress, stats, circuit breaker, list/filter)
  - All 16 integration tests passing

#### Phase 11.2: Documentation Updates
- **`docs/plugins_architecture.md` v0.5.0**: Implementation status section added
- **`README.md` v1.8.48**: Updated with Bridge v2 plugin system:
  - Plugin CLI commands section (install, uninstall, update, sign, verify, etc.)
  - Plugin management section with features overview
  - New API endpoints (plugins v2, jobs)
  - New documentation references

### Tests
- Total test count: 74 tests (58 CLI + 16 integration)
- All tests passing

## 1.8.47 - Phase 5.6/8.1/9/11 Plugin System Enhancements

### Added

#### Phase 5.6: Backend Log Level Management
- **`jupiter/core/bridge/services.py` v0.3.0**:
  - `set_global_log_level_floor()` : Définir un niveau plancher global pour tous les plugins
  - `get_global_log_level_floor()` : Obtenir le niveau plancher global
  - `set_plugin_log_level()` : Définir un niveau de log par plugin
  - `get_plugin_log_level()` / `clear_plugin_log_levels()` : Gestion des niveaux par plugin
  - Enhanced `PluginLogger` avec `_should_log()`, `_get_effective_level()`, `isEnabledFor()`
  - Le niveau effectif = max(global_floor, plugin_level)
- 13 nouveaux tests dans `test_bridge_services.py`

#### Phase 8.1: Developer Mode Hot Reload
- **`jupiter/config/config.py` v1.4.0**: Ajout champ `developer_mode: bool = False`
- **`jupiter/server/models.py` v1.1.0**: `ConfigModel` et `PartialConfigModel` incluent `developer_mode`
- **`jupiter/server/routers/system.py` v1.10.0**: Endpoints config gèrent `developer_mode`
- **`jupiter/server/routers/plugins.py` v0.4.0**:
  - `POST /plugins/v2/{id}/reload` : Hot reload avec vérification dev_mode
  - `HotReloadResponse` model avec success, duration_ms, versions, warnings
- **`jupiter/web/app.js` v1.7.0**:
  - État `developerMode` dans state
  - Bouton 🔥 sur les cartes plugins (visible uniquement en dev mode)
  - Fonction `hotReloadPlugin(name)` pour appel API

#### Phase 9: Marketplace CLI Commands
- **`jupiter/cli/main.py` v1.6.0**:
  - `jupiter plugins update <id>` : Mise à jour avec backup/rollback
  - `jupiter plugins check-updates` : Vérification des mises à jour
  - Options `--install-deps` et `--dry-run` pour install
- **`jupiter/cli/plugin_commands.py` v0.5.0**:
  - `_install_plugin_dependencies()` : Installation pip depuis requirements.txt
  - `handle_plugins_update()` : Backup automatique, rollback sur erreur, signature check
  - `handle_plugins_check_updates()` : Liste versions et sources

#### Phase 11.2: Documentation
- **`docs/PLUGIN_DEVELOPER_GUIDE.md` v1.0.0** : Guide complet développeur plugins
  - 15 sections : Introduction, Quick Start, Architecture, Manifest, etc.
  - Exemples de code complets pour CLI, API, WebUI, Jobs
  - Référence API ServiceLocator et hooks
- **`Manual.md`** : Nouvelle section "Gestion des plugins (CLI)" avec toutes les commandes

### Changed
- Export des nouvelles fonctions de log dans `bridge/__init__.py` v0.24.0
- Statut TODO mis à jour : Phase 9.1/9.2/9.3 CLI complètes

### Tests
- 50 tests passent dans test_bridge_services.py (13 nouveaux pour log levels)

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

