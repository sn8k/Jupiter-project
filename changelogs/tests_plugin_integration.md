# Changelog - tests/test_plugin_integration.py

## Version 0.3.0

### Added
- Scenario 7: Hot Reload with Dev Mode Guard integration tests
  - `test_hot_reload_blocked_without_dev_mode` - verify reload fails when dev mode disabled
  - `test_hot_reload_allowed_with_dev_mode` - verify reload proceeds with dev mode
  - `test_can_reload_checks_dev_mode_first` - verify dev mode check is first
  - `test_skip_dev_mode_check_for_testing` - verify bypass parameter works
- Scenario 8: API Integration tests
  - `test_plugin_api_registry_integration` - verify API route registration
  - `test_plugin_permissions_checked` - verify permission checking

### Changed
- Total integration tests: 22

## Version 0.2.0

### Added
- Scenario 6: Jobs with Cancellation tests (Phase 11.1)
  - `test_job_submit_and_complete`
  - `test_job_cancellation`
  - `test_job_with_failure`
  - `test_job_progress_tracking`
  - `test_job_stats`
  - `test_circuit_breaker_integration`
  - `test_job_list_and_filter`

## Version 0.1.0

### Added
- Initial integration tests for plugin system
- Scenario 1: Install Plugin from Scratch
- Scenario 2: Full Plugin Usage (CLI)
- Scenario 3: Plugin Update with Rollback
- Scenario 4: Failure and Recovery
- Scenario 5: Performance Tests
