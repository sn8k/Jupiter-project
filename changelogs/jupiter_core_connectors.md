# Changelog - jupiter/core/connectors/

## [Unreleased]

### Added
- Created `jupiter.core.connectors` package.
- Defined `BaseConnector` abstract base class in `base.py`.
- Implemented `LocalConnector` in `local.py` for local filesystem operations.
- `LocalConnector` wraps `ProjectScanner`, `ProjectAnalyzer`, and `Runner` to provide a unified interface.

### Changed
- `RemoteConnector` now centralizes HTTP calls through `_request_json` to remove duplicate request/raise patterns across endpoints.
- Local and remote scans/analyze calls can now consume project-level ignore globs (wired through server routers).
