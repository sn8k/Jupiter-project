# Changelog – jupiter/cli/command_handlers.py
- Introduced `ScanOptions`, `SnapshotOptions`, and `WorkflowServices` helpers so `scan`, `analyze`, and `ci` share the same plugin/scanner/cache pipeline.
- Added `_collect_scan_payload`, `_persist_scan_artifacts`, and `_evaluate_ci_thresholds` utilities to remove duplicated logic and keep snapshot handling consistent.
- Refactored the CI handler to reuse the standard workflow and expose uniform metrics/failure reporting.
- Centralized scan-option/service construction in `_build_services_from_args` to eliminate repeated argument blocks in `handle_scan` and `handle_analyze`.
