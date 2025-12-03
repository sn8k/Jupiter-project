# Jupiter API Reference (v1.8.5)

This document describes the HTTP API exposed by Jupiter. The same API powers the Web UI and can be called directly from scripts or CI.

All responses are JSON unless otherwise noted.

## Base URL & Auth

- **Default base URL**: `http://127.0.0.1:8000`
- **Authentication**: token-based.
  - Either define a single `security.token`.
  - Or declare named users with roles in `<project>.jupiter.yaml`.
- **Roles**:
  - `admin`: full access (configuration, run, update, plugins).
  - `viewer`: read-only access (scan/analyze, snapshots, metrics, browsing).
- **WebSocket**: `/ws` accepts the token as a query parameter when security is enabled.

## Core Endpoints

### Health & Metrics

- `GET /health` → returns the basic status of the server:
  ```json
  {
    "status": "ok",
    "root": "/path/to/current/project"
  }
  ```
- `GET /metrics` (auth) → returns aggregate scan/plugin/system metrics used by the dashboard.

### Scan & Analyze

- `POST /scan` (auth)  
  Runs a filesystem scan on the current project root.

  **Request body (JSON)**:
  ```json
  {
    "show_hidden": false,
    "ignore_globs": ["*.log"],
    "incremental": true,
    "capture_snapshot": true,
    "snapshot_label": "pre-release",
    "backend_name": "local"
  }
  ```

  **Behavior**:
  - Returns a full `ScanReport` (files, quality, plugins, pylance, refactoring).
  - Saves `.jupiter/cache/last_scan.json`.
  - Persists a snapshot unless `capture_snapshot` is explicitly set to `false`.

- `GET /analyze` (auth)  
  Performs a scan + analysis and returns a summary.

  **Query parameters**:
  - `top`: number of largest files to include in the summary (default: 5).
  - `show_hidden`: include hidden files (`true`/`false`).
  - `ignore_globs`: can be repeated to exclude patterns.
  - `backend_name`: override the default backend.

  **Response**:
  - Aggregated stats (file counts, sizes, by extension).
  - Hotspots (complexity, duplication).
  - Optional `python_summary` (total functions, potentially unused functions).
  - Plugin-provided sections (Code Quality, AI Helper, etc.).

- `POST /ci` (auth)  
  Runs analysis in “quality gate” mode.

  **Request body (JSON)**:
  ```json
  {
    "fail_on_complexity": 20,
    "fail_on_duplication": 5,
    "fail_on_unused": 50
  }
  ```

  **Response**:
  - `CIResponse` structure with:
    - aggregated metrics,
    - which thresholds have been exceeded,
    - a boolean flag used by CI to decide pass/fail.

- `GET /reports/last` (auth)  
  Returns the last cached scan report (`.jupiter/cache/last_scan.json`), normalized to the public schema.

- `GET /api/endpoints` (auth)  
  Returns the list of exposed routes. Used by autodiag and debugging tools.

### Snapshots

- `GET /snapshots` (auth)  
  Returns a list of snapshot metadata (newest first).

- `GET /snapshots/{id}` (auth)  
  Returns:
  ```json
  {
    "metadata": { "...": "..." },
    "report": { "...": "..." }
  }
  ```

- `GET /snapshots/diff` (auth)  
  **Query parameters**:
  - `id_a`: base snapshot ID.
  - `id_b`: comparison snapshot ID.

  **Response**:
  - Metrics deltas (file count, size, functions, unused functions).
  - Lists of added/removed/modified files.
  - Function-level additions/removals where available.

### Simulation

- `POST /simulate/remove`  
  Simulates the impact of removing a file or function without touching the filesystem.

  **Request body (JSON)**:
  ```json
  {
    "target_type": "file",
    "path": "jupiter/core/scanner.py",
    "function_name": null
  }
  ```
  or:
  ```json
  {
    "target_type": "function",
    "path": "jupiter/core/scanner.py",
    "function_name": "ProjectScanner.scan"
  }
  ```

  **Response**:
  - A risk score (low/medium/high).
  - A list of impacted files/functions and the reason (broken import, missing symbol, etc.).

### Run (shell)

- `POST /run` (auth, **admin**)  
  Executes a shell command in the project context and optionally wraps it in dynamic analysis.

  **Request body (JSON)**:
  ```json
  {
    "command": ["python", "script.py", "--flag"],
    "with_dynamic": true
  }
  ```

  **Response**:
  ```json
  {
    "stdout": "...",
    "stderr": "...",
    "returncode": 0,
    "dynamic_analysis": {
      "calls": {"module.func": 12},
      "times": {"module.func": 0.123}
    }
  }
  ```

  This endpoint is governed by `security.allow_run` and `security.allowed_commands` and should only be exposed on trusted networks.

## Projects, Backends, Config

- `GET /projects` (auth) → list of registered projects with `is_active`.
- `POST /projects` (admin) → register and activate a project.  
  Body: `{ "path": "/abs/path", "name": "Optional label" }`.
- `POST /projects/{id}/activate` (admin) → switch active project, reload config/plugins/history.
- `DELETE /projects/{id}` (admin) → remove from registry (does not delete files on disk).
- `POST /projects/{id}/ignore` (admin) → persist ignore globs for the project.
- `GET /projects/{id}/api_config` / `POST /projects/{id}/api_config` (admin) → manage remote API connector settings.
- `GET /projects/{id}/api_status` (auth) → status of the configured remote API.
- `POST /init` → initialize a new Jupiter project with a default `<project>.jupiter.yaml`.

