# Changelog - jupiter/core/bridge/alerting.py

## [0.1.0]

### Added
- Initial implementation of threshold-based alerting system
- `ComparisonOperator` enum: gt, gte, lt, lte, eq, neq
- `AlertSeverity` enum: info, warning, error, critical
- `AlertState` enum: pending, firing, resolved, acknowledged, silenced
- `AlertThreshold` dataclass:
  - Configurable threshold_id, plugin_id, metric_name
  - Comparison operator and threshold_value
  - Cooldown period to prevent notification storms
  - notify_on_recovery option
  - `evaluate(value)` method for threshold checking
  - `can_trigger()` method for cooldown checking
  - Serialization via `to_dict()` and `from_dict()`
- `Alert` dataclass:
  - Alert instance with metric details
  - State management: acknowledge(), resolve(), silence()
  - Timestamps for creation, resolution, acknowledgment
  - Serialization support
- `AlertingManager` class:
  - `add_threshold()`, `remove_threshold()`, `get_threshold()`
  - `list_thresholds()` with plugin_id and enabled_only filters
  - `enable_threshold()`, `disable_threshold()`
  - `check_metric()` to evaluate against thresholds
  - `check_all_from_metrics_collector()` integration
  - Alert management: `list_alerts()`, `acknowledge_alert()`, `resolve_alert()`, `silence_alert()`
  - Alert history with configurable max size
  - Statistics tracking
  - Persistence to JSON file
  - Notification callback support
- Default thresholds:
  - `high_error_rate`: error_count > 10 (warning)
  - `critical_error_rate`: error_count > 50 (critical)
  - `low_request_count`: request_count < 1 (info, disabled by default)
- Global functions:
  - `get_alerting_manager()`, `init_alerting_manager()`, `reset_alerting_manager()`
  - `add_threshold()`, `remove_threshold()`
  - `check_metric()`, `check_all()`
  - `list_alerts()`, `acknowledge_alert()`
- Tests: 53 tests in tests/test_bridge_alerting.py
