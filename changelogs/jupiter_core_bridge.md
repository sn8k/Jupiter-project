# Changelog - jupiter/core/bridge/

Ce fichier documente les modifications apportées au module Bridge du système de plugins Jupiter v2.

## [0.22.0] - Phase 1.3/4.3 : Ready Method & Job Export

### Ajouté
- **`bridge.py`** (v0.2.0 → v0.3.0) - Méthode ready()
  - `ready()` : Publication vers WebUI à la fin de l'initialisation
    - Construction du manifest UI (plugins_summary, ui_contributions, menu_entries)
    - Comptage des états plugins (ready/error)
    - Émission de l'événement PLUGINS_READY
    - Auto-initialisation si nécessaire
  - `_build_ui_manifest()` : Helper pour construire le manifest WebUI
  - 18 tests dans test_bridge_lifecycle.py

- **`events.py`** (v0.0.1 → v0.1.0)
  - `EventTopic.PLUGINS_READY` : Nouveau topic pour la notification ready
  - `emit_plugins_ready()` : Fonction d'émission avec plugins_ready, plugins_error, ui_manifest

- **`jobs.py`** (v0.2.0 → v0.3.0) - Export de jobs
  - `export_job()` : Export d'un job vers JSON/YAML ou dict
  - `export_jobs()` : Export multiple avec filtres (status, plugin_id)
  - Fonctions convenience au niveau module
  - 12 tests dans test_bridge_jobs.py

### Modifié
- **`__init__.py`** (v0.21.0 → v0.22.0)
  - Export de `emit_plugins_ready` depuis events
  - Export de `export_job`, `export_jobs` depuis jobs

## [0.15.0] - Phase 7.2/7.3/7.4 : Signature, Circuit Breaker, Monitoring

### Ajouté
- **`signature.py`** (v0.1.0) - Système de signature cryptographique
  - `TrustLevel` : Niveaux de confiance (OFFICIAL, VERIFIED, COMMUNITY, UNSIGNED)
  - `SignatureAlgorithm` : Algorithmes supportés (SHA256_RSA, SHA512_RSA, ED25519)
  - `SignatureInfo`, `VerificationResult`, `SigningResult` : Dataclasses
  - `TrustedSigner` : Signataires de confiance avec révocation
  - `SignatureVerifier` : Vérification des plugins signés
  - `PluginSigner` : Signature de plugins
  - Fonctions module : `get_signature_verifier()`, `verify_plugin()`, `sign_plugin()`, etc.
  - 58 tests

- **`jobs.py`** (v0.1.0 → v0.2.0) - Circuit Breaker ajouté
  - `CircuitState` enum : CLOSED, OPEN, HALF_OPEN
  - `CircuitBreaker` dataclass : Track des échecs, seuil, cooldown
  - `CircuitBreakerRegistry` : Gestion des circuit breakers
  - `JobManager` : Intégration circuit breaker
  - 42 nouveaux tests

- **`monitoring.py`** (v0.1.0) - Système de monitoring
  - `AuditEventType` enum : Types d'événements d'audit
  - `AuditEntry`, `AuditLogger` : Logging d'audit avec filtres et stats
  - `TimeoutConfig` : Configuration des timeouts par opération
  - `with_timeout()`, `sync_with_timeout()` : Wrappers timeout
  - `RateLimitConfig`, `RateLimiter` : Rate limiting token bucket
  - `PluginMonitor` : Classe centrale combinant audit, timeouts, rate limiting
  - Fonctions module : `get_monitor()`, `audit_log()`, `check_rate_limit()`, etc.
  - 50 tests

### Modifié
- **`__init__.py`** (v0.14.0 → v0.15.0)
  - Export signature : TrustLevel, SignatureVerifier, PluginSigner, etc.
  - Export circuit breaker : CircuitState, CircuitBreaker, CircuitBreakerRegistry
  - Export monitoring : AuditEventType, AuditLogger, PluginMonitor, RateLimiter, etc.
  - Documentation mise à jour

### Tests
- **766 tests** Bridge passing (vs 674 précédemment)
  - +58 tests signature
  - +42 tests circuit breaker
  - +50 tests monitoring (note: some overlap with deselected tests)

