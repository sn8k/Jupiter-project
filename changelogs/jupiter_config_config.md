# Changelog – jupiter/config/config.py

- Added `project_root` field to `JupiterConfig` dataclass to fix `TypeError` in `load_config`.
- Added `PluginsConfig` dataclass.
- Added `ProjectBackendConfig` dataclass for defining project backends.
- Added `backends` list to `JupiterConfig` to support multiple project backends.
- Updated `from_dict` and `save_config` to handle backend configuration.
