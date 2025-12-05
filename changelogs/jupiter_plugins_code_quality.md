# Changelog – jupiter/plugins/code_quality/

## [0.8.2] - plugin.yaml Schema Compliance Fix

### Fixed
- Rewrote `plugin.yaml` for JSON schema compliance
- Added required `type: tool` field
- Added required `jupiter_version: ">=1.8.0"` field
- Proper `capabilities` object structure (was array)
- Proper `ui.panels` array structure
- Proper `entrypoints` object (init, shutdown only)
- Proper `config.defaults` object

---

## [0.8.1] - Migrated to Bridge v2 Structure

### Changed
- Migrated from legacy single-file `jupiter/plugins/code_quality.py` to Bridge v2 modular structure
- Split into:
  - `__init__.py` - Plugin lifecycle and API
  - `core/models.py` - Data classes (QualityIssue, FileQualityReport, QualitySummary, ManualDuplicationLink)
  - `core/analyzer.py` - CodeQualityAnalyzer class
  - `web/ui.py` - HTML/CSS/JS templates
  - `web/lang/` - i18n files
- Added `plugin.yaml` manifest with complete metadata
- Uses `bridge.services.get_logger()` for logging
- UI type: `both` (sidebar + settings)

### Added
- `plugin.yaml` manifest v0.8.1 with full Bridge v2 metadata
- `core/models.py` with dataclasses:
  - `QualityIssue` - Single quality issue
  - `FileQualityReport` - Per-file report
  - `QualitySummary` - Overall project summary
  - `ManualLinkOccurrence` - Duplication link occurrence
  - `ManualDuplicationLink` - User-defined duplication cluster
- `core/analyzer.py` with `CodeQualityAnalyzer` class
- `web/ui.py` with:
  - Dashboard with score circle and metrics
  - Tabbed interface (Dashboard, Issues, Files, Duplication, Recommendations)
  - Manual duplication linking UI
  - Settings panel with threshold configuration
- `web/lang/en.json` and `web/lang/fr.json` i18n files

### Technical Details
- Plugin ID: `code_quality`
- View ID: `code_quality`
- Integrates with `jupiter.core.quality.complexity` and `jupiter.core.quality.duplication`
- Complexity thresholds: low=10, moderate=20, high=30, very_high=50
- Duplication thresholds: acceptable=3%, warning=5%, high=10%
- Manual duplication links stored in `.jupiter/manual_duplication_links.json`

---

## 2025-12-02 – Settings persistence & UX polish

### Changed
- Le panneau de configuration injecté dans l'onglet Settings adopte une carte dédiée avec grille responsive, boutons contextualisés et hints explicites pour les seuils.
- Les actions `load`/`save` passent désormais par un helper `request` qui déduit `apiBaseUrl`, applique l'entête `Authorization` et affiche un indicateur d'état (⟳/✅/⚠️) selon le résultat.
- Les valeurs booléennes/numériques sont normalisées (fallback `false` et `3` pour les seuils) afin d'éviter des inputs vides lors du premier rendu.
- Le conteneur global reçoit une classe (`plugin-settings-card`) partagée qui harmonise la présentation avec les cartes natives de la page Settings.

## 2025-12-01 – v1.2.3 (plugin 0.8.1)

### Changed
- Ajout d'une journalisation détaillée sur `on_scan`, `on_analyze`, le filtrage des fichiers et le chargement des liens manuels afin que le niveau DEBUG expose les totaux analysés, les chemins échantillons et les clusters ajoutés.
- Les messages INFO continuent de synthétiser les résultats (score, nombre de fichiers), tandis que DEBUG liste désormais les payloads complets pour faciliter le troubleshooting.

## 2025-12-01 – v1.2.2 – Dashboard & settings refresh

### Added
- Nouveau sous-onglet **Dashboard** dans la vue plugin qui reprend l'ancienne page Qualité (tableaux complexité/duplication + bouton d'export) afin que toutes les métriques résident dans le plugin.

### Changed
- `code_quality_render` pilote désormais les tableaux du Dashboard (top 10 fichiers les plus complexes et 10 clusters de duplication) en plus des onglets historiques.
- Réécriture du panneau de paramètres (carte responsive avec hints) et ajout du champ `duplication_chunk_size` pour aligner l'UI sur les options réellement supportées.

## 2025-12-01 – v1.2.1 – Version metadata decoupled

### Changed
- Le plugin expose désormais son propre numéro (`0.8.0`) pour que la Web UI affiche la version du module plutôt que celle de Jupiter.

## 2025-12-01 – v1.2.0 – Manual duplication linking

### Added
- Duplication tab now exposes selection checkboxes and toolbar actions so you can merge overlapping detector clusters into a single linked block with one click.
- Linked blocks display badges (Linked + verification status) and inline actions to re-check or remove them. They surface in the `/analyze` payload as `source: "manual"` clusters without affecting duplication percentages or severity penalties.
- Manual links persist in `.jupiter/manual_duplication_links.json` and can also be seeded via the plugin configuration (`manual_duplication_links`).
- Added helper methods (`create_manual_link`, `delete_manual_link`, `recheck_manual_links`) plus disk persistence helpers so the server router can expose CRUD endpoints.