## [0.14.0] - Phase 7.2 : Plugin Signature System

### Ajouté
- **`legacy_adapter.py`** (v0.1.0) - Adaptateur pour plugins v1
  - `LegacyAdapter` : Découverte et wrapping des plugins legacy
  - `LegacyPluginWrapper` : Adapte les plugins v1 à l'interface v2
  - `LegacyManifest`, `LegacyCapabilities` : Manifest auto-généré
  - `is_legacy_plugin()`, `is_legacy_ui_plugin()` : Fonctions de détection
  - Singleton avec `get_legacy_adapter()`, `init_legacy_adapter()`
  - 50 tests

- **`permissions.py`** (v0.1.0) - Système de permissions granulaires
  - `PermissionChecker` : Vérification centrale des permissions
  - `has_permission()`, `check_permission()`, `require_permission()` : API de vérification
  - `require_any_permission()`, `require_all_permissions()` : Multi-permissions
  - Checks scopés : `check_fs_read()`, `check_fs_write()`, `check_run_command()`, etc.
  - `@require_permission` décorateur
  - Logging audit avec `get_check_log()`, `get_stats()`
  - 52 tests

- **`hot_reload.py`** (v0.1.0) - Rechargement dynamique des plugins
  - `HotReloader` : Gestion du hot reload
  - `reload()` : Rechargement avec unload/reimport
  - `can_reload()` : Validation avant reload
  - `HotReloadError`, `ReloadResult`, `ReloadHistoryEntry` : Types
  - Historique avec `get_history()`, stats avec `get_stats()`
  - Blacklist pour plugins core
  - Thread safety avec locks par plugin
  - 57 tests

### Modifié
- **`__init__.py`** (v0.12.0 → v0.13.0)
  - Export des nouveaux modules : `legacy_adapter`, `permissions`, `hot_reload`
  - Documentation mise à jour

### Tests
- **616 tests** Bridge passing (vs 457 précédemment)
  - +50 tests legacy_adapter
  - +52 tests permissions
  - +57 tests hot_reload

## [0.12.0] - Phase 3.1 & 4.1 : CLI & API dynamiques

### Modifié
- **`jupiter/cli/main.py`** (v1.2.0 → v1.3.0)
  - Ajout `_add_plugin_commands()` : charge commandes CLI depuis Bridge
  - Ajout `_handle_plugin_command()` : exécute commande plugin dynamique
  - Commandes plugins préfixées `p:plugin_id:command_name`
  - Support arguments et options depuis `RegisteredCommand`

- **`jupiter/server/api.py`** (v1.2.0 → v1.3.0)
  - Ajout `_mount_plugin_api_routes()` : monte routers FastAPI des plugins
  - Appel automatique après init Bridge dans lifespan
  - Support prefix et tags depuis `APIContribution`
  - Logging des routes montées

### Tests
- **425 tests** Bridge + router plugins passing

## [0.11.0] - Phase 2.2 : Configuration par projet

### Ajouté
- **`plugin_config.py`** (v0.1.0) - Gestionnaire de configuration plugins
  - `PluginConfigManager` : Gère la fusion config globale + project overrides
  - `ProjectPluginRegistry` : Registre des états enabled/disabled par projet
  - Support des 3 couches : defaults manifest → global config → project overrides
  - `get_merged_config()` : Configuration fusionnée
  - `is_enabled_for_project()` : Vérifier si plugin activé
  - `set_enabled_for_project()` : Modifier état par projet
  - `save_global_config()` : Sauvegarder config globale
  - Deep merge pour configurations imbriquées
  - Support notation pointée (dot notation) pour accès aux clés

### Modifié
- **`services.py`** (v0.1.0 → v0.2.0)
  - `get_config()` utilise maintenant `PluginConfigManager`
  - Ajout `get_config_manager()` pour opérations avancées
  - Ajout `is_enabled_for_project()` méthode directe
  - Suppression des méthodes privées dupliquées

- **`__init__.py`** (v0.9.0 → v0.10.0)
  - Export de `PluginConfigManager`, `ProjectPluginRegistry`

