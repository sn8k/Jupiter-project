# Changelog – jupiter/core/report.py

**Section 1 Implementation (API Stabilization & Schemas)**

- Renamed `dynamic_analysis` field to `dynamic` for consistency with API schema.
- Added explicit `schema_version` field (default "1.0") to track report format version.
- Updated `to_dict()` method to use the new field names.
- Improved docstring to reflect the updated schema structure.

**Previous entries**

- Added `ScanReport` to serialize scanner findings for CLI and API layers.
