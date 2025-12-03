# Changelog - jupiter/core/bridge/

Ce fichier documente les modifications apportées au module Bridge du système de plugins Jupiter v2.

## [0.7.0] - Phase 4.1 : API Registry

### Ajouté
- **`api_registry.py`** (v0.1.0)
  - `HTTPMethod` : Enum des méthodes HTTP (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS)
  - `RegisteredRoute` : Dataclass représentant une route enregistrée
    - `full_path` incluant le préfixe `/plugins/<plugin_id>`
    - Support des tags OpenAPI, auth_required, deprecated
  - `PluginRouter` : Groupe de routes pour un plugin
    - `route_count` pour statistiques
  - `APIRegistry` : Registre central des routes API
    - `register_route()` : enregistrer une route
    - `register_from_contribution()` : depuis APIContribution
    - `enable_standard_endpoints()` : activer /health, /metrics, /config, /logs
    - `unregister_route()` / `unregister_plugin()` : retrait
    - `get_route()` / `get_plugin_routes()` / `get_all_routes()` : requêtes
    - `get_routes_by_method()` / `get_routes_by_tag()` : filtrage
    - Validation des chemins et protection contre path traversal
    - Contrôle des permissions `REGISTER_API`
  - `get_api_registry()` / `reset_api_registry()` : Singleton global

- **Tests** : 41 nouveaux tests dans `test_bridge_api_registry.py`
  - TestHTTPMethod : 1 test
  - TestRegisteredRoute : 3 tests
  - TestPluginRouter : 3 tests
  - TestAPIRegistryPermissions : 4 tests
  - TestAPIRegistryRegisterRoute : 5 tests
  - TestAPIRegistryValidation : 3 tests
  - TestAPIRegistryStandardEndpoints : 4 tests
  - TestAPIRegistryQueries : 10 tests
  - TestAPIRegistryUnregister : 4 tests
  - TestAPIRegistrySerialization : 2 tests
  - TestGlobalAPIRegistry : 2 tests

### Mis à jour
- **`__init__.py`** → v0.7.0
  - Export de `APIRegistry`, `HTTPMethod`, `RegisteredRoute`, `PluginRouter`
  - Export de `get_api_registry`, `reset_api_registry`

### Total Tests
- interfaces: 43 tests
- manifest: 24 tests  
- bridge: 42 tests
- services: 37 tests
- events: 48 tests
- cli_registry: 44 tests
- api_registry: 41 tests
- **Total: 279 tests passing**

## [0.6.0] - Phase 1.3 : CLI Registry

### Ajouté
- **`cli_registry.py`** (v0.1.0)
  - `RegisteredCommand` : Dataclass représentant une commande enregistrée
    - `full_name` pour les sous-commandes (e.g., "group cmd")
    - Sérialisation via `to_dict()`
  - `CommandGroup` : Groupe de commandes (pour sous-commandes)
  - `CLIRegistry` : Registre central des commandes CLI
    - `register_command()` : enregistrer une commande
    - `register_from_contribution()` : depuis CLIContribution
    - `register_group()` : créer un groupe de sous-commandes
    - `unregister_command()` / `unregister_plugin()` : retrait
    - `get_command()` / `get_plugin_commands()` / `get_all_commands()` : requêtes
    - `get_visible_commands()` : filtrage des commandes cachées
    - `resolve_command()` : résolution par chemin complet
    - `find_commands_by_name()` : recherche par nom/alias
    - Validation des noms et protection des commandes système
    - Contrôle des permissions `REGISTER_CLI`
  - `get_cli_registry()` / `reset_cli_registry()` : Singleton global
  - Liste des commandes protégées : scan, analyze, server, gui, ci, plugins, config, version, help

