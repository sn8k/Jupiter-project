# Changelog

## 1.0.1 – UI Polish & Quality Data
- **Scan Modal**: Rebuilt layout/padding and persisted the previous options automatically.
- **Quality View**: Scan responses now embed complexity/duplication metrics so the Qualité page shows data immediately (even while watching a local backend).

## 0.1.13 – Login UI & Config Fixes
- **Fix**: Resolved "Invalid credentials" error by ensuring the API server receives the correctly loaded configuration.
- **UI**: Improved styling of the Login Modal (backdrop, spacing, inputs).

## 0.1.12 – Real Login System
- **Auth**: Implemented Username/Password login with "Remember Me".
- **UI**: Login modal now blocks access until authenticated.
- **Backend**: Added `/login` endpoint and updated token verification.

## 0.1.11 – User Management & Update Upload
- **Settings**: Added User Management section (Global config).
- **Update**: Added "Browse" button for uploading update ZIPs.
- **Backend**: Added endpoints for users and file upload.

## 0.1.10 – Split Configuration Architecture
- **Architecture**: Implemented a split configuration system. Global settings (Meeting, UI, Server) are now stored in the installation directory, while Project settings (Performance, CI) are stored in the project directory.
- **Fix**: Resolved issue where Meeting Key was lost when scanning a new project.
- **API**: Updated `JupiterAPIServer` to handle merged configurations.

## 0.1.9 – Launch & Config Persistence Fixes
- **Launch**: `Jupiter UI.cmd` now forces the application to start with the configuration from the installation directory, fixing issues where settings were ignored.
- **Persistence**: Switching projects in the UI now preserves the Meeting license/configuration if the target project doesn't have one.
- **CLI**: Added global `--root` argument.

## 0.1.8 – Configuration Robustness
- **Config**: Added support for `device_key` alias in `jupiter.yaml` to prevent loading issues.
- **UI**: Improved settings loading logic for Meeting configuration.
- **Debug**: Added logging for configuration state.

## 0.1.7 – Settings Enhancements (API & Raw Config)
- **Settings**: Added "API Inspection" configuration (connector, app var, path) to the Settings page.
- **Raw Editor**: Added a "Edit Raw YAML" feature to modify `jupiter.yaml` directly from the UI.
- **UX**: Added tooltips to settings fields for better guidance.
- **Backend**: Updated API endpoints to support new configuration fields and raw file access.

## 0.1.6 – Snapshot history & diff
- Added automatic snapshot persistence for every scan (CLI/API/UI) with metadata-rich JSON stored under `.jupiter/snapshots/`.
- Introduced CLI controls (`--snapshot-label`, `--no-snapshot`, `snapshots list|show|diff`) plus FastAPI endpoints (`/snapshots`, `/snapshots/{id}`, `/snapshots/diff`).
- Extended Web UI with a History view that lists snapshots, renders diffs, and refreshes when scans complete.
- Updated README, Manual, and docs (User Guide, API, Developer Guide) to explain the workflow and new options.

## 0.1.5 – Modal Visibility Fix
- Added global `.hidden` utility class so overlays/modals are truly hidden until opened.
- Removed duplicate `startScan` definition that broke the Web UI script execution.

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

## 0.1.0 – Initial scaffolding
- Established Jupiter Python package with core scanning, analysis, and reporting primitives.
- Added CLI entrypoint supporting `scan`, `analyze`, and server stubs.
- Introduced server placeholders for API hosting and Meeting integration.
- Documented usage in README and Manual; created per-file changelogs.
