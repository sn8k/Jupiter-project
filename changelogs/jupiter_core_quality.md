# Changelog - jupiter/core/quality/

## [Unreleased]

### Added
- Initial creation of `jupiter/core/quality/` package.
- `complexity.py`: Naive cyclomatic complexity estimation.
- `duplication.py`: Chunk-based code duplication detection.
- Duplication detection now records enclosing function names and code excerpts for each occurrence to make remediation actionable.
