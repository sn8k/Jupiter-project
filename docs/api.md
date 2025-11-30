# Jupiter API Reference

The Jupiter API is a RESTful interface built with FastAPI.

## Base URL

By default: `http://127.0.0.1:8000`

## Authentication

Jupiter supports token-based authentication with roles. Tokens are configured in `jupiter.yaml` (under `security.tokens`).

**Header:**
`Authorization: Bearer <your-token>`

**Roles:**
* **Admin**: Full access.
* **Viewer**: Read-only access.

**Protected Endpoints:**

*   **Admin Only**:
    *   `POST /run`
    *   `POST /update`
    *   `POST /config`
    *   `POST /config/root`
    *   `POST /plugins/{name}/toggle`
    *   `POST /plugins/{name}/config`

*   **Authenticated (Admin or Viewer)**:
    *   `POST /scan`
    *   `GET /snapshots`
    *   `GET /snapshots/{id}`
    *   `GET /snapshots/diff`
    *   `GET /graph`
    *   `GET /analyze`
    *   `GET /config`
    *   `GET /fs/list`
    *   `GET /reports/last`
    *   `GET /plugins`
    *   `GET /backends`
    *   `WS /ws` (via query parameter `token`)

## Endpoints

### `GET /health`

Returns the health status of the server.

**Response:**
```json
{
  "status": "ok"
}
```

### `POST /scan`

Runs a filesystem scan on the configured project root.

**Body:**
```json
{
  "show_hidden": false,
  "ignore_globs": ["*.tmp"],
  "incremental": true,
  "capture_snapshot": true,
  "snapshot_label": "pre-release"
}
```

- `capture_snapshot` (default `true`): Persist the resulting report under `.jupiter/snapshots/`.
- `snapshot_label` (optional): Override the default timestamp label for the stored snapshot.

**Response:**
Returns a full JSON scan report (see Report Schema).

**Note:** This endpoint triggers the `on_scan` hook for all active plugins.

### `GET /analyze`

Runs a scan and returns a summary analysis.

**Query Parameters:**
* `top`: Number of largest files to return (default: 5)
* `show_hidden`: Boolean
* `ignore_globs`: List of strings

**Response:**
Returns a JSON summary object.

**Note:** This endpoint triggers the `on_analyze` hook for all active plugins.

### `POST /run`

Executes a shell command within the project context.

**Body:**
```json
{
  "command": ["python", "script.py", "--arg"],
  "with_dynamic": true
}
```

**Response:**
```json
{
  "stdout": "...",
  "stderr": "...",
  "returncode": 0,
  "dynamic_analysis": {
    "calls": {"module.func": 12},
    "times": {"module.func": 0.123},
    "call_graph": {"module.func": {"other.func": 3}}
  }
}
```

**Security notes:**

* This endpoint is protected by Bearer token authentication (`security.token`).
* Execution can be globally disabled via `security.allow_run = false` in `jupiter.yaml`.
* When `security.allowed_commands` is non‑empty, only commands or executables listed there are accepted.

### `GET /meeting/status`

Returns the current licensing and session status.

**Response:**
```json
{
  "device_key": "...",
  "is_licensed": true,
  "session_active": true,
  "status": "active",
  "message": "License valid."
}
```

### `GET /snapshots`

Returns the list of stored scan snapshots (newest first).

**Response:**
```json
{
  "snapshots": [
    {
      "id": "scan-1700000000000",
      "timestamp": 1700000000.0,
      "label": "pre-release",
      "jupiter_version": "0.1.5",
      "backend_name": null,
      "project_root": "/repo",
      "project_name": "repo",
      "file_count": 523,
      "total_size_bytes": 1234567,
      "function_count": 812,
      "unused_function_count": 37
    }
  ]
}
```

### `GET /snapshots/{snapshot_id}`

Returns the metadata and full report for a single snapshot.

**Response:**
```json
{
  "metadata": { "id": "scan-1700000000000", "label": "pre-release", "file_count": 523, "total_size_bytes": 1234567, "function_count": 812, "unused_function_count": 37, "timestamp": 1700000000.0, "jupiter_version": "0.1.5", "backend_name": null, "project_root": "/repo", "project_name": "repo" },
  "report": { "root": "/repo", "files": [ ... ] }
}
```

### `GET /snapshots/diff`

Computes a diff between two snapshots.

**Query Parameters:**
- `id_a`: Snapshot identifier considered the "before" reference.
- `id_b`: Snapshot identifier considered the "after" reference.

