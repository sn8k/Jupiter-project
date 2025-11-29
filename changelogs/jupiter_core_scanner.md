# Changelog – jupiter/core/scanner.py
- Added `ProjectScanner` to enumerate project files with optional hidden filtering.
- Added `FileMetadata` dataclass to capture size and timestamps.
- Added glob-based ignore support with automatic `.jupiterignore` loading.
- Switched to `os.walk` with in-place `dirnames` pruning for efficient directory exclusion (e.g. `venv`, `node_modules`).
- Added incremental scan support using `CacheManager`.
