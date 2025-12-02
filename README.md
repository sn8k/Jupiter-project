# Jupiter

**Project Inspection & Observability Tool**

Jupiter is a modular tool designed to scan, analyze, and observe software projects. It combines static analysis, dynamic tracing, and a modern web interface to give you deep insights into your codebase.

## Features

*   **Static Analysis**: Scan files, detect languages, compute metrics (size, complexity, duplication).
*   **Dynamic Analysis**: Trace function calls during execution to find dead code.
*   **Incremental Scanning**: Fast re-scans using caching.
*   **Snapshot History**: Automatically persist each scan, label important milestones, and diff snapshots via CLI/API/UI.
*   **Live Map Plugin**: Interactive dependency graph combining static structure, hotspots, and dynamic usage. Now a full plugin with sidebar view, contextual help panel, configurable settings, and improved import resolution for JS/TS.
*   **Plugin Watchdog**: Developer-oriented system plugin that monitors plugin files for changes and triggers automatic hot-reloads without restarting Jupiter. Configurable check interval and per-plugin reload tracking.
*   **Plugin Bridge**: Core services gateway that decouples plugins from Jupiter internals. Provides stable, versioned API access to scanning, caching, events, configuration, and history services. Enables future-proof plugin development.
*   **Polyglot Support**: First-class support for Python and JS/TS projects.
*   **Pylance Diagnostics**: Pyright-powered analysis in the Pylance view now explains when no Python files are present, avoiding misleading “no data” states on polyglot repos.
*   **Simulation**: Impact analysis when virtually removing a file or function.
*   **Project API Connectors**: OpenAPI connector to inspect your own project's HTTP API.
*   **Web Interface**: Visual dashboard for exploring your project.
*   **CI / Quality Gates View (v1.2.0)**: Complete quality gates workflow in the WebUI with configurable thresholds, metrics display, violations list, and CI history.
*   **Advanced Scan Options (v1.2.0)**: Skip cache, disable snapshot, custom snapshot labels from the scan modal.
*   **Snapshot Detail View (v1.2.0)**: View full snapshot summary and export individual snapshots as JSON.
*   **License Details Panel (v1.2.0)**: Complete Meeting license info in Settings with refresh capability.
*   **Plugins & Webhooks**: Extensible plugin architecture with webhook notifications.
*   **Notification Center**: Global toast popups surface plugin alerts (including the API connectivity event) and webhook messages directly inside the Web UI.
*   **Manual Duplicate Linking**: Merge overlapping duplication clusters directly from the Code Quality plugin UI; linked definitions live in `.jupiter/manual_duplication_links.json` and can be rechecked on demand.
*   **Configurable Logging**: Set the global log level (Debug/Info/Warning/Error/Critical) from the Settings page and keep CLI/API/Uvicorn aligned.
*   **Plugin-Aware Logging**: All bundled plugins emit structured INFO/DEBUG traces that honor the Settings log level so troubleshooting never requires patching code.
*   **Plugin Settings Persistence**: Notification/Code Quality options now load from and save to the unified config, and their UI cards share the refreshed two-column Settings layout for faster edits.
*   **Version Awareness**: Le bandeau principal et la carte "Mise à jour" affichent la version du cœur (fichier `VERSION`) tandis que la page Plugins expose désormais le numéro propre à chaque module.
*   **Meeting Integration**: License management and session control.
*   **Multi-Project Management**: Manage multiple projects with distinct configurations and switch between them easily.
*   **Projects Control Center**: Dedicated Web UI dashboard to view the active project, key stats, and manage configured roots in one place.
*   **AI Suggestions Evidence**: Duplication recommendations now surface the exact file/line, nearest function, and a code excerpt inside reports and the Suggestions tab.
*   **Dynamic Multilingual UI (v1.3.0)**: Fully dynamic i18n system with automatic language detection and version tracking. The language selector auto-populates with available translations, each file exposing its own version via `_meta` metadata.
*   **Fun Language Packs (v1.3.0)**: Beyond French and English, the Web UI now ships with three fun translations—Klingon 🖖, Sindarin/Elvish 🧝, and Pirate French 🏴‍☠️—for entertainment and community enjoyment.

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