### Tests
- `tests/test_bridge_plugin_config.py` (v0.1.0) - 27 tests
- **425 tests** Bridge + router plugins passing

## [0.10.0] - Phase 2.1 : Core Plugins & Contributions

### Ajouté
- **`core_plugins/__init__.py`** (v0.1.0) - Registre des core plugins
  - `get_core_plugins()` : Retourne liste d'instances IPlugin
  - `get_core_plugin_ids()` : Retourne liste des IDs
  - Plugins hard-codés, pas de fichiers manifest

- **`core_plugins/settings_update_plugin.py`** (v0.1.0) - Premier core plugin
  - `SettingsUpdateManifest` : Implémente IPluginManifest
  - `SettingsUpdatePlugin` : Implémente IPlugin, IPluginHealth, IPluginMetrics
  - Routes API : `/version`, `/apply`, `/upload`
  - Contribution UI pour page Settings
  - Logique update ZIP/Git avec validation

### Modifié
- **`bridge.py`** (v0.2.0)
  - Ajout `discover_core_plugins()` method
  - `discover()` appelle core plugins en premier
  - `_initialize_v2_plugin()` supporte plugins pré-instanciés
  - `_register_contributions()` appelle `get_api_contribution()`/`get_ui_contribution()`

- **`interfaces.py`** (v0.2.0)
  - `APIContribution` : ajout `router`, `prefix`, `plugin_id` fields
  - `UIContribution` : ajout `plugin_id`, `panel_type`, `panel_id`, `mount_point` fields
  - Tous les champs optionnels avec defaults pour flexibilité

### Tests
- `tests/test_bridge_core_plugins.py` (v0.1.0) - 24 tests
- `tests/test_bridge_bridge.py` (v0.1.1) - Mise à jour pour core plugins
- **398 tests** Bridge + router plugins passing

## [0.9.2] - Corrections Pylance

### Corrigé (bootstrap.py v0.1.1)
- Utilisation de `bridge.plugins_dir = plugins_dir` avant `bridge.discover()` au lieu de passer un argument
- Fix de l'itération `get_all_plugins()` qui retourne une List, pas un Dict (suppression de `.keys()`)
- Utilisation de `getattr()` pour l'appel à `disable_plugin` (future-proof)
- Chemin plugins_dir calculé via `Path(__file__)` au lieu de `get_project_root()` inexistant

## [0.9.1] - Phase 3.2 : CLI Commands

### Ajouté
- **`jupiter/cli/plugin_commands.py`** (v0.1.0) - Commandes CLI plugins
  - `jupiter plugins list` : Liste tous les plugins (groupés par type)
  - `jupiter plugins info <id>` : Détails d'un plugin
  - `jupiter plugins enable <id>` : Active un plugin
  - `jupiter plugins disable <id>` : Désactive un plugin
  - `jupiter plugins status` : Statut du Bridge
  - Support `--json` sur toutes les commandes

### Modifié
- **`jupiter/cli/main.py`** (v1.2.0)
  - Ajout des imports pour plugin_commands
  - Ajout des handlers au registre CLI_HANDLERS
  - Ajout du parser pour la commande `plugins`

### Total Tests
- 343 tests Bridge + registries passing

## [0.9.0] - Phase 1.5 : Integration Bootstrap

### Ajouté
- **`bootstrap.py`** (v0.1.0) - Module d'initialisation du système de plugins
  - `init_plugin_system(app, config, plugins_dir)` : Initialise le Bridge et les registries
  - `shutdown_plugin_system()` : Arrête proprement le système de plugins
  - `is_initialized()` : Vérifie l'état d'initialisation
  - `get_bridge()` : Retourne l'instance du Bridge
  - `get_plugin_stats()` : Statistiques sur les plugins chargés
  - Reset automatique des registries au démarrage
  - Découverte et chargement des plugins dans l'ordre de dépendance
  - Attach des registries à `app.state` de FastAPI

