# Changelog - jupiter/web/js/logs_panel.js

## v0.2.0
### Added
- Rate limiting for incoming logs to prevent UI flooding
  - `enableRateLimit` option (default: true)
  - `rateLimitMs` option (default: 50ms)
  - `batchSize` option (default: 10)
- Batch processing of pending logs
- Message truncation for long log messages
  - `truncateLongMessages` option (default: true)
  - `maxMessageLength` option (default: 500)
- ZIP compression for log export using JSZip if available
- Gzip compression fallback using CompressionStream API
- `getLogsPerSecond()` method for rate monitoring
- `getPendingCount()` method for queue monitoring
- `setRateLimit()` method for runtime configuration
- `setTruncation()` method for runtime configuration
- `_scheduleProcessBatch()` method
- `_processBatch()` method
- `_processLogEntry()` method
- Rate limiting state variables

### Changed
- `addLog()` now supports rate limiting with batch processing
- Enhanced `downloadZip()` to use JSZip or CompressionStream when available
- Improved log entry handling with truncation support

## v0.1.0
### Added
- Initial release
- WebSocket connection for real-time log streaming
- Log level filtering (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Text search within logs
- Pause/resume streaming
- Auto-scroll with toggle
- Download logs as .log or .txt files
- Tail N last lines display
- Plugin-specific log filtering
- Log entry normalization
- Automatic reconnection on disconnect
- Line count display
- Manual scroll detection
