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

### Analyzer (`analyzer.py`)

The `ProjectAnalyzer` class consumes the `ScanReport` and produces higher-level insights.

*   **Responsibility**: Aggregates statistics, detects hotspots, and delegates language-specific analysis.
*   **Key Methods**:
    *   `analyze(report: ScanReport) -> AnalyzeResponse`: Main method.
    *   `_analyze_file(file: FileAnalysis)`: Dispatches to language handlers (e.g., `PythonAnalyzer`).

### Runner (`runner.py`)

The `run_command` function handles the execution of external processes.

*   **Responsibility**: Runs shell commands, captures stdout/stderr, and optionally wraps execution for dynamic analysis.
*   **Dynamic Analysis**: When enabled, it sets up a tracing environment (using `sys.settrace` or similar mechanisms via `tracer.py`) to count function calls during execution.

### Quality (`quality/`)

*   **Complexity (`complexity.py`)**: Calculates Cyclomatic Complexity for Python code using the `ast` module.
*   **Duplication (`duplication.py`)**: Hashes chunks of code (sliding window) to find identical blocks across files.

## API Server (`jupiter.server`)

The API is built with FastAPI and provides endpoints for the Web UI and CLI. It uses `ProjectManager` to delegate operations to the appropriate backend (local or remote).

*   **Endpoints**:
    *   `POST /scan`: Triggers a scan (supports `backend_name`).
    *   `GET /analyze`: Returns analysis summary (supports `backend_name`).
    *   `POST /run`: Executes commands (supports `backend_name`).
    *   `GET /backends`: Lists configured backends.
    *   `GET /config` & `POST /config`: Manages `jupiter.yaml`.
    *   `POST /update`: Handles self-update.
    *   `WS /ws`: WebSocket for real-time events (watch mode).

## Security

Jupiter includes a basic security layer:

*   **Authentication**: A token can be configured in `jupiter.yaml`. If present, the API enforces `Authorization: Bearer <token>` on sensitive endpoints (`/run`, `/update`, etc.).
*   **Meeting Integration**: The `MeetingAdapter` validates the `deviceKey` against a hardcoded valid key (mock) to prevent trivial bypass via config modification.
*   **Plugin Isolation**: Plugins are executed within `try/except` blocks to prevent a single plugin from crashing the entire server.

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
