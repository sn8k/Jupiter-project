# Changelog - jupiter/plugins/bridge_config

## Version 1.0.1

### Fixed
- Fixed `GovernanceConfig` attribute access: `list_mode` → `mode`
- Fixed feature flags access: replaced deprecated `gov.config.feature_flags` with iteration over `global_feature_flags` and `plugin_policies`
- Updated `__init__.py` governance status retrieval to use correct attributes
- Updated `server/api.py` governance endpoint to properly iterate feature flags

## Version 1.0.0

### Added
- Created new `bridge_config` plugin (v2 architecture) to expose Bridge settings in the WebUI
- Plugin manifest (`plugin.yaml`) with:
  - System plugin type
  - Config schema for auto-UI generation with 10 configurable parameters
  - API and UI contributions declarations
  - i18n support (en/fr)
- Main module (`__init__.py`) implementing:
  - Bridge v2 lifecycle hooks (init, shutdown, health, metrics)
  - Configuration application to Bridge subsystems
  - Public API for status retrieval and config updates
- Server API (`server/api.py`) with endpoints:
  - `/status` - Bridge status overview
  - `/config` - Get/update configuration
  - `/dev-mode` - Developer mode status and toggle
  - `/governance` - Governance status
  - `/plugins-summary` - Loaded plugins summary
  - `/health` and `/metrics` - Standard plugin endpoints
- WebUI panel (`web/panels/main.js`) featuring:
  - Status section with Bridge availability, dev mode, and governance indicators
  - Plugins summary with counts (total, ready, error, legacy)
  - Quick actions for dev mode toggle, refresh, and plugins view
  - Developer mode settings section
  - Expandable plugins list
- i18n files for English and French translations
- Default configuration (`config.yaml`)
- Plugin changelog

### Configuration Options
- `developer_mode` - Enable/disable developer mode
- `allow_unsigned_plugins` - Allow plugins without signatures
- `hot_reload_enabled` - Enable automatic plugin reloading
- `verbose_logging` - Enable detailed debug logging
- `plugin_timeout` - Default operation timeout (5-300s)
- `health_check_interval` - Health check frequency (10-600s)
- `max_concurrent_jobs` - Max parallel jobs (1-20)
- `governance_mode` - disabled/whitelist/blacklist
- `metrics_collection` - Enable/disable metrics
- `circuit_breaker_threshold` - Failure threshold (1-20)
