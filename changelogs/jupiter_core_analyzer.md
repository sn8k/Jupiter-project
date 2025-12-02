# Changelog – jupiter/core/analyzer.py

## Version 1.1.0 (2025-12-02) – Phase 2: Confidence Scoring
- Added `FunctionUsageStatus` enum with values: `USED`, `LIKELY_USED`, `POSSIBLY_UNUSED`, `UNUSED`
- Added `FunctionUsageInfo` dataclass for detailed function usage tracking with confidence scores
- Added `compute_function_confidence()` function with scoring logic:
  - Directly called: USED (1.0)
  - Framework decorator: LIKELY_USED (0.95)
  - Dynamically registered: LIKELY_USED (0.90)
  - Known pattern: LIKELY_USED (0.85)
  - Private function: POSSIBLY_UNUSED (0.55-0.65)
  - Public no usage: UNUSED (0.75)
- Updated `PythonProjectSummary` with:
  - `function_usage_details`: List of non-USED functions with scores
  - `usage_summary`: Count per status
- Updated `summarize()` to compute confidence scores for all Python functions

## Previous Changes
- Created `ProjectAnalyzer` to aggregate scan outputs by extension and size.
- Added `AnalysisSummary` dataclass with human-readable description helper.
- Added JSON serialization, average size computation, and tracking of the largest files in summaries.
- Integrated `jupiter.core.quality` modules to calculate complexity and duplication metrics.
- Updated `AnalysisSummary` to include `quality` dictionary and "most_complex" hotspot.
- Duplication refactoring hints now embed file:line occurrences (deduplicated) and preview them in the human-readable summary for clearer reports.
- Refactoring recommendations carry code excerpts and nearest function names so duplication reports point straight to actionable code blocks.
