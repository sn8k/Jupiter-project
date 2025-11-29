# Changelog - Fix Tests

## [Unreleased]

### Fixed
- Fixed `tests/test_integration.py` to properly initialize `ProjectManager` with `JupiterConfig` and `ProjectBackendConfig`.
- Fixed `tests/test_scan.py` to access `FileMetadata.path.name` instead of `FileMetadata.name`.
- Fixed `tests/test_analyze.py` to use `summary.file_count` instead of `summary.total_files`.
- Fixed `tests/test_api.py` to check specific fields in `/health` response.
- Fixed `tests/test_cache.py` to check for file existence instead of directory existence after clear.
- Fixed `tests/test_dynamic.py` to use `os.path.abspath` and `os.path.join` for cross-platform path compatibility in mocks.