- **Tests** : 44 nouveaux tests dans `test_bridge_cli_registry.py`
  - TestRegisteredCommand : 4 tests
  - TestCommandGroup : 2 tests
  - TestCLIRegistryPermissions : 5 tests
  - TestCLIRegistryRegisterCommand : 4 tests
  - TestCLIRegistryValidation : 7 tests
  - TestCLIRegistryQueries : 14 tests
  - TestCLIRegistryUnregister : 5 tests
  - TestCLIRegistrySerialization : 2 tests
  - TestGlobalCLIRegistry : 2 tests

### Mis à jour
- **`__init__.py`** → v0.6.0
  - Export de `CLIRegistry`, `RegisteredCommand`, `CommandGroup`
  - Export de `get_cli_registry`, `reset_cli_registry`

### Total Tests
- interfaces: 43 tests
- manifest: 24 tests  
- bridge: 42 tests
- services: 37 tests
- events: 48 tests
- cli_registry: 44 tests
- **Total: 238 tests passing**

## [0.5.0] - Phase 1.4 : Event Bus

### Ajouté
- **`events.py`** (v0.1.0)
  - `EventTopic` : Enum des topics d'événements standard
    - Plugin lifecycle : `plugin.loaded`, `plugin.error`, `plugin.disabled`, `plugin.reloaded`
    - Scan : `scan.started`, `scan.progress`, `scan.finished`, `scan.error`
    - Analysis : `analyze.started`, `analyze.finished`, `analyze.error`
    - Config : `config.changed`, `config.reset`
    - Jobs : `job.started`, `job.progress`, `job.completed`, `job.failed`, `job.cancelled`
    - Project : `project.changed`, `project.created`, `project.deleted`
    - System : `system.ready`, `system.shutdown`
  - `Event` : Dataclass représentant un événement (topic, payload, timestamp, source_plugin)
  - `Subscription` : Dataclass pour les abonnements (topic, callback, plugin_id)
  - `EventBus` : Bus d'événements central
    - `subscribe()` / `subscribe_async()` pour s'abonner
    - `unsubscribe()` / `unsubscribe_plugin()` pour se désabonner
    - `emit()` pour émettre des événements
    - `pause()` / `resume()` pour contrôler le dispatch
    - `get_history()` / `clear_history()` pour l'historique
    - `add_websocket_hook()` / `remove_websocket_hook()` pour propagation WebSocket
    - `get_subscriptions()` / `get_topics()` pour introspection
  - `get_event_bus()` / `reset_event_bus()` : Singleton global
  - Fonctions de commodité :
    - `emit_plugin_loaded()`, `emit_plugin_error()`
    - `emit_scan_started()`, `emit_scan_progress()`, `emit_scan_finished()`, `emit_scan_error()`
    - `emit_config_changed()`
    - `emit_job_started()`, `emit_job_progress()`, `emit_job_completed()`, `emit_job_failed()`

- **Tests** : 48 nouveaux tests dans `test_bridge_events.py`
  - TestEventTopic : 4 tests
  - TestEvent : 3 tests
  - TestSubscription : 4 tests
  - TestEventBusSubscribe : 4 tests
  - TestEventBusUnsubscribe : 4 tests
  - TestEventBusEmit : 5 tests
  - TestEventBusPauseResume : 2 tests
  - TestEventBusHistory : 3 tests
  - TestEventBusWebSocket : 3 tests
  - TestEventBusIntrospection : 3 tests
  - TestGlobalEventBus : 2 tests
  - TestConvenienceFunctions : 11 tests

### Mis à jour
- **`__init__.py`** → v0.5.0
  - Export de `EventBus`, `EventTopic`, `Event`, `Subscription`
  - Export de `get_event_bus`, `reset_event_bus`
  - Export des fonctions de commodité pour emit

### Corrigé
- **`events.py`**
  - Utilisation de `datetime.now(timezone.utc)` au lieu de `datetime.utcnow()` (déprécié)
  - Comptage correct des wildcard subscriptions dans `unsubscribe_plugin()`

### Total Tests
- interfaces: 43 tests
- manifest: 24 tests  
- bridge: 42 tests
- services: 37 tests
- events: 48 tests
- **Total: 194 tests passing**

