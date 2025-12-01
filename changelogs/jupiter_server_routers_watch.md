# Changelog - jupiter/server/routers/watch.py

## 2025-12-01 - Initial implementation
- Created `/watch/start` endpoint to start watching for function calls and file changes.
- Created `/watch/stop` endpoint to stop watching and return final statistics.
- Created `/watch/status` endpoint to get current watch status.
- Created `/watch/calls` endpoint to get current function call counts.
- Created `/watch/calls/reset` endpoint to reset call counts.
- Added `WatchState` dataclass to hold global watch state.
- Added `record_function_calls()` async function to record calls from dynamic analysis runs.
- Added `broadcast_file_change()` async function for future file change notifications.
- Integrated with WebSocket manager to broadcast `FUNCTION_CALLS`, `WATCH_STARTED`, `WATCH_STOPPED`, `WATCH_CALLS_RESET`, and `FILE_CHANGE` events.
- When `run` command is executed with `with_dynamic=true`, function calls are automatically recorded if watch is active.
