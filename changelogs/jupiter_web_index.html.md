# Changelog – jupiter/web/index.html
- Appended build/version indicator badge and bumped script reference to `app.js?v=0.1.4+` for cache busting.
- Refactored layout into navigable views (Dashboard, Analyse, Fichiers, Paramètres, Plugins) with dark theme defaults.
- Added quick-action area, alert list, plugin grid, and settings placeholders for Meeting, thèmes et i18n.
- Introduced contextual footer log stream and live event feed for future runtime updates.
- Restored dedicated Analysis, Diagnostic, Files, and Plugins pages with tables, badges, and log/live streams aligned to `web_interface.md` guidance.
- Added "Qualité" tab and view section to display complexity and duplication metrics.
- Rebuilt the Projects view as a dashboard: active-project hero, health metrics, quick actions, and card-based list with activate/delete controls.
- Wired Projects actions to the new `/projects` API endpoints and added a refresh control that rehydrates overview stats without reloading the page.
- Added Cancel to the project wizard, improved delete button visibility, and kept the project list in a responsive grid layout.
- Added log level selectors to both the dashboard log stream and the Settings form to align UI filtering with backend verbosity.
- Updated copy around API docs, raw editor, and quick actions to reflect the new `.jupiter.yaml` naming convention.
- Added a log file path field to Settings so users can set the destination file directly from the UI.

