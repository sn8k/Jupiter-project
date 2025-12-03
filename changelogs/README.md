# Changelog – README.md

## 2025-12-03: CLI Commands Documentation Harmonization
- Updated CLI Commands section with complete, accurate syntax for all 12 Jupiter commands
- Added notation: `(*)` `--ignore` can be specified multiple times
- Separated compound commands (`server|gui` → individual `server`, `gui`, `run`, `watch`, `update`)
- Added `--perf` flag to `scan` and `analyze` options
- Added `--output` to `scan` options
- Now reflects actual parser implementation (bug fix: `--snapshot-label` and `--no-snapshot` placement)

- Added quickstart instructions for the new CLI scanner and analyzer.
- Documented early server stub and Meeting adapter placeholders.
- Documented ignore patterns, `.jupiterignore` usage, and richer scan/analyze options.
- Added GUI quickstart command and décrit la nouvelle interface web refondue (navigation multi-vues, placeholders Scan/Watch/Run, chargement drag-and-drop).
- Clarified Diagnostic page role, CORS-enabled API access for the Scan button, and `JUPITER_API_BASE` override.
- Added snapshot history overview (auto-saved scans, CLI `snapshots` subcommands, `.jupiter/snapshots/` storage, and Web/API entry points).
- Documented Phase 5 features: simulation (`simulate remove`), Live Map (`/graph` + UI view), JS/TS support, project API connectors, webhook notifications, and security hardening (`security.allow_run`, `security.allowed_commands`).
- Added CI command reference plus the note about the unified CLI workflow that now powers `scan`, `analyze`, and `ci` consistently.
- Added Projects Control Center bullet describing the redesigned Web UI page for multi-project management.
- Added release note for 1.1.4 covering the wired Projects Control Center and `/projects` API integration.
- Documented the configurable logging level (Debug/Info/Warning/Error/Critical) surfaced in the Settings page and applied across CLI/API/Uvicorn.
- Updated setup guidance to mention `<project>.jupiter.yaml` for authentication tokens and the new config naming scheme.
- Clarified persistent state: the CLI/GUI now reopen the project marked active in the global registry (`~/.jupiter/global_config.yaml` or legacy `global.yaml`) and sync `state.json` accordingly.
- Highlighted that AI duplication suggestions now include file:line evidence in the API and Web UI release notes.
- Added release note 1.1.10 describing internal deduplication of CLI/server/UI workflows.
- Noted per-project ignore globs can be managed from the Projects page and saved via the `/projects/{id}/ignore` endpoint.
- Ajouté un point dans la section "Features" détaillant le badge de version global et l'affichage des versions propres aux plugins.
- Ajouté une note de version 1.1.11 décrivant la migration de la vue Qualité vers l'onglet Dashboard du plugin Code Quality et son panneau de paramètres remanié.
- Documenté la persistance des paramètres plugins et la nouvelle mise en page Settings (grille deux colonnes + carte Mise à jour dédiée) dans la section Features.
- Ajouté la release note 1.1.12 retraçant la refonte des panneaux Settings/plugins et la sauvegarde unifiée des préférences.
- Rafraîchi le README pour mettre en avant le flux GUI-first, la matrice CLI complète (scan/analyze/ci/snapshots/simulate/meeting/autodiag) et un aperçu API aligné sur les routes actuelles.

## 2025-12-03 (v1.8.6) : Polish rédactionnel
- Amélioré les formulations de l’intro et de la section CLI (mention explicite des usages SSH/CI et du partage de pipeline entre scan/analyze/ci).
- Ajouté une référence claire à `docs/api.md` pour les schémas complets et des exemples `curl` copy-paste.
