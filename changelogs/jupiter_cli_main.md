# Changelog – jupiter/cli/main.py

## Version 1.6.0 - Phase 9 Marketplace Commands
- Added plugin marketplace commands:
  - `jupiter plugins update <id>` : Update a plugin to a new version
    - `--source` : Update source (URL or path)
    - `--force` : Force update even if at latest version
    - `--install-deps` : Install Python dependencies
    - `--no-backup` : Skip creating backup of current version
  - `jupiter plugins check-updates` : Check for available plugin updates
    - `--json` : Output as JSON
- Enhanced `jupiter plugins install`:
  - `--install-deps` : Install Python dependencies from requirements.txt
  - `--dry-run` : Simulate installation without making changes
- Added handlers to `CLI_HANDLERS` registry:
  - `plugins_update`, `plugins_check_updates`
- Update supports backup/rollback on failure
- Import `handle_plugins_update`, `handle_plugins_check_updates`

## Version 1.5.0 - Phase 7.2 Plugin Signing Commands
- Added plugin signing commands:
  - `jupiter plugins sign <path>` : Sign a plugin with cryptographic signature
    - `--signer-id` : Signer identifier (default: $JUPITER_SIGNER_ID)
    - `--signer-name` : Signer name (default: $JUPITER_SIGNER_NAME)
    - `--trust-level` : Trust level (official/verified/community)
    - `--key` : Path to private key file
  - `jupiter plugins verify <path>` : Verify a plugin's signature
    - `--require-level` : Require minimum trust level (exit 1 if not met)
- Added handlers to `CLI_HANDLERS` registry:
  - `plugins_sign`, `plugins_verify`
- 10 new tests in test_cli_plugin_commands.py

## Version 1.4.0 - Phase 3.2 Plugin Management Commands
- Added plugin management commands:
  - `jupiter plugins install <source>` : Install from URL, ZIP, or Git
  - `jupiter plugins uninstall <id>` : Remove a plugin
  - `jupiter plugins scaffold <id>` : Generate new plugin skeleton
  - `jupiter plugins reload <id>` : Hot-reload in dev mode
- Added handlers to `CLI_HANDLERS` registry:
  - `plugins_install`, `plugins_uninstall`, `plugins_scaffold`, `plugins_reload`
- Install supports: local paths, local ZIP files, HTTP URLs, Git repositories
- Scaffold generates: `manifest.json`, `plugin.py`, `README.md`
- Reload requires developer mode enabled in Bridge config

## Version 1.3.0 - Dynamic Plugin CLI Commands
- Added `_add_plugin_commands()` to dynamically load CLI commands from plugins
- Added `_handle_plugin_command()` to execute plugin command handlers
- Plugin commands use prefix `p:plugin_id:cmd` to avoid conflicts

## Version 1.2.0 - Plugins Commands (Bridge v2)
- Added `plugins` command group with subcommands:
  - `jupiter plugins list` : List all registered plugins
  - `jupiter plugins info <id>` : Show plugin details
  - `jupiter plugins enable <id>` : Enable a plugin
  - `jupiter plugins disable <id>` : Disable a plugin
  - `jupiter plugins status` : Show Bridge system status
- Added imports from `jupiter.cli.plugin_commands`
- Added plugin handlers to `CLI_HANDLERS` registry:
  - `plugins_list`, `plugins_info`, `plugins_enable`, `plugins_disable`, `plugins_status`
- All commands support `--json` flag for machine-readable output

## Version 1.1.1 (2025-12-03) – CLI Parser Fix
- **Bug Fix**: Fixed argument parser where `--no-snapshot` and `--snapshot-label` were incorrectly attached to `scan_parser` after `analyze_parser` definition
- **Impact**: `scan` command now correctly accepts `--no-snapshot` and `--snapshot-label` flags
- **Test**: `python -m jupiter.cli.main scan --snapshot-label "test" --no-snapshot` now works

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
