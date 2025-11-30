# Changelog

## 1.1.10 – Internal Deduplication
- CLI scan/analyze commands now reuse a shared service builder to remove repeated argument blocks.
- API routers reuse a common history manager helper (SystemState) instead of duplicated local implementations.
- Remote connector HTTP calls are centralized to avoid repeated request/raise patterns.
- Web UI project actions share a single mutation helper to reduce copy/paste error handling.
- Projects page now lets you edit per-project ignore globs, stored in the global registry and applied by default to scans/analyses.
- Project API connector settings moved to the Projects page with dedicated save endpoints (`/projects/{id}/api_config`).

## 1.1.9 – Detailed Duplication Evidence
- Duplication refactoring hints now embed file:line occurrences so AI suggestions explicitly list where duplicated blocks live.
- `/analyze` responses and the Suggestions tab surface these locations (with line numbers), the nearest function name, and a code excerpt to make the report actionable without hunting through duplication clusters.

# Changelog

## 1.1.8 – Active Project Persistence
- CLI root resolution now uses the active project stored in the global registry (`~/.jupiter/global_config.yaml` or legacy `global.yaml`) and syncs the local state file so restarting the GUI/CLI reopens the last project activated from the Web UI.
- Project activation in the backend now persists the selected root to the shared state file, keeping the registry and CLI defaults aligned.
- Global project registry entries are normalized on load (legacy `jupiter.yaml` -> `<project>.jupiter.yaml`, absolute paths), and Windows event-loop policy is enforced to suppress noisy connection-reset traces on client disconnects.

## 1.1.6 – Config Naming Update
- Global install configuration now targets `global_config.yaml` (with backward-compatible loading of legacy install overrides).
- Project configurations follow the `<project>.jupiter.yaml` naming scheme; legacy `jupiter.yaml` files are still loaded for existing setups.
- Documentation and UI copy have been refreshed to highlight the new naming and the registry path `~/.jupiter/global_config.yaml`.

## 1.1.7 – Log Destination in Settings
- Settings page now exposes a log file path field; the API, CLI, and debug server pass this value to logging setup to attach a file handler.
- Config schema (`logging.path`) persists this path across global/project saves and is exposed via `/config`.

## 1.1.5 – Configurable Logging
- Added centralized logging configuration with a project-level `logging.level` setting applied to CLI, FastAPI, and Uvicorn.
- Settings page now exposes the log level selector (Debug/Info/Warning/Error/Critic) and reuses it to filter dashboard logs.
- API config endpoints normalize and persist the log level while rebuilding runtime services with the updated verbosity.

## 1.1.4 – Projects Control Center
- Projects page is now fully wired to `/projects` (list, activate, delete) with refresh controls and in-place overview updates.
- Documented the Projects API endpoints and the new Web UI dashboard for multi-project management.
- Added a regression test (FastAPI TestClient) covering project create/activate/delete using the provided secondary project path.
- History view now scopes snapshots/diffs to the active project, clearing stale selections when switching.
- Forced context reload on project switch (no-cache) so the top bar and History view update to the newly active project immediately.

## 1.0.4 – Cache Schema & Notification Fallbacks
- Normalized cached scan payloads (plugins serialized as lists) and forced the API to resave the enriched report so `/reports/last` never fails Pydantic validation after upgrading plugins.
- Added a `PLUGIN_NOTIFICATION` event and taught the webhook plugin to emit local Live Events (via WebSocket) whenever no webhook URL is configured instead of logging errors.

## 1.0.3 – CLI Workflow & System Router Service
- Unified `scan`, `analyze`, and `ci` behind a shared CLI workflow (plugins, caching, snapshots) and exposed new helpers for CI gate evaluation.
- Introduced `SystemState` helper to rebuild plugin/project managers, Meeting adapter, and history whenever the API root or config changes.
- Root changes now preserve the last Meeting `deviceKey`, refresh plugin discovery once, and broadcast consistent state updates across WebSocket clients.
- Documentation refreshed (README, Manual) to describe the CI command and the automatic root refresh behavior.
- Fixed the Suggestions IA "Actualiser" button so it now calls the `/analyze` API and refreshes refactoring hints in-place with proper status feedback.

## 1.0.2 – CLI & Config Deduplication
- Refactored CLI scan/analyze setup to share a single options builder and scanner bootstrap, reducing duplicated logic.
- Centralized dynamic analysis cache merging in `CacheManager` and reused it across CLI and local connector flows.
- Consolidated configuration serialization helpers for performance/backends/API sections to avoid drift between project/global saves.

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
