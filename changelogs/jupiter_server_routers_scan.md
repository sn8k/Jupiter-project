# Changelog – jupiter/server/routers/scan.py
- Removed duplicate `_history_manager` implementation and now reuse `SystemState.history_manager()` for snapshot creation.
- Added fallback to apply active project's `ignore_globs` when scan requests omit patterns.
