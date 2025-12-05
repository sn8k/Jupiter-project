# Changelog – tests/test_plugin_integration.py

## v0.2.0
- Added TestScenarioJobsCancellation with 7 tests:
  - test_job_submit_and_complete: Job submission and successful completion
  - test_job_cancellation: Cancel running job
  - test_job_with_failure: Handle job failure
  - test_job_progress_tracking: Track progress updates
  - test_job_stats: Statistics accuracy
  - test_circuit_breaker_integration: Circuit breaker opens after failures
  - test_job_list_and_filter: List and filter jobs by plugin/status
- Total: 16 integration tests

## v0.1.0
- Initial integration test scenarios for plugin system (Phase 11.1)
- TestScenarioInstallFromScratch: Tests install → validate → register flow
- TestScenarioInstallFromScratch: Tests signature verification during install
- TestScenarioFullUsage: Tests CLI command registration by plugins
- TestScenarioFullUsage: Tests event bus integration (subscribe/emit)
- TestScenarioUpdateWithRollback: Tests backup creation during updates
- TestScenarioUpdateWithRollback: Tests rollback on update failure
- TestScenarioFailureRecovery: Tests invalid plugin rejection
- TestScenarioFailureRecovery: Tests uninstall preserves other plugins
- TestScenarioPerformance: Tests bulk event emission performance
- All 9 integration tests passing
