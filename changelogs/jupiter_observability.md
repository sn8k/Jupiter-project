# Changelog - Jupiter Observability

## [Unreleased]

### Added
- **Metrics Endpoint**: `GET /metrics` exposes system statistics (scan counts, averages, plugin status).
- **Structured Events**: WebSocket now broadcasts typed `JupiterEvent` objects (e.g., `SCAN_STARTED`, `RUN_FINISHED`).
- **Metrics Collector**: New `MetricsCollector` class in `jupiter.core.metrics`.
- **Event Definitions**: `jupiter.core.events` defines standard event types.

### Changed
- **WebSocket**: Updated `broadcast` to handle `JupiterEvent` serialization.
- **Notifications Plugin**: Updated to consume structured events and map them to webhook payloads.
- **API**: `post_scan`, `post_run`, `update_config`, `toggle_plugin` now emit structured events.
