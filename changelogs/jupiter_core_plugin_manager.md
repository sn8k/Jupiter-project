# Changelog - jupiter/core/plugin_manager.py

## [1.14.0]

### Fixed
- **`get_sidebar_plugins()`**: Fix view_id collision causing wrong plugin views to be shown
  - Previously used `ui_contrib.id` (often "main") which caused all plugins to share the same viewId
  - Now always uses `plugin_info.manifest.id` as view_id to ensure unique containers
  - Fixed: clicking "Autodiag" no longer shows Live Map content

### Added
- **`get_plugin_translations(plugin_name, lang_code)`**: New method to load plugin translations
  - Loads translations from plugin's `web/lang/{lang_code}.json` file
  - Supports both v2 and legacy plugins
  - Falls back to English if requested language not available
  - Returns empty dict if no translations found

## [1.13.0]

### Fixed
- **`get_plugin_ui_html()`**: Now tries to import `web.ui` module and call `get_ui_html()` for v2 plugins
  - Falls back to empty container div if no module found
- **`get_plugin_ui_js()`**: Now tries to import `web.ui` module and call `get_ui_js()` for v2 plugins
  - Falls back to `web/panels/main.js` file if available
- Uses `Bridge.get_instance()` instead of `get_bridge()` for reliable access in all contexts

### Restored
- Live Map, Autodiag, Code Quality, Pylance Analyzer plugins now display their UIs correctly

## [1.12.0]

### Deprecated
- **DEPRECATED**: PluginManager class is deprecated, will be removed in Jupiter 2.0.0
- Emits DeprecationWarning on instantiation
- Use Bridge v2 architecture instead for plugin management
- Migration guide reference: docs/PLUGIN_MIGRATION_GUIDE.md
- See: docs/BRIDGE_V2_CHANGELOG.md for v2 architecture details

## [1.11.0]

### Added
- V2 plugin support for sidebar menu (`get_sidebar_plugins()`):
  - Includes plugins with `ui_contributions` having `location: sidebar` or `both`
  - Returns `v2: true` and `route` fields for v2 plugins
- V2 plugin support for settings page (`get_settings_plugins()`):
  - Includes plugins with `ui_contributions` having `location: settings` or `both`
  - Also includes plugins with `config_schema` for auto-form generation
  - Returns `v2: true` and `has_config_schema` fields
- V2 plugin UI serving (`get_plugin_ui_html()`, `get_plugin_ui_js()`):
  - Returns mount container HTML for v2 plugins
  - Reads JS from `web/panels/main.js` in plugin directory
- V2 plugin settings serving (`get_plugin_settings_html()`):
  - Generates container with embedded JSON schema for auto-form

### Changed
- All sidebar/settings/UI methods now check Bridge for v2 plugins first
- V2 plugins take precedence over legacy plugins with same name

## [1.10.0]

### Added
- V2 plugin support in `get_plugins_info()`:
  - Now queries Bridge for v2 plugins (those with plugin.yaml manifests)
  - V2 plugins include additional fields: `v2: true`, `state`, `error`
  - V2 plugins take precedence over legacy plugins with the same name
  - Uses `ui_contributions` property from `IPluginManifest` interface

### Changed
- `get_plugins_info()` now returns a merged list of legacy and v2 plugins
- Legacy plugins are skipped if a v2 version exists with the same ID

## [1.9.1]

### Fixed
- `get_plugins_info()` now reads signer metadata from `VerificationResult.signature_info` and converts timestamps via UTC, matching the verifier data model and Pyright expectations.
- Circuit breaker status retrieval uses the public `JobManager.get_circuit_breaker()` API, avoiding private attributes and exposing `opened_at` / `last_failure` in ISO format only when present.

## [1.9.0]

### Added
- `signature` field in `get_plugins_info()` output with signature verification info:
  - `verified`: boolean indicating if plugin has valid signature
  - `trust_level`: one of "official", "verified", "community", "unsigned", "experimental"
  - `signer`: optional signer identity string
- `circuit_breaker` field in `get_plugins_info()` output:
  - `state`: one of "closed", "half_open", "open"
  - `failure_count`: number of consecutive failures
  - `last_failure`: timestamp of last failure (if any)
- `_get_circuit_breaker_status(name)`: Internal method to retrieve circuit breaker info from JobManager

### Changed
- `get_plugins_info()` now returns richer metadata for WebUI badges (trust + circuit breaker)

## [1.8.1]

### Added
- `restartable` field in `get_plugins_info()` output
- Returns `getattr(p, "restartable", True)` to indicate if plugin can be restarted by users
- Default is `True` for backward compatibility with existing plugins
- Plugins can set `restartable = False` to prevent user-initiated restarts

## [1.8.0]

### Added
- `get_enabled_plugins()`: Returns list of all enabled plugin instances.
  - Used by system/autodiag routers to enumerate active plugins and their hooks.
  - Fixes AttributeError in `/diag/handlers` and `/system/handlers` endpoints.

## [Unreleased]

### Added
- Initial creation of `PluginManager`.
- `discover_and_load`: Automatically loads plugins from `jupiter.plugins`.
- `register`: Registers plugin instances with duplicate checks and config filtering.
- `hook_on_scan`, `hook_on_analyze`: Dispatches hooks to registered plugins.
- Config support: Filters plugins based on `enabled`/`disabled` lists in `jupiter.yaml`.

## [2025-12-01] - Plugin Install/Uninstall Support

### Added
- `CORE_PLUGINS`: Frozenset defining core plugins that cannot be uninstalled.
- `install_plugin_from_url(url)`: Download and install a plugin from a URL (ZIP file).
- `install_plugin_from_bytes(content, filename)`: Install a plugin from uploaded file bytes (.zip or .py).
- `_install_from_zip(zip_path, plugins_dir)`: Internal method to handle ZIP extraction and installation.
- `uninstall_plugin(plugin_name)`: Remove a plugin's files from disk and unregister it.
- `is_core` flag in `get_plugins_info()` to indicate which plugins cannot be uninstalled.
