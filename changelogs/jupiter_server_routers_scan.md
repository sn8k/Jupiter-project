# Changelog – jupiter/server/routers/scan.py

## Version 1.3.1 – Event Loop Fix
- Fixed "no running event loop" error in background scan
- Replaced `BackgroundTasks` with `asyncio.create_task` for proper async execution
- Fixed thread-safe WebSocket broadcast in progress callback using `run_coroutine_threadsafe`
- Added proper error handling for WebSocket broadcast failures

## Version 1.3.0 – Background Scan Support
- Added background scan system for non-blocking scans:
  - `POST /scan/background`: Start a scan in background, returns immediately with job ID
  - `GET /scan/status/{job_id}`: Check status of a background scan job
  - `GET /scan/status`: Get current running scan status
  - `GET /scan/result/{job_id}`: Fetch result of completed background scan
- Added `BackgroundScanJob` class to track scan jobs with progress info
- Added `ScanStatus` enum (PENDING, RUNNING, COMPLETED, FAILED)
- Progress updates broadcast via WebSocket during background scan
- Original `/scan` endpoint preserved for backward compatibility
- Auto-cleanup of old completed jobs (keeps last 10)

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
