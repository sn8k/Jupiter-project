# Changelog: jupiter/core/bridge/dev_mode.py

## Version 0.1.1

### Fixed
- Adjusted `PluginFileHandler.on_modified` to accept the base `FileSystemEvent`, keeping the watchdog override signature compatible while still ignoring directory events in practice.

## Version 0.1.0

### Added
- Initial implementation of developer mode module
- `DevModeConfig` dataclass for developer mode configuration:
  - `enabled`: Enable/disable developer mode
  - `allow_unsigned_plugins`: Allow loading unsigned plugins
  - `skip_signature_verification`: Skip signature verification
  - `allow_all_permissions`: Auto-grant all permissions
  - `verbose_logging`: Enable DEBUG logging
  - `log_level`: Configurable log level
  - `disable_rate_limiting`: Disable rate limiting
  - `enable_hot_reload`: Enable hot reload feature
  - `auto_reload_on_change`: Auto-reload on file changes
  - `watch_dirs`: Directories to watch
  - `enable_test_console`: Enable test console
  - `enable_debug_endpoints`: Enable debug API endpoints
  - `enable_profiling`: Enable profiling
  - `profile_plugin_loads`: Profile plugin loading
- `DevModeConfig.to_dict()` for serialization
- `DevModeConfig.from_dict()` for deserialization
- `PluginFileHandler` for file system event handling:
  - Watches Python files for changes
  - Debounced reload scheduling
  - Plugin-to-path mapping
- `DeveloperMode` class for managing dev mode:
  - `enable()` / `disable()` methods
  - Security bypass methods:
    - `should_allow_unsigned()`
    - `should_skip_signature_verification()`
    - `should_allow_all_permissions()`
    - `should_disable_rate_limiting()`
  - Debug feature methods:
    - `is_test_console_enabled()`
    - `is_debug_endpoints_enabled()`
    - `is_profiling_enabled()`
  - Plugin watching:
    - `watch_plugin()`
    - `unwatch_plugin()`
  - Auto-reload:
    - `schedule_reload()`
    - `add_reload_callback()`
    - `remove_reload_callback()`
    - `get_pending_reloads()`
    - `clear_pending_reload()`
  - Logging control:
    - `_apply_logging_settings()`
    - `_restore_logging_settings()`
  - Status and stats:
    - `get_stats()`
    - `get_status()`
- Global instance management:
  - `get_dev_mode()`
  - `init_dev_mode()`
  - `reset_dev_mode()`
- Convenience functions:
  - `is_dev_mode()`
  - `enable_dev_mode()`
  - `disable_dev_mode()`
  - `get_dev_mode_status()`
- File watching with watchdog library
- Thread-safe implementation with locks
- Production safety (all bypasses disabled when dev mode is off)
- 61 unit tests covering all functionality
