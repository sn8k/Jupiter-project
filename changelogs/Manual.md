# Changelog – Manual.md

## v1.8.35: Version badge refresh
- Mise à jour de l'en-tête du manuel vers la version 1.8.35 pour rester aligné avec `VERSION` et le README.

## v1.8.21: Note migration SQL
- Mise à jour de l'en-tête du manuel vers la version 1.8.21.
- Ajout d'un encart indiquant la roadmap de transition vers un stockage SQL automatisé tout en conservant le mode fichier durant la migration.

## 2025-12-03: v1.8.7 cache navigateur desactive
- Mise a jour de l'en-tete du manuel vers la version 1.8.7.
- Ajout d'une note expliquant que la Web UI est servie avec `Cache-Control: no-store` / `Pragma: no-cache` pour empecher tout cache navigateur ou proxy.

## 2025-12-03: CLI Commands Harmonization
- Synchronized French CLI command examples with README.md and user_guide.md
- Updated all command syntax to match actual parser implementation
- Added `--perf` option to scan and analyze commands
- Separated compound commands into individual commands: `server`, `gui`, `run`, `watch`, `update`
- Added notation: `(*) `--ignore` peut être spécifié plusieurs fois`
- Removed deprecated `server|gui` compound format
- Ensured consistency of French terminology across all CLI documentation

- Replaced placeholder with user guide covering setup, commands, and extensions.
- Added documentation for ignore patterns, `.jupiterignore`, and new CLI flags (JSON export, top N, output path).
- Documented GUI launch command and détaillé la nouvelle interface web (multi-vues Dashboard/Analyse/Fichiers/Paramètres/Plugins, placeholders d’actions et de licences).
- Added Diagnostic view description, API base override via `JUPITER_API_BASE`, and CORS-enabled scan call.
- Documented snapshot workflow (auto-save, `--snapshot-label`, `--no-snapshot`, `snapshots list|show|diff`, History view diff panel, API endpoints).
- Added CI command coverage plus the explanation of the shared CLI pipeline.
- Documented the `/config/root` behavior (automatic connector/plugin/Meeting refresh and history alignment).
- Mentioned the redesigned Projects dashboard (active summary, root, last scan, quick actions) in the UI overview.
- Added a logging section describing the new Settings-based log level control and where it is stored (`logging.level`).
- Clarified configuration naming: project files are now `<projet>.jupiter.yaml` and the project registry lives in `~/.jupiter/global_config.yaml` (legacy names still readable).
- Added guidance on the new log file path field in Settings (optional to enable file logging).
- Clarified that activating a project from the Web UI updates the global registry and `~/.jupiter/state.json` so the next launch reopens the same project automatically.
- Documented that AI Helper duplication suggestions now enumerate file:line occurrences so exported reports are directly actionable.
- Mentioned internal refactors (CLI/API/UI) that remove duplicated scan/historique/projet handling code.
- Documented per-project ignore globs editable depuis la page Projets (appliqués automatiquement aux scans/analyses).
- Ajouté que la configuration API (connector/app_var/chemin) se gère désormais dans la page Projets, par projet, via un formulaire dédié.
- Nouvel encart "Versionnage visible" décrivant le badge de version global, le rappel dans Settings > Mise à jour, et l'affichage des versions propres aux plugins.
- Mentionné que la vue Qualité vit maintenant dans l'onglet Dashboard du plugin Code Quality (avec export, complexité et duplication).
- Ajouté une section "Paramètres plugins persistants" détaillant la grille deux colonnes des Settings, les cartes dédiées pour Notifications/Code Quality et la synchronisation automatique avec le registre global/projet.
- Mise à jour du manuel (v1.8.5) : installation GUI par défaut, registre multi-projets, pipeline CLI unifié (scan/analyze/ci), snapshots/simulation, sécurité (tokens, run restreint, WS), Meeting et panorama des plugins (Code Quality, Live Map, Watchdog, Bridge, Settings Update).

## 2025-12-03 (v1.8.6) : Polish rédactionnel
- Correction des problèmes d’encodage (accents) et reformulation de plusieurs phrases pour une lecture plus fluide.
- Harmonisation du résumé API en fin de document avec `docs/api.md` (endpoints, rôles, exemples d’usage).
