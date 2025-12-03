# Changelog

## 1.8.6 — Documentation polish (language, examples, roles)

### Updated
- `docs/api.md` with clearer introduction, explicit JSON payload examples for `scan`, `ci`, `simulate`, `run`, and more precise wording for roles and safety constraints.
- `Manual.md` (FR) to fix encoding issues, improve phrasing, and keep the CLI/API summaries aligned with the current endpoints.
- `README.md` wording to clarify the CI/SSH usage of the CLI and point to concrete API examples.
- `docs/index.md` to better describe the scope and audience of each document.

## 1.8.5 — Documentation refresh (API/UI/CLI alignment)

### Updated
- README to highlight GUI-first flow, full CLI matrix, and API overview tied to current routers.
- Manual (FR) with accurate setup, multi-projet registry, snapshots/simulation, sécurité, Meeting, and plugin coverage.
- API reference with real endpoints, roles, and payload summaries (scan/analyze/ci, snapshots, simulate, projects/config, plugins, watch, Meeting, update).
- Docs index to point to up-to-date guides and mention Projects/History in the Web UI.

## 1.8.2 — Plugin Bridge System & Log Path Setting

### Added
- **Plugin Bridge** (`jupiter/plugins/bridge_plugin.py`):
  - Core services gateway providing stable API access for plugins
  - Decouples plugins from Jupiter internals for future-proof architecture
  - **Service Registry**: Central registry with lazy-loaded service instantiation
  - **Built-in Services**:
    - `events`: Event emission and creation (JupiterEvent)
    - `config`: Configuration access (project root, plugin config)
    - `scanner`: Filesystem scanning operations
    - `cache`: Report caching (get, save, clear)
    - `history`: Snapshot management and diff
    - `logging`: Structured logging for plugins
  - **Capability System**:
    - Services declare their capabilities declaratively
    - Plugins can search services by capability
    - Generic invocation via `bridge.invoke(capability, *args)`
    - Versioned API (`BRIDGE_API_VERSION = 1.0`)
  - Settings-only UI showing:
    - API version and plugin version
    - Number of available/loaded services
    - Service list with categories and capabilities
    - All capabilities across services
  - **Global Access Functions**:
    - `get_bridge()`: Get BridgeContext from any plugin
    - `has_bridge()`: Check if Bridge is available

- **Bridge API Endpoints**:
  - `GET /plugins/bridge/status`: Full Bridge status
  - `GET /plugins/bridge/services`: List available services
  - `GET /plugins/bridge/capabilities`: List all capabilities
  - `GET /plugins/bridge/service/{name}`: Service details

- **Plugin System Enhancements**:
  - Added `get_bridge()` and `has_bridge()` exports to `jupiter.plugins`
  - Bridge context accessible from any plugin

- **Log File Path Setting**:
  - Added log file path input in Settings > Security section
  - Default value: `logs/jupiter.log` (file logging enabled by default)
  - Leave empty to disable file output
  - Persisted in configuration

### Changed
- Updated `jupiter/server/routers/system.py` to v1.5.0 with Bridge endpoints
- Changed `LoggingConfig.path` default from `None` to `"logs/jupiter.log"`

### Documentation
- Added `changelogs/jupiter_plugins_bridge.md`
- Updated `changelogs/jupiter_config_config.md` to v1.2.0
- Updated `README.md` with Bridge feature
- Updated `Manual.md` with Bridge plugin documentation

---

## Older entries

See historical notes in the individual files under `changelogs/` for versions prior to 1.8.2.

