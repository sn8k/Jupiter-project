# Changelog – jupiter/web/app.py
- Added `JupiterWebUI` static HTTP server backed by `ThreadingTCPServer`.
- Added `WebUISettings` dataclass to configure host, port, and project root.
- Exposed `launch_web_ui` helper to start the GUI with minimal boilerplate.
