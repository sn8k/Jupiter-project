# Changelog – jupiter/web/app.py
- Added `JupiterWebUI` static HTTP server backed by `ThreadingTCPServer`.
- Added `WebUISettings` dataclass to configure host, port, and project root.
- Exposed `launch_web_ui` helper to start the GUI with minimal boilerplate.
- Context payload now includes `api_base_url` (configurable via `JUPITER_API_BASE`) so the frontend can target the correct API host.
