# Changelog - jupiter/core/bridge/hot_reload.py

## Version 0.2.0

### Added
- Developer mode guard: hot reload now requires `developer_mode: true` to be enabled
- `can_reload()` checks dev mode status as first validation step
- `reload()` checks dev mode before proceeding with any operations
- New parameter `skip_dev_mode_check` for testing/internal bypass
- Clear error messages when dev mode is disabled

### Changed
- Updated `reload()` signature to include `skip_dev_mode_check: bool = False`
- Updated `reload_plugin()` convenience function signature
- Updated documentation to reflect dev mode requirement

### Tests
- Added 4 new tests for dev mode guard functionality:
  - `test_can_reload_requires_dev_mode`
  - `test_reload_fails_without_dev_mode`
  - `test_skip_dev_mode_check`
  - `test_can_reload_checks_dev_mode_first`
- Total tests: 61

## Version 0.1.0

### Added
- Initial implementation of Hot Reload system
- `HotReloader` class for managing plugin reloading
  - `reload(plugin_id, force, preserve_config)` - Main reload method
  - `can_reload(plugin_id)` - Validation check
  - `get_history(plugin_id, limit)` - Reload history
  - `get_stats()` - Reload statistics
  - `add_to_blacklist()` / `remove_from_blacklist()` - Blacklist management
  - `register_callback()` / `unregister_callback()` - Event callbacks
- `HotReloadError` exception for reload failures
- `ReloadResult` dataclass with success/failure details
- `ReloadHistoryEntry` for history tracking
- Singleton pattern with `get_hot_reloader()`, `init_hot_reloader()`, `reset_hot_reloader()`
- Convenience functions: `reload_plugin()`, `can_reload_plugin()`, `get_reload_history()`, `get_reload_stats()`

### Features
- Graceful plugin shutdown during reload
- Module cache invalidation (unloads from sys.modules)
- Contribution re-registration (CLI, API, UI)
- Event emission (PLUGIN_RELOADED, PLUGIN_RELOAD_FAILED)
- Thread safety with per-plugin locks
- Blacklist for core plugins that cannot be reloaded
- History tracking with configurable max size
- Statistics (success rate, average duration)
- Callback system for reload notifications

### Tests
- 57 tests covering all functionality
- TestHotReloadError: Exception creation and serialization
- TestReloadResult: Result dataclass handling
- TestHotReloaderInit: Initialization and Bridge setup
- TestCanReload: Validation for various plugin states
- TestReloadFlow: Full reload lifecycle
- TestReloadErrors: Error handling for each phase
- TestReloadHistory: History tracking and filtering
- TestReloadStats: Statistics calculation
- TestBlacklist: Blacklist management
- TestCallbacks: Callback registration and invocation
- TestSingletonFunctions: Module-level functions
- TestConvenienceFunctions: Convenience wrappers
- TestThreadSafety: Lock management
- TestModuleUnloading: Module cache cleanup
