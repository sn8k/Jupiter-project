# Changelog - Metrics Manager Plugin

All notable changes to the Metrics Manager plugin will be documented in this file.

## [1.0.2] - API URL Fix

### Fixed
- Fixed all API URLs in WebUI panel to use `bridge.api.get()` and `bridge.api.post()`
- Changed paths from `/api/v1/plugins/metrics_manager/*` to `/metrics_manager/*`
- Now consistent with other v2 plugins like `ai_helper`
- Metrics should now load properly in the WebUI

## [1.0.1] - Manifest Fix

### Fixed
- Corrected plugin.yaml manifest to match Bridge v2 schema
- Removed non-standard properties (`settings_frame`, `monitoring`, `governance`)
- Simplified config schema (removed unsupported keywords like `minimum`, `maximum`, `title`, `description`)
- Added missing `cli.commands: []` entry
- Plugin now properly appears in WebUI sidebar menu

## [1.0.0] - Initial Release

### Added
- Initial implementation of the Metrics Manager plugin
- Core functionality:
  - Integration with `jupiter.core.bridge.metrics.MetricsCollector`
  - Real-time metrics collection and display
  - System metrics monitoring (uptime, collected metrics, unique metrics, counters)
  - Plugin metrics aggregation and display
  
- API endpoints:
  - `GET /all` - Retrieve all collected metrics
  - `GET /system` - System-level metrics only
  - `GET /plugins` - Plugin metrics only
  - `GET /counters` - Counter metrics
  - `GET /history/{name}` - Historical data points for a metric
  - `GET /export` - Export metrics (JSON/Prometheus format)
  - `POST /record` - Record custom metrics
  - `POST /reset` - Reset all metrics
  - `GET /alerts` - Active alerts
  - `DELETE /alerts` - Clear all alerts
  - `GET /stream` - SSE endpoint for real-time metrics
  - Standard plugin endpoints (health, metrics, logs, changelog)

- WebUI Panel:
  - System metrics dashboard with metric cards
  - Alert management section
  - Counters and gauges tables
  - Metric history chart with canvas rendering
  - Plugin metrics accordion view
  - Real-time log streaming with filtering
  - Plugin statistics sidebar
  - Help documentation panel

- Configuration:
  - Configurable refresh intervals
  - Alert threshold settings (error rate, response time)
  - Export format selection (JSON/Prometheus)
  - Chart type preferences (line/bar/area)
  - History size configuration

- i18n Support:
  - English translations
  - French translations
  - All UI text externalized to language files

### Technical Details
- Follows Bridge v2 plugin architecture (plugins_architecture.md v0.6.0)
- Implements standard lifecycle hooks: init(), shutdown(), health(), metrics()
- Event bus integration for metric recording events
- Thread-safe metric collection
- SSE-based real-time streaming for logs and metrics

### Dependencies
- jupiter.core.bridge.metrics (MetricsCollector)
- FastAPI for API routes
- No external JavaScript libraries (pure canvas charts)
