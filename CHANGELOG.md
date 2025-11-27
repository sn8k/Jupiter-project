# Changelog

## 0.1.0 – Initial scaffolding
- Established Jupiter Python package with core scanning, analysis, and reporting primitives.
- Added CLI entrypoint supporting `scan`, `analyze`, and server stubs.
- Introduced server placeholders for API hosting and Meeting integration.
- Documented usage in README and Manual; created per-file changelogs.

## 0.1.1 – CLI exclusions and richer analysis
- Added glob-based ignore handling (including `.jupiterignore`) to the scanner and CLI.
- Extended analysis summaries with average size and top N largest files, plus JSON export.
- Documented new CLI flags, exclusion behavior, and report persistence in the README and Manual.
