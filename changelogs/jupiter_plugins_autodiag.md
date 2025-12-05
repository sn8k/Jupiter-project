# Changelog – jupiter/plugins/autodiag/

## [1.4.0] - Router Fix and JavaScript/HTML Synchronization

### Fixed
- **Router resolution failure**: FastAPI rejected `Union[Dict[str, Any], JSONResponse]` return type
  - Error: "Invalid args for response field! Hint: check that Union[...] is a valid Pydantic field type"
  - Solution: Changed `update_report()` to use `response_model=None` decorator
  - This fix allows the plugin API router to be properly mounted at `/api/plugins/autodiag/`
- **JS Element IDs**: Synchronized all JavaScript functions with correct HTML element IDs
- **Tab switching**: `switchTab()` now properly shows/hides `.tab-content` with `hidden` class
- **Scenario filtering**: `filterScenarios()` now queries `#autodiag-scenarios-body tr[data-status]` (table rows instead of divs)
- **Server status**: `checkDiagServerHealth()` now uses `#autodiag-status-dot` and `#autodiag-server-status-text`

### Added
- `bindQuickSettings()` function for sidebar quick settings toggles
- Quick settings localStorage persistence (skip CLI, skip API, skip plugins)
- Tab badge count updates in `renderScenarios()`, `renderFalsePositives()`, `renderTrulyUnused()`
- Load confidence data button event binding

### Changed
- `renderScenarios()`: Now renders table rows (`<tr>`) with 6 columns instead of div items
- `renderFalsePositives()`: Now renders table rows with 4 columns
- `renderTrulyUnused()`: Uses `.function-grid` and `.function-card` pattern
- `updateUI()`: Shows stats dashboard and tabs on data load, calculates accuracy rate
- Removed unused `renderSummary()` function
- `server/api.py`: Removed `Union` from imports, using `response_model=None` pattern

---

## [1.3.0] - 2-Column Layout with Sidebar

### Added
- **2-column layout**: Main content area + 320px sidebar
- **Quick Settings panel**: Toggle options for skipping CLI/API/plugins tests
- **How to Use panel**: 4-step guide with icons
- **Confidence Legend panel**: Explains Used/Likely/Possibly/Unused badges
- **Server Status panel**: Live status indicator with URL
- **Plugin API router**: `server/api.py` with `/state` and `/report` endpoints
- **Complete translations**: 50+ new i18n keys in en.json and fr.json

### Changed
- HTML structure: `<div class="autodiag-wrapper">` → `<div class="autodiag-main">` + `<aside class="autodiag-sidebar">`
- Scenarios display: Full table with columns (name, type, status, duration, error, functions)
- CSS: ~700 lines with grid layout, sidebar panels, legend badges

---

## [1.2.0] - Fixed API URLs and Added Inline CSS

### Fixed
- **API endpoint URLs**: Changed `/run` to `/diag/run` and `/health` to `/diag/health` (the autodiag router has `/diag` prefix)
- POST /run endpoint now correctly reaches the autodiag server

### Added
- **Inline CSS injection**: Complete CSS styles injected via JavaScript at initialization
- Follows same pattern as ai_helper plugin for consistency
- Dark theme compatible with CSS variables fallbacks

### Technical Details
- CSS ID: `autodiag-plugin-styles`
- Styles cover: status cards, tabs, panels, scenario list, function list, confidence table, progress bars
- Uses CSS scoping via `.autodiag-container` prefix

---

## [1.1.1] - plugin.yaml Schema Compliance Fix

### Fixed
- Rewrote `plugin.yaml` for JSON schema compliance
- Added required `type: tool` field
- Added required `jupiter_version: ">=1.8.0"` field
- Proper `capabilities` object structure (was array)
- Proper `ui.panels` array structure
- Proper `entrypoints` object (init, shutdown only)
- Proper `config.defaults` object

---

## [1.1.0] - Migrated to Bridge v2 Structure

### Changed
- Migrated from legacy single-file plugin to Bridge v2 modular structure
- Split into `__init__.py` (lifecycle), `web/ui.py` (templates), `web/lang/` (i18n)
- Added `plugin.yaml` manifest with complete metadata
- Uses `bridge.services.get_logger()` for logging
- UI type: `both` (sidebar + settings)

### Added
- `plugin.yaml` manifest v1.1.0 with full Bridge v2 metadata
- `web/ui.py` with `get_ui_html()`, `get_ui_css()`, `get_ui_js()`, `get_settings_html()`, `get_settings_js()`
- `web/lang/en.json` and `web/lang/fr.json` i18n files
- `AutodiagPluginState` dataclass for state management

### Technical Details
- Plugin ID: `autodiag`
- View ID: `autodiag`
- Default port: 8081 (configurable)
- Communicates with separate autodiag server for false-positive detection

---

## [1.5.0] – 2025-12-02

### Corrigé
- **Métrique FP Rate remplacée par Accuracy** : Le "FP Rate 100%" était trompeur car il mesurait le pourcentage de fonctions "flagged" qui étaient des faux positifs. Remplacé par "Accuracy" qui affiche le % de fonctions correctement classifiées (plus intuitif : 99% = bon)
- **Affichage des erreurs de scénarios** : Ajout d'une colonne "Error" dans le tableau des scénarios pour afficher `error_message` quand un test échoue

### Modifié
- Le dashboard affiche maintenant `autodiag-accuracy-rate` au lieu de `autodiag-fp-rate`
- Coloration inversée : vert pour accuracy >= 95%, orange >= 80%, rouge sinon
- Tableau des scénarios passe de 4 à 5 colonnes (Scenario, Status, Duration, **Error**, Functions)
- Les lignes en erreur ont un fond rouge léger (`row-error`)

