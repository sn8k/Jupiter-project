# Changelog - jupiter/plugins/__init__.py

## Version 0.6.0
- **DEPRECATED**: The v1 plugin system (Plugin/UIPlugin Protocols) is deprecated
- Will be removed in Jupiter 2.0.0
- Module-level deprecation warning on import
- Docstring deprecation notes on Plugin and UIPlugin protocols
- Migration guide reference: docs/PLUGIN_MIGRATION_GUIDE.md
- See: docs/BRIDGE_V2_CHANGELOG.md for v2 architecture details

## Version 0.5.1
- Fixed imports for `BridgeContext` - now correctly uses `jupiter.core.bridge.Bridge`
- Fixed `get_bridge()` function to import from `jupiter.core.bridge.bootstrap` instead of non-existent `jupiter.plugins.bridge_plugin`
- Resolved pyright errors for missing module imports

## Version 0.5.0
- Added Bridge access functions (`get_bridge()`, `has_bridge()`)
- Protocol-based plugin interfaces

## Version 0.4.0
- Added `PluginUIType` enum
- Added `PluginUIConfig` dataclass for UI integration

## Version 0.3.0
- Added `UIPlugin` protocol for plugins with UI components

## Version 0.2.0
- Added `Plugin` protocol base interface

## Version 0.1.0
- Initial plugin system module
