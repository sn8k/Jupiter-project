# Changelog – jupiter/server/routers/system.py
- Replaced ad-hoc root/config wiring with the shared `SystemState` helper for metrics, config reads, and runtime rebuilds.
- Root updates now preserve Meeting keys, refresh Meeting adapter/project manager/plugin manager in one place, and reset the history manager only when needed.
- Config updates call the same helper, ensuring WebSocket clients receive consistent `CONFIG_UPDATED` payloads.
- API `/config` now reads/writes `log_level`, normalizes user-provided aliases, and forwards the value to the runtime rebuild.
- Raw config endpoints and project initialization now resolve the project config path via the new `<project>.jupiter.yaml` naming (with legacy support), so the UI edits the correct file even after the rename.
- Settings API now exposes `log_path` to allow configuring the destination log file path from the UI.
- Added `/projects/{id}/ignore` to persist per-project ignore globs in the global registry and serve them to the UI/projects list.
- Added `/projects/{id}/api_config` (GET/POST) to read/update API inspection settings per project without touching unrelated config fields.
