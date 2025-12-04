# Changelog - jupiter/core/bridge/metrics.py

## Version 0.1.0
- Initial implementation of Bridge Metrics Collection System
- Created `MetricsCollector` class with:
  - `record()` for recording gauge/counter/histogram metrics
  - `increment()` for counter convenience
  - `gauge()` for gauge convenience
  - `timing()` for timing/duration metrics
  - `get_metric()` for single metric summary
  - `get_metric_history()` for historical data points
  - `get_all_metrics()` for complete metrics export
  - `collect_plugin_metrics()` for IPluginMetrics collection
  - `to_prometheus()` for Prometheus format export
  - `reset()` to clear all metrics
- Created dataclasses: `MetricPoint`, `MetricSummary`
- Created `MetricType` enum (COUNTER, GAUGE, HISTOGRAM, SUMMARY)
- Created `TimingContext` context manager for automatic timing
- Created `@timed` decorator for function timing
- Global convenience functions: `record_metric()`, `increment_counter()`, `record_timing()`
- Thread-safe with Lock for concurrent access
- Configurable history size per metric
