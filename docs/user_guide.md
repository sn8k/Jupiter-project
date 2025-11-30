# Jupiter User Guide

Jupiter is a tool for inspecting, analyzing, and observing your software projects. It provides a CLI for quick checks and a web interface for a more visual experience.

## Installation

### Windows Users (Standalone)
Download the `jupiter.exe` executable. Double-click it to launch the application. No other dependencies are required.

### Windows Users (Source)
Simply double-click **`Jupiter UI.cmd`** in the project root. This script will:
1. Create a virtual environment if needed.
2. Install dependencies.
3. Launch the application and open your browser.

### Manual Installation (Developers)
(Assuming you are in the development environment)

```bash
pip install -r requirements.txt
```

## Getting Started (User Mode)

To start Jupiter with the full graphical interface:

```bash
python -m jupiter.cli.main
```

This will:
1. Load your configuration.
2. Start the API server and Web UI.
3. Open your default web browser.

If no project is configured, an onboarding wizard will help you create a default configuration.

## Configuration

Jupiter looks for a `jupiter.yaml` file in the project root. You can configure the server, UI, and meeting integration there.

Example `jupiter.yaml`:

```yaml
server:
  host: "127.0.0.1"
  port: 8000

ui:
  theme: "dark"
  language: "en"

performance:
  parallel_scan: true
  max_workers: null  # Auto-detect
  graph_simplification: false
  max_graph_nodes: 1000

meeting:
  enabled: true
  deviceKey: "YOUR_DEVICE_KEY"

project_api:
  type: "openapi"
  base_url: "http://localhost:8000"
  openapi_url: "/openapi.json"
```

## Web Interface

The Web Interface is the primary way to interact with Jupiter. It provides a visual dashboard and access to all features.

### Dashboard
The dashboard shows a panorama of your project:
- **Status Badges**: Meeting license status, scan status.
- **Stats Grid**: File count, total size, last update time.
- **Live Watch**: Real-time file change events (when Watch mode is active).

### Features

#### Scanning
Click the **Scan** button in the header to open the scan options:
- **Include hidden files**: Toggle scanning of dotfiles.
- **Incremental scan**: Use cache for faster results.
- **Ignore patterns**: Specify glob patterns to exclude (e.g., `*.log`).
- **Snapshot label**: Provide an optional text that will tag the resulting snapshot (defaults to an automatic timestamp).
- **Skip snapshot**: Turn off snapshot persistence for experimental scans.

#### Running Commands
Click the **Run** button to execute shell commands within the project root:
- **Command**: The command string (e.g., `python script.py`).
- **Dynamic Analysis**: Enable tracing to capture function calls during execution.

#### Watch Mode
Click **Watch** to enable real-time monitoring. File changes will appear in the "Live Watch" panel on the dashboard.

#### Settings
The **Settings** view allows you to configure `jupiter.yaml` directly:
- **Server/GUI Host & Port**: Network configuration.
- **Meeting**: Enable/Disable and set Device Key.
- **Theme & Language**: Customize the UI appearance.
- **Update**: Trigger a self-update from a ZIP file or Git URL.

#### History
The **History** view lists every stored snapshot (newest first) with their labels, timestamps, file counts, and size deltas. Select any two snapshots to render a diff showing:
- Files added/removed/modified with size/function deltas.
- Aggregate metrics delta (file count, project size, total/potentially unused functions).
- Function-level additions/removals grouped by file.

Snapshots are refreshed automatically after each scan (CLI, API, or GUI) and when other users trigger scans via WebSockets.

## CLI Commands (Advanced)

The main entry point is `python -m jupiter.cli.main` (or `jupiter` if installed).

### `scan`

Scans a directory and outputs a JSON report.

```bash
# Scan current directory
python -m jupiter.cli.main scan

# Scan specific directory and save to file
python -m jupiter.cli.main scan /path/to/project --output report.json

# Ignore specific patterns
python -m jupiter.cli.main scan --ignore "*.log" --ignore "tmp/"

# Incremental scan (uses cache for faster results)
python -m jupiter.cli.main scan --incremental

# Force scan without cache (clears existing cache)
python -m jupiter.cli.main scan --no-cache

# Assign a custom label to the stored snapshot
python -m jupiter.cli.main scan --snapshot-label "pre-release"

# Skip snapshot creation for this run
python -m jupiter.cli.main scan --no-snapshot

# Enable performance profiling
python -m jupiter.cli.main scan --perf
```

**Note on Caching:**
*   `--incremental`: Uses the cache from previous scans to skip unchanged files. It checks file modification time and size.
*   `--no-cache`: Ignores any existing cache and forces a full re-scan. This is useful if you suspect the cache is corrupted or want to ensure a fresh state.
*   Volatile files (e.g., `.tmp`, `.log`, `.pyc`) are automatically excluded from the cache to prevent pollution.

### `analyze`

Scans and provides a summary analysis (file counts, sizes, Python stats).

```bash
# Text summary
python -m jupiter.cli.main analyze

# JSON output
python -m jupiter.cli.main analyze --json

# Incremental analysis
python -m jupiter.cli.main analyze --incremental

# Force analysis without cache
python -m jupiter.cli.main analyze --no-cache

# Enable performance profiling
python -m jupiter.cli.main analyze --perf
```

**Note on Analysis Cache:**
*   Jupiter caches analysis results (like complexity scores) for files that haven't changed.
*   Using `--incremental` (or just running analyze repeatedly without `--no-cache`) will speed up the process by reusing these results.
*   Using `--no-cache` forces a re-calculation of all metrics.

### `server`

Starts the API server.

```bash
python -m jupiter.cli.main server --port 8000
```

### `gui`

