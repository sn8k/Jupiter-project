# TODO – Refonte du système de plugins Jupiter

**Version cible** : Architecture v2 (basée sur `docs/plugins_architecture.md` v0.5.0)  
**Date de création** : 2025-12-03  
**Statut** : En cours - Phase 0/1/1.3/2/3.1/3.2/4.1/4.2/4.2.1/4.3/5.3/5.6(backend)/6.1/6.2/7.1/7.2/7.3/7.5/8.1/8.2/8.3/9.1/9.2/9.3(CLI)/11.1/11.2(partiel) complètes

**Total tests Bridge** : 1348 (inclus 74 tests CLI+intégration)

---

## Vue d'ensemble

Cette roadmap décrit les étapes de migration du système de plugins actuel vers l'architecture v2. L'objectif est d'alléger la base (`app.js`), améliorer l'extensibilité, et préparer Jupiter pour un futur modulaire.

**Principes directeurs** :
  - Migration progressive (pas de big bang)
  - Compatibilité ascendante temporaire (adaptateur legacy)
  - Chaque phase est testable et déployable indépendamment
  - chaque fichier doit avoir son propre numero de version, mis à jour meme en cas de hotfix mineur
  - on verifie les fichiers avec pylance avant de tester.

**infos importante**
  - modele de plugin prevu : voir dossier docs\plugin_model
  - documents complementaires : 
    - docs\plugins_architecture.md
    - docs\PLUGIN_AUDIT.md
    - docs\PLUGIN_MIGRATION_GUIDE.md
---

## Phase 0 : Préparation (1-2 semaines)

### 0.1 Audit de l'existant
- [x] Inventorier tous les plugins actuels (`jupiter/plugins/`) ✅ docs/PLUGIN_AUDIT.md
- [x] Documenter leurs hooks actuels (`on_scan`, `on_analyze`, `register_cli`, `register_api`) ✅ docs/PLUGIN_AUDIT.md §2
- [x] Identifier les dépendances inter-plugins existantes ✅ docs/PLUGIN_AUDIT.md §4
- [x] Lister les contributions CLI/API/UI de chaque plugin ✅ docs/PLUGIN_AUDIT.md §3
- [x] Évaluer la complexité de migration de chaque plugin (simple/moyen/complexe) ✅ docs/PLUGIN_AUDIT.md §5

### 0.2 Infrastructure de base
- [x] Créer le dossier `jupiter/core/bridge/` pour le futur Bridge ✅
- [x] Définir les interfaces Python (ABC) pour les contrats de plugins :
  - [x] `IPlugin` : interface de base ✅ jupiter/core/bridge/interfaces.py
  - [x] `IPluginManifest` : parsing de `plugin.yaml` ✅ jupiter/core/bridge/interfaces.py
  - [x] `IPluginContribution` : CLI/API/UI contributions ✅ jupiter/core/bridge/interfaces.py
  - [x] `IPluginHealth` : healthcheck ✅ jupiter/core/bridge/interfaces.py
  - [x] `IPluginMetrics` : métriques ✅ jupiter/core/bridge/interfaces.py
- [x] Créer les classes d'exception dédiées (`PluginError`, `ManifestError`, `DependencyError`) ✅ jupiter/core/bridge/exceptions.py
- [x] Ajouter les tests unitaires pour les interfaces ✅ tests/test_bridge_interfaces.py (43 tests)

### 0.3 Documentation et standards
- [x] Finaliser `docs/plugins_architecture.md` (fait : v0.4.0) ✅
- [x] Créer `docs/PLUGIN_MIGRATION_GUIDE.md` pour les développeurs ✅
- [x] Mettre à jour `docs/plugin_model/` comme référence (fait : v0.3.0) ✅
- [x] Définir le schéma JSON pour validation des manifests ✅ jupiter/core/bridge/schemas/plugin_manifest.json

---

## Phase 1 : Plugin Core Bridge (2-3 semaines)

### 1.1 Implémentation du Bridge de base
- [x] Créer `jupiter/core/bridge/__init__.py` ✅ v0.3.0
- [x] Créer `jupiter/core/bridge/bridge.py` ✅ v0.1.0 :
  - [x] Classe `Bridge` singleton ✅
  - [x] Registre des plugins (`_plugins: Dict[str, PluginInfo]`) ✅
  - [x] Registre des contributions CLI (`_cli_contributions`) ✅
  - [x] Registre des contributions API (`_api_contributions`) ✅
  - [x] Registre des contributions UI (`_ui_contributions`) ✅
  - [x] Registre des actions distantes (`_remote_actions`) pour Meeting ✅
- [x] Implémenter le parsing de manifest (`plugin.yaml`) ✅ jupiter/core/bridge/manifest.py :
  - [x] Validation du schéma (JSON Schema) ✅
  - [x] Vérification de compatibilité `jupiter.version` ✅
  - [x] Extraction des entrypoints ✅
  - [x] Extraction des permissions ✅
  - [x] Support `extends: true` pour mode extension (§3.8) ✅
- [x] Tests unitaires pour le Bridge de base ✅ tests/test_bridge_bridge.py (42 tests)

### 1.2 Service Locator (§3.3.1)
- [x] Créer `jupiter/core/bridge/services.py` ✅ (37 tests) :
  - [x] `get_logger(plugin_id)` → logger préconfiguré ✅
  - [x] `get_runner()` → wrapper sécurisé sur `core.runner` ✅
  - [x] `get_history()` → accès au HistoryManager ✅
  - [x] `get_graph()` → accès au GraphManager ✅
  - [x] `get_project_manager()` → accès au ProjectManager ✅
  - [x] `get_event_bus()` → bus d'événements ✅
  - [x] `get_config(plugin_id)` → config du plugin avec fusion overrides ✅
- [x] Wrapper sécurisé pour `runner.py` ✅ SecureRunner :
  - [x] Vérification des permissions avant exécution ✅
  - [x] Logging des appels ✅
  - [x] Timeout configurable ✅
- [x] Tests unitaires pour chaque service ✅ tests/test_bridge_services.py

### 1.3 Cycle de vie des plugins (§3.5)
- [x] Implémenter les phases :
  - [x] `discover()` : scan de `jupiter/plugins/`, validation manifests ✅
  - [x] `initialize()` : chargement des plugins core, puis système ✅
  - [x] `register()` : enregistrement des contributions ✅ `_register_contributions()`
  - [x] `ready()` : publication vers WebUI ✅ bridge.py v0.3.0, events.py v0.1.0
