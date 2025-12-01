# Changelog - jupiter/core/quality/

## [Unreleased]

### Added
- Initial creation of `jupiter/core/quality/` package.
- `complexity.py`: Naive cyclomatic complexity estimation.
- `duplication.py`: Chunk-based code duplication detection.
- Duplication detection now records enclosing function names and code excerpts for each occurrence to make remediation actionable.

### Changed
- Duplication detector now preserves `end_line` for every occurrence and feeds that into the merged cluster builder so downstream consumers (Code Quality plugin, CLI summaries) can highlight the full duplicated block span instead of the original window size.
