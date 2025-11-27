# Changelog – jupiter/core/analyzer.py
- Created `ProjectAnalyzer` to aggregate scan outputs by extension and size.
- Added `AnalysisSummary` dataclass with human-readable description helper.
- Added JSON serialization, average size computation, and tracking of the largest files in summaries.
