# Changelog - AI Helper Plugin

## [1.3.0] - Ollama Support & CSS Fix

### Added
- **Ollama Provider Support**: Full integration with local LLM via Ollama
  - Connect to local Ollama instance (default: http://localhost:11434)
  - Support for codellama, mistral, llama2, deepseek-coder models
  - JSON-based suggestion extraction from LLM responses
  - Configurable via `ollama_url` and `ollama_model` settings

- **Provider Architecture**: Extensible provider system
  - `mock`: Heuristic-based suggestions (default, no API needed)
  - `ollama`: Local LLM via Ollama (free, private)
  - `openai`: OpenAI API (placeholder, requires api_key)
  - `anthropic`: Anthropic Claude API (placeholder, requires api_key)
  - `azure_openai`: Azure OpenAI / GitHub Models (placeholder, requires api_key)

### Fixed
- **CSS Status Indicator Overflow**: "Analyse terminée" text now stays within bounds
  - Added `overflow: hidden`, `text-overflow: ellipsis` to `.status-text`
  - Added `max-width: 100%` and `flex-shrink: 0` to `.status-indicator`
  - Improved responsive behavior for mobile (full width on small screens)
  - Fixed `.status-dot` min-width to prevent shrinking

### Changed
- Updated `core/logic.py` to v1.2.0 with provider routing
- Updated `web/panels/main.js` to v1.3.0 with improved CSS
- Config validation now supports Ollama-specific settings

## [1.2.0] - CSS Fix for WebUI Panel

### Fixed
- **Inline CSS Injection**: The WebUI panel was displaying without styles because no CSS file was loaded
  - Added inline CSS in `main.js` that injects styles dynamically
  - Styles now match the Jupiter dark theme design system
  - Responsive layout with mobile breakpoints

### Added
- **Complete Plugin CSS**: Comprehensive styling for all panel elements:
  - `.ai-helper-plugin` container with flex layout
  - Control section with buttons and status indicator
  - Info grid with provider/enabled status
  - Suggestions list with severity color coding
  - Logs panel with controls and streaming output
  - Statistics grid with execution metrics
  - Help sidebar with documentation

### Changed
- `web/panels/main.js` version bumped to 1.2.0
- CSS injected via `<style>` tag on mount (no external file dependency)

## [1.1.0] - Complete Bridge v2 Migration

### Added
- **Server Module** (`server/api.py`):
  - FastAPI router with `/ai_helper` prefix
  - Standard endpoints: `/health`, `/metrics`, `/logs`, `/logs/stream`
  - Job management: `/jobs` (GET, POST), `/jobs/{id}` (GET, DELETE)
  - AI-specific: `/suggestions`, `/suggestions/file`, `/config`
  - Settings reset: `/reset-settings`
  - Changelog endpoint: `/changelog`
  - `register_api_contribution(app, bridge)` for Bridge registration

- **CLI Module** (`cli/commands.py`):
  - `jupiter ai suggest`: Generate AI suggestions with type/severity filters
  - `jupiter ai analyze-file <path>`: Analyze a specific file
  - `jupiter ai status`: Show plugin status and metrics
  - `jupiter ai health`: Check plugin health
  - `jupiter ai config show|set|reset`: Configuration management
  - JSON output support with `--json` flag
  - `register_cli_contribution(subparsers)` for Bridge registration

- **WebUI Panel** (`web/panels/main.js`):
  - Full-featured panel conforming to plugins_architecture.md
  - Run analysis button with status indicator
  - Suggestions list with type/severity filters
  - JSON export and AI context export
  - Real-time logs panel with pause/resume/download
  - Usage statistics (executions, suggestions, errors)
  - Help sidebar with documentation links
  - `mount(container, bridge)` and `unmount(container)` exports

- **Unit Tests** (`tests/test_plugin.py`):
  - Lifecycle tests (init, health, metrics, reset_settings)
  - Business logic tests (suggestion generation)
  - Hook tests (on_scan, on_analyze)
  - API helper tests
  - MockBridge for isolated testing

- **i18n Updates**:
  - Added all panel translation keys (50+ new keys)
  - Both `en.json` and `fr.json` complete

### Changed
- Updated `plugin.yaml` with complete entrypoints (server, cli, reset_settings)
- API routes now follow `/ai_helper/*` prefix convention
- Added job management endpoints to capabilities declaration
- Version bumped to 1.1.0

### Fixed
- Plugin now fully conforms to `docs/plugin_model/` reference structure
- All entrypoints properly declared for Bridge registration

## [1.0.0] - Migration to Bridge v2

### Breaking Changes
- Plugin restructured from single file (`ai_helper.py`) to package (`ai_helper/`)
- Now uses Bridge v2 manifest-based architecture
- Configuration schema changed (see `plugin.yaml`)

### Added
- **Bridge v2 Manifest** (`plugin.yaml`):
  - Full configuration schema with JSON Schema for Auto-UI
  - Declared permissions (fs_read, network_outbound)
  - Defined entrypoints for lifecycle methods
  - CLI and API capabilities declaration
  - UI panels and widgets specification
  - Healthcheck configuration

- **Lifecycle Methods**:
  - `init(config)`: Initialize plugin with merged configuration
  - `health()`: Health check returning status, message, and details
  - `metrics()`: Plugin metrics for monitoring dashboards

- **Enhanced Configuration**:
  - `suggestion_types`: Select which suggestion types to generate
  - `severity_threshold`: Filter suggestions by minimum severity
  - `large_file_threshold_kb`: Configurable threshold for large file warnings
  - `max_functions_threshold`: Configurable threshold for God Object detection

- **i18n Support**:
  - English translations (`web/lang/en.json`)
  - French translations (`web/lang/fr.json`)

- **Metrics Tracking**:
  - Execution count
  - Error count
  - Total suggestions generated
  - Last run timestamp

### Changed
- Moved from class-based (`AIHelperPlugin`) to function-based module API
- Configuration via `init()` instead of `configure()` method
- Internal state managed via `PluginState` dataclass singleton
- Improved logging with structured output
- Better error handling with error count tracking

### Deprecated
- Legacy `AIHelperPlugin` class (still available for backward compatibility)
- Direct `configure()` method (use `init()` instead)

### Migration Guide
1. Update imports: `from jupiter.plugins.ai_helper import init, health, metrics`
2. Configuration is now passed to `init()` during plugin initialization
3. Access suggestions via `get_suggestions()` function
4. Health and metrics are now standard Bridge v2 endpoints

---

## [0.3.1] - Previous Legacy Version

### Features (preserved in 1.0.0)
- Mock AI provider for demonstration
- Documentation suggestions based on function density
- Cleanup suggestions for unused functions
- Large file refactoring suggestions
- God Object detection
- Test coverage gap analysis