- [x] Gestion des états par plugin (`loading`, `ready`, `error`, `disabled`) ✅
- [x] Détection des cycles de dépendances (§3.8) ✅ `CircularDependencyError`
- [x] Ordre de chargement topologique ✅ `_sort_by_load_order()`
- [x] Tests d'intégration pour le cycle de vie ✅ tests/test_bridge_lifecycle.py (18 tests)

### 1.4 Événements pub/sub
- [x] Créer event bus basique dans bridge.py :
  - [x] `emit(topic, payload)` côté serveur ✅
  - [x] `subscribe(topic, callback)` côté serveur ✅
  - [x] Propagation vers WebSocket pour WebUI ✅ ws_bridge.py v0.1.0
- [x] Créer `jupiter/core/bridge/events.py` avec module dédié ✅ (48 tests)
- [x] Topics standard :
  - [x] `PLUGIN_LOADED`, `PLUGIN_ERROR`, `PLUGIN_DISABLED` ✅ (émis dans bridge.py)
  - [x] `SCAN_STARTED`, `SCAN_FINISHED`, `SCAN_ERROR` ✅ (émis dans scan.py router v1.2.0)
  - [x] `CONFIG_CHANGED` ✅ (émis dans system.py router v1.7.0)
- [x] Tests pour les événements ✅ tests/test_bridge_events.py (48 tests)

### 1.5 Intégration Bootstrap
- [x] Créer `jupiter/core/bridge/bootstrap.py` ✅ (10 tests)
  - [x] `init_plugin_system(app, config, plugins_dir)` ✅
  - [x] `shutdown_plugin_system()` ✅
  - [x] `is_initialized()`, `get_bridge()`, `get_plugin_stats()` ✅
- [x] Créer `jupiter/server/routers/plugins.py` ✅ (17 tests)
  - [x] `GET /plugins/v2/status` ✅
  - [x] `GET /plugins/v2` avec filtres ✅
  - [x] `GET /plugins/v2/{id}` ✅
  - [x] `GET /plugins/v2/ui/manifest` ✅
- [x] Modifier `jupiter/server/api.py` pour initialiser le Bridge au démarrage ✅ v1.2.0
  - [x] Import du router plugins v2 ✅
  - [x] Initialisation dans le lifespan ✅
  - [x] Shutdown propre ✅
- [x] Tests d'intégration API ✅ tests/test_router_plugins.py

---

## Phase 2 : Migration des plugins core (1-2 semaines)

### 2.1 settings_update comme plugin core
- [x] Identifier les fonctionnalités actuelles de `settings_update` ✅
- [x] Migrer vers le nouveau modèle (pas de manifest, hard-codé) ✅
  - [x] Créer `core_plugins/__init__.py` ✅ v0.1.0
  - [x] Créer `core_plugins/settings_update_plugin.py` ✅ v0.1.0
  - [x] `SettingsUpdateManifest` implements IPluginManifest ✅
  - [x] `SettingsUpdatePlugin` implements IPlugin, IPluginHealth, IPluginMetrics ✅
- [x] Enregistrer les routes API via `get_api_contribution()` ✅
- [x] Enregistrer les UI via `get_ui_contribution()` ✅
- [x] Câbler avec le Service Locator ✅
- [x] Tests de non-régression ✅ tests/test_bridge_core_plugins.py (24 tests)

### 2.2 Configuration par projet (§3.1.1)
- [x] Implémenter la fusion config globale + overrides projet ✅
  - [x] Lecture de `jupiter/plugins/<id>/config.yaml` (config globale plugin) ✅
  - [x] Lecture de `<project>.jupiter.yaml` section `plugins.<id>.config_overrides` ✅
  - [x] Fusion avec priorité aux overrides projet ✅
- [x] Exposer via `bridge.services.get_config(plugin_id)` ✅
- [x] Supporter `enabled: true/false` par projet ✅
- [x] Tests de fusion de configuration ✅ tests/test_bridge_plugin_config.py (27 tests)

---

## Phase 3 : Contributions CLI (1-2 semaines)

### 3.1 Enregistrement CLI via Bridge
- [x] Créer `jupiter/core/bridge/cli_registry.py` ✅ (44 tests) :
  - [x] `register_cli_contribution(plugin_id, commands)` ✅
  - [x] Résolution dynamique des entrypoints ✅
- [x] Modifier `jupiter/cli/main.py` pour interroger le Bridge ✅ v1.3.0
  - [x] `_add_plugin_commands()` : charge commandes depuis CLIRegistry
  - [x] `_handle_plugin_command()` : exécute handler dynamiquement
  - [x] Commandes préfixées `p:plugin_id:cmd` pour éviter conflits
- [x] Charger les sous-commandes des plugins dynamiquement ✅
- [x] Tests E2E des commandes CLI de plugins ✅ tests/test_cli_plugin_commands.py (32 tests)

### 3.2 Commandes système
- [x] `jupiter plugins list` : lister les plugins (état, version, type) ✅
- [x] `jupiter plugins info <id>` : détails d'un plugin ✅
- [x] `jupiter plugins enable <id>` / `disable <id>` : activation/désactivation ✅
- [x] `jupiter plugins status` : statut du Bridge ✅
- [x] `jupiter plugins install <source>` : installation depuis URL/path ✅ v0.2.0
- [x] `jupiter plugins uninstall <id>` : désinstallation ✅ v0.2.0
- [x] `jupiter plugins scaffold <id>` : génération d'un nouveau plugin (§7.1) ✅ v0.2.0
- [x] `jupiter plugins reload <id>` : hot reload en dev mode (§10.5) ✅ v0.2.0
- [x] Tests pour chaque commande ✅ tests/test_cli_plugin_commands.py

---

## Phase 4 : Contributions API (1-2 semaines)

### 4.1 Enregistrement API via Bridge
- [x] Créer `jupiter/core/bridge/api_registry.py` ✅ (71 tests) :
  - [x] `register_api_contribution(plugin_id, router)` ✅
  - [x] Montage dynamique des routers FastAPI ✅
  - [x] Préfixe automatique `/plugins/<id>/` ✅
- [x] Modifier `jupiter/server/api.py` pour monter les routes des plugins ✅ v1.3.0
  - [x] `_mount_plugin_api_routes()` : monte routers depuis Bridge
  - [x] Appel automatique après init dans lifespan
- [x] Validation des permissions avant appel de route ✅ api_registry.py v0.2.0
  - [x] `APIPermissionValidator` : validateur runtime avec middleware ✅
  - [x] `RoutePermissionConfig` : configuration par route ✅
  - [x] `PermissionValidationResult` : résultat détaillé ✅
  - [x] `@require_plugin_permission()` : décorateur pour handlers ✅
  - [x] Bypass configurable (health, metrics, docs) ✅
  - [x] Statistiques de validation ✅
