# Changelog – jupiter/server/routers/scan.py

## Version 1.1.0 (2025-12-02) – Phase 2: Handler Introspection
- Added `handlers` field to `/api/endpoints` response with FastAPI route handler info
- Added `get_registered_handlers(app)` function to extract route handler details:
  - `path`, `methods`, `handler_name`, `handler_module`, `handler_qualname`
- Added version docstring header

## Previous Changes
- Removed duplicate `_history_manager` implementation and now reuse `SystemState.history_manager()` for snapshot creation.
- Added fallback to apply active project's `ignore_globs` when scan requests omit patterns.