### Ajouté
- Fonction JS `truncateText(text, maxLen)` pour tronquer les messages d'erreur
- Styles CSS : `.error-text`, `.error-cell`, `.row-error`

---

## [1.4.0] – 2025-12-02

### Corrigé
- **Erreurs 401 sur les appels API** : Le plugin transmet maintenant le token d'authentification
- Ajout de la fonction `getAuthHeaders()` qui récupère `state.token` depuis `app.js`
- Tous les appels `fetch()` incluent maintenant le header `Authorization: Bearer <token>`
- Endpoints concernés : `/diag/health`, `/diag/run`, `/diag/functions`

---

## [1.3.0] – 2025-12-02

### Corrigé
- **Traductions manquantes** : Ajout des clés i18n pour :
  - `autodiag_opt_skip_cli`, `autodiag_opt_skip_api`, `autodiag_opt_skip_plugins`, `autodiag_opt_timeout`
  - `autodiag_help_step_1_short`, `autodiag_help_step_2_short`, `autodiag_help_step_3_short`, `autodiag_help_step_4_short`
  - `autodiag_legend_title`, `autodiag_legend_used`, `autodiag_legend_likely`, `autodiag_legend_possibly`, `autodiag_legend_unused`
  - `autodiag_no_data`, `autodiag_tab_fp`, `autodiag_no_fp`, `autodiag_no_unused`, `autodiag_no_rec`
  - `autodiag_server_title`, `autodiag_checking`

### Supprimé
- **Bouton Toggle Sidebar** : Suppression du bouton "☰" inutile, la sidebar est toujours visible

---

## [1.2.0] – 2025-12-02

### Ajouté
- **Bouton Export** : nouveau bouton dans le header pour exporter les résultats
- **Modal Export** : fenêtre modale avec rapport formaté en Markdown
- **Génération de rapport** : fonction `generateExportText()` qui génère :
  - Résumé avec statistiques (faux positifs, confiance, durée)
  - Résultats des scénarios par statut
  - Liste des faux positifs identifiés
  - Liste des fonctions réellement inutilisées
  - Recommandations
  - Instructions pour l'agent IA
- **Copie dans le presse-papiers** : fonction `copyToClipboard()` avec notification
- **Bouton Save Settings** : ajout d'un bouton de sauvegarde dans les paramètres du plugin

### i18n
- Nouvelles clés : `autodiag_export`, `autodiag_export_title`, `autodiag_export_instructions`, `autodiag_copy`, `autodiag_export_copied`
- Traductions FR ajoutées

---

## [1.1.0] – 2025-12-02

### Amélioré
- Refonte complète du layout de l'interface Web UI
- Nouveau design à deux colonnes (contenu principal + sidebar à droite)
- Navigation par onglets au lieu de sections empilées
- Panel "Quick Settings" dans la sidebar pour configuration rapide
- Panel "Help" dans la sidebar avec explication du fonctionnement
- Panel "Legend" avec badges de statut colorés
- Indicateur "Server Status" avec point vert/rouge

### Settings améliorés
- Nouveau layout avec toggle switches stylisés
- Sections organisées : General, Display, Server Configuration, Scenario Options
- Descriptions et hints détaillés pour chaque option
- Nouvelles options : timeout, skip_cli, skip_api, skip_plugins
- Synchronisation settings/quick-settings

### CSS
- 200+ lignes de nouveaux styles ajoutés
- `.autodiag-layout` : grille deux colonnes responsive
- `.autodiag-sidebar`, `.sidebar-panel` : panneaux latéraux
- `.autodiag-tabs`, `.tab-btn` : navigation par onglets
- `.toggle-switch`, `.toggle-slider` : interrupteurs stylisés
- Badges de statut et confiance colorés
- États vides avec icônes
- Responsive design pour écrans < 900px

### i18n
- 30+ nouvelles clés de traduction ajoutées (EN/FR)
- Traductions pour onglets, settings, légende, aide

---

## [1.0.0] – 2025-12-02

### Créé
- Plugin autodiag complet avec interface Web UI
- `AutodiagPlugin` : classe principale du plugin
- `AutodiagPluginState` : dataclass pour l'état du plugin
- Configuration via `PluginUIConfig` avec intégration sidebar
- Hook `on_scan` : ajoute les infos autodiag au rapport de scan
- Hook `on_analyze` : enrichit le résumé avec les métriques de fonctions

### Interface utilisateur
- Section principale avec stats (faux positifs, taux FP, durée, etc.)
- Carte d'aide détaillée expliquant le fonctionnement
- Tableau des scénarios exécutés (CLI, API, plugins)
- Tableau des faux positifs détectés
- Liste des fonctions vraiment inutilisées
- Section recommandations
- Section scores de confiance avec filtrage

### Fonctionnalités
- Bouton "Run Autodiag" pour lancer l'analyse
- Bouton "Refresh" pour actualiser les données
- Bouton "Load Confidence Data" pour charger les scores
- Filtrage par nom de fonction et par statut
- Barre de progression animée pendant l'exécution
- Gestion des erreurs (serveur non disponible, échec d'analyse)

### Settings
- Option enabled/disabled
- Option auto-run après chaque scan
- Option affichage des scores de confiance
- Configuration du port autodiag

### Intégration
- Communication avec le serveur autodiag sur port 8081
- Appels aux endpoints `/diag/health`, `/diag/run`, `/diag/functions`, `/diag/handlers`
- Support CORS pour les requêtes cross-origin

### i18n
- Toutes les chaînes traduites en anglais (`en.json`)
- Toutes les chaînes traduites en français (`fr.json`)
- 70+ clés de traduction ajoutées
