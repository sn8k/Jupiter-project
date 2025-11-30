# Changelog - Jupiter UI Launch Fix

## [0.1.9] - 2024-10-27

### Fixed
- **Launch Script**: Updated `Jupiter UI.cmd` to explicitly pass the script's directory as the root (`--root "%~dp0"`). This ensures that the `jupiter.yaml` located next to the script is loaded on startup, fixing the issue where settings were ignored if the last used root was different.
- **CLI**: Added `--root` argument to the top-level CLI parser to support the above fix.
- **Config Persistence**: Updated `update_root` in the API to preserve the Meeting configuration (Device Key & Enabled state) when switching to a project root that doesn't have its own configuration. This prevents the license from being dropped when browsing projects.
