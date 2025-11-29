# Changelog – jupiter/core/state.py
- Added a lightweight state helper that saves the last served root under `~/.jupiter/state.json` and returns it only if the directory still exists so the CLI/API can reconnect to the same project without extra arguments.