## [0.4.0] - Phase 1.2 : Service Locator

### Ajouté
- **`services.py`** (v0.1.0)
  - `PluginLogger` : Logger préfixé avec `[plugin:<id>]` pour traçabilité
  - `SecureRunner` : Wrapper sécurisé pour `core.runner` avec :
    - Vérification des permissions `run_commands`
    - Support des allow-lists de commandes
    - Logging de toutes les exécutions
  - `ConfigProxy` : Accès à la configuration avec fusion :
    - Defaults du manifest
    - Config globale du plugin
    - Overrides projet
    - Support de la notation pointée (`config.get("nested.key")`)
  - `ServiceLocator` : Point d'accès unique aux services pour les plugins :
    - `get_logger()` → PluginLogger
    - `get_runner()` → SecureRunner
    - `get_history()` → HistoryManager (avec permission fs_read)
    - `get_graph()` → GraphBuilder class
    - `get_project_manager()` → ProjectManager
    - `get_config()` → ConfigProxy
    - `get_event_bus()` → EventBusProxy
    - `has_permission()` / `require_permission()` pour vérification
  - `create_service_locator()` : Factory function

- **Tests** : 37 nouveaux tests dans `test_bridge_services.py`

### Mis à jour
- **`__init__.py`** → v0.4.0
  - Export de `PluginLogger`, `SecureRunner`, `ConfigProxy`
  - Export de `ServiceLocator` depuis services.py (remplace celui de bridge.py)
  - Export de `create_service_locator`

### Total Tests
- interfaces: 43 tests
- manifest: 24 tests  
- bridge: 42 tests
- services: 37 tests
- **Total: 146 tests passing**

## [0.3.1] - Correction des erreurs Pylance

### Corrigé
- **`manifest.py`** (v0.1.1)
  - Conversion du dataclass vers une classe normale avec `__init__` explicite
  - Les propriétés `@abstractmethod` de l'interface sont maintenant correctement implémentées
  - Correction du type de retour de `_load_schema()` (mise en cache du dict vide)
  - Suppression des imports inutilisés (`dataclass`, `field`)

- **`bridge.py`** (v0.1.1)
  - Ajout de vérification null pour `plugin_class` dans `_initialize_legacy_plugin()`
  - Meilleure gestion des erreurs lors de l'initialisation des plugins legacy

- **`interfaces.py`** (v0.1.1)
  - Ajout des propriétés abstraites manquantes : `trust_level`, `source_path`, `config_defaults`
  - Ajout de l'import `Path` pour le type `source_path`

### Tests mis à jour
- **`test_bridge_bridge.py`**
  - Correction du helper `make_manifest()` pour utiliser le bon format de données
  - Les contributions CLI/API/UI utilisent maintenant `{commands: [...]}`, `{routes: [...]}`, `{panels: [...]}`
  - Ajout d'assertions `is not None` pour les retours optionnels
  
- **`test_bridge_manifest.py`**
  - Ajout d'assertion `is not None` avant l'accès aux propriétés optionnelles

## [0.3.0] - Phase 1.1 : Bridge Singleton

### Ajouté
- **`bridge.py`** (v0.1.0)
  - Classe `Bridge` singleton centrale
  - Découverte de plugins (manifests v2 + plugins legacy v1)
  - Initialisation avec résolution des dépendances
  - Tri topologique pour l'ordre de chargement (core → system → tool)
  - Détection des dépendances circulaires
  - Shutdown et cleanup des plugins
  - `PluginInfo` : Dataclass d'info runtime pour les plugins chargés
  - `ServiceLocator` : Accès scopé aux services pour les plugins
  - `EventBusProxy` : Émission d'événements avec tracking de source
  - Registres de contributions (CLI, API, UI)
  - Registre d'actions distantes pour l'intégration Meeting
  - Health check et collecte de métriques

