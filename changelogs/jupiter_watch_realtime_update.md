# Changelog: Watch Real-time Functionality Enhancement

**Date:** 2025-12-01  
**Version:** Enhanced Watch according to specs_watch.md  
**Author:** AI Agent  

## Summary

Enhanced the Watch functionality in Jupiter to provide real-time monitoring of project analysis and execution, as specified in `TODOs/specs_watch.md`. The Watch panel now displays:

- **Live tracking of scans** with progress bar and file-by-file updates
- **Function analysis events** showing discovered functions in real-time
- **File change events** for modifications during watch mode
- **Simulation progress** for `simulate remove` operations
- **Real-time logs** from the analysis engine

## Changes

### 1. Core Events (`jupiter/core/events.py`)

Added new event types for real-time tracking:

- `WATCH_STARTED`, `WATCH_STOPPED`, `WATCH_CALLS_RESET` - Watch lifecycle
- `FILE_CHANGE` - File modifications
- `SCAN_PROGRESS`, `SCAN_FILE_PROCESSING`, `SCAN_FILE_COMPLETED` - Scan tracking
- `FUNCTION_ANALYZED` - Function discovery events
- `ANALYSIS_PROGRESS` - Analysis phase tracking
- `SIMULATE_STARTED`, `SIMULATE_PROGRESS`, `SIMULATE_COMPLETED` - Simulation events
- `LOG_MESSAGE` - Real-time log messages

### 2. Scanner (`jupiter/core/scanner.py`)

- Added `progress_callback` parameter to `ProjectScanner.__init__()`
- Modified `iter_files()` to emit progress events during scanning
- Modified `_process_single_file()` to emit `FUNCTION_ANALYZED` events when functions are discovered
- Events include: file path, progress percentage, function counts, function names

### 3. Local Connector (`jupiter/core/connectors/local.py`)

- Added `set_progress_callback()` method to allow external callers to inject a progress callback
- The callback is passed to `ProjectScanner` during scan operations

### 4. Watch Router (`jupiter/server/routers/watch.py`)

Added new broadcast functions:

- `broadcast_scan_progress()` - Emit scan progress events
- `broadcast_log_message()` - Emit log messages in real-time
- `create_scan_progress_callback()` - Factory function to create a callback for the scanner

### 5. Scan Router (`jupiter/server/routers/scan.py`)

- Integrated watch progress callback: when Watch is active, the scan endpoint now sets up a progress callback on the connector to emit real-time events

### 6. Web UI - HTML (`jupiter/web/index.html`)

Enhanced the watch panel with:

- Progress bar section with label, percentage, and detail text
- Stats grid showing: files scanned, functions found, events count, dynamic calls
- Events container with clear button
- i18n support for all labels

### 7. Web UI - CSS (`jupiter/web/styles.css`)

Added styles for:

- Watch panel with accent border and gradient background
- Progress bar with gradient fill and animation
- Stats grid with responsive layout
- Events list with styled entries
- Pulse animation for active status badge

### 8. Web UI - JavaScript (`jupiter/web/app.js`)

Enhanced state and functions:

- Extended `state.watch` with: `filesScanned`, `functionsFound`, `currentFile`, `progress`, `phase`
- Added WebSocket handlers for new event types
- New functions:
  - `updateWatchPanel()` - Update panel visibility and status
  - `updateWatchProgress()` - Update progress bar
  - `addWatchEvent()` - Add styled events to the list
  - `clearWatchEvents()` - Clear the events list
- Enhanced `updateWatchStats()` to update new UI elements

### 9. Localization

Updated `jupiter/web/lang/fr.json` and `jupiter/web/lang/en.json` with:

- `watch_eyebrow`, `watch_title`, `watch_subtitle`
- `watch_files_scanned`, `watch_functions_found`
- `watch_total_events`, `watch_call_count`
- `watch_events_title`

## Usage

1. Click the **Watch** button in the top bar to start watching
2. The watch panel appears on the dashboard with:
   - A progress bar showing scan progress
   - Live stats (files scanned, functions found, events)
   - A scrolling event log showing real-time activity
3. Run a **Scan** while Watch is active to see:
   - Per-file scanning progress
   - Function discovery events
   - Completion notification
4. Use **Run** with dynamic analysis to track function calls
5. Click the trash icon to clear the event log
6. Click **Watch** again to stop watching

## Technical Notes

- Events are throttled (every 10th file) to avoid flooding the WebSocket
- The progress callback is synchronous but uses `asyncio.ensure_future()` to queue async broadcasts
- The watch panel persists on screen briefly after stopping to show final state
- All events include timestamps for debugging

## Related Files

- `TODOs/specs_watch.md` - Original specification
- `jupiter/core/events.py` - Event types
- `jupiter/core/scanner.py` - Scanner with progress callback
- `jupiter/core/connectors/local.py` - Local connector with callback support
- `jupiter/server/routers/watch.py` - Watch API and broadcast helpers
- `jupiter/server/routers/scan.py` - Scan integration
- `jupiter/web/index.html` - Watch panel HTML
- `jupiter/web/styles.css` - Watch panel styles
- `jupiter/web/app.js` - Watch panel logic
- `jupiter/web/lang/*.json` - Translations
