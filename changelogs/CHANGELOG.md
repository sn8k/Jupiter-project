# Changelog – CHANGELOG.md

## 1.8.21

### Documentation & Roadmaps
- Ajout de `TODOs/sql_migration_roadmap.md` (v0.1.0) : feuille de route détaillée pour basculer Jupiter vers un stockage SQL géré automatiquement (SQLite par défaut, PostgreSQL optionnel), phases 0-7, schéma cible et risques.
- README mis à jour (v1.8.21) avec mention explicite des roadmaps `TODOs/` et de la migration SQL.
- Manuel utilisateur mis à jour (v1.8.21) pour signaler la future bascule SQL tout en rappelant la compatibilité fichier actuelle.

## 1.8.19 – 2025-12-03

### Docs
- `docs/plugins_architecture.md` : mise à jour v0.4.0 avec clarifications complètes
  - §3.1 : plugins core sans manifest, hard-codés
  - §3.1.1 : scope global vs par projet (install, activation, config overrides)
  - §3.3.1 : Bridge comme Service Locator (`bridge.services.*`)
  - §3.4.1-3.4.3 : manifest minimal et complet, Auto-UI (JSON Schema → formulaire)
  - §8 : Meeting reformulé comme SPÉCULATIF avec scope v1 limité
  - §10.5 : Hot Reload en mode développement
  - §10.6 : Modèle async et tâches longues (jobs, WS, circuit breaker)

- `docs/plugin_model/` : mise à jour v0.3.0
  - `plugin.yaml` : nouveau format avec config_schema.schema, jobs, entrypoints explicites
  - `__init__.py` : support bridge.services, jobs async, pattern d'annulation
  - `server/api.py` : endpoints jobs, metrics, changelog
  - `core/logic.py` : fonctions utilitaires supplémentaires
  - `README.md` : documentation complète des nouveautés

### TODO
- `TODOs/refonte_plugins.md` : roadmap complète de la refonte (11 phases, ~180 tâches)

---

- Added version 0.1.1 section covering CLI exclusions, richer analysis summaries, and documentation updates.
- Added refactored static GUI with multi-vue dashboard/analyse/fichiers, placeholders Scan/Watch/Run, alerts, plugins grid, and refreshed dark theme.
- Remember the last served root across launches by persisting it to `~/.jupiter/state.json` and reload cached data through `/reports/last` so the UI stays aligned with the previous project.
- Logged version 1.1.5 entry describing the configurable logging level across CLI/API/UI.
- Logged version 1.1.9 entry describing detailed duplication evidence now present in AI suggestions (file:line occurrences in reports and UI).
- Logged addition of function context and code excerpts in duplication suggestions for faster remediation.
- Logged version 1.1.10 entry summarizing internal deduplication (CLI workflows, server routers, remote connector, Web UI project actions).
- Logged relocation of project API settings into the Projects page with supporting endpoints and translations.
