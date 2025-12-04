# Changelog - jupiter/core/bridge/jobs.py

## Version 0.3.0 - Job Export

### Added
- **Job Export Functionality**:
  - `export_job()` method on JobManager:
    - Export single job to JSON or YAML file
    - Returns dict when no output_path provided
    - Includes full job data: id, name, status, result, metadata, timestamps
    - Raises ValueError if job not found
    - Creates parent directories if needed
  - `export_jobs()` method on JobManager:
    - Export multiple jobs to file
    - Filter by status and/or plugin_id
    - Supports JSON and YAML formats
    - Optional include_results flag
    - Export data includes: exported_at, total_jobs, filters, jobs array
  - `_build_export_data()` helper method
  - `_write_export_file()` helper method
- **Module-level convenience functions**:
  - `export_job(job_id, output_path, format)` → Dict or Path
  - `export_jobs(output_path, status, plugin_id, format, include_results)` → Path
- 12 new tests for job export functionality

## Version 0.2.0 - Circuit Breaker

### Added
- **Circuit Breaker System** for plugin failure management
  - `CircuitState` enum: CLOSED, OPEN, HALF_OPEN
  - `CircuitBreaker` dataclass:
    - Track consecutive failures per plugin
    - Configurable failure threshold and cooldown
    - Automatic state transitions (closed → open → half-open → closed)
    - `can_execute()` to check if requests allowed
    - `record_success()` / `record_failure()` to update state
    - `reset()` for manual recovery
    - Statistics: total_calls, total_failures, times_opened
  - `CircuitBreakerRegistry` class:
    - Manage circuit breakers per plugin
    - `get_or_create()` with default or custom thresholds
    - `list_open()` to find problematic plugins
    - `reset_all()` for bulk recovery
    - `get_stats()` for summary statistics
- **JobManager Circuit Breaker Integration**:
  - New constructor params: `circuit_breaker_threshold`, `circuit_breaker_cooldown`, `enable_circuit_breaker`
  - `submit()` checks circuit breaker before job submission
  - `bypass_circuit_breaker` flag to skip check
  - Automatic success/failure recording on job completion
  - New methods:
    - `get_circuit_breaker()` / `get_circuit_breaker_state()`
    - `is_circuit_open()` to check plugin status
    - `reset_circuit_breaker()` / `reset_all_circuit_breakers()`
    - `list_open_circuits()` to find problematic plugins
    - `get_circuit_breaker_stats()` / `get_all_circuit_breakers()`
- Updated `init_job_manager()` with circuit breaker params
- 42 new tests for circuit breaker functionality

## Version 0.1.0
- Initial implementation of Bridge Job Management System
- Created `JobManager` class with:
  - `submit()` for async/sync job submission
  - `cancel()` for job cancellation
  - `get()` for retrieving single job
  - `list()` for listing jobs with filters
  - `get_stats()` for job statistics
  - `clear_history()` to remove completed jobs
- Created `Job` dataclass with:
  - id, name, status, progress, result, error
  - Timestamps: created_at, started_at, completed_at
  - Plugin association and metadata support
  - `to_dict()` serialization with duration calculation
- Created `JobStatus` enum (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
- Supports both async and sync job functions
- Concurrency control with configurable max_concurrent
- History limit with automatic pruning
- Event emission for job lifecycle (started, progress, completed, failed, cancelled)
- Thread-safe with Lock for concurrent access
- Global convenience functions: `submit_job()`, `cancel_job()`, `get_job()`, `list_jobs()`