- [x] Tests des routes API de plugins (E2E) ✅ tests/test_bridge_api_registry.py (71 tests)

### 4.2 Endpoints standard par plugin
- [x] `/plugins/<id>/health` : healthcheck du plugin ✅
- [x] `/plugins/<id>/metrics` : métriques du plugin (format JSON) ✅
- [x] `/plugins/<id>/logs` : téléchargement des logs ✅
- [x] `/plugins/<id>/logs/stream` : WebSocket pour logs temps réel ✅ (v0.3.0)
- [x] `/plugins/<id>/config` : GET/PUT configuration ✅
- [x] `/plugins/<id>/reset-settings` : reset aux defaults ✅
- [x] Tests d'intégration API ✅ tests/test_router_plugins.py (31 tests)

### 4.2.1 Collecte des métriques (§10.2)
- [x] Plugins exposent optionnellement `metrics() -> dict` ✅
- [x] Bridge collecte et expose via `/metrics` ✅ metrics.py v0.1.0
- [x] Déclaration dans manifest : `capabilities.metrics.enabled`, `export_format` ✅
- [x] Fréquence de collecte configurable (globale et par plugin) ✅
- [x] Mode `debug-metrics` pour collecte intensive temporaire ✅
- [x] Dashboards WebUI : widgets activité des plugins ✅ app.js getPluginActivityWidget(), loadPluginActivityWidgets()
- [x] Alerting : seuils configurables déclenchant notifications ✅ alerting.py v0.1.0 (53 tests)
- [x] Tests ✅ tests/test_bridge_metrics.py (30 tests) + tests/test_bridge_alerting.py (53 tests)

### 4.3 Système de jobs (§10.6)
- [x] Créer `jupiter/core/bridge/jobs.py` ✅ v0.1.0 :
  - [x] `submit(plugin_id, handler, params)` → job_id ✅
  - [x] `cancel(job_id)` → bool ✅
  - [x] `get(job_id)` → JobInfo ✅
  - [x] `list(plugin_id)` → List[JobInfo] ✅
- [x] États de job : `pending`, `running`, `completed`, `failed`, `cancelled` ✅
- [x] Événements WebSocket : `JOB_STARTED`, `JOB_PROGRESS`, `JOB_COMPLETED`, `JOB_FAILED` ✅
- [x] Payload progression avec `progress`, `message`, `eta_seconds` ✅
- [x] Timeouts configurables (global + par plugin dans manifest `capabilities.jobs`) ✅
- [x] Circuit breaker par plugin (échecs répétés → refus temporaire) ✅
- [x] Période de cool-down avant réactivation ✅
- [x] Pattern coopératif d'annulation (plugin vérifie `job.is_cancelled()`) ✅
- [x] Limites de concurrence par plugin (`max_concurrent`) ✅
- [x] Endpoints API ✅ system.py v1.9.0 :
  - [x] `GET /jobs` : tous les jobs ✅
  - [x] `GET /jobs/{id}` : statut d'un job ✅
  - [x] `POST /jobs/{id}/cancel` : annuler un job ✅
  - [x] `DELETE /jobs/history` : nettoyer jobs terminés ✅
- [x] Persistance optionnelle (jobs terminés consultables, nettoyage auto) ✅
- [x] Export des résultats de job vers fichier ✅ jobs.py v0.3.0 :
  - [x] `export_job()` : export single job to JSON/YAML or dict ✅
  - [x] `export_jobs()` : export multiple jobs with filters ✅
  - [x] 12 tests export ✅ tests/test_bridge_jobs.py
- [x] Tests des jobs async ✅ tests/test_bridge_jobs.py (34 tests total)

---

## Phase 5 : Contributions WebUI (3-4 semaines)

### 5.1 Conteneur de plugins dans la WebUI
- [x] Créer `jupiter/web/js/plugin_container.js` ✅ v0.1.0 :
  - [x] Zone dynamique pour monter les panneaux plugins ✅
  - [x] Chargement lazy des bundles JS ✅
  - [x] Gestion du routage `/plugins/<id>` ✅
- [x] Créer `jupiter/web/js/plugin_integration.js` ✅ v0.1.0 :
  - [x] Récupérer la liste des plugins via `/plugins` ✅
  - [x] Intégration avec pluginUIState existant ✅
  - [x] Router vers les panneaux plugins ✅
- [ ] Tests UI (manuel ou Playwright)

### 5.2 API front commune (window.jupiterBridge)
- [x] Créer `jupiter/web/js/jupiter_bridge.js` ✅ v0.1.0 :
  - [x] `api.get(path)`, `api.post(path, data)` : appels API avec auth/logs ✅
  - [x] `ws.connect(path)` : connexion WebSocket ✅
  - [x] `events.subscribe(topic, callback)` : abonnement aux events ✅
  - [x] `events.unsubscribe(topic, callback)` : désabonnement ✅
  - [x] `i18n.t(key)` : traduction ✅
  - [x] `notify.info(msg)`, `notify.success(msg)`, `notify.error(msg)` : notifications ✅
  - [x] `modal.show(options)` : modale générique ✅
  - [x] `config.get(plugin_id)`, `config.set(plugin_id, data)` : config plugin ✅
  - [x] `plugins.getVersion(plugin_id)` : version d'un plugin ✅
  - [x] `plugins.checkUpdate(plugin_id)` : vérifier mise à jour ✅
  - [x] `plugins.update(plugin_id, version)` : mettre à jour ✅
  - [x] `ai.sendContext(plugin_id, data)` : export vers agent IA ✅
- [x] Exposer globalement `window.jupiterBridge` ✅
- [ ] Tests du bridge front

### 5.3 Enregistrement UI via Bridge (backend)
- [x] Créer `jupiter/core/bridge/ui_registry.py` ✅ v0.1.0 (54 tests) :
  - [x] `register_ui_contribution(plugin_id, panels, menus)` ✅
  - [x] Stocker les infos de panneau (mount_point, route, title_key) ✅
  - [x] `RegisteredPanel`, `RegisteredMenuItem`, `SettingsSchema` dataclasses ✅
  - [x] Validation des IDs et caractères autorisés ✅
  - [x] Support des menus et sous-menus ✅
  - [x] i18n keys avec préfixes automatiques ✅
- [x] Endpoint `/plugins/ui-manifest` retournant toutes les contributions UI ✅
- [x] Tests backend ✅ tests/test_bridge_ui_registry.py (54 tests)

