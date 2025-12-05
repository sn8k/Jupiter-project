# Changelog – jupiter/plugins/notifications_webhook/

## v1.0.1 – plugin.yaml Schema Compliance Fix

### Fixed
- Rewrote `plugin.yaml` for JSON schema compliance
- Added missing `id` field
- Added required `type: tool` field
- Added required `jupiter_version: ">=1.8.0"` field
- Proper `capabilities` object structure
- Proper `ui.panels` array structure
- Proper `entrypoints` object
- Proper `config.defaults` object

---

## v1.0.0 – Migration Bridge v2
- **Migration vers Bridge v2**: Structure plugin.yaml + modules
- **Lifecycle**: `init(bridge)`, `shutdown()`, `health()`, `metrics()`, `reset_settings()`
- **Hooks**: `on_scan(report)`, `on_analyze(summary)`
- **Dispatch async**: `_dispatch_notification()`, `_send_webhook()`, `_emit_local_notification()`
- **Config**: `get_config()`, `configure(config)`
- **Test**: `run_test()` pour validation transport
- **UI**: Module web avec `get_settings_html()`, `get_settings_js()` dans `web/ui.py`
- **i18n**: Fichiers de traduction `en.json` et `fr.json`
- **Backward Compat**: Classe `Plugin` pour PluginManager legacy

---

## v0.2.2 (Legacy)
- Fichier monolithique `notifications_webhook.py` (506 lignes)
- Classe unique Plugin avec UI et logique embarquées
- Events: scan_complete, api_connected
- Settings UI avec HTML/JS inline
