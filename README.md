# Jupiter

**Project Inspection & Observability Tool**

Jupiter is a modular tool designed to scan, analyze, and observe software projects. It combines static analysis, dynamic tracing, and a modern web interface to give you deep insights into your codebase.

## Features

*   **Static Analysis**: Scan files, detect languages, compute metrics (size, complexity, duplication).
*   **Dynamic Analysis**: Trace function calls during execution to find dead code.
*   **Incremental Scanning**: Fast re-scans using caching.
*   **Web Interface**: Visual dashboard for exploring your project.
*   **Plugins**: Extensible architecture.
*   **Meeting Integration**: License management and session control.

## Quick Start

### Windows Users
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

### Persistent state

When you change the served root in the Web UI or relaunch Jupiter without explicitly passing a directory, the tool reloads the last root saved in `~/.jupiter/state.json` and restores any cached scan data from `.jupiter/cache/last_scan.json` so your dashboards stay synchronized with the previous project.

## Documentation

Full documentation is available in the `docs/` directory:

*   [User Guide](docs/user_guide.md)
*   [API Reference](docs/api.md)
*   [Architecture](docs/architecture.md)
*   [Developer Guide](docs/dev_guide.md)

## Security

Jupiter is primarily a local development tool. However, when exposing the API (e.g. on a shared network), you should:

1.  **Configure a Token**: Add `security.token` in `jupiter.yaml`.
2.  **Use a Reverse Proxy**: For SSL/TLS termination if needed.

## Release Notes

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
