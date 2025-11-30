# Jupiter Developer Guide

This guide provides detailed information on the internal architecture and modules of Jupiter. It is intended for developers who want to contribute to the core codebase or create advanced plugins.

## Core Modules (`jupiter.core`)

### Scanner (`scanner.py`)

The `ProjectScanner` class is the entry point for filesystem analysis.

*   **Responsibility**: Walks the directory tree, filters files based on ignore patterns, and collects basic metadata (size, mtime, type).
*   **Key Methods**:
    *   `scan(root: Path) -> ScanReport`: Main method.
    *   `_should_ignore(path: Path) -> bool`: Checks against `.jupiterignore` and CLI ignore patterns.
*   **Incremental Scan**: Uses `CacheManager` to compare current file state with the previous scan. Only changed files are re-processed by downstream analyzers.
*   **Performance**: Supports parallel scanning via `ThreadPoolExecutor` (configurable via `PerformanceConfig`).

### Analyzer (`analyzer.py`)

The `ProjectAnalyzer` class consumes the `ScanReport` and produces higher-level insights.

*   **Responsibility**: Aggregates statistics, detects hotspots, and delegates language-specific analysis.
*   **Key Methods**:
    *   `analyze(report: ScanReport) -> AnalyzeResponse`: Main method.
    *   `_analyze_file(file: FileAnalysis)`: Dispatches to language handlers (e.g., `PythonAnalyzer`).

### Language Support (`jupiter.core.language`)

Jupiter supports multiple languages via dedicated analyzers.

*   **Python (`python.py`)**: Uses `ast` module for robust parsing.
*   **JS/TS (`js_ts.py`)**: Uses regex heuristics for lightweight analysis of `.js`, `.ts`, `.jsx`, `.tsx` files.

**Adding a new language:**
1.  Create `jupiter/core/language/<lang>.py`.
2.  Implement an `analyze_<lang>_source(source_code: str) -> Dict` function returning `imports` and `defined_functions`.
3.  Update `jupiter/core/scanner.py` to import your analyzer and call it based on file extension.
4.  Update `jupiter/core/analyzer.py` to include the new language stats in `AnalysisSummary`.

### Runner (`runner.py`)

The `run_command` function handles the execution of external processes.

*   **Responsibility**: Runs shell commands, captures stdout/stderr, and optionally wraps execution for dynamic analysis.
*   **Dynamic Analysis**: When enabled, it sets up a tracing environment (using `sys.settrace` or similar mechanisms via `tracer.py`) to count function calls during execution.

### Quality (`quality/`)

*   **Complexity (`complexity.py`)**: Calculates Cyclomatic Complexity for Python code using the `ast` module.
*   **Duplication (`duplication.py`)**: Hashes chunks of code (sliding window) to find identical blocks across files.

### AI Helper (`plugins/ai_helper.py`)

The AI Helper plugin demonstrates how to extend Jupiter with intelligent features. It is a strictly **optional** component that is isolated from the core analysis logic.

*   **Responsibility**: Provides code suggestions and refactoring tips based on the analysis report.
*   **Architecture**: 
    *   Hooks into `on_analyze` to inspect the `AnalysisSummary`.
    *   Receives data about hotspots, complexity, and code structure.
    *   Returns a list of `RefactoringRecommendation` objects (suggestions, tags, annotations).
    *   Does **not** modify code directly; it only produces metadata.
*   **Extensibility**: Designed to support multiple providers (Mock, OpenAI, Local LLM) via configuration. The provider implementation is swappable and does not impact the core system.


### History (`history.py`)

`HistoryManager` centralizes snapshot persistence under `.jupiter/snapshots/`.

*   **Responsibility**: Store every scan report with metadata (timestamp, backend, counts) and compute diffs.
*   **Key Methods**:
    *   `create_snapshot(report, label=None, backend_name=None) -> SnapshotMetadata`: Serialize the report to disk.
    *   `list_snapshots() -> list[SnapshotMetadata]`: Read and sort available snapshots.
    *   `compare_snapshots(id_a, id_b) -> SnapshotDiff`: Produce structured file/function delta.
*   **Usage**: Called automatically by the CLI `scan` flow and the FastAPI `/scan` endpoint (unless explicitly disabled by the client).

## API Server (`jupiter.server`)

The API is built with FastAPI and provides endpoints for the Web UI and CLI. It uses `ProjectManager` to delegate operations to the appropriate backend (local or remote).