Starts the web interface (and the server in the background).

```bash
python -m jupiter.cli.main gui
```

### `snapshots`

Inspect the snapshot history saved under `.jupiter/snapshots/`.

```bash
# List available snapshots (newest first)
python -m jupiter.cli.main snapshots list

# Show metadata or (with --report) the full stored scan
python -m jupiter.cli.main snapshots show scan-1700000000000 --report

# Diff two snapshots to understand project evolution
python -m jupiter.cli.main snapshots diff scan-1699999990000 scan-1700000000000
```

Add `--json` to any subcommand to integrate with scripts or dashboards.

### `watch`

Watches a directory for changes and logs them.

```bash
python -m jupiter.cli.main watch
```

### `update`

Updates Jupiter from a source (ZIP file or Git repository).

```bash
# Update from a local ZIP
python -m jupiter.cli.main update /path/to/jupiter-update.zip

# Update from Git (simulated)
python -m jupiter.cli.main update git+https://github.com/sn8k/jupiter.git
```

## Features

### Incremental Scan

Use the `--incremental` flag with `scan` or `analyze` to speed up processing. Jupiter caches file metadata in `.jupiter/cache/` and only re-scans files that have changed since the last run.

### Dynamic Analysis

Jupiter can trace function calls during execution.
1. Use `python -m jupiter.cli.main run "python my_script.py" --with-dynamic`.
2. The report will include a `dynamic` section with call counts.
3. Subsequent `analyze` calls will combine static and dynamic data to identify "truly unused" functions.

### Code Quality

The `analyze` command (and the Web UI) reports on code quality metrics:
- **Complexity**: Cyclomatic complexity estimation for Python files.
- **Duplication**: Detection of duplicated code blocks (clusters).

### Plugins

Jupiter supports plugins to extend functionality.
- Configure plugins in `jupiter.yaml`:
  ```yaml
  plugins:
    enabled: ["ai_helper", "code_quality_stub", "notifications_webhook"]
    disabled: []
  ```
- Plugins can hook into `scan`, `analyze`, and `run` events.

The **Plugins** view in the Web UI lists all loaded plugins, shows whether they are enabled, and (for configurable plugins such as `notifications_webhook`) exposes a small form to adjust settings (e.g. webhook URL).

### Meeting Integration

If configured with a `deviceKey`, Jupiter connects to the Meeting service for license validation.
- **Valid License**: Full access to all features.
- **No License / Invalid**: Trial mode (limited time, restricted features like `watch` or `run`).
- Check status via the Web UI or API `/meeting/status`.

## Ignoring Files

Create a `.jupiterignore` file in your project root to exclude files from scans. It uses gitignore syntax.

```text
__pycache__/
*.pyc
node_modules/
```

## Performance Tips

- **Large Files**: Jupiter automatically skips files larger than 10MB to prevent memory issues.
- **Caching**: Use incremental scans (default) to save time. Use `--no-cache` only when necessary.
- **Dynamic Analysis**: Running `jupiter run` with tracing enabled can be slower; use it for targeted debugging.

### Simulation

You can simulate the removal of a file or function to see the potential impact on your project (broken imports, broken calls).

**CLI:**
```bash
python -m jupiter.cli.main simulate remove jupiter/core/scanner.py
python -m jupiter.cli.main simulate remove "jupiter/core/scanner.py::FileMetadata"
```

**Web UI:**
In the **Files** or **Functions** view, click the trash icon (🗑️) next to an item to trigger the simulation. A modal will display the risk score and list of impacted files.

### Live Map

The **Live Map** view renders an interactive graph of your project:
- Nodes represent files and functions (Python in blue, JS/TS in yellow).
- Edges represent imports and function calls.
- Node size and color can reflect size, complexity, or dynamic usage.

Use zoom and pan to explore the structure, and click on a node to highlight its neighborhood.

### Project APIs (OpenAPI)

If you configure a `project_api` section in `jupiter.yaml`, Jupiter will:
- Fetch your OpenAPI schema.
- List endpoints (path, method, tags) in the **API** view.
- Optionally correlate endpoints with files/handlers when possible.

Example configuration:

```yaml
project_api:
  type: "openapi"
  base_url: "http://localhost:8000"
  openapi_url: "/openapi.json"
```

### Polyglot Support (Python + JS/TS)

Jupiter analyzes both Python and JavaScript/TypeScript code:
- Detects `.py`, `.js`, `.ts`, `.jsx`, `.tsx` files.
- Extracts functions and imports using language‑specific analyzers.

## CI/CD Integration

Jupiter can be used in your CI/CD pipelines to enforce quality gates.

### Configuration

Add a `ci` section to your `jupiter.yaml`:

```yaml
ci:
  fail_on:
    max_complexity: 20          # Fail if any file has complexity > 20
    max_duplication_clusters: 5 # Fail if more than 5 duplication clusters found
    max_unused_functions: 50    # Fail if more than 50 potentially unused functions found
```

### CLI Command

Use the `ci` command in your pipeline script:

```bash
# Run analysis and check thresholds
python -m jupiter.cli.main ci

# Output JSON for parsing
python -m jupiter.cli.main ci --json

# Override thresholds via CLI
python -m jupiter.cli.main ci --fail-on-complexity 15
```

If any threshold is exceeded, the command exits with code `1`, causing the pipeline step to fail.

### GitHub Actions Example

Create `.github/workflows/jupiter-ci.yml`:

```yaml
name: Jupiter CI
on: [push, pull_request]
jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.10"
      - run: pip install -r requirements.txt
      - run: python -m jupiter.cli.main ci --json
```
- Includes JS/TS metrics in analysis summaries and Live Map.