- **Tests** : 42 nouveaux tests dans `test_bridge_bridge.py`

### Mis à jour
- **`__init__.py`** → v0.3.0
  - Export de `Bridge`, `PluginInfo`, `ServiceLocator`, `EventBusProxy`
  - Export des exceptions manquantes (`CircularDependencyError`, `ValidationError`, `SignatureError`)

### Total Tests
- interfaces: 43 tests
- manifest: 24 tests  
- bridge: 42 tests
- **Total: 109 tests passing**

## [0.2.0] - Phase 1.1 : Manifest Parsing

### Ajouté
- **`manifest.py`** (v0.1.0)
  - `PluginManifest` dataclass implémentant `IPluginManifest`
  - Parsing YAML avec `from_yaml()` et `from_plugin_dir()`
  - Validation JSON Schema
  - `generate_manifest_for_legacy()` pour l'adaptateur v1

- **Tests** : 24 nouveaux tests dans `test_bridge_manifest.py`

### Mis à jour
- **`__init__.py`** → v0.2.0
  - Export de `PluginManifest`, `generate_manifest_for_legacy`

## [0.1.0] - Phase 0 : Préparation

### Ajouté
- **`__init__.py`** (v0.1.0)
  - Package principal du Bridge
  - Export des exceptions et interfaces
  
- **`exceptions.py`** (v0.1.0)
  - `BridgeError` : Exception de base
  - `PluginError` : Erreurs liées à un plugin spécifique
  - `ManifestError` : Erreurs de parsing/validation de manifest
  - `DependencyError` : Erreurs de dépendances
  - `CircularDependencyError` : Cycles de dépendances détectés
  - `ServiceNotFoundError` : Service non enregistré
  - `PermissionDeniedError` : Permission manquante
  - `LifecycleError` : Erreurs de cycle de vie
  - `ValidationError` : Erreurs de validation de configuration
  - `SignatureError` : Erreurs de signature de plugin

- **`interfaces.py`** (v0.1.0)
  - Énumérations :
    - `PluginState` : États du cycle de vie (discovered, loading, ready, error, disabled)
    - `PluginType` : Types de plugins (core, system, tool)
    - `Permission` : Permissions granulaires (fs_read, run_commands, etc.)
    - `UILocation` : Emplacements UI (none, sidebar, settings, both)
    - `HealthStatus` : États de santé (healthy, degraded, unhealthy)
  - Data classes :
    - `PluginCapabilities` : Déclaration des capacités
    - `CLIContribution` : Contribution CLI
    - `APIContribution` : Contribution API
    - `UIContribution` : Contribution UI
    - `HealthCheckResult` : Résultat de health check
    - `PluginMetrics` : Métriques exposées
  - Interfaces ABC :
    - `IPluginManifest` : Interface manifest
    - `IPlugin` : Interface plugin de base
    - `IPluginContribution` : Interface contribution
    - `IPluginHealth` : Interface health check
    - `IPluginMetrics` : Interface métriques
  - Protocols (duck-typing) :
    - `LegacyPlugin` : Détection plugins v1
    - `ConfigurablePlugin` : Plugins configurables
    - `UICapablePlugin` : Plugins avec UI

- **`schemas/plugin_manifest.json`** (v0.1.0)
  - Schéma JSON complet pour validation des manifests `plugin.yaml`
  - Support de toutes les sections : permissions, dependencies, capabilities, cli, api, ui, config
  - Patterns de validation pour id, version, jupiter_version
  - Énumérations pour type, trust_level, permissions, methods HTTP

- **Tests** : 43 tests dans `test_bridge_interfaces.py`

### Documentation
- `docs/PLUGIN_AUDIT.md` : Audit complet des 10 plugins existants
- `docs/PLUGIN_MIGRATION_GUIDE.md` : Guide de migration v1 → v2

### À venir (Phase 1.2)
- `services.py` : Service Locator complet
- `events.py` : Event bus pub/sub
