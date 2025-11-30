# Changelog – CHANGELOG.md
- Added version 0.1.1 section covering CLI exclusions, richer analysis summaries, and documentation updates.
- Added refactored static GUI with multi-vue dashboard/analyse/fichiers, placeholders Scan/Watch/Run, alerts, plugins grid, and refreshed dark theme.
- Remember the last served root across launches by persisting it to `~/.jupiter/state.json` and reload cached data through `/reports/last` so the UI stays aligned with the previous project.
- Logged version 1.1.5 entry describing the configurable logging level across CLI/API/UI.
- Logged version 1.1.9 entry describing detailed duplication evidence now present in AI suggestions (file:line occurrences in reports and UI).
- Logged addition of function context and code excerpts in duplication suggestions for faster remediation.
- Logged version 1.1.10 entry summarizing internal deduplication (CLI workflows, server routers, remote connector, Web UI project actions).
- Logged relocation of project API settings into the Projects page with supporting endpoints and translations.
