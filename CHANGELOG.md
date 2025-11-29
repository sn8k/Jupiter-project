# Changelog

## 0.1.5 – Modal Visibility Fix
- Added global `.hidden` utility class so overlays/modals are truly hidden until opened.
- Removed duplicate `startScan` definition that broke the Web UI script execution.

## 0.1.0 – Initial scaffolding
- Established Jupiter Python package with core scanning, analysis, and reporting primitives.
- Added CLI entrypoint supporting `scan`, `analyze`, and server stubs.
- Introduced server placeholders for API hosting and Meeting integration.
- Documented usage in README and Manual; created per-file changelogs.

## 0.1.4 – Web Interface Modal Fixes
- Added `pointer-events: auto` to modal overlay and content to ensure clicks are registered.
- Bumped client version to `0.1.4`.

## 0.1.3 – Web Interface Cache Fixes
- Forced server-side 200 OK for `index.html` and `app.js` to bypass aggressive browser caching.
- Bumped client version to `0.1.3` with visual indicator.
- Added debug logging for action handling.

## 0.1.2 – Web Interface Fixes
- Fixed unresponsive WebUI caused by ES Module scope issues.
- Refactored event handling to use delegation instead of inline handlers.
- Improved robustness of `app.js`.

## 0.1.1 – CLI exclusions and richer analysis
- Added glob-based ignore handling (including `.jupiterignore`) to the scanner and CLI.
- Extended analysis summaries with average size and top N largest files, plus JSON export.
- Documented new CLI flags, exclusion behavior, and report persistence in the README and Manual.
