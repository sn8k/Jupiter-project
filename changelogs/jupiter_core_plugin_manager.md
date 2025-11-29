# Changelog - jupiter/core/plugin_manager.py

## [Unreleased]

### Added
- Initial creation of `PluginManager`.
- `discover_and_load`: Automatically loads plugins from `jupiter.plugins`.
- `register`: Registers plugin instances with duplicate checks and config filtering.
- `hook_on_scan`, `hook_on_analyze`: Dispatches hooks to registered plugins.
- Config support: Filters plugins based on `enabled`/`disabled` lists in `jupiter.yaml`.