- **`jupiter/server/routers/plugins.py`** (v0.1.0) - Router API pour plugins v2
  - `GET /plugins/v2/status` : Statut du système Bridge
  - `GET /plugins/v2` : Liste des plugins avec filtres (type, state)
  - `GET /plugins/v2/{plugin_id}` : Détails d'un plugin
  - `GET /plugins/v2/ui/manifest` : Manifeste UI pour le frontend
  - `GET /plugins/v2/cli/manifest` : Manifeste CLI pour documentation
  - `GET /plugins/v2/api/manifest` : Manifeste API pour documentation

- **Tests** : 10 tests dans `test_bridge_bootstrap.py`
  - TestIsInitialized : 2 tests
  - TestGetBridge : 2 tests
  - TestGetPluginStats : 2 tests
  - TestInitPluginSystemSync : 2 tests
  - TestShutdownPluginSystemSync : 2 tests

### Corrigé
- Fix : `get_all_plugins()` retourne une liste et non un dict

### Total Tests
- interfaces: 43 tests
- manifest: 24 tests  
- bridge: 42 tests
- services: 37 tests
- events: 48 tests
- cli_registry: 44 tests
- api_registry: 41 tests
- ui_registry: 54 tests
- bootstrap: 10 tests
- **Total: 343 tests passing**

## [0.8.0] - Phase 5 : UI Registry

### Ajouté
- **`ui_registry.py`** (v0.1.0)
  - `RegisteredPanel` : Dataclass représentant un panneau UI
    - `full_route` incluant le préfixe `/plugins/<plugin_id>`
    - `i18n_title_key` avec préfixe automatique `plugin.<id>.`
    - Support de `lazy_load`, `requires_auth`, `component_path`
  - `RegisteredMenuItem` : Dataclass pour les items de menu
    - Support des sous-menus via `parent`
    - `separator_before` / `separator_after` pour séparateurs
  - `SettingsSchema` : Schéma JSON de configuration plugin
    - Support `ui_schema` pour personnalisation de l'interface
    - `defaults` pour valeurs par défaut
  - `PluginUIManifest` : Manifeste UI d'un plugin
    - `has_sidebar` / `has_settings` propriétés calculées
    - `i18n_namespace` pour localisation
  - `UIRegistry` : Registre central des contributions UI
    - `register_panel()` : enregistrer un panneau
    - `register_from_contribution()` : depuis UIContribution
    - `register_menu_item()` : enregistrer un item de menu
    - `register_settings_schema()` : enregistrer un schéma de config
    - `unregister_panel()` / `unregister_menu_item()` / `unregister_plugin()` : retrait
    - `get_panel()` / `get_plugin_panels()` / `get_sidebar_panels()` / `get_settings_panels()` : requêtes
    - `get_menu_items()` avec filtrage par parent
    - `get_plugin_manifest()` / `get_ui_manifest()` : export complet
    - Validation des IDs et contrôle des permissions `REGISTER_UI`
  - `get_ui_registry()` / `reset_ui_registry()` : Singleton global

- **Tests** : 54 nouveaux tests dans `test_bridge_ui_registry.py`
  - TestRegisteredPanel : 6 tests
  - TestRegisteredMenuItem : 3 tests
  - TestSettingsSchema : 2 tests
  - TestPluginUIManifest : 5 tests
  - TestUIRegistryPermissions : 5 tests
  - TestUIRegistryRegisterPanel : 3 tests
  - TestUIRegistryValidation : 5 tests
  - TestUIRegistryMenuItems : 3 tests
  - TestUIRegistrySettingsSchema : 3 tests
  - TestUIRegistryQueries : 9 tests
  - TestUIRegistryUnregister : 5 tests
  - TestUIRegistryManifest : 2 tests
  - TestUIRegistrySerialization : 2 tests
  - TestGlobalUIRegistry : 2 tests

### Mis à jour
- **`__init__.py`** → v0.8.0
  - Export de `UIRegistry`, `RegisteredPanel`, `RegisteredMenuItem`
  - Export de `SettingsSchema`, `PluginUIManifest`
  - Export de `get_ui_registry`, `reset_ui_registry`

### Total Tests
- interfaces: 43 tests
- manifest: 24 tests  
- bridge: 42 tests
- services: 37 tests
- events: 48 tests
- cli_registry: 44 tests
- api_registry: 41 tests
- ui_registry: 54 tests
- **Total: 333 tests passing**

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
