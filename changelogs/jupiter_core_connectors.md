# Changelog - jupiter/core/connectors/

## [Unreleased]

### Added
- Created `jupiter.core.connectors` package.
- Defined `BaseConnector` abstract base class in `base.py`.
- Implemented `LocalConnector` in `local.py` for local filesystem operations.
- `LocalConnector` wraps `ProjectScanner`, `ProjectAnalyzer`, and `Runner` to provide a unified interface.
