# Changelog - Watchdog Plugin

## v1.0.0
- **Migration vers Bridge v2**: Structure plugin.yaml + modules
- **Lifecycle**: `init(bridge)`, `shutdown()`, `health()`, `metrics()`, `reset_settings()`
- **Monitoring**: Thread de surveillance avec `_monitor_loop()`, `_check_for_changes()`
- **Reload**: `_trigger_reload()` avec support callback et plugin_manager
- **API**: `force_check()`, `get_status()`, `get_config()`, `configure()`
- **UI**: Module web avec `get_settings_html()`, `get_settings_js()` 
- **i18n**: Fichiers de traduction `en.json` et `fr.json`
- **Backward Compat**: Classe `PluginWatchdog` pour PluginManager legacy

## v1.0.2 (Legacy)
- Fichier monolithique `watchdog_plugin.py` (710 lignes)
- Classe unique PluginWatchdog avec threading et UI embarqués