*   **Endpoints**:
    *   `POST /scan`: Triggers a scan (supports `backend_name`).
        *   When `capture_snapshot` is true (default), the API persists the report via `HistoryManager` and notifies the WebSocket manager so the UI refreshes the History view.
        *   Also dispatches the `on_scan` hook to all active plugins.
    *   `GET /analyze`: Returns analysis summary (supports `backend_name`) and calls `on_analyze` hooks.
    *   `POST /run`: Executes commands (supports `backend_name`) and returns optional dynamic analysis data.
    *   `GET /snapshots`, `GET /snapshots/{id}`, `GET /snapshots/diff`: Provide read-only access to the stored history for the Web UI and tooling.
    *   `POST /simulate/remove`: Delegates to `ProjectSimulator` to compute impact of removing a file or function.
    *   `GET /graph`: Delegates to `GraphBuilder` to expose a graph suitable for the Live Map. Supports `simplify` (group by directory) and `max_nodes` parameters for large projects.
    *   `GET /backends`: Lists configured backends.
    *   `GET /plugins`, `POST /plugins/{name}/toggle`, `POST /plugins/{name}/config`: Introspect and manage plugins (including webhook configuration).
    *   `GET /config` & `POST /config`: Manages `<project>.jupiter.yaml`.
    *   `POST /update`: Handles self-update.
    *   `WS /ws`: WebSocket for real-time events (watch mode).

## Security

Jupiter includes a basic security layer with Role-Based Access Control (RBAC):

*   **Authentication**: Tokens are configured in `<project>.jupiter.yaml`. The API enforces `Authorization: Bearer <token>` on protected endpoints.
*   **Roles**:
    *   **Admin**: Full access (`/run`, `/update`, `/config`, `/plugins`, `/scan`).
    *   **Viewer**: Read-only access (`/snapshots`, `/graph`, `/analyze`, `/reports`, `/fs/list`).
*   **Run Restrictions**: `SecurityConfig` exposes `allow_run` and `allowed_commands` so operators can disable `run` completely or restrict it to a whitelist.
*   **Meeting Integration**: The `MeetingAdapter` validates the `deviceKey` to gate advanced features like `run` and `watch`.
*   **Remote Backends**: `RemoteConnector` uses explicit timeouts and catches network errors, logging high‑level failures without leaking secrets.
*   **Plugin Isolation & Policy**: Plugins are executed within `try/except` blocks, and each plugin can declare a `trust_level` (`trusted` vs `experimental`) that is surfaced in logs and the Plugins view.
*   **Audit Logging**: Sensitive actions (run, config change, update) are logged with the role and details of the action.

## Connectors (`jupiter.core.connectors`)

Jupiter supports multiple backends via the `BaseConnector` interface.

*   **LocalConnector**: Wraps `ProjectScanner`, `ProjectAnalyzer`, and `Runner` for local projects.
*   **RemoteConnector**: Proxies requests to a remote Jupiter API instance.

## Web UI (`jupiter.web`)

The Web UI is a single-page application (SPA) served by a lightweight Python HTTP server (or the API server in dev mode).

*   **Structure**:
    *   `index.html`: Main layout and views.
    *   `app.js`: Logic for state management, API calls, and DOM rendering.
    *   `styles.css`: Theming and layout.
*   **Key Concepts**:
    *   **Views**: Dashboard, Analysis, Settings, etc., toggled via `data-view`.
    *   **Modals**: For complex interactions (Scan options, Run command).
    *   **State**: Centralized `state` object in `app.js`.

## Plugin System (`jupiter.plugins`)

Jupiter uses a hook-based plugin system managed by `PluginManager`. For detailed documentation on creating and configuring plugins, see [Plugin System Documentation](plugins.md).

### Quick Start

1.  Create a new file in `jupiter/plugins/` (e.g., `my_plugin.py`).
2.  Define a class with `name`, `version`, and hook methods (`on_scan`, `on_analyze`).

## Meeting Integration (`jupiter.server.meeting_adapter`)

The `MeetingAdapter` handles the connection to the external Meeting service.

*   **Device Registration**: Exchanges a `deviceKey` for a session token.
*   **Heartbeat**: Periodically sends "I'm alive" signals.
*   **License Check**: Validates if the current session allows specific features (e.g., `watch`, `run`).

## Observability

Jupiter exposes metrics and structured events for monitoring.

*   **Metrics**: `GET /metrics` provides aggregated stats (scan counts, averages, plugin status).
*   **Events**: The WebSocket stream broadcasts typed events (`JupiterEvent`) which can be consumed by the UI or external tools.
*   **Notifications**: The `notifications_webhook` plugin subscribes to these events to trigger external webhooks.

## Testing

We use `pytest` for all testing.

*   **Unit Tests**: `tests/test_*.py` (focus on individual modules).
*   **Integration Tests**: `tests/test_integration.py` (focus on API and end-to-end flows).

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=jupiter
```

## Continuous Integration (CI)

Jupiter uses GitHub Actions for CI. The workflow is defined in `.github/workflows/ci.yml`.

*   **Triggers**: Push to `main`, Pull Requests.
*   **Steps**:
    1.  Checkout code.
    2.  Set up Python.
    3.  Install dependencies (`requirements.txt` + `requirements-dev.txt`).
    4.  Run tests with coverage.
    5.  Linting (optional/future).
