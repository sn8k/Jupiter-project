# Changelog – jupiter/config/config.py

- Added `project_root` field to `JupiterConfig` dataclass to fix `TypeError` in `load_config`.
- Added `PluginsConfig` dataclass.
- Added `ProjectBackendConfig` dataclass for defining project backends.
- Added `backends` list to `JupiterConfig` to support multiple project backends.
- Updated `from_dict` and `save_config` to handle backend configuration.
- Introduced `LoggingConfig` with persisted `logging.level` and wired save helpers to write the log level in both global and project YAML updates.
- Introduced explicit config naming helpers (`<project>.jupiter.yaml`, `global_config.yaml`) with legacy fallbacks, plus install/project path resolution helpers reused by save/load utilities.
- Logging config now supports an optional `path` persisted across global/project saves for the Settings log destination field.
- Global registry load now normalizes legacy entries (`jupiter.yaml` -> `<project>.jupiter.yaml` and absolute paths) and auto-saves the cleaned structure to keep project activation/deletion reliable across upgrades.
- Fixed `load_merged_config` to always load project config (even when install_path == project_path). This ensures project-specific settings like `project_api` are loaded at server startup, not just after saving via UI.
