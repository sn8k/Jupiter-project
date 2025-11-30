# Changelog - Section 7: Notifications & Webhooks

## Ajouts
- **Plugin Webhook** : `jupiter/plugins/notifications_webhook.py`
  - Envoi de notifications JSON sur événements (scan_complete).
  - Configurable via URL.

## Modifications
- **Configuration** :
  - Mise à jour de `PluginsConfig` dans `jupiter/config/config.py` pour supporter les settings arbitraires.
  - Support de la persistance de la configuration des plugins dans `jupiter.yaml`.
- **Plugin Manager** :
  - Injection de la configuration (`configure()`) dans les plugins.
  - Support de la mise à jour à chaud (`update_plugin_config`).
- **API Server** :
  - Nouvel endpoint `POST /plugins/{name}/config`.
- **Frontend** :
  - UI de configuration pour le plugin Webhook dans l'onglet Plugins.

## Validation
- Le plugin est chargé au démarrage.
- L'URL peut être configurée depuis l'interface web.
- Les notifications sont envoyées lors des scans.
