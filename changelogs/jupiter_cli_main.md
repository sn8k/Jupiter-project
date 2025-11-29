# Changelog – jupiter/cli/main.py
- Implemented argparse-based CLI with `scan`, `analyze`, and `server` commands.
- Wired commands to scanner, analyzer, and API server placeholders.
- Added ignore patterns, output-to-file support, JSON summaries, and top-N controls for scan/analyze commands.
- Added `gui` command to launch the static web interface (host/port configurable).
- Added path sanitization to strip quotes from CLI arguments (Windows compatibility).
- Integrated incremental scan flag into `scan` and `analyze` commands.
- Integrated `PluginManager` into `scan`, `analyze`, and `server` commands.
- Passed `plugins_config` from `jupiter.yaml` to `PluginManager`.
- Remember the last root between sessions via `jupiter.core.state`, so the CLI (and GUI) default to the previous project and keep that path in sync whenever a command or the UI launches.

