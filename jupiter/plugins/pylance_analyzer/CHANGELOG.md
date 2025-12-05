# Changelog - Pylance Analyzer Plugin

## v1.0.0
- **Migration vers Bridge v2**: Structure complète plugin.yaml + modules
- **Core**: Extraction de la logique dans `core/analyzer.py`
  - Classes: `PylanceDiagnostic`, `PylanceFileReport`, `PylanceSummary`, `PylanceAnalyzer`
  - Méthodes: `check_pyright_available()`, `run_pyright()`, `parse_pyright_output()`
- **Lifecycle**: Implémentation complète des hooks Bridge
  - `init(bridge)`, `shutdown()`, `health()`, `metrics()`, `reset_settings()`
- **Hooks**: `on_scan(report)`, `on_analyze(summary)`
- **API**: Router FastAPI dans `server/api.py`
  - Endpoints: `/status`, `/config`, `/summary`, `/file/{path}`
- **UI**: Module web avec HTML/JS legacy dans `web/ui.py`
  - `get_ui_html()`, `get_ui_js()`, `get_settings_html()`, `get_settings_js()`
- **i18n**: Fichiers de traduction `web/lang/en.json` et `fr.json` (60+ clés)
- **Backward Compat**: Classe `PylanceAnalyzerPlugin` pour PluginManager legacy

## Legacy (pre-v1.0.0)
- Fichier monolithique `pylance_analyzer.py` (1069 lignes)
- Classe unique PylanceAnalyzerPlugin avec tout le code embarqué
