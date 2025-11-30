# Changelog – jupiter/server/system_services.py
- Added `SystemState` wrapper to centralize merged config loading, saving, and runtime rebuild logic (root path, Meeting adapter, ProjectManager, PluginManager, HistoryManager).
- Added `preserve_meeting_config` helper to carry the license key across root switches when the new config lacks one.
- Runtime rebuild now applies the configured `logging.level` across root, API, and plugin services to keep verbosity consistent.
- Runtime rebuild now forwards the optional `logging.path` to `configure_logging` so file handlers are attached when a destination is provided.
