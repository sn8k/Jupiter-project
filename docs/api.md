# Jupiter API Reference

The Jupiter API is a RESTful interface built with FastAPI.

## Base URL

By default: `http://127.0.0.1:8000`

## Authentication

Jupiter supports a simple token-based authentication. If a token is configured in `jupiter.yaml` (under `security.token`), it must be provided in the `Authorization` header for sensitive endpoints.

**Header:**
`Authorization: Bearer <your-token>`

**Protected Endpoints:**
* `POST /run`
* `POST /update`
* `POST /config`
* `POST /config/root`
* `POST /plugins/{name}/toggle`
* `WS /ws` (via query parameter `token`)

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
  "incremental": true
}
```

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
  "returncode": 0
}
```

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

Executes a command in the project root.

**Body:**
```json
{
  "command": ["ls", "-la"]
}
```

**Response:**
```json
{
  "stdout": "...",
  "stderr": "...",
  "return_code": 0
}
```

### `GET /meeting/status`

Returns the status of the Meeting integration and license.

**Response:**
```json
{
  "licensed": true,
  "status": "active",
  "deviceKey": "...",
  "lastHeartbeat": "..."
}
```

## WebSockets

### `/ws`

Real-time event stream (logs, file changes).
