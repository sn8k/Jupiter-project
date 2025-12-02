# Changelog - jupiter/core/plugin_manager.py

## [1.8.1] - 2025-12-03

### Added
- `restartable` field in `get_plugins_info()` output
- Returns `getattr(p, "restartable", True)` to indicate if plugin can be restarted by users
- Default is `True` for backward compatibility with existing plugins
- Plugins can set `restartable = False` to prevent user-initiated restarts

## [1.8.0] - 2025-12-15

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