When you change the served root in the Web UI or relaunch Jupiter without explicitly passing a directory, the tool reloads the default project defined in the global registry (`~/.jupiter/global_config.yaml` with legacy fallback to `global.yaml`) and keeps `~/.jupiter/state.json` in sync. Cached scan data from `.jupiter/cache/last_scan.json` and the snapshot history in `.jupiter/snapshots/` are restored per project so dashboards and diffs stay aligned with the same root. Activating a project from the Web UI writes it back to the registry so the next CLI/GUI launch opens the same project automatically.

Legacy registries are auto-normalized: entries still pointing to `jupiter.yaml` are rewritten to `<project>.jupiter.yaml` and paths are stored absolute so multi-project switching, activation, and deletion stay reliable across upgrades.

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

1.  **Configure a Token**: Add `security.token` in your `<project>.jupiter.yaml`.
2.  **Restrict `run`**: Use `security.allow_run` and `security.allowed_commands` to disable or whitelist commands.
3.  **Use a Reverse Proxy**: For SSL/TLS termination if needed.

## Meeting License Integration

Jupiter can optionally verify its license via the Meeting backend API. When configured with a `deviceKey` in `~/.jupiter/global_config.yaml`:

- License is verified at startup against Meeting API
- A valid license requires: `authorized == true`, `device_type == "Jupiter"`, and `token_count > 0`
- Without a valid license, Jupiter runs in restricted mode (10-minute trial)

**Check license via CLI:**
```bash
python -m jupiter.cli.main meeting check-license
```

**API endpoints:**
- `GET /license/status` – Get detailed license verification status
- `POST /license/refresh` – Force a license re-check (admin only)

See [Manual.md](Manual.md) for detailed configuration.

## Release Notes

- **1.8.1** – Live Map Plugin: migrated from core to plugin architecture with sidebar view, help panel, and settings. Plugin Watchdog: new system plugin for auto-reloading modified plugins during development. Comprehensive logging for livemap debugging.
- **1.3.3** – Settings Save Fix: Added `PATCH /config` endpoint for partial config updates. Fixed Code Quality plugin Save button (JS was not executing when injected via innerHTML).
- **1.3.2** – Log Level Setting Restored: the global log level dropdown was accidentally removed in v1.3.1 and is now back in the Security section of Settings.
- **1.3.1** – Settings UX Refactor: each section (Network, Interface, Security) now has its own Save button. Performance settings moved to Projects view. Fixed Code Quality plugin config save and project API restoration on startup.
- **1.3.0** – Dynamic i18n: language selector auto-detects available translations with versioned `_meta` metadata. Adds 3 fun language packs: Klingon, Elvish, and Pirate French. Full translation audit with 729 keys in perfect French/English parity.
- **1.2.1** – Settings UX Improvements & User Management.
- **1.1.12** – La page Settings adopte une grille deux colonnes avec carte "Mise à jour" dédiée, les panneaux plugins (Notifications & Code Quality) reçoivent une UI plus claire avec états de sauvegarde, et leurs paramètres sont maintenant persistés dans la configuration globale/projet.
- **1.1.11** – La vue Qualité est désormais intégrée dans l'onglet *Dashboard* du plugin Code Quality (tableaux complexité/duplication + export), avec un panneau de paramètres revu et plus descriptif.
- **1.1.10** – Internal deduplication: shared helpers now drive CLI scan/analyze setup, server snapshot handling, and project UI mutations to reduce drift.
- **1.1.9** – AI duplication suggestions now include concrete file:line evidence in the API response and the Web UI Suggestions tab.
- **1.1.4** – Projects Control Center fully wired to `/projects` (refresh, activate, delete) with dashboard stats and documented multi-project management.
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