### Changed
- Duplication list now caps at 15 clusters, shows full line ranges (line/end_line) and includes the new manual badges/toolbar styling.
- Manual verification compares normalized code excerpts and raises statuses (`verified`, `missing`, `diverged`) that are rendered in the UI and returned to the API.
- Duplication issues/percentages now ignore manual clusters to avoid double counting linked blocks.

---

## 2025-12-01 – v1.1.1 – GUI API fallback

### Fixed
- The plugin UI now rewrites fallback origins served on port 8050 to the API port 8000 so refresh requests stop hitting the static file server and triggering 404s when `inferApiBaseUrl` is not yet available.
- Added a default fallback to `http://127.0.0.1:8000` if no origin can be inferred, ensuring offline builds still reach the API.
- Added detailed console diagnostics (selected base URL, fallback origin, final fetch URL) to help trace misconfigurations when the view still fails to load data.

---

## 2025-12-01 – v1.1.0 – API Integration Fix

### Fixed
- **Plugin now receives `project_root`** from plugin manager hooks, enabling file discovery.
- **Improved file discovery** in `on_analyze`:
  - Method 1: Extract files from hotspots (works with Pydantic models).
  - Method 2: Load from last scan cache.
  - Method 3: Scan project root directory with smart filtering.
- **JavaScript UI improvements**:
  - Added console logging for debugging.
  - Better error handling and null checks.
  - Graceful handling of missing data.
  - Display meaningful messages when no data available.

### Changed
- Updated `AnalyzeResponse` model to include `code_quality` field.
- Updated `ScanReport` model to include `code_quality` field.
- Modified `hook_on_scan` and `hook_on_analyze` in `PluginManager` to accept `project_root` parameter.
- Updated API routers to pass `project_root` to plugin hooks.

---

## 2025-12-01 – v1.0.0 – Full Implementation

### Changed
- **Renamed** from `code_quality_stub.py` to `code_quality.py` – the module is now fully functional.
- **Plugin name** changed from `code_quality_stub` to `code_quality`.

### Added
- **Real complexity analysis** using `jupiter.core.quality.complexity`:
  - Cyclomatic complexity estimation for Python files (AST-based).
  - Cyclomatic complexity estimation for JS/TS files (regex heuristics).
  - Per-file complexity grades (A-F scale).

- **Code duplication detection** using `jupiter.core.quality.duplication`:
  - Detects duplicated code chunks across files.
  - Merges adjacent/overlapping duplications into larger blocks.
  - Reports duplication percentage and cluster details.

- **Maintainability index calculation**:
  - Simplified MI formula based on complexity, LOC, and comment ratio.
  - Per-file maintainability scores (0-100 scale).

- **Comprehensive quality scoring**:
  - Overall project quality score (0-100).
  - Letter grade (A-F) based on score thresholds.
  - Penalty system for complexity, duplication, and issues.

- **Issue detection and reporting**:
  - Issues categorized by severity (error, warning, info).
  - Issues categorized by type (complexity, duplication, maintainability).
  - Detailed suggestions for each issue.

- **File quality reports**:
  - Per-file metrics: complexity, grade, LOC, comment ratio, maintainability.
  - Per-file issue list with suggestions.

- **Configuration options**:
  - `enabled`: Toggle analysis on/off.
  - `max_files`: Limit number of files to analyze.
  - `complexity_threshold`: Custom warning threshold.
  - `duplication_chunk_size`: Lines per duplication chunk.
  - `include_tests`: Whether to include test files.

- **Full UI integration**:
  - Sidebar menu entry with 📊 icon.
  - Dashboard with score circle and key metrics.
  - Tabbed interface: Issues, Files, Duplication, Recommendations.
  - Settings section for configuration.

- **i18n support**:
  - Added English translations in `web/lang/en.json`.
  - Added French translations in `web/lang/fr.json`.

### Hooks
- `on_scan()`: Adds quick quality summary to scan reports.
- `on_analyze()`: Performs full quality analysis and enriches summary.

### UI Features
- Score circle with grade display.
- Metrics grid: files, complexity, duplication, issues.
- Issues table with severity highlighting.
- Files table sorted by complexity.
- Duplication clusters with code excerpts.
- Recommendations list with actionable suggestions.

### Dependencies
- Uses `jupiter.core.quality.complexity` for complexity estimation.
- Uses `jupiter.core.quality.duplication` for duplication detection.
- No external dependencies required.

---

## Previous (stub version)

The original `code_quality_stub.py` was a minimal placeholder that returned
static dummy values:
- `complexity: "low"`
- `maintainability: "high"`
- `score: 95`
- `issues: []`

This has been replaced with a fully functional implementation.
