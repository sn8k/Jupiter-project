# Changelog – jupiter/core/bridge/monitoring.py

## Version 0.1.0

### Added
- Initial implementation of monitoring and limits system
- **Audit Logging**:
  - `AuditEventType` enum with comprehensive event types:
    - Plugin lifecycle: INSTALLED, UNINSTALLED, ENABLED, DISABLED, RELOADED
    - Security: PERMISSION_GRANTED, PERMISSION_DENIED, SIGNATURE_VERIFIED
    - Jobs: SUBMITTED, COMPLETED, FAILED, CANCELLED
    - Circuit breaker: OPENED, CLOSED, RESET
    - Commands, file system, network, API events
  - `AuditEntry` dataclass with timestamp, plugin_id, user, details, success/error
  - `AuditLogger` class:
    - `log()` - Record audit events
    - `get_entries()` - Query with filters (event_type, plugin_id, since, success_only)
    - `get_stats()` - Aggregate statistics
    - Event handlers support for external integrations
    - Configurable max entries with automatic pruning

- **Timeout Management**:
  - `TimeoutConfig` dataclass with configurable timeouts:
    - plugin_load/unload/start/stop
    - job_default/job_max
    - health_check, api_request, file_read/write, network_request
  - Per-plugin timeout overrides
  - `TimeoutError` exception with operation and timeout info
  - `with_timeout()` - Async timeout wrapper
  - `sync_with_timeout()` - Sync timeout wrapper with threads

- **Rate Limiting**:
  - `RateLimitConfig` dataclass (requests, window_seconds, burst)
  - `RateLimiter` class with token bucket algorithm:
    - `check()` - Check if operation allowed
    - `get_remaining()` - Get remaining tokens
    - `reset()` - Reset rate limits
    - Per-plugin rate limit configuration
    - Automatic token refill over time

- **PluginMonitor** central class:
  - Combines audit, timeouts, and rate limiting
  - `enabled` flag to disable monitoring
  - Convenience methods: `log()`, `check_rate()`, `get_timeout()`
  - `get_stats()` for monitoring overview

- Module-level functions:
  - `get_monitor()` / `init_monitor()` / `reset_monitor()` - Singleton management
  - `audit_log()` - Convenience audit logging
  - `check_rate_limit()` - Convenience rate checking
  - `get_timeout()` - Convenience timeout lookup

- 50 comprehensive tests
