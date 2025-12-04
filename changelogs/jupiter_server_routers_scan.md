# Changelog – jupiter/server/routers/scan.py

## Version 1.2.0 – Phase 1.4: Bridge Event Integration
- Added import of Bridge event emitters (`emit_scan_started`, `emit_scan_finished`, `emit_scan_error`)
- Added `import time` for scan duration measurement
- `POST /scan` now emits Bridge events alongside WebSocket broadcasts:
  - `emit_scan_started(root, options)` at scan start
  - `emit_scan_finished(root, file_count, duration_ms)` on success
  - `emit_scan_error(root, error)` on failure
- These events allow plugins to subscribe to scan lifecycle events

## Version 1.1.0 – Phase 2: Handler Introspection
- Added `handlers` field to `/api/endpoints` response with FastAPI route handler info
- Added `get_registered_handlers(app)` function to extract route handler details:
  - `path`, `methods`, `handler_name`, `handler_module`, `handler_qualname`
- Added version docstring header

## Previous Changes
- Removed duplicate `_history_manager` implementation and now reuse `SystemState.history_manager()` for snapshot creation.
- Added fallback to apply active project's `ignore_globs` when scan requests omit patterns.
