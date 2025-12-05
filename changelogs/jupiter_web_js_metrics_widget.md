# Changelog - jupiter/web/js/metrics_widget.js

## v0.1.0
- Initial creation of MetricsWidget module
- Real-time metrics dashboard with auto-refresh
- System and plugin metrics scope switching
- Key metrics cards (plugins loaded, requests/sec, CPU, memory, latency, errors)
- Sparkline mini-charts for historical data
- Metrics history tracking with configurable buffer
- Threshold-based alerting (warning/critical levels)
- Trend indicators (up/down arrows)
- Value formatting (bytes, duration, percentage, numbers)
- Canvas-based chart rendering
- Configurable refresh interval
- Integration with jupiterBridge API
- Gradient-filled sparklines matching dark theme

## v0.1.1
- Infer API base to hit the API port (8000) when GUI/diag ports are used.
- Fetch metrics from `/metrics` and `/metrics/bridge` instead of invalid `/plugins` path.