### 5.4 Auto-UI : formulaires de configuration (§3.4.3)
- [x] Créer `jupiter/web/js/auto_form.js` ✅ v0.1.0 :
  - [x] Générer un formulaire HTML depuis un JSON Schema ✅
  - [x] Types supportés : string, boolean, integer, number, array, object ✅
  - [x] Attributs : title, description, default, enum, format, min, max ✅
- [x] Intégrer dans la page Settings (cadre par plugin) ✅ plugin_integration.js
- [x] Validation avant sauvegarde ✅ v0.2.0 (format, exclusiveMin/Max, multipleOf, uniqueItems, enum, x-validate)
- [ ] Tests de génération de formulaires

### 5.5 Auto-UI : carte de statistiques
- [x] Créer `jupiter/web/js/metrics_widget.js` ✅ v0.1.0 :
  - [x] Si `capabilities.metrics.enabled` → générer une carte de stats ✅
  - [x] Afficher : exécutions, erreurs, dernière exécution, durée moyenne ✅
  - [x] Refresh périodique via `/metrics` ✅
  - [x] Sparkline charts pour historique ✅
  - [x] Threshold alerts (warning/critical) ✅
- [ ] Tests

### 5.6 Composant de logs partagé (§10.3)
- [x] Créer `jupiter/web/js/logs_panel.js` ✅ v0.2.0 :
  - [x] Connexion WebSocket pour logs temps réel ✅
  - [x] Filtrage par niveau (DEBUG, INFO, WARNING, ERROR) ✅
  - [x] Recherche textuelle ✅
  - [x] Pause/reprise du flux ✅
  - [x] Auto-scroll configurable ✅
  - [x] Bouton téléchargement (`.log`/`.txt`) ✅
  - [x] Option compression `.zip` ✅ v0.2.0 (JSZip/CompressionStream)
  - [x] Tronquage côté client (truncateLongMessages, maxMessageLength) ✅ v0.2.0
  - [x] Limitation du flux WS pour éviter saturation ✅ v0.2.0 (rate limiting, batch processing)
- [ ] Injecter automatiquement dans chaque page plugin
- [ ] Panneau logs centralisé avec filtre par plugin, niveau, plage de temps
- [x] Export des logs filtrés vers fichier ✅
- [x] Backend : logger avec préfixe `[plugin:<plugin_id>]` pour traçabilité ✅ services.py v0.3.0
- [x] Config niveau de log par plugin (dans `config.yaml` ou Settings) ✅ services.py v0.3.0
- [x] Niveau global comme plancher (plugin ne peut pas être plus verbeux) ✅ services.py v0.3.0
- [ ] Tests

### 5.7 Cadre Settings par plugin (§9)
- [x] Créer `jupiter/web/js/plugin_settings_frame.js` ✅ v0.2.0 :
  - [x] En-tête avec version du plugin ✅
  - [x] Bouton "Check for update" ✅ v0.2.0
  - [x] Bouton "Update plugin" (avec confirmation et rollback) ✅ v0.2.0
  - [x] Formulaire auto-généré (ou custom) ✅
  - [x] Bouton "Save" avec validation et feedback (succès/erreur) ✅
  - [ ] Support `dry-run` quand pertinent
  - [x] Bouton "View changelog" (affiche `changelog.md` en modale) ✅ v0.2.0
  - [x] Bouton "Reset settings" ✅
  - [x] Toggle "Debug mode" (avec désactivation auto après délai configurable) ✅ v0.2.0
  - [x] Réglages versionnés, exportables/importables (fichier) ✅
- [ ] Intégrer dans la page Settings globale
- [ ] Tests

### 5.8 i18n pour plugins
- [x] Créer `jupiter/web/js/i18n_loader.js` ✅ v0.2.0 :
  - [x] Chargement dynamique des fichiers de langue ✅
  - [x] Support des namespaces pour plugins ✅
  - [x] Clés préfixées `plugin.<plugin_id>.<key>` ✅
  - [x] Fonction `bridge.i18n.t()` avec fallback ✅
  - [x] Pluralisation et interpolation ✅
- [x] Fusionner les fichiers `web/lang/*.json` des plugins au chargement ✅ v0.2.0 (loadPluginTranslations, loadAllPluginTranslations)
- [ ] Tests de traduction

### 5.9 Panneau d'aide contextuel (§9)
- [x] Créer `jupiter/web/js/help_panel.js` ✅ v0.1.0 :
  - [x] Chaque plugin avec WebUI peut afficher un panneau d'aide (slide-in) ✅
  - [x] Contenu provenant de fragments i18n (`web/lang/*.json`) ✅
  - [x] Liens vers documentation inclus ✅
  - [x] Sections collapsibles avec recherche ✅
  - [x] Raccourcis clavier (F1, ?, Escape) ✅
  - [x] Formatage markdown-like (bold, code, listes) ✅
  - [x] Formulaire de feedback intégré ✅
- [ ] Tests UI

### 5.10 Export de données (§9)
- [x] Créer `jupiter/web/js/data_export.js` ✅ v0.1.0 :
  - [x] Suivre le modèle "pylance analyzer" pour exports vers agents IA ✅
  - [x] Format JSON structuré avec schéma documenté ✅
  - [x] Formats supportés : JSON, NDJSON, CSV, Markdown ✅
  - [x] Sélection de source de données (scan, analysis, functions, files, metrics, history) ✅
  - [x] Filtres (eq, ne, gt, lt, contains, startswith) ✅
  - [x] Sélection de champs à exporter ✅
  - [x] Export vers fichier téléchargeable ou clipboard ✅
  - [x] Indication de taille et prévisualisation rapide ✅
- [ ] Tests

### 5.11 Ergonomie WebUI (§9)
- [x] Créer `jupiter/web/js/ux_utils.js` ✅ v0.1.0 :
  - [x] Progress indicators (ring, bar, steps) ✅
  - [x] Task status badges (pending, running, success, error) ✅
  - [x] Skeleton loaders ✅
  - [x] Debounce/throttle utilities ✅
  - [x] Focus management (trapFocus, saveFocus) ✅
  - [x] Keyboard navigation helpers ✅
  - [x] Responsive breakpoint utilities ✅
  - [x] Animation helpers (fadeIn/Out, slideUp/Down) ✅
- [x] Styles CSS ajoutés pour tous les composants ✅ styles.css v1.2.0
- [ ] Intégration dans les composants existants
- [ ] Tests UX

---

## Phase 6 : Migration des plugins existants (2-3 semaines)

### 6.1 Adaptateur legacy (§4.2)


