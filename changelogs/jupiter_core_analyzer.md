# Changelog – jupiter/core/analyzer.py
- Created `ProjectAnalyzer` to aggregate scan outputs by extension and size.
- Added `AnalysisSummary` dataclass with human-readable description helper.
- Added JSON serialization, average size computation, and tracking of the largest files in summaries.
- Integrated `jupiter.core.quality` modules to calculate complexity and duplication metrics.
- Updated `AnalysisSummary` to include `quality` dictionary and "most_complex" hotspot.
- Duplication refactoring hints now embed file:line occurrences (deduplicated) and preview them in the human-readable summary for clearer reports.
- Refactoring recommendations carry code excerpts and nearest function names so duplication reports point straight to actionable code blocks.

