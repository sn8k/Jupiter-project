# Changelog — docs/api.md

## 2025-12-03: Completed Missing Endpoint Documentation
- Added missing endpoints to Plugins section:
  - `GET /plugins/{name}/ui` (auth) → UI content (HTML/JS) for a plugin view.
  - `GET /plugins/{name}/settings-ui` (auth) → settings UI content for a plugin.
- Added missing Projects/Initialization section:
  - `POST /init` → initialize a new Jupiter project with default config file.
- All endpoints now documented; reference is complete and exhaustive.

## 2025-12-03 (v1.8.6) : Polish rédactionnel
- Re-écrit la référence API pour refléter les routes FastAPI actuelles : scan/analyze/ci, snapshots, simulate/remove, projects/config/backends, plugins (code_quality, livemap, watchdog, bridge, settings_update), watch, Meeting, update, auth/users et WS.
- Ajout des rôles admin/viewer, du modèle d'erreur, des paramètres attendus pour les principales requêtes et d’exemples JSON pour `scan`, `ci`, `simulate` et `run`.

