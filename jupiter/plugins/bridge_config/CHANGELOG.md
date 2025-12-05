# Changelog - bridge_config Plugin

## Version 1.0.0

### Added
- Initial release of Bridge Configuration plugin (v2 architecture)
- Settings panel for Bridge infrastructure configuration
- Configuration options:
  - Developer Mode toggle
  - Allow unsigned plugins setting
  - Hot reload toggle
  - Verbose logging toggle
  - Plugin timeout configuration
  - Health check interval
  - Max concurrent jobs
  - Governance mode selection
  - Metrics collection toggle
  - Circuit breaker threshold
- API endpoints:
  - `GET /bridge_config/status` - Get Bridge status
  - `GET /bridge_config/config` - Get current config
  - `PUT /bridge_config/config` - Update config
  - `GET /bridge_config/dev-mode` - Get dev mode status
  - `POST /bridge_config/dev-mode/enable` - Enable dev mode
  - `POST /bridge_config/dev-mode/disable` - Disable dev mode
  - `GET /bridge_config/governance` - Get governance status
  - `GET /bridge_config/plugins-summary` - Get plugins summary
- WebUI panel with:
  - Bridge status overview
  - Plugins summary (total, ready, error, legacy counts)
  - Quick actions (toggle dev mode, refresh, view plugins)
  - Dev mode settings section
  - Expandable plugins list
- i18n support (English and French)
- Auto-generated settings form via config schema
