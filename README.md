# Jupiter

**Project Inspection & Observability Tool**

Jupiter is a modular tool designed to scan, analyze, and observe software projects. It combines static analysis, dynamic tracing, and a modern web interface to give you deep insights into your codebase.

## Features

*   **Static Analysis**: Scan files, detect languages, compute metrics (size, complexity, duplication).
*   **Dynamic Analysis**: Trace function calls during execution to find dead code.
*   **Incremental Scanning**: Fast re-scans using caching.
*   **Snapshot History**: Automatically persist each scan, label important milestones, and diff snapshots via CLI/API/UI.
*   **Live Map**: Interactive dependency graph combining static structure, hotspots, and dynamic usage.
*   **Polyglot Support**: First-class support for Python and JS/TS projects.
*   **Simulation**: Impact analysis when virtually removing a file or function.
*   **Project API Connectors**: OpenAPI connector to inspect your own project's HTTP API.
*   **Web Interface**: Visual dashboard for exploring your project.
*   **Plugins & Webhooks**: Extensible plugin architecture with webhook notifications.
*   **Meeting Integration**: License management and session control.
*   **Multi-Project Management**: Manage multiple projects with distinct configurations and switch between them easily.

## Quick Start

### Windows Users (Standalone)
Download `jupiter.exe` and double-click it. It will launch the application and open your browser. No Python installation required.

### Windows Users (Source)
Double-click on **`Jupiter UI.cmd`**. It will set up the environment and launch the application automatically.

### Developers / Manual
1.  **Install**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Launch**:
    ```bash
    python -m jupiter.cli.main
    ```
    This will start the API server, the Web UI, and open your browser.

## Advanced Usage (CLI)

You can still use the CLI for specific tasks:

*   **Scan**: `python -m jupiter.cli.main scan`
*   **Analyze**: `python -m jupiter.cli.main analyze`
*   **Snapshots**: `python -m jupiter.cli.main snapshots list|show|diff`
*   **Simulation**: `python -m jupiter.cli.main simulate remove <cible>`
*   **CI**: `python -m jupiter.cli.main ci --json` to enforce quality gates with the exact same scanner/plugins as the other commands.

### Snapshot History & Diff

Jupiter now records every scan inside `.jupiter/snapshots/scan-*.json` so you can track how the project evolves. Use the CLI to control the behavior:

```bash
# Label a scan before merging
python -m jupiter.cli.main scan --snapshot-label "pre-release"

# Skip snapshot creation if you are experimenting
python -m jupiter.cli.main scan --no-snapshot

# Explore saved history
python -m jupiter.cli.main snapshots list
python -m jupiter.cli.main snapshots show scan-1700000000000
python -m jupiter.cli.main snapshots diff scan-old scan-new
```

Snapshots power the new **History** panel in the Web UI and the `/snapshots` API family (`/snapshots`, `/snapshots/{id}`, `/snapshots/diff`).

### Persistent state

When you change the served root in the Web UI or relaunch Jupiter without explicitly passing a directory, the tool reloads the last root saved in `~/.jupiter/state.json`, restores cached scan data from `.jupiter/cache/last_scan.json`, and keeps the snapshot history in `.jupiter/snapshots/` scoped per project so dashboards and diffs stay aligned with the same root.

`scan`, `analyze`, and `ci` now share a unified workflow builder that wires plugins, caching, performance settings, and snapshot persistence the same way no matter which command you trigger. This removes the subtle drifts that previously existed between the commands.

Cached reports are normalized before being written to `.jupiter/cache/last_scan.json`, keeping `/reports/last` compatible with the server schema even if plugin metadata evolves between versions.

## Documentation

Full documentation is available in the `docs/` directory:

*   [User Guide](docs/user_guide.md) – end‑to‑end walkthrough of the GUI and CLI (snapshots, simulation, Live Map, JS/TS, multi‑backends).
*   [API Reference](docs/api.md) – REST endpoints (`/scan`, `/analyze`, `/run`, `/snapshots`, `/simulate/remove`, `/graph`, `/backends`, `/plugins`).
*   [Architecture](docs/architecture.md) – core modules, connectors, project API integration, plugin system, security model.
*   [Developer Guide](docs/dev_guide.md) – internals, language analyzers, history, graph builder, simulation engine.
*   [Plugins](docs/plugins.md) – how to develop and configure plugins (including webhook notifications).

## Security

Jupiter is primarily a local development tool. However, when exposing the API (e.g. on a shared network), you should:

1.  **Configure a Token**: Add `security.token` in `jupiter.yaml`.
2.  **Restrict `run`**: Use `security.allow_run` and `security.allowed_commands` to disable or whitelist commands.
3.  **Use a Reverse Proxy**: For SSL/TLS termination if needed.

## Release Notes

- **1.0.4** – Hardened `/reports/last` (cached data now matches the API schema) and added a local notification fallback when the webhook URL is missing.
- **1.0.1** – Scan modal restyle (with persisted options) and automatic population of the Quality view right after each scan, even in Watch mode.
- **1.0.0** – First stable release. Includes standalone executable, full CI/CD integration, AI plugin support, and performance optimizations for large repositories.
- **0.1.5** – Ensures Web UI modals remain hidden (global `.hidden` helper) and fixes duplicated `startScan` logic that blocked the dashboard script.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

See [LICENSE](LICENSE).

### Installation

```bash
pip install -r requirements.txt
```

### Usage

**Scan a project:**
```bash
python -m jupiter.cli.main scan
```

**Start the Web UI:**
```bash
python -m jupiter.cli.main gui
```

_Note: the `scan` et `analyze` commands partagent désormais le même chemin d'initialisation (plugins + scanner) pour garantir un comportement cohérent._

**Start the API Server:**
```bash
python -m jupiter.cli.main server
```

## Documentation

Full documentation is available in the `docs/` directory:

* [User Guide](docs/user_guide.md)
* [API Reference](docs/api.md)
* [Architecture](docs/architecture.md)

## License

Proprietary / Internal.
