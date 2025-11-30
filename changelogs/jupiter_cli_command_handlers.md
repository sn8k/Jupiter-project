# Changelog – jupiter/cli/command_handlers.py
- Introduced `ScanOptions`, `SnapshotOptions`, and `WorkflowServices` helpers so `scan`, `analyze`, and `ci` share the same plugin/scanner/cache pipeline.
- Added `_collect_scan_payload`, `_persist_scan_artifacts`, and `_evaluate_ci_thresholds` utilities to remove duplicated logic and keep snapshot handling consistent.
- Refactored the CI handler to reuse the standard workflow and expose uniform metrics/failure reporting.
