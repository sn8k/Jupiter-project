# Changelog - jupiter/server/manager.py

## [Unreleased]

### Added
- Created `ProjectManager` class to manage project backends.
- Implemented initialization of connectors based on configuration.
- Added support for `local_fs` backend type using `LocalConnector`.
- Added placeholder for `remote_jupiter_api` backend type.
- Added `_resolve_local_path` plus a `refresh_for_root` helper so connectors can be rebuilt against the current root and relative paths stay anchored to the served project.
