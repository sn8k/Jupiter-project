# Changelog – jupiter/cli/main.py

## Version 1.2.0 (2025-12-02) – Phase 4: Autodiag Command
- Added `autodiag` command to CLI with full argument support:
  - `--json`: Output as JSON
  - `--api-url`: Override main API URL
  - `--diag-url`: Override diag API URL
  - `--skip-cli`: Skip CLI scenario tests
  - `--skip-api`: Skip API scenario tests
  - `--skip-plugins`: Skip plugin hook tests
  - `--timeout`: Timeout per scenario (seconds)
- Added `handle_autodiag` to `CLI_HANDLERS` registry
- Import `handle_autodiag` from command_handlers

## Version 1.1.0 (2025-12-02) – Phase 2: CLI Handler Registry
- Added `CLI_HANDLERS` dict mapping command names to handler functions
- Added `get_cli_handlers()` function for autodiag introspection
- Added version docstring header
- Exposes all 14 CLI handlers for diagnostic endpoint consumption

## Previous Changes
- Implemented argparse-based CLI with `scan`, `analyze`, and `server` commands.
- Wired commands to scanner, analyzer, and API server placeholders.
- Added ignore patterns, output-to-file support, JSON summaries, and top-N controls for scan/analyze commands.
- Added `gui` command to launch the static web interface (host/port configurable).
- Added path sanitization to strip quotes from CLI arguments (Windows compatibility).
- Integrated incremental scan flag into `scan` and `analyze` commands.
- Integrated `PluginManager` into `scan`, `analyze`, and `server` commands.
- Passed `plugins_config` from `jupiter.yaml` to `PluginManager`.
- Remember the last root between sessions via `jupiter.core.state`, so the CLI (and GUI) default to the previous project and keep that path in sync whenever a command or the UI launches.
- CLI bootstrap now applies the project `logging.level` (Debug/Info/Warning/Error/Critical) so all commands share the same verbosity as the UI settings.
- Logging setup now honors an optional `logging.path` (when configured) to mirror the Settings page log destination in CLI runs.
