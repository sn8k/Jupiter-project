# Jupiter

Version : 1.8.49  
**Project Inspection & Observability Tool**

Jupiter scans, analyzes, and observes software projects through a unified pipeline used by the CLI, API, and Web UI. It blends static analysis, optional dynamic traces, snapshots, and plugins to help you understand what your codebase does and how it evolves.

## Key Capabilities

- Static + incremental scans with cache reuse and project-level ignore globs.
- Analyze summaries: largest files, per-extension metrics, hotspots, refactoring hints, Python usage, and plugin-enriched outputs.
- Snapshot history with automatic persistence on scans and CLI/API/UI diff tooling.
- Simulation (`simulate remove`) to estimate impacts of deleting a file/function.
- **Bridge v2 Plugin System** (1400+ tests): Complete plugin architecture with:
  - Plugin lifecycle management (discover, initialize, register, ready states)
  - CLI, API, and WebUI contribution registries
  - Job system with progress tracking, cancellation, and circuit breakers
  - Event bus (pub/sub) with WebSocket propagation
  - Permissions system with signature verification (OFFICIAL, VERIFIED, COMMUNITY, UNSIGNED)
  - Hot reload in developer mode (with dev mode guard)
  - Metrics, alerting, notifications, usage stats, error reporting
  - Governance: whitelist/blacklist and feature flags
- Plugins: Code Quality (duplication/complexity + manual links), Live Map graph, Pylance analyzer, Notifications webhook, AI Helper, Watchdog hot-reload, Bridge services gateway, Settings update helper.
- Multi-project registry with activation from Web UI or API; connectors for local FS, remote Jupiter, or OpenAPI projects.
- Meeting license checks (optional) with refresh endpoint and restricted fallback when unlicensed.
- Dynamic i18n Web UI, Settings-driven logging (including file path), and token-based access control for API/WS.
- Roadmaps suivies dans `TODOs/` dont la migration SQL (stockage snapshots/configs/états) gérée automatiquement par Jupiter.

## Quick Start (GUI-first)

1) **Windows packaged**: double-click `jupiter.exe`.
2) **Windows source**: double-click `Jupiter UI.cmd` to set up the venv and launch the Web UI.
3) **Any platform (dev)**:
```bash
pip install -r requirements.txt
python -m jupiter.cli.main               # starts API + Web UI and opens your browser
```

The active project is read from `~/.jupiter/global_config.yaml` (legacy `global.yaml` supported) and synced with `~/.jupiter/state.json`. The Web UI Projects panel lets you register, activate, or delete projects without restarting.

## CLI Commands (advanced / SSH / CI)

```bash
python -m jupiter.cli.main scan [root] [--ignore GLOB]* [--show-hidden] [--incremental] [--no-cache] [--no-snapshot] [--snapshot-label TEXT] [--output report.json] [--perf]
python -m jupiter.cli.main analyze [root] [--json] [--top N] [--ignore GLOB]* [--show-hidden] [--incremental] [--no-cache] [--perf]
python -m jupiter.cli.main ci [root] [--json] [--fail-on-complexity N] [--fail-on-duplication N] [--fail-on-unused N]
python -m jupiter.cli.main snapshots list|show|diff [args]
python -m jupiter.cli.main simulate remove <path|path::function> [root] [--json]
python -m jupiter.cli.main server [root] [--host HOST] [--port PORT]
python -m jupiter.cli.main gui [root] [--host HOST] [--port PORT]
python -m jupiter.cli.main run <command> [root] [--with-dynamic]
python -m jupiter.cli.main watch [root]
python -m jupiter.cli.main meeting check-license [root] [--json]
python -m jupiter.cli.main autodiag [root] [--api-url URL] [--diag-url URL] [--skip-cli] [--skip-api] [--skip-plugins] [--timeout SECONDS]
python -m jupiter.cli.main update <source> [--force]

# Plugin Management (Bridge v2)
python -m jupiter.cli.main plugins list [--json]
python -m jupiter.cli.main plugins info <id>
python -m jupiter.cli.main plugins enable|disable <id>
python -m jupiter.cli.main plugins status
python -m jupiter.cli.main plugins install <source> [--force] [--install-deps] [--dry-run]
python -m jupiter.cli.main plugins uninstall <id> [--force]
python -m jupiter.cli.main plugins update <id> [--source URL] [--no-backup] [--force]
python -m jupiter.cli.main plugins check-updates [--json]
python -m jupiter.cli.main plugins sign <path> [--signer-id ID] [--signer-name NAME] [--trust-level LEVEL]
python -m jupiter.cli.main plugins verify <path> [--require-level LEVEL]
python -m jupiter.cli.main plugins scaffold <id>
python -m jupiter.cli.main plugins reload <id>  # requires developer_mode: true
python -m jupiter.cli.main plugins jobs [--json]  # list active jobs
python -m jupiter.cli.main plugins jobs <job_id>   # job details
python -m jupiter.cli.main plugins jobs cancel <job_id>  # cancel a job
```