- `GET /backends` (auth) → available connectors (local filesystem, remote Jupiter API, OpenAPI).
- `GET /project/root-entries` (auth) → directory listing helper for the currently active root.

- `GET /config` (auth) → resolved config (global + project), including plugin sections.
- `POST /config` (admin) → replace configuration.
- `PATCH /config` (admin) → partial update (used by Settings Save buttons).
- `GET /config/raw` (admin) / `POST /config/raw` (admin) → raw YAML blobs for advanced editing.
- `POST /config/root` (admin) → change active root; rebuilds runtime and resets history for the new project.

## Auth & Users

- `POST /login` → `{token}` for UI and API clients. Validates against configured users/tokens.
- `GET /users` (admin) → list users.
- `POST /users` (admin) → create a new user.
- `PUT /users/{name}` (admin) → update an existing user.
- `DELETE /users/{name}` (admin) → delete a user.
- `GET /me` (auth) → information about the current user.

## Plugins

- `GET /plugins` (auth) → list loaded plugins and their status.
- `POST /plugins/{name}/toggle` (**admin**) → enable/disable a plugin.
- `GET /plugins/{name}/config` (auth) / `POST /plugins/{name}/config` (**admin**) → get/set plugin configuration.
- `POST /plugins/{name}/test` (**admin**) → plugin-provided self-test.
- `POST /plugins/reload` (**admin**) / `POST /plugins/{name}/restart` (**admin**) → reload plugin code at runtime.
- `POST /plugins/install` / `POST /plugins/install/upload` (**admin**) → install a plugin from URL or uploaded archive.
- `DELETE /plugins/{name}/uninstall` (**admin**) → uninstall a plugin.
- `GET /plugins/settings` / `GET /plugins/sidebar` (auth) → descriptors for plugin Settings cards and sidebar entries.
- `GET /plugins/{name}/ui` (auth) → HTML/JS snippet for a plugin’s main UI.
- `GET /plugins/{name}/settings-ui` (auth) → HTML/JS snippet for the plugin Settings panel.

### Code Quality (duplication/complexity)

- `POST /plugins/code_quality/manual-links` (**admin**) → merge detector clusters with a label and persist to `.jupiter/manual_duplication_links.json`.
- `DELETE /plugins/code_quality/manual-links/{link_id}` (**admin**) → remove a manual link.
- `POST /plugins/code_quality/manual-links/recheck` (**admin**) → re-verify links (optional `link_id` filter).

### Live Map

- `GET /plugins/livemap/graph` (auth) → dependency graph nodes/links for the Live Map.
- `GET /plugins/livemap/config` / `POST /plugins/livemap/config` (auth) → retrieve/update Live Map configuration.

### Watchdog

- `GET /plugins/watchdog/config` / `POST /plugins/watchdog/config` (auth) → check interval and enable flags.
- `GET /plugins/watchdog/status` (auth) → watch status and reload counts.
- `POST /plugins/watchdog/check` (auth) → force an immediate check.

### Bridge (core services gateway)

- `GET /plugins/bridge/status` (auth) → plugin health and version.
- `POST /plugins/bridge/config` (auth) → endpoints/settings for Bridge.
- `GET /plugins/bridge/services` / `GET /plugins/bridge/capabilities` (auth) → catalog of exposed services and capabilities.
- `GET /plugins/bridge/service/{service_name}` (auth) → detailed information about a specific service.

### Settings Update (helper)

- `GET /plugins/settings_update/version` → version metadata for the updater.
- `POST /plugins/settings_update/apply` (**admin**) → apply an uploaded settings package.
- `POST /plugins/settings_update/upload` (**admin**) → upload the package to be applied.

## Meeting & Licensing

- `GET /license/status` → current license state (`authorized`, `device_type`, `token_count`, message).
- `POST /license/refresh` (auth) → force a license re-check against the Meeting backend.
- `GET /meeting/status` → deprecated alias; still returns `MeetingStatus`.

## Watch & Live Events

- `POST /watch/start` (auth) → begin watching the project and enable dynamic progress callbacks.
- `POST /watch/stop` (auth) → stop watching.
- `GET /watch/status` (auth) → current watch state.
- `GET /watch/calls` (auth) → aggregated dynamic call counts for watched runs.
- `POST /watch/calls/reset` (auth) → reset collected call data.
- `WS /ws` (auth token in query when configured) → broadcast channel for scan/run/config/plugin events consumed by the Web UI.

## File System Helpers

- `GET /fs/list` (auth) → filesystem listing helper for the active project (used by the Files view in the Web UI).

## Update Utility

- `POST /update` (**admin**) → update Jupiter from a URL/path (ZIP or git) as configured.
- `POST /update/upload` (**admin**) → upload an archive to be applied as an update.

## Autodiag (internal diagnostics)

- `GET /diag/handlers` (auth) → inventory of CLI handlers and their modules.
- `GET /diag/functions` (auth) → function usage details with confidence scores.
- `GET /api/endpoints` (auth) → list of routes (same as above, provided explicitly for tools).

## Error Model

Errors are returned with a consistent envelope:

```json
{
  "error": {
    "code": "string",
    "message": "human-readable explanation",
    "details": {}
  }
}
```

- Request/validation errors use standard HTTP 4xx codes.
- Internal failures (scan/analyze/run) use 500.
- Meeting-specific errors use 503 with explicit codes.
