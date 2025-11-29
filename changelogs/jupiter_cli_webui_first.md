# Changelog - WebUI First Experience

## Added
- **CLI Entry Point**: `python -m jupiter.cli.main` (without arguments) now launches the full application (API + WebUI) and opens the browser.
- **WebUI Onboarding**: Added a "First Run" modal in the WebUI if no `jupiter.yaml` is found.
- **API Endpoint**: Added `/init` endpoint to create a default configuration.
- **Documentation**: Updated `README.md`, `Manual.md`, and `docs/user_guide.md` to reflect the new WebUI-first approach.

## Changed
- **CLI**: Made subcommands optional in `jupiter.cli.main`.
- **WebUI**: Updated `app.js` to check for configuration status on startup.
