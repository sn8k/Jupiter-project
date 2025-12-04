# Changelog - jupiter/plugins/ai_helper

## [1.1.0] - Complete Bridge v2 Migration

### Added
- **Server Module** (`server/api.py`):
  - FastAPI router with `/ai_helper` prefix
  - Standard endpoints: `/health`, `/metrics`, `/logs`, `/logs/stream`
  - Job management: `/jobs` (GET, POST), `/jobs/{id}` (GET, DELETE)
  - AI-specific: `/suggestions`, `/suggestions/file`, `/config`
  - Settings reset: `/reset-settings`, changelog: `/changelog`
  - `register_api_contribution(app, bridge)` for Bridge registration

- **CLI Module** (`cli/commands.py`):
  - `jupiter ai suggest`: Generate suggestions with type/severity filters
  - `jupiter ai analyze-file <path>`: Analyze specific file
  - `jupiter ai status|health|config`: Plugin management commands
  - `register_cli_contribution(subparsers)` for Bridge registration

- **WebUI Panel** (`web/panels/main.js`):
  - Full-featured panel per plugins_architecture.md
  - Suggestions list with filters, export, real-time logs, stats
  - `mount(container, bridge)` and `unmount(container)` exports

- **Unit Tests** (`tests/test_plugin.py`):
  - Lifecycle, business logic, hook, and API tests with MockBridge

- **Business Logic** (`core/logic.py`):
  - Added `analyze_single_file()` for targeted file analysis

- **i18n Updates**: 50+ new translation keys for panel

### Changed
- Updated `plugin.yaml` with server, cli, reset_settings entrypoints
- API routes now use `/ai_helper/*` prefix convention
- Version bumped to 1.1.0

## [1.0.0] - Migration to Bridge v2 Architecture

### Added
- **Package Structure**: Migrated from single file to package format
  - `plugin.yaml`: Full manifest with JSON Schema configuration
  - `__init__.py`: Main plugin module with lifecycle methods
  - `web/lang/en.json`: English translations
  - `web/lang/fr.json`: French translations
  - `CHANGELOG.md`: Plugin-specific changelog

- **Bridge v2 Lifecycle Methods**:
  - `init(config)`: Initialize with merged configuration
  - `health()`: Health check returning status and details
  - `metrics()`: Metrics for monitoring dashboards

- **Enhanced Configuration Schema**:
  - `enabled`: Enable/disable plugin
  - `provider`: AI provider selection (mock, openai, anthropic, local)
  - `api_key`: Secure API key storage
  - `suggestion_types`: Selectable suggestion types
  - `severity_threshold`: Minimum severity filter
  - `large_file_threshold_kb`: Configurable large file detection
  - `max_functions_threshold`: Configurable God Object detection

- **Declared Capabilities**:
  - CLI commands: `suggest`, `analyze-file`
  - API routes: `/suggestions`, `/suggestions/file`, `/config`, `/health`
  - UI panels: main panel, suggestions sidebar
  - Widgets: suggestion counter
  - Metrics enabled with JSON export

- **i18n Support**:
  - Full English and French translations

- **Metrics Tracking**:
  - `execution_count`, `error_count`, `total_suggestions`, `last_run`

### Changed
- Architecture changed from class-based to function-based module
- Configuration via `init()` instead of `configure()` method

---

## [0.3.1] - Legacy Version
- Ajout d'une journalisation détaillée (INFO/DEBUG) lors de la configuration, de la capture des fichiers scannés et de la génération d'idées afin que le loglevel défini dans les Settings permette de diagnostiquer les heuristiques déclenchées.

## [0.3.0]
- Définit un numéro de version propre au plugin (`0.3.0`) pour ne plus dépendre du numéro global de Jupiter dans l'UI Plugins.

## [0.1.0]
- Création initiale du plugin AI Helper.
- Implémentation de la classe `AIHelperPlugin`.
- Ajout de la dataclass `AISuggestion`.
- Implémentation du hook `on_analyze` pour injecter des suggestions dans le rapport.
- Ajout d'une logique mock pour générer des suggestions basées sur des heuristiques simples (densité de fonctions, fonctions inutilisées).

- Ajout d'heuristiques avancées :
  - Détection des "God Objects" (fichiers avec trop de fonctions).
  - Détection des fichiers trop volumineux (> 50KB).
  - Analyse de couverture de tests (fichiers sources sans fichier de test correspondant).
  - Utilisation des données de scan (on_scan) pour l'analyse globale.