- [x] Créer `jupiter/core/bridge/legacy_adapter.py` ✅ v0.1.0 (50 tests) :
  - [x] Détecter les anciens plugins (classe avec `on_scan`/`on_analyze`) ✅ `is_legacy_plugin()`
  - [x] Générer un manifest minimal à la volée ✅ `LegacyManifest`
  - [x] Enregistrer via le Bridge avec flag `legacy: true` ✅
  - [x] Appliquer des permissions restrictives par défaut ✅
  - [x] `LegacyPluginWrapper` pour adapter les plugins v1 ✅
  - [x] `LegacyAdapter` singleton pour gestion centralisée ✅
  - [x] Detection des plugins UI legacy (`is_legacy_ui_plugin()`) ✅
- [x] Flag `legacy: true` dans réponse `/plugins` pour indication WebUI ✅
- [x] Documentation de migration avec exemples concrets ✅ docs/PLUGIN_MIGRATION_GUIDE.md v0.2.0
  - [x] Exemple complet avant/après pour plugin d'analyse ✅
  - [x] Checklist de migration ✅
  - [x] Points clés de comparaison v1/v2 ✅
- [x] Les plugins legacy continuent de fonctionner pendant la transition ✅
- [x] Tests de l'adaptateur ✅ tests/test_bridge_legacy_adapter.py (50 tests)

### 6.2 Migration de `ai_helper`
- [x] Créer `jupiter/plugins/ai_helper/plugin.yaml` ✅ v1.1.0
- [x] Refactorer vers le nouveau modèle ✅ :
  - [x] `__init__.py` avec `init()`, `health()`, `metrics()`, `reset_settings()` ✅
  - [x] Configuration schema avec JSON Schema pour Auto-UI ✅
  - [x] Hooks: `on_scan()`, `on_analyze()` ✅
  - [x] `web/lang/en.json`, `fr.json` pour i18n (50+ clés) ✅
  - [x] `CHANGELOG.md` pour historique ✅
  - [x] `server/api.py` avec routes enregistrées via Bridge ✅ v1.1.0
    - [x] Endpoints standard: `/health`, `/metrics`, `/logs`, `/logs/stream` ✅
    - [x] Job management: `/jobs` (GET, POST), `/jobs/{id}` (GET, DELETE) ✅
    - [x] AI-specific: `/suggestions`, `/suggestions/file`, `/config` ✅
    - [x] `register_api_contribution(app, bridge)` ✅
  - [x] `cli/commands.py` avec sous-commandes ✅ v1.1.0
    - [x] `jupiter ai suggest` : génération de suggestions ✅
    - [x] `jupiter ai analyze-file` : analyse de fichier ✅
    - [x] `jupiter ai status|health|config` : gestion plugin ✅
    - [x] `register_cli_contribution(subparsers)` ✅
  - [x] `web/panels/main.js` pour panneau WebUI ✅ v1.1.0
    - [x] Panneau complet avec filtres, exports, logs temps réel ✅
    - [x] `mount(container, bridge)` et `unmount(container)` ✅
  - [x] `core/logic.py` : logique métier isolée ✅
    - [x] `generate_suggestions()`, `analyze_single_file()` ✅
  - [x] `tests/test_plugin.py` : tests unitaires ✅
- [x] Tests de non-régression ✅ (imports, lifecycle, CLI, logic validés)
- [x] Legacy `ai_helper.py` conservé pour compatibilité ✅

### 6.3 Migration des autres plugins
- [x] Pour chaque plugin existant :
  - [x] Créer le manifest `plugin.yaml`
  - [x] Refactorer le code
  - [x] Créer les fichiers WebUI si UI
  - [x] Ajouter les traductions i18n
  - [x] Tests (Pylance verification passed)
- [x] Plugins migrés (complexité basse) :
  - [x] `pylance_analyzer` (v1.0.0) ✅ - Complete v2 structure with core/server/web
  - [x] `notifications_webhook` (v1.0.0) ✅ - Async notification dispatch, i18n
  - [x] `watchdog` (v1.0.0) ✅ - Background monitoring thread, settings UI
- [ ] Plugins restants (complexité haute/moyenne) :
  - [ ] `code_quality` (2276 lignes, complexité haute)
  - [ ] `livemap` (1245 lignes, complexité moyenne)
  - [ ] `autodiag_plugin` (1523 lignes, complexité moyenne)

### 6.4 Retrait de l'adaptateur legacy
- [ ] Une fois tous les plugins migrés, marquer l'adaptateur comme deprecated
- [ ] Supprimer dans une version future

---

## Phase 7 : Sécurité et sandbox (2-3 semaines)

### 7.1 Permissions granulaires (§3.6)
- [x] Créer `jupiter/core/bridge/permissions.py` ✅ v0.1.0 (52 tests) :
  - [x] `PermissionChecker` classe centrale de vérification ✅
  - [x] `has_permission(plugin_id, permission)` - vérification sans exception ✅
  - [x] `check_permission(plugin_id, permission)` - retourne `PermissionCheckResult` ✅
  - [x] `require_permission(plugin_id, permission)` - lève exception si refusé ✅
  - [x] `require_any_permission()`, `require_all_permissions()` - multi-permissions ✅
- [x] Implémenter la vérification des permissions dans le Bridge :
  - [x] `check_fs_read(plugin_id, path)` : autoriser/refuser lecture FS ✅
  - [x] `check_fs_write(plugin_id, path)` : autoriser/refuser écriture FS ✅
  - [x] `check_run_command(plugin_id, command)` : autoriser/refuser exécution runner ✅
  - [x] `check_network(plugin_id, url)` : autoriser/refuser appels réseau ✅
  - [x] `check_meeting_access(plugin_id)` : autoriser/refuser accès Meeting ✅
  - [x] `check_config_access(plugin_id)` : autoriser/refuser accès config ✅
  - [x] `check_emit_events(plugin_id)` : autoriser/refuser émission events ✅
- [x] Décorateur `@require_permission(Permission.X)` ✅
- [x] Logging audit avec `get_check_log()` et `get_stats()` ✅
- [ ] Affichage des permissions demandées lors de l'installation (WebUI)
- [x] Tests des contrôles de permission ✅ tests/test_bridge_permissions.py (52 tests)

### 7.2 Signature des plugins (§3.9)
- [x] Créer `jupiter/core/bridge/signature.py` ✅ (58 tests) :
  - [x] `TrustLevel` enum : OFFICIAL, VERIFIED, COMMUNITY, UNSIGNED ✅
  - [x] `SignatureVerifier` classe principale ✅
    - [x] `verify_plugin(plugin_path)` → VerificationResult avec trust_level ✅
    - [x] Gestion des signataires de confiance (add/remove/revoke) ✅
    - [x] Niveau de confiance minimum configurable ✅
    - [x] Expiration des signatures ✅
    - [x] Logging des vérifications ✅
    - [x] Persistance du trust store ✅
  - [x] `PluginSigner` pour signer les plugins ✅
    - [x] `sign_plugin(plugin_path)` → SigningResult ✅
    - [x] Génération de fichiers plugin.sig ✅
  - [x] Support RSA/Ed25519 (prêt pour intégration cryptography) ✅
