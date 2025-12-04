# Changelog - jupiter/core/bridge/legacy_adapter.py

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