**Response:**
```json
{
  "snapshot_a": { "id": "scan-old", "label": "baseline", ... },
  "snapshot_b": { "id": "scan-new", "label": "post-upgrade", ... },
  "diff": {
    "metrics_delta": {
      "file_count": 12,
      "total_size_bytes": 42000,
      "function_count": 37,
      "unused_function_count": -5
    },
    "files_added": [{ "path": "src/new.py", "size_after": 1337 }],
    "files_removed": [{ "path": "legacy/tmp.py", "size_before": 512 }],
    "files_modified": [{ "path": "core/app.py", "size_before": 2048, "size_after": 2300 }],
    "functions_added": [{ "path": "core/app.py", "function": "upgrade_service", "change_type": "added" }],
    "functions_removed": []
  }
}
```

### `POST /simulate/remove`

Simulates the impact of removing a file or function.

**Body:**
```json
{
  "target_type": "file",  // or "function"
  "path": "jupiter/core/scanner.py",
  "function_name": null   // required if target_type is "function"
}
```

**Response:**
```json
{
  "target": "Remove file jupiter/core/scanner.py",
  "risk_score": "high",
  "impacts": [
    {
      "target": "jupiter/core/analyzer.py",
      "impact_type": "broken_import",
      "details": "Imports removed module 'jupiter.core.scanner'",
      "severity": "high"
    }
  ]
}
```

### `GET /graph`

Returns a dependency graph of the project for visualization.

**Query Parameters:**
- `backend_name`: (Optional) Name of the backend to use.

**Response:**
```json
{
  "nodes": [
    {
      "id": "jupiter/core/scanner.py",
      "type": "file",
      "label": "scanner.py",
      "size": 18456,
      "group": "file"
    },
    {
      "id": "jupiter/core/scanner.py::ProjectScanner",
      "type": "function",
      "label": "ProjectScanner",
      "group": "function"
    }
  ],
  "links": [
    {
      "source": "jupiter/core/scanner.py",
      "target": "jupiter/core/scanner.py::ProjectScanner",
      "type": "contains"
    }
  ]
}
```

### `GET /metrics`

Returns system metrics and statistics.

**Response:**
```json
{
  "scans": {
    "total": 42,
    "avg_files": 150.5,
    "avg_size_bytes": 1024000,
    "avg_functions": 45.2
  },
  "plugins": {
    "total": 5,
    "active_count": 3,
    "active_list": ["notifications_webhook", "code_quality"]
  },
  "system": {
    "version": "1.0.1"
  }
}
```

### `WS /ws`

WebSocket endpoint for real-time events.

**Events:**

*   `SCAN_STARTED`: `{"type": "SCAN_STARTED", "payload": {"root": "...", "options": {...}}}`
*   `SCAN_FINISHED`: `{"type": "SCAN_FINISHED", "payload": {"file_count": 123}}`
*   `RUN_STARTED`: `{"type": "RUN_STARTED", "payload": {"command": ["ls", "-la"]}}`
*   `RUN_FINISHED`: `{"type": "RUN_FINISHED", "payload": {"returncode": 0}}`
*   `CONFIG_UPDATED`: `{"type": "CONFIG_UPDATED", "payload": {...}}`
*   `PLUGIN_TOGGLED`: `{"type": "PLUGIN_TOGGLED", "payload": {"name": "...", "enabled": true}}`

### `GET /backends`

Lists configured project backends.

**Response:**
```json
[
  {"name": "local", "type": "local_fs", "path": "."},
  {"name": "remote-prod", "type": "remote_jupiter_api", "api_url": "http://prod:8000"}
]
```

### `GET /plugins`

Returns the list of loaded plugins and their status.

**Response:**
```json
[
  {"name": "notifications_webhook", "version": "1.0.1", "description": "Sends notifications to a webhook URL.", "enabled": true,
   "config": {"url": "https://httpbin.org/post", "events": ["scan_complete"]}}
]
```

### `POST /plugins/{name}/toggle`

Enable or disable a plugin. Protected by token.

**Response:**
```json
{"success": true, "enabled": true}
```

### `POST /plugins/{name}/config`

Update a plugin configuration (for example, the webhook URL). Protected by token.

**Body (example for `notifications_webhook`):**
```json
{"url": "https://my-service/hooks/jupiter", "events": ["scan_complete"]}
```

**Response:**
```json
{"success": true}
```

## WebSockets

### `/ws`

Real-time event stream (logs, file changes).
