# Changelog: jupiter/server/routers/plugins.py

## Version 0.3.0

### WebSocket Logs Streaming (Phase 4.2)
- Ajout `WebSocket /plugins/v2/{id}/logs/stream` - Streaming logs temps réel
  - Support connexions multiples par plugin
  - Envoi historique au connect (configurable via `tail` param)
  - Protocole ping/pong pour keepalive
  - Filtrage par niveau de log
  - Nettoyage automatique des connexions fermées

### Nouveau système PluginLogConnectionManager
- Classe `PluginLogConnectionManager` pour gérer les connexions WebSocket
  - `connect(plugin_id, websocket)` - Accepter une nouvelle connexion
  - `disconnect(plugin_id, websocket)` - Retirer une connexion
  - `broadcast(plugin_id, message)` - Diffuser à tous les abonnés
  - `get_connection_count(plugin_id)` - Nombre de connexions actives
  - `get_all_stats()` - Statistiques globales
- Fonction `broadcast_plugin_log(plugin_id, entry)` pour émettre des logs
- Fonction `get_log_manager()` pour accéder au gestionnaire global
- Fonction helper `_get_log_history()` async pour lire l'historique

### Tests
- 14 nouveaux tests pour WebSocket logs (31 total)
  - Tests PluginLogConnectionManager (7 tests)
  - Tests broadcast_plugin_log (1 test)
  - Tests _get_log_history (2 tests)
  - Tests WebSocket endpoint (4 tests)

## Version 0.2.0

### Endpoints standard par plugin (Phase 4.2)
- Ajout `GET /plugins/v2/{id}/health` - Health check du plugin
  - Appelle l'interface IPluginHealth si disponible
  - Sinon dérive le statut depuis l'état du plugin
- Ajout `GET /plugins/v2/{id}/metrics` - Métriques du plugin
  - Appelle l'interface IPluginMetrics si disponible
  - Retourne métriques de base sinon
- Ajout `GET /plugins/v2/{id}/logs` - Logs du plugin
  - Lit les logs depuis fichier dédié ou jupiter.log filtré
  - Supporte filtrage par niveau et limite de lignes
- Ajout `GET /plugins/v2/{id}/config` - Configuration du plugin
  - Retourne config actuelle, defaults et schema
- Ajout `PUT /plugins/v2/{id}/config` - Mise à jour configuration
  - Requiert authentification admin
  - Stocke dans plugins.settings du projet
- Ajout `POST /plugins/v2/{id}/reset-settings` - Reset aux defaults
  - Requiert authentification admin

### Modèles de réponse
- Ajout `HealthCheckResponse` avec status, message, checks
- Ajout `MetricsResponse` avec uptime, request_count, error_count
- Ajout `PluginConfigResponse` avec config, defaults, config_schema
- Ajout `LogEntry` pour les entrées de log

### Corrections
- Utilisation de `datetime.now(timezone.utc)` au lieu de `datetime.utcnow()` déprécié
- Renommage du champ `schema` en `config_schema` pour éviter le shadowing
- Alignement avec les interfaces `HealthCheckResult.details` et `PluginMetrics`

## Version 0.1.0

### Endpoints de base
- `GET /plugins/v2/status` - Statut global du Bridge v2
- `GET /plugins/v2` - Liste des plugins avec filtres
- `GET /plugins/v2/{id}` - Détails d'un plugin
- `GET /plugins/v2/ui/manifest` - Manifest UI pour la WebUI
- `GET /plugins/v2/cli/manifest` - Manifest CLI pour documentation
- `GET /plugins/v2/api/manifest` - Manifest API pour documentation
