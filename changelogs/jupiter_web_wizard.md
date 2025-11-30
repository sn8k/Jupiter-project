# Web UI Project Wizard

## Added
- **Web UI Wizard**: Added a "Project Wizard" modal in the Web UI that appears when no projects are configured.
- **Setup Mode**: Updated the server to start in a "setup mode" when no configuration is found, allowing access to project creation endpoints.
- **API Updates**: 
    - `GET /config` now returns default values if no project is loaded.
    - `POST /run` now checks for active project configuration before execution.
    - `verify_token` allows admin access in setup mode to facilitate project creation.

## Changed
- **CLI**: Removed the terminal-based wizard in favor of the Web UI wizard.
- **App Startup**: `handle_app` now gracefully handles missing configuration by using defaults for the server.