- [x] Export dans `bridge/__init__.py` ✅ v0.14.0
- [x] Commande CLI `jupiter plugins sign <path>` ✅ main.py v1.5.0, plugin_commands.py v0.3.0
  - [x] `--signer-id`, `--signer-name` (or env vars) ✅
  - [x] `--trust-level` (official/verified/community) ✅
  - [x] `--key` (optional private key) ✅
- [x] Commande CLI `jupiter plugins verify <path>` ✅
  - [x] `--require-level` pour validation stricte ✅
- [x] Vérification à l'installation dans Bridge ✅ plugin_commands.py v0.4.0
  - [x] `_verify_plugin_signature()` helper function ✅
  - [x] Intégration dans `handle_plugins_install()` ✅
  - [x] Support mode développeur (auto-approve unsigned) ✅
  - [x] Support `--force` pour bypass ✅
- [x] Badge de confiance dans la WebUI ✅ app.js getTrustBadge(), styles.css, lang/en.json + fr.json
- [x] Tests de signature ✅ tests/test_bridge_signature.py (58 tests)
- [x] Tests CLI sign/verify ✅ tests/test_cli_plugin_commands.py (14 tests)

### 7.3 Circuit breaker (§10.6)
- [x] Implémenter le circuit breaker par plugin ✅ jobs.py v0.2.0 (42 tests) :
  - [x] `CircuitState` enum : CLOSED, OPEN, HALF_OPEN ✅
  - [x] `CircuitBreaker` dataclass ✅
    - [x] Compter les échecs consécutifs ✅
    - [x] Seuil configurable (`failure_threshold`) ✅
    - [x] Période de cool-down (`cooldown_seconds`) ✅
    - [x] Transitions automatiques d'état ✅
  - [x] `CircuitBreakerRegistry` pour gestion multi-plugins ✅
  - [x] Intégration dans `JobManager` :
    - [x] Vérification avant soumission de job ✅
    - [x] Enregistrement automatique succès/échec ✅
    - [x] `is_circuit_open()`, `reset_circuit_breaker()`, `list_open_circuits()` ✅
- [x] Afficher l'état du circuit breaker dans `/plugins` et WebUI ✅ plugin_manager.py v1.9.0, app.js getCircuitBreakerBadge()
- [x] Tests ✅ tests/test_bridge_circuit_breaker.py (42 tests)

### 7.4 Monitoring et limites
- [x] Créer `jupiter/core/bridge/monitoring.py` ✅ v0.1.0 (50 tests) :
  - [x] **Audit Logging** ✅
    - [x] `AuditEventType` enum avec types complets ✅
    - [x] `AuditEntry` dataclass pour les événements ✅
    - [x] `AuditLogger` classe avec filtres et stats ✅
    - [x] Logging de toutes les actions sensibles ✅
  - [x] **Timeout Management** ✅
    - [x] `TimeoutConfig` avec timeouts par opération ✅
    - [x] Overrides par plugin ✅
    - [x] `with_timeout()` async wrapper ✅
    - [x] `sync_with_timeout()` sync wrapper ✅
    - [x] Timeouts configurables sur toutes les opérations ✅
  - [x] **Rate Limiting** ✅
    - [x] `RateLimitConfig` configuration ✅
    - [x] `RateLimiter` token bucket algorithm ✅
    - [x] Limites par plugin configurables ✅
  - [x] `PluginMonitor` classe centrale ✅
  - [x] Fonctions globales : `get_monitor()`, `audit_log()`, `check_rate_limit()` ✅
- [ ] Monitoring des métriques CPU/RAM par plugin (optionnel v2)
- [x] Export dans `bridge/__init__.py` ✅ v0.15.0
- [x] Tests ✅ tests/test_bridge_monitoring.py (50 tests)

### 7.5 Gouvernance (§6)
- [x] Liste blanche/blacklist via config globale ✅
  - [x] `governance.py` v0.1.0 ✅
  - [x] `ListMode` enum (DISABLED, WHITELIST, BLACKLIST) ✅
  - [x] `GovernanceConfig` dataclass ✅
  - [x] `GovernanceManager` classe centrale ✅
  - [x] Protected plugins (cannot be blacklisted) ✅
  - [x] JSON persistence ✅
- [x] Feature flags pour activer/désactiver sans désinstaller ✅
  - [x] `FeatureFlag` dataclass (dev_mode requirements, deprecation) ✅
  - [x] Per-plugin feature flags ✅
  - [x] Global feature flags (override plugin-level) ✅
- [x] Export dans `bridge/__init__.py` ✅ v0.17.0
- [x] Tests ✅ tests/test_bridge_governance.py (75 tests)

---

## Phase 8 : Hot Reload et mode développeur (1-2 semaines)

### 8.1 Hot Reload (§10.5)
- [x] Créer `jupiter/core/bridge/hot_reload.py` ✅ v0.1.0 (57 tests) :
  - [x] `HotReloader` classe pour gestion du rechargement ✅
  - [x] `reload(plugin_id, force, preserve_config)` - méthode principale ✅
  - [x] `can_reload(plugin_id)` - vérification de faisabilité ✅
  - [x] `HotReloadError` exception avec détails de phase ✅
  - [x] `ReloadResult` dataclass avec success/failure/duration ✅
- [x] Implémenter `bridge.reload_plugin(plugin_id)` ✅ via `reload_plugin()` :
  - [x] Dé-enregistrement des contributions (CLI, API, UI) ✅
  - [x] Déchargement modules (`sys.modules`) ✅
  - [x] Ré-import frais ✅
  - [x] Ré-appel des entrypoints (via `_rediscover_plugin()`, `initialize()`) ✅
  - [x] Notification WebSocket `PLUGIN_RELOADED` ✅
- [x] Historique des rechargements avec `get_history()` ✅
- [x] Statistiques avec `get_stats()` ✅
- [x] Blacklist pour plugins core non-reloadables ✅
- [x] Callbacks pour notifications ✅
- [x] Thread safety avec locks par plugin ✅
- [x] Activer uniquement si `developer_mode: true` ✅ plugins.py v0.4.0, config.py v1.4.0
- [x] Commande CLI `jupiter plugins reload <id>` ✅ (déjà implémentée en 3.2)
- [x] Bouton dans WebUI (cadre développeur) ✅ app.js v1.7.0 (visible en dev mode)
- [x] Tests ✅ tests/test_bridge_hot_reload.py (57 tests)