(*) `--ignore` can be specified multiple times for multiple globs.

`scan`, `analyze`, and `ci` share the same initialization (plugins, cache, snapshot/persistence, performance toggles) so they behave identically whether called from a laptop, a CI runner, or a remote shell.

### Snapshot Workflow

- Reports are cached in `.jupiter/cache/last_scan.json`.
- Snapshots are written to `.jupiter/snapshots/scan-*.json` unless `--no-snapshot` is set; label with `--snapshot-label`.
- Inspect history via CLI (`snapshots list|show|diff`), API (`/snapshots`, `/snapshots/{id}`, `/snapshots/diff`), or the Web UI History panel.

### Simulation

`simulate remove` estimates broken imports and impacted functions/classes before deleting code. Available from CLI and `/simulate/remove`.

### Plugin Management

The Bridge v2 plugin system provides comprehensive plugin management:
- **Install**: From local path or URL with signature verification and dependency installation
- **Update**: With automatic backup and rollback on failure
- **Sign/Verify**: Cryptographic signatures with trust levels (OFFICIAL, VERIFIED, COMMUNITY, UNSIGNED)
- **Hot Reload**: Reload plugins without server restart (developer mode only)
- **Scaffold**: Generate new plugin boilerplate

See `docs/PLUGIN_DEVELOPER_GUIDE.md` for creating new plugins.

## API & Web UI Overview

- Base API: `http://127.0.0.1:8000` (default). Token protection uses `security.token` or per-user tokens declared in `<project>.jupiter.yaml`.
- Web UI assets are served with `Cache-Control: no-store` / `Pragma: no-cache` so browsers always reload the latest HTML/CSS/JS; disable any proxy cache if you front the UI.
- Core endpoints: `/scan`, `/analyze`, `/ci`, `/snapshots`, `/snapshots/{id}`, `/snapshots/diff`, `/simulate/remove`, `/reports/last`, `/metrics`, `/health`.
- Project & config: `/projects` CRUD + activate, `/config`, `/config/root`, `/config/raw`, `/project/root-entries`, `/backends`.
- Plugins v2: `/plugins/v2`, `/plugins/v2/{id}`, `/plugins/v2/status`, `/plugins/v2/ui/manifest`, `/plugins/v2/{id}/reload`.
- Jobs: `/jobs`, `/jobs/{id}`, `/jobs/{id}/cancel`, `/jobs/history`.
- Legacy plugins: `/plugins`, `/plugins/{name}/toggle|config|test`, `/plugins/code_quality/manual-links`, `/plugins/livemap/*`, `/plugins/watchdog/*`, `/plugins/bridge/*`, `/plugins/settings_update/*`.
- Auth & users: `/login`, `/users`, `/me`.
- Meeting license: `/license/status`, `/license/refresh`.
- Watch & WS: `/watch/start|stop|status|calls`, `/watch/calls/reset`, WebSocket at `/ws` (passes token as query when enabled).

See `docs/api.md` for request/response schemas, admin vs viewer protections, and copy-pastable `curl` examples.

## Security

- Set `security.token` or user tokens/roles in `<project>.jupiter.yaml`.
- Disable shell execution or whitelist allowed commands with `security.allow_run` and `security.allowed_commands` (affects `/run` and CLI `run`).
- Use a reverse proxy for TLS when exposing the API.
- **Plugin signatures**: Verify plugin authenticity and trust levels before installation.

## Meeting License Integration

Add `deviceKey` to `~/.jupiter/global_config.yaml` to enable license verification. `meeting check-license` and `/license/status` reveal the current status; `/license/refresh` forces a re-check. Unlicensed mode runs with time-limited features.

## Documentation

Full documentation lives in `docs/`:
- `docs/user_guide.md` – GUI + CLI walkthroughs (snapshots, simulation, Live Map, multi-backends).
- `docs/api.md` – REST endpoints, auth roles, sample payloads.
- `docs/architecture.md` – core modules, connectors, plugin system, security.
- `docs/dev_guide.md` – internals and extension points.
- `docs/plugins.md` – building/configuring plugins (webhooks, livemap, watchdog, bridge).
- `docs/plugins_architecture.md` – Bridge v2 plugin architecture design.
- `docs/PLUGIN_DEVELOPER_GUIDE.md` – complete guide for plugin developers.
- `docs/PLUGIN_MIGRATION_GUIDE.md` – migrating v1 plugins to Bridge v2.

## Contributing

See `CONTRIBUTING.md`.

## License

Proprietary / Internal.
