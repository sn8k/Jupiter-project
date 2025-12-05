# Changelog - Notifications Webhook Plugin

## v1.0.0
- **Migration vers Bridge v2**: Structure plugin.yaml + modules
- **Lifecycle**: `init(bridge)`, `shutdown()`, `health()`, `metrics()`, `reset_settings()`
- **Hooks**: `on_scan(report)`, `on_analyze(summary)`
- **Dispatch async**: `_dispatch_notification()`, `_send_webhook()`, `_emit_local_notification()`
- **Config**: `get_config()`, `configure(config)`
- **Test**: `run_test()` pour validation transport
- **UI**: Module web avec `get_settings_html()`, `get_settings_js()`
- **i18n**: Fichiers de traduction `en.json` et `fr.json`
- **Backward Compat**: Classe `Plugin` pour PluginManager legacy

## v0.2.2 (Legacy)
- Fichier monolithique `notifications_webhook.py` (506 lignes)
- Classe unique Plugin avec UI et logique embarquées
