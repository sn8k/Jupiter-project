# Changelog – jupiter/config/__init__.py
- Added `JupiterConfig` dataclass with defaults for host, port, and Meeting device key.
- Added `PluginsConfig` to manage enabled/disabled plugins via `jupiter.yaml`.
- Exported `PluginsConfig` to fix `ImportError`.
- Exported the new `LoggingConfig` helper so callers can type config objects while selecting log levels.