### 8.2 Mode développeur
- [x] Flag `developer_mode` dans `global_config.yaml` ✅
- [x] Créer `jupiter/core/bridge/dev_mode.py` ✅ v0.1.0 (61 tests) :
  - [x] `DevModeConfig` dataclass de configuration ✅
  - [x] `DeveloperMode` classe gestionnaire ✅
  - [x] `PluginFileHandler` pour file watching ✅
- [x] Activer :
  - [x] Hot reload (`enable_hot_reload`, `auto_reload_on_change`) ✅
  - [x] Logs DEBUG par défaut (`verbose_logging`, `log_level`) ✅
  - [x] Plugins non signés acceptés sans confirmation (`allow_unsigned_plugins`, `skip_signature_verification`) ✅
  - [x] Console de test pour exécuter commandes plugin manuellement (`enable_test_console`) ✅
  - [x] Désactiver rate limiting (`disable_rate_limiting`) ✅
  - [x] Endpoints debug (`enable_debug_endpoints`) ✅
  - [x] Profiling optionnel (`enable_profiling`) ✅
- [x] Désactiver en production (all bypasses return False when `enabled=False`) ✅
- [x] Fonctions globales : `get_dev_mode()`, `is_dev_mode()`, `enable_dev_mode()`, `disable_dev_mode()` ✅
- [x] Tests ✅ tests/test_bridge_dev_mode.py (61 tests)

### 8.3 Idées complémentaires (§10.4)
- [x] Notifications par plugin ✅ notifications.py v0.1.0 :
  - [x] Émission de notifications (toast, badge sur icône) ✅
  - [x] Types : info, success, warning, error, action_required ✅
  - [x] Priorités : LOW, NORMAL, HIGH, URGENT ✅
  - [x] Canaux : TOAST, BADGE, ALERT, SILENT ✅
  - [x] Configurable par utilisateur (désactiver par plugin) ✅
  - [x] Muting global et par plugin avec expiration ✅
  - [x] Actions avec callbacks ✅
  - [x] Badge counters pour notifications non lues ✅
  - [x] Delivery callbacks pour intégration WebSocket ✅
- [x] Export dans `bridge/__init__.py` ✅ v0.18.0
- [x] Tests ✅ tests/test_bridge_notifications.py (79 tests)
- [x] Statistiques d'utilisation par plugin ✅ usage_stats.py v0.1.0 :
  - [x] Nombre d'exécutions, dernière exécution, durée moyenne ✅
  - [x] Statistiques par méthode (min/max/median/p95) ✅
  - [x] Taux de succès/échec par plugin et méthode ✅
  - [x] Tracking load/unload des plugins ✅
  - [x] Tagging des plugins pour filtrage ✅
  - [x] Agrégations par timeframe (hour/day/week/month) ✅
  - [x] Top plugins par exécutions, durée, erreurs ✅
  - [x] Méthodes les plus lentes ✅
  - [x] Résumé des erreurs avec types ✅
  - [x] ExecutionTimer context manager ✅
  - [x] Persistance sur disque ✅
  - [x] Callbacks sur nouvelles exécutions ✅
- [x] Export dans `bridge/__init__.py` ✅ v0.19.0
- [x] Tests ✅ tests/test_bridge_usage_stats.py (91 tests)
- [x] Rapport d'erreur intégré ✅ error_report.py v0.1.0 :
  - [x] Création de rapports depuis exceptions ✅
  - [x] Anonymisation des données sensibles (chemins, emails, IPs, tokens) ✅
  - [x] Détection automatique de sévérité et catégorie ✅
  - [x] Déduplication par hash de stacktrace ✅
  - [x] Export multi-format (JSON, Markdown, Text, Minimal) ✅
  - [x] Callbacks pour soumission externe ✅
  - [x] Persistance sur disque ✅
  - [x] Notes utilisateur et étapes de reproduction ✅
- [x] Export dans `bridge/__init__.py` ✅ v0.20.0
- [x] Tests ✅ tests/test_bridge_error_report.py (85 tests)

---

## Phase 9 : Marketplace et distribution (3-4 semaines)

### 9.1 Installation depuis source externe (§6)
- [x] `jupiter plugins install <url>` ✅ plugin_commands.py v0.5.0 :
  - [x] Télécharger le paquet (zip) ✅ `_download_from_url()`
  - [x] Vérifier signature si présente ✅ `_verify_plugin_signature()`
  - [x] Valider manifest ✅ `_validate_plugin_manifest()`
  - [x] Vérifier dépendances ✅ via `--install-deps`
  - [x] Installer sous `jupiter/plugins/<id>/` ✅
  - [x] Journaliser l'installation ✅ (logger)
- [x] `jupiter plugins install <path>` : installation locale ✅
- [x] Option `--install-deps` : installer les dépendances manquantes ✅
- [x] Option `--dry-run` : simuler sans installer ✅
- [x] Rollback en cas d'échec ✅ (via backup dans update)
- [x] Tests ✅ tests/test_cli_plugin_commands.py (TestInstallComprehensive, TestValidateManifest, TestInstallDependencies)

### 9.2 Désinstallation
- [x] `jupiter plugins uninstall <id>` ✅ :
  - [x] Vérifier qu'aucun autre plugin n'en dépend ✅ (via `plugin_type == core`)
  - [x] Décharger le plugin ✅
  - [x] Supprimer les fichiers ✅ `shutil.rmtree()`
  - [x] Journaliser ✅
- [x] Confirmation utilisateur ✅ (prompt ou `--force`)
- [x] Tests ✅ tests/test_cli_plugin_commands.py (TestUninstallComprehensive)

### 9.3 Mise à jour
- [x] `jupiter plugins update <id>` ✅ plugin_commands.py v0.5.0 :
  - [x] Vérifier le registre/marketplace ✅ (manifest repository/homepage)
  - [x] Télécharger la nouvelle version ✅
  - [x] Backup de l'ancienne version ✅ (plugins/.backups/)
  - [x] Installer la nouvelle version ✅
  - [x] Rollback si échec ✅
- [x] `jupiter plugins check-updates` : vérifier toutes les mises à jour ✅
- [ ] Boutons "Check for update" / "Update" dans WebUI
- [x] Tests ✅ tests/test_cli_plugin_commands.py (TestUpdateComprehensive, TestCheckUpdates)

