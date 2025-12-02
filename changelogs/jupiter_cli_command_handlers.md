# Changelog – jupiter/cli/command_handlers.py

## Version 1.1.0 (2025-12-02) – Phase 4: Autodiag Handler
- Added `handle_autodiag()` function for the `jupiter autodiag` command
- Supports options: as_json, api_url, diag_url, skip_cli, skip_api, skip_plugins, timeout
- Prints human-readable report with status, metrics, false positives, and recommendations
- Returns exit codes: 0=success, 1=partial/issues, 2=failed

## Previous Changes
- Introduced `ScanOptions`, `SnapshotOptions`, and `WorkflowServices` helpers so `scan`, `analyze`, and `ci` share the same plugin/scanner/cache pipeline.
- Added `_collect_scan_payload`, `_persist_scan_artifacts`, and `_evaluate_ci_thresholds` utilities to remove duplicated logic and keep snapshot handling consistent.
- Refactored the CI handler to reuse the standard workflow and expose uniform metrics/failure reporting.
- Centralized scan-option/service construction in `_build_services_from_args` to eliminate repeated argument blocks in `handle_scan` and `handle_analyze`.
