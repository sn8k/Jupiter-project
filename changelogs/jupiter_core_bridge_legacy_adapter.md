# Changelog - jupiter/core/bridge/legacy_adapter.py

## Version 0.2.0

### Deprecated
- **Module-level deprecation**: This entire module is now deprecated
  - Will be removed in Jupiter 2.0.0
  - All built-in plugins migrated to Bridge v2 manifests (plugin.yaml)
  - See docs/PLUGIN_MIGRATION_GUIDE.md for migration instructions
- `is_legacy_plugin()` - Marked deprecated, emits DeprecationWarning
- `is_legacy_ui_plugin()` - Marked deprecated, emits DeprecationWarning
- `LegacyAdapter` class - Marked deprecated, emits DeprecationWarning on init
- `LegacyPluginWrapper` class - Marked deprecated, emits DeprecationWarning on init
- Deprecation warning emitted on module import

### Changed
- Updated docstrings with `.. deprecated::` notices
- Added `warnings` import
- All deprecation warnings include reference to migration guide

### Notes
- Module retained for third-party legacy plugin compatibility
- Recommended to migrate all plugins to Bridge v2 before Jupiter 2.0.0

---

## Version 0.1.0

### Added
- Initial implementation of Legacy Plugin Adapter
- `LegacyAdapter` class for discovering and wrapping v1 plugins
  - `discover_plugins(directory)` - Scan directory for legacy plugins
  - `wrap_plugin(plugin_class)` - Wrap legacy plugin class
  - `get_wrapped_plugins()` - List all wrapped plugins
  - `get_plugin(plugin_id)` - Get specific wrapped plugin
  - `unload_plugin(plugin_id)` - Remove wrapped plugin
- `LegacyPluginWrapper` class to adapt v1 plugins to v2 interface
  - Implements plugin lifecycle (init, shutdown)
  - Maps legacy hooks (on_scan, on_analyze) to new system
  - Preserves UI configuration
- `LegacyManifest` dataclass for auto-generated manifests
- `LegacyCapabilities` dataclass for simplified capability model
- Detection functions:
  - `is_legacy_plugin(obj)` - Check if class is legacy plugin
  - `is_legacy_ui_plugin(obj)` - Check if has UI configuration
- Singleton pattern with `get_legacy_adapter()`, `init_legacy_adapter()`, `shutdown_legacy_adapter()`
- `discover_legacy_plugins(directory)` convenience function

### Features
- Automatic detection of v1 plugins by attribute signatures
- Manifest generation from plugin attributes (name, version, description)
- UI type detection and configuration preservation
- Hook method mapping (on_scan → scan event handling)
- Graceful handling of missing attributes
- Integration with Bridge plugin registry

### Tests
- 50 tests covering all functionality
- TestLegacyCapabilities: Capability dataclass
- TestLegacyManifest: Manifest generation
- TestIsLegacyPlugin: Detection logic
- TestIsLegacyUIPlugin: UI plugin detection
- TestLegacyPluginWrapper: Wrapper behavior
- TestLegacyAdapter: Adapter operations
- TestLegacyAdapterDiscovery: Plugin discovery
- TestLegacyAdapterLifecycle: Init/shutdown
- TestModuleFunctions: Singleton functions
- TestLegacyPluginError: Error handling