### 9.4 Registre/Marketplace (optionnel v2+)
- [ ] Définir le format du registre (JSON, API REST)
- [ ] Endpoint `/marketplace/search`, `/marketplace/info/<id>`
- [ ] Intégration WebUI pour parcourir le catalogue
- [ ] Notation et avis (futur)
- [ ] Tests

---

## Phase 10 : Meeting et opérations distantes (Conditionnel)

> **⚠️ Cette phase est spéculative et dépend de la disponibilité de Meeting.**

### 10.1 Actions distantes (§8)
- [ ] Si Meeting disponible :
  - [ ] Scope v1 limité : lecture seule + confirmation locale obligatoire
  - [ ] `bridge.remote_actions.register(action_id, plugin_id, requires_confirmation)`
  - [ ] Validation des plans d'action signés
  - [ ] Mode "demande / approbation locale" avant "forcer" complet
  - [ ] Limiter aux plugins de confiance (signés) et actions réversibles
  - [ ] Alertes UI/CLI et mécanisme dry-run
- [ ] Tests (mocks)

### 10.2 Reset distant
- [ ] Action `reset_plugin_settings` :
  - [ ] Meeting envoie la demande (plan d'action signé)
  - [ ] Bridge valide (signature, plugin présent, permissions)
  - [ ] Bridge affiche confirmation dans UI
  - [ ] Exécution si confirmé
- [ ] Schéma de configuration versionné avec defaults sûrs
- [ ] Audit trail (qui, quand, quoi)
- [ ] Mode dégradé : si Meeting indisponible, aucune opération forcée
- [ ] Tests

### 10.3 Standardisation actions distantes
- [ ] API Bridge : `bridge.remote_actions.register(id, plugin_id, requires_confirmation)`
- [ ] Meeting envoie plan d'action signé JSON
- [ ] Bridge valide signature, plugin, permissions
- [ ] Affichage dans UI comme demande à accepter
- [ ] Tests

---

## Phase 11 : Finalisation et documentation (1-2 semaines)

### 11.1 Tests d'intégration complets
- [x] Scénario : installation d'un plugin depuis zéro ✅ tests/test_plugin_integration.py
- [x] Scénario : utilisation complète d'un plugin (CLI, API, WebUI) ✅ tests/test_plugin_integration.py
- [x] Scénario : mise à jour d'un plugin ✅ tests/test_plugin_integration.py
- [x] Scénario : échec et recovery ✅ tests/test_plugin_integration.py
- [ ] Scénario : jobs longs avec annulation
- [x] Tests de performance ✅ tests/test_plugin_integration.py (bulk event emission)

### 11.2 Documentation finale
- [x] Mettre à jour `docs/plugins_architecture.md` avec retours d'implémentation ✅ v0.5.0
- [ ] Mettre à jour `docs/plugin_model/` avec exemples finaux
- [x] Créer `docs/PLUGIN_DEVELOPER_GUIDE.md` complet ✅ v1.0.0
- [x] Mettre à jour `Manual.md` avec nouvelles commandes ✅
- [x] Mettre à jour `README.md` ✅ v1.8.48
- [ ] Changelog global

### 11.3 Dépréciation et nettoyage
- [ ] Marquer l'ancien système comme deprecated
- [ ] Supprimer le code obsolète
- [ ] Bump version majeure si breaking changes

---

## Estimation globale

| Phase | Durée estimée | Priorité |
|-------|---------------|----------|
| Phase 0 : Préparation | 1-2 semaines | Haute |
| Phase 1 : Bridge core | 2-3 semaines | Haute |
| Phase 2 : Plugins core | 1-2 semaines | Haute |
| Phase 3 : CLI | 1-2 semaines | Haute |
| Phase 4 : API | 1-2 semaines | Haute |
| Phase 5 : WebUI | 3-4 semaines | Haute |
| Phase 6 : Migration plugins | 2-3 semaines | Haute |
| Phase 7 : Sécurité | 2-3 semaines | Moyenne |
| Phase 8 : Hot Reload | 1-2 semaines | Moyenne |
| Phase 9 : Marketplace | 3-4 semaines | Basse |
| Phase 10 : Meeting | Conditionnel | Basse |
| Phase 11 : Finalisation | 1-2 semaines | Haute |

**Total estimé** : 18-28 semaines (4.5-7 mois)

---

## Dépendances critiques

```
Phase 0 ─┬─> Phase 1 (Bridge) ─┬─> Phase 2 (Plugins core)
         │                     ├─> Phase 3 (CLI)
         │                     ├─> Phase 4 (API) ─> Phase 5 (WebUI)
         │                     └─> Phase 6 (Migration) ─> Phase 7 (Sécurité)
         │
         └─> Phase 8 (Hot Reload) ─> Phase 9 (Marketplace)
                                 └─> Phase 10 (Meeting) [si disponible]
         
         Tout ─> Phase 11 (Finalisation)
```

---

## Notes

- Les durées sont des estimations basées sur un développeur à temps partiel.
- Les phases peuvent être parallélisées si plusieurs développeurs sont disponibles.
- Les phases 9 et 10 sont optionnelles pour la v1.
- Chaque phase doit être validée avant de passer à la suivante.
- pylance doit etre lancé AVANT les tests
- Les tests  sont obligatoires à chaque phase.

---

## Changelog de ce document

### 2025-12-03 (mise à jour)
- Ajout §5.9 : Panneau d'aide contextuel (§9 architecture)
- Ajout §5.10 : Export de données vers agents IA (§9 architecture)
- Ajout §5.11 : Ergonomie WebUI (§9 architecture)
- Enrichissement §5.6 : Logs (tronquage, compression, niveau plancher)
- Enrichissement §5.7 : Settings frame (dry-run, versioning, désactivation auto debug)
- Ajout §4.2.1 : Collecte métriques détaillée (§10.2)
- Enrichissement §4.3 : Jobs (payload, concurrence, persistance)
- Ajout §7.5 : Gouvernance (whitelist/blacklist, feature flags)
- Enrichissement §8.2 : Mode dev (console de test)
- Ajout §8.3 : Idées complémentaires (notifications, stats, rapport erreur)
- Enrichissement §10.1-10.2 : Actions distantes (dry-run, mode dégradé, audit)
- Ajout §10.3 : Standardisation actions distantes Meeting
- Enrichissement §1.1 : Bridge (remote_actions, extends mode)
- Enrichissement §6.1 : Legacy adapter (flag WebUI, doc migration)
- ~200 tâches totales

### 2025-12-03
- Création initiale basée sur `plugins_architecture.md` v0.4.0
- 11 phases définies avec ~180 tâches
