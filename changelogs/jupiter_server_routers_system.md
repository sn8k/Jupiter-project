# Changelog – jupiter/server/routers/system.py
- Replaced ad-hoc root/config wiring with the shared `SystemState` helper for metrics, config reads, and runtime rebuilds.
- Root updates now preserve Meeting keys, refresh Meeting adapter/project manager/plugin manager in one place, and reset the history manager only when needed.
- Config updates call the same helper, ensuring WebSocket clients receive consistent `CONFIG_UPDATED` payloads.
