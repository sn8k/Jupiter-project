# Changelog – jupiter/server/models.py

**Section 1 Implementation (API Stabilization & Schemas)**

- Created comprehensive Pydantic models module to formalize API contracts.
- **Request models**: `ScanRequest`, `RunRequest` for input validation.
- **Response models**: `ScanReport`, `RunResponse`, `AnalyzeResponse`, `MeetingStatus` for consistent serialization.
- **Supporting models**: `FileAnalysis`, `Hotspot`, `PythonProjectSummary`, `HealthStatus`, `RootUpdateResponse`, `FSListResponse`, `FSListEntry`.
- All models include detailed Field descriptions for OpenAPI documentation.
- Ensures strong typing throughout the API layer.
- Extended `ConfigModel` with a `log_level` field so settings can drive server verbosity.
- Added optional `log_path` to `ConfigModel` so the Settings page can persist the log destination path.
- `RefactoringRecommendation` now carries optional `locations` (path + line) so duplication suggestions surface precise evidence in API responses.
- Added optional `code_excerpt` to `RefactoringRecommendation` so responses can include a snippet of the duplicated block.
