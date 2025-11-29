# Jupiter User Guide

Jupiter is a tool for inspecting, analyzing, and observing your software projects. It provides a CLI for quick checks and a web interface for a more visual experience.

## Installation

### Windows Users (Recommended)
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

meeting:
  enabled: true
  deviceKey: "YOUR_DEVICE_KEY"
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
    enabled: ["ai_helper", "code_quality_stub"]
    disabled: []
  ```
- Plugins can hook into `scan`, `analyze`, and `run` events.

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

