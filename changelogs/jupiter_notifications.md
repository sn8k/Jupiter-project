# Changelog - Section 7: Notifications & Webhooks

## 2025-12-01 – Versionnement dédié

### Changed
- Le plugin `notifications_webhook` expose désormais sa propre version (`0.2.1`) afin que la vue Plugins reflète correctement l'état du module, indépendamment de la version principale de Jupiter.

## 2025-12-01 – Logs alignés sur le Settings loglevel (0.2.2)

### Changed
- Ajout de logs INFO/DEBUG tout au long du flux (configuration, planification, webhook/local dispatch) pour que le niveau DEBUG fournisse le payload complet des notifications tandis que le niveau INFO reste synthétique.
- L'action "Test notification" journalise désormais explicitement le transport utilisé, ce qui facilite le diagnostic des réglages.

## 2025-12-01 – UI popups & API heartbeat

### Added
- Global notification center (toast popups) wired to `PLUGIN_NOTIFICATION` events and the new API heartbeat so alerts surface across every view.
- Web UI heartbeat that pings `/health` and emits the "API connectée" notification when the backend goes online/offline.
- `GET /plugins/{name}/config` endpoint so settings panels can load persisted plugin configuration reliably.
- `api_connected` notification emitted by `notifications_webhook` whenever the inspected project API switches online/offline (with webhook + local fallback).

### Changed
- Notifications settings UI now loads the stored config via the new endpoint, exposes a dedicated **Enregistrer** button, and keeps the `Test` action isolated from writes.
- Plugin configuration honors the `enabled` flag and defaults to both `scan_complete` and `api_connected` events for new installs.
- Plugin payloads carry a `level` hint consumed by the toast renderer for consistent severity colors.

## 2025-12-01 – Test endpoint & settings fixes

### Added
- New `POST /plugins/{name}/test` API route so admins can trigger plugin-provided diagnostics (used by the webhook plugin test button).
- `PluginManager.get_plugin()` helper to expose registered plugin instances to API routes.

### Fixed
- `jupiter/plugins/notifications_webhook.py` now exposes an async `run_test()` helper that dispatches a synthetic notification, enabling the API and UI test workflow.
- Settings UI now calls the correct `/plugins/notifications_webhook/config` endpoint, reuses `apiFetch` for auth/401 handling, and degrades gracefully when the global `showNotification` helper is missing.
- Added a lightweight notification fallback and better error logging around the test button, resolving the JS `ReferenceError` and 404s.

## Ajouts
- **Plugin Webhook** : `jupiter/plugins/notifications_webhook.py`
  - Envoi de notifications JSON sur événements (scan_complete).
  - Configurable via URL.

## Modifications
- **Fallback local notifications** :
  - Ajout de l'événement `PLUGIN_NOTIFICATION` pour diffuser les alertes sur le WebSocket.
  - Si aucune URL n'est configurée, le plugin envoie désormais un message local (Live Events + logs) au lieu de tenter un POST HTTP qui échouerait.
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
- Sans URL, l'UI reçoit l'événement `PLUGIN_NOTIFICATION` (Live Events + logs) prouvant la dégradation contrôlée.
