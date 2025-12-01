# Changelog – jupiter/server/api.py

## 2025-12-01 – Version metadata alignment

### Changed
- Le constructeur FastAPI renseigne désormais `version=__version__` afin que la documentation OpenAPI expose la même version que la CLI/GUI.

## 2025-12-01 – Code Quality manual linking endpoints

### Added
- `POST /plugins/code_quality/manual-links` to persist linked duplication clusters created from the UI.
- `DELETE /plugins/code_quality/manual-links/{link_id}` to remove disk-backed links.
- `POST /plugins/code_quality/manual-links/recheck` to re-verify one or all manual links without triggering a new scan.
- Router helpers now cast the Code Quality plugin to access the new helper methods while keeping the plugin interface generic.

---

**Section 1 Implementation (API Stabilization & Schemas)**

- Integrated Pydantic models from `server.models` module for all endpoints.
- Updated `POST /scan` to use `ScanRequest` input and `ScanReport` response model.
- Updated `GET /analyze` to return strongly-typed `AnalyzeResponse`.
- Updated `POST /run` to return `RunResponse` instead of raw `CommandResult`.
- Updated `GET /health` to return `HealthStatus` model.
- Updated `POST /config/root` to use `RootUpdate` and `RootUpdateResponse` models.
- Updated `GET /fs/list` to return `FSListResponse` with `FSListEntry` models.
- Updated `GET /meeting/status` to return `MeetingStatus` model with proper field mapping.
- All endpoints now include `response_model` parameter for automatic OpenAPI schema generation.
- Cleaned up duplicate `uvicorn.run` call in `JupiterAPIServer.start()`.
- Enforced license restrictions in `POST /run` and `WebSocket /ws` using `MeetingAdapter.validate_feature_access`.
- Updated `GET /meeting/status` to reflect detailed license state (active, limited, expired).
- Integrated `PluginManager` in `JupiterAPIServer.start`.
- Updated `POST /scan` and `GET /analyze` to include plugin info in responses and trigger plugin hooks.
- Integrated `ProjectManager` into `JupiterAPIServer` to handle backend selection.
- Updated `POST /scan`, `GET /analyze`, and `POST /run` to use `ProjectManager` and `Connector` interface instead of direct `ProjectScanner`/`ProjectAnalyzer`/`Runner` usage.
- Added `GET /backends` endpoint to list configured backends.
- Updated `POST /scan`, `GET /analyze`, and `POST /run` to accept `backend_name` parameter.

**Session persistence & cached data**

- Added `GET /reports/last` so the Web UI can restore the most recent scan from `.jupiter/cache/last_scan.json` without running a new scan.
- `POST /scan` now re-saves the enriched report (with plugin metadata) through `CacheManager` so cached payloads remain schema-compatible for `/reports/last`.
- `POST /config/root` now reloads the new root's configuration/connectors/plugins and writes the fresh path to `~/.jupiter/state.json` so future launches start back where the user left off.
- On Windows, the API now forces the selector event loop policy to silence noisy proactor connection-reset traces when clients close abruptly.

**Previous entries**

- Added `JupiterAPIServer` stub with start/stop logging hooks.
- Enabled permissive CORS middleware so the web UI Scan button can reach `/scan` without browser fetch errors.

**Section 6 Implementation (AI Plugin Integration)**

- Updated `GET /analyze` to convert the response model to a dictionary before calling `hook_on_analyze`.
- This allows plugins (like `ai_helper`) to modify the response data (e.g., injecting suggestions) before it is returned to the client.
- API startup now normalizes the configured `logging.level`, applies it to Uvicorn, and logs the active verbosity when booting the server.
- API startup now also forwards `logging.path` (when set) to configure a file handler so log destinations configured in Settings are honored.
