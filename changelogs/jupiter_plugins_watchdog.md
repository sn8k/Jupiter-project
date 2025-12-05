# Changelog – jupiter/plugins/watchdog/

## v1.0.1 – plugin.yaml Schema Compliance Fix

### Fixed
- Rewrote `plugin.yaml` for JSON schema compliance
- Added required `type: tool` field
- Added required `jupiter_version: ">=1.8.0"` field
- Proper `capabilities` object structure (was array)
- Proper `ui.panels` array structure
- Proper `entrypoints` object
- Proper `config.defaults` object

---

## v1.0.0 – Migration Bridge v2
- **Migration vers Bridge v2**: Structure plugin.yaml + modules
- **Lifecycle**: `init(bridge)`, `shutdown()`, `health()`, `metrics()`, `reset_settings()`
- **Monitoring**: Thread de surveillance avec `_monitor_loop()`, `_check_for_changes()`
- **Reload**: `_trigger_reload()` avec support callback et plugin_manager
- **API**: `force_check()`, `get_status()`, `get_config()`, `configure()`
- **UI**: Module web avec `get_settings_html()`, `get_settings_js()` dans `web/ui.py`
- **i18n**: Fichiers de traduction `en.json` et `fr.json`
- **Backward Compat**: Classe `PluginWatchdog` pour PluginManager legacy

---

## v1.0.2 (Legacy)

**Fixed serialization error in get_status().**

### Fixed
- `_discover_plugin_files()` now validates that `name` attribute is a string before using it
- Prevents `property` objects from being stored as plugin names
- Fixes "Unable to serialize unknown type: <class 'property'>" error on `/plugins/watchdog/status`

---

## v1.0.1 (Legacy)

**Fixed settings panel API connectivity.**

### Fixed
- Settings JS now uses `state.apiBaseUrl` instead of undefined `window.API_BASE`
- Added `getApiBase()` helper to properly retrieve API base URL from global state
- Added `getAuthHeaders()` helper to include authentication token in requests
- All fetch calls now include proper Authorization headers

### Notes
- This fixes the "Error saving settings" issue when using the GUI served on port 8000
- API requests now correctly target port 8000 instead of relative URLs

---

## v1.0.0 (Legacy)

**Initial release – Plugin Watchdog for development.**

### Added
- `PluginWatchdog` class implementing system plugin (SETTINGS only, no sidebar)
- Automatic file monitoring for all plugin files in `jupiter/plugins/`
- Detection of file modifications via mtime comparison
- Auto-reload of modified plugins without Jupiter restart
- Configurable options:
  - `enabled`: Enable/disable watchdog (default: disabled)
  - `check_interval`: How often to check for changes (default: 2 seconds)
  - `auto_reload`: Auto-reload or just notify (default: true)
- Status reporting:
  - Monitoring state (active/stopped)
  - Number of watched files
  - Total reload count
  - Last reload timestamp
- Manual actions:
  - Force check now
  - Refresh status
- Threaded monitoring loop (daemon thread)
- Preservation of plugin enabled/disabled state on reload
- Detailed logging for debugging
- Complete i18n support (en/fr)

### API Endpoints
- `GET /plugins/watchdog/config` - Get configuration
- `POST /plugins/watchdog/config` - Save configuration
- `GET /plugins/watchdog/status` - Get current status
- `POST /plugins/watchdog/check` - Force immediate check

### Notes
- Disabled by default (opt-in for development)
- Skips self-reload to avoid issues
- Works with existing `PluginManager.restart_plugin()` method
