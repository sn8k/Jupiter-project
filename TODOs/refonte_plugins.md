# TODO – Refonte du système de plugins Jupiter

**Version cible** : Architecture v2 (basée sur `docs/plugins_architecture.md` v0.4.0)  
**Date de création** : 2025-12-03  
**Statut** : En cours - Phase 0 complète (sauf tests), Phase 1 en préparation

---

## Vue d'ensemble

Cette roadmap décrit les étapes de migration du système de plugins actuel vers l'architecture v2. L'objectif est d'alléger la base (`app.js`), améliorer l'extensibilité, et préparer Jupiter pour un futur modulaire.

**Principes directeurs** :
- Migration progressive (pas de big bang)
- Compatibilité ascendante temporaire (adaptateur legacy)
- Chaque phase est testable et déployable indépendamment
- chaque fichier doit avoir son propre numero de version, mis à jour meme en cas de hotfix mineur

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
- [ ] Créer `jupiter/core/bridge/services.py` :
  - [ ] `get_logger(plugin_id)` → logger préconfiguré
  - [ ] `get_runner()` → wrapper sécurisé sur `core.runner`
  - [ ] `get_history()` → accès au HistoryManager
  - [ ] `get_graph()` → accès au GraphManager
  - [ ] `get_project_manager()` → accès au ProjectManager
  - [ ] `get_event_bus()` → bus d'événements
  - [ ] `get_config(plugin_id)` → config du plugin avec fusion overrides
- [ ] Wrapper sécurisé pour `runner.py` :
  - [ ] Vérification des permissions avant exécution
  - [ ] Logging des appels
  - [ ] Timeout configurable
- [ ] Tests unitaires pour chaque service

### 1.3 Cycle de vie des plugins (§3.5)
- [x] Implémenter les phases :
  - [x] `discover()` : scan de `jupiter/plugins/`, validation manifests ✅
  - [x] `initialize()` : chargement des plugins core, puis système ✅
  - [x] `register()` : enregistrement des contributions ✅ `_register_contributions()`
  - [ ] `ready()` : publication vers WebUI
- [x] Gestion des états par plugin (`loading`, `ready`, `error`, `disabled`) ✅
- [x] Détection des cycles de dépendances (§3.8) ✅ `CircularDependencyError`
- [x] Ordre de chargement topologique ✅ `_sort_by_load_order()`
- [ ] Tests d'intégration pour le cycle de vie

### 1.4 Événements pub/sub
- [x] Créer event bus basique dans bridge.py :
  - [x] `emit(topic, payload)` côté serveur ✅
  - [x] `subscribe(topic, callback)` côté serveur ✅
  - [ ] Propagation vers WebSocket pour WebUI
- [ ] Créer `jupiter/core/bridge/events.py` avec module dédié
- [ ] Topics standard :
  - [x] `PLUGIN_LOADED`, `PLUGIN_ERROR`, `PLUGIN_DISABLED` ✅ (émis dans bridge.py)
  - [ ] `SCAN_STARTED`, `SCAN_FINISHED`, `SCAN_ERROR`
  - [ ] `CONFIG_CHANGED`
- [ ] Tests pour les événements

### 1.5 Intégration Bootstrap
- [ ] Modifier `jupiter/server/api.py` pour initialiser le Bridge au démarrage
- [ ] Le Bridge charge les plugins core (lui-même, `settings_update`)
- [ ] Exposer `/plugins` endpoint (liste des plugins, états, versions)
- [ ] Exposer `/plugins/{id}` endpoint (détails d'un plugin)
- [ ] Tests d'intégration API

---

## Phase 2 : Migration des plugins core (1-2 semaines)

### 2.1 settings_update comme plugin core
- [ ] Identifier les fonctionnalités actuelles de `settings_update`
- [ ] Migrer vers le nouveau modèle (pas de manifest, hard-codé)
- [ ] Enregistrer les gardes de configuration via Bridge
- [ ] Câbler avec le Service Locator
- [ ] Tests de non-régression

### 2.2 Configuration par projet (§3.1.1)
- [ ] Implémenter la fusion config globale + overrides projet :
  - [ ] Lecture de `jupiter/plugins/<id>/config.yaml` (config globale plugin)
  - [ ] Lecture de `<project>.jupiter.yaml` section `plugins.<id>.config_overrides`
  - [ ] Fusion avec priorité aux overrides projet
- [ ] Exposer via `bridge.services.get_config(plugin_id)`
- [ ] Supporter `enabled: true/false` par projet
- [ ] Tests de fusion de configuration

---

## Phase 3 : Contributions CLI (1-2 semaines)

### 3.1 Enregistrement CLI via Bridge
- [ ] Créer `jupiter/core/bridge/cli_registry.py` :
  - [ ] `register_cli_contribution(plugin_id, commands)`
  - [ ] Résolution dynamique des entrypoints
- [ ] Modifier `jupiter/cli/main.py` pour interroger le Bridge
- [ ] Charger les sous-commandes des plugins dynamiquement
- [ ] Tests des commandes CLI de plugins

### 3.2 Commandes système
- [ ] `jupiter plugins list` : lister les plugins (état, version, type)
- [ ] `jupiter plugins info <id>` : détails d'un plugin
- [ ] `jupiter plugins enable <id>` / `disable <id>` : activation/désactivation
- [ ] `jupiter plugins install <source>` : installation depuis URL/path
- [ ] `jupiter plugins uninstall <id>` : désinstallation
- [ ] `jupiter plugins scaffold <id>` : génération d'un nouveau plugin (§7.1)
- [ ] `jupiter plugins reload <id>` : hot reload en dev mode (§10.5)
- [ ] Tests pour chaque commande

---

## Phase 4 : Contributions API (1-2 semaines)

### 4.1 Enregistrement API via Bridge
- [ ] Créer `jupiter/core/bridge/api_registry.py` :
  - [ ] `register_api_contribution(plugin_id, router)`
  - [ ] Montage dynamique des routers FastAPI
  - [ ] Préfixe automatique `/plugins/<id>/`
- [ ] Modifier `jupiter/server/api.py` pour monter les routes des plugins
- [ ] Validation des permissions avant appel de route
- [ ] Tests des routes API de plugins

### 4.2 Endpoints standard par plugin
- [ ] `/plugins/<id>/health` : healthcheck du plugin
- [ ] `/plugins/<id>/metrics` : métriques du plugin (format Prometheus ou JSON configurable)
- [ ] `/plugins/<id>/logs` : téléchargement des logs
- [ ] `/plugins/<id>/logs/stream` : WebSocket pour logs temps réel
- [ ] `/plugins/<id>/config` : GET/PUT configuration
- [ ] `/plugins/<id>/reset-settings` : reset aux defaults
- [ ] Tests d'intégration API

### 4.2.1 Collecte des métriques (§10.2)
- [ ] Plugins exposent optionnellement `metrics() -> dict`
- [ ] Bridge collecte et expose via `/metrics`
- [ ] Déclaration dans manifest : `capabilities.metrics.enabled`, `export_format`
- [ ] Fréquence de collecte configurable (globale et par plugin)
- [ ] Mode `debug-metrics` pour collecte intensive temporaire
- [ ] Dashboards WebUI : widgets activité des plugins
- [ ] Alerting : seuils configurables déclenchant notifications
- [ ] Tests

### 4.3 Système de jobs (§10.6)
- [ ] Créer `jupiter/core/bridge/jobs.py` :
  - [ ] `submit(plugin_id, handler, params)` → job_id
  - [ ] `cancel(job_id)` → bool
  - [ ] `get(job_id)` → JobInfo
  - [ ] `list(plugin_id)` → List[JobInfo]
- [ ] États de job : `pending`, `running`, `completed`, `failed`, `cancelled`
- [ ] Événements WebSocket : `JOB_STARTED`, `JOB_PROGRESS`, `JOB_COMPLETED`, `JOB_FAILED`
- [ ] Payload progression avec `progress`, `message`, `eta_seconds`
- [ ] Timeouts configurables (global + par plugin dans manifest `capabilities.jobs`)
- [ ] Circuit breaker par plugin (échecs répétés → refus temporaire)
- [ ] Période de cool-down avant réactivation
- [ ] Pattern coopératif d'annulation (plugin vérifie `job.is_cancelled()`)
- [ ] Limites de concurrence par plugin (`max_concurrent`)
- [ ] Endpoints API :
  - [ ] `GET /jobs` : tous les jobs
  - [ ] `POST /jobs` : créer un job
  - [ ] `GET /jobs/{id}` : statut d'un job
  - [ ] `DELETE /jobs/{id}` : annuler un job
- [ ] Persistance optionnelle (jobs terminés consultables, nettoyage auto)
- [ ] Export des résultats de job vers fichier
- [ ] Tests des jobs async

---

## Phase 5 : Contributions WebUI (3-4 semaines)

### 5.1 Conteneur de plugins dans la WebUI
- [ ] Créer `jupiter/web/js/plugin_container.js` :
  - [ ] Zone dynamique pour monter les panneaux plugins
  - [ ] Chargement lazy des bundles JS
  - [ ] Gestion du routage `/plugins/<id>`
- [ ] Modifier `jupiter/web/app.js` :
  - [ ] Récupérer la liste des plugins via `/plugins`
  - [ ] Générer les entrées de menu dynamiquement
  - [ ] Router vers les panneaux plugins
- [ ] Tests UI (manuel ou Playwright)

### 5.2 API front commune (window.jupiterBridge)
- [ ] Créer `jupiter/web/js/jupiter_bridge.js` :
  - [ ] `api.get(path)`, `api.post(path, data)` : appels API avec auth/logs
  - [ ] `ws.connect(path)` : connexion WebSocket
  - [ ] `events.subscribe(topic, callback)` : abonnement aux events
  - [ ] `events.unsubscribe(topic, callback)` : désabonnement
  - [ ] `i18n.t(key)` : traduction
  - [ ] `notify.info(msg)`, `notify.success(msg)`, `notify.error(msg)` : notifications
  - [ ] `modal.show(options)` : modale générique
  - [ ] `config.get(plugin_id)`, `config.set(plugin_id, data)` : config plugin
  - [ ] `plugins.getVersion(plugin_id)` : version d'un plugin
  - [ ] `plugins.checkUpdate(plugin_id)` : vérifier mise à jour
  - [ ] `plugins.update(plugin_id, version)` : mettre à jour
  - [ ] `ai.sendContext(plugin_id, data)` : export vers agent IA
- [ ] Exposer globalement `window.jupiterBridge`
- [ ] Tests du bridge front

### 5.3 Enregistrement UI via Bridge (backend)
- [ ] Créer `jupiter/core/bridge/ui_registry.py` :
  - [ ] `register_ui_contribution(plugin_id, panels, menus)`
  - [ ] Stocker les infos de panneau (mount_point, route, title_key)
- [ ] Endpoint `/plugins/ui-manifest` retournant toutes les contributions UI
- [ ] Tests backend

### 5.4 Auto-UI : formulaires de configuration (§3.4.3)
- [ ] Créer `jupiter/web/js/auto_form.js` :
  - [ ] Générer un formulaire HTML depuis un JSON Schema
  - [ ] Types supportés : string, boolean, integer, number, array, object
  - [ ] Attributs : title, description, default, enum, format, min, max
- [ ] Intégrer dans la page Settings (cadre par plugin)
- [ ] Validation avant sauvegarde
- [ ] Tests de génération de formulaires

### 5.5 Auto-UI : carte de statistiques
- [ ] Si `capabilities.metrics.enabled` → générer une carte de stats
- [ ] Afficher : exécutions, erreurs, dernière exécution, durée moyenne
- [ ] Refresh périodique via `/metrics`
- [ ] Tests

### 5.6 Composant de logs partagé (§10.3)
- [ ] Créer `jupiter/web/js/logs_panel.js` :
  - [ ] Connexion WebSocket pour logs temps réel
  - [ ] Filtrage par niveau (DEBUG, INFO, WARNING, ERROR)
  - [ ] Recherche textuelle
  - [ ] Pause/reprise du flux
  - [ ] Auto-scroll configurable
  - [ ] Bouton téléchargement (`.log`/`.txt`, option compression `.zip`)
  - [ ] Tronquage côté serveur (tail N dernières lignes, configurable)
  - [ ] Limitation du flux WS pour éviter saturation
- [ ] Injecter automatiquement dans chaque page plugin
- [ ] Panneau logs centralisé avec filtre par plugin, niveau, plage de temps
- [ ] Export des logs filtrés vers fichier
- [ ] Backend : logger avec préfixe `[plugin:<plugin_id>]` pour traçabilité
- [ ] Config niveau de log par plugin (dans `config.yaml` ou Settings)
- [ ] Niveau global comme plancher (plugin ne peut pas être plus verbeux)
- [ ] Tests

### 5.7 Cadre Settings par plugin (§9)
- [ ] Créer `jupiter/web/js/plugin_settings_frame.js` :
  - [ ] En-tête avec version du plugin
  - [ ] Bouton "Check for update"
  - [ ] Bouton "Update plugin" (avec confirmation et rollback)
  - [ ] Formulaire auto-généré (ou custom)
  - [ ] Bouton "Save" avec validation et feedback (succès/erreur)
  - [ ] Support `dry-run` quand pertinent
  - [ ] Bouton "View changelog" (affiche `changelog.md` en modale)
  - [ ] Bouton "Reset settings"
  - [ ] Toggle "Debug mode" (avec désactivation auto après délai configurable)
  - [ ] Réglages versionnés, exportables/importables (fichier)
- [ ] Intégrer dans la page Settings globale
- [ ] Tests

### 5.8 i18n pour plugins
- [ ] Fusionner les fichiers `web/lang/*.json` des plugins au chargement
- [ ] Clés préfixées `plugin.<plugin_id>.<key>`
- [ ] Fonction `bridge.i18n.t()` avec fallback
- [ ] Tests de traduction

### 5.9 Panneau d'aide contextuel (§9)
- [ ] Chaque plugin avec WebUI doit afficher un panneau d'aide à droite
- [ ] Contenu provenant de fragments i18n (`web/lang/*.json`)
- [ ] Liens vers documentation inclus
- [ ] Accessibilité pour novices

### 5.10 Export de données (§9)
- [ ] Suivre le modèle "pylance analyzer" pour exports vers agents IA
- [ ] Format JSON structuré, schéma documenté, endpoint dédié
- [ ] Option d'export vers fichier téléchargeable (`.json`/`.ndjson`)
- [ ] Indication de taille et prévisualisation rapide
- [ ] Tests

### 5.11 Ergonomie WebUI (§9)
- [ ] Éviter les simples tables : contrôles adaptés à chaque plugin
- [ ] Actions, filtres, status, indicateurs de progression
- [ ] Ergonomie orientée tâche
- [ ] Tests UX

---

## Phase 6 : Migration des plugins existants (2-3 semaines)

### 6.1 Adaptateur legacy (§4.2)
- [ ] Créer `jupiter/core/bridge/legacy_adapter.py` :
  - [ ] Détecter les anciens plugins (classe avec `on_scan`/`on_analyze`)
  - [ ] Générer un manifest minimal à la volée
  - [ ] Enregistrer via le Bridge avec flag `legacy: true`
  - [ ] Appliquer des permissions restrictives par défaut
- [ ] Flag `legacy: true` dans réponse `/plugins` pour indication WebUI
- [ ] Documentation de migration avec exemples concrets
- [ ] Les plugins legacy continuent de fonctionner pendant la transition
- [ ] Tests de l'adaptateur

### 6.2 Migration de `ai_helper`
- [ ] Créer `jupiter/plugins/ai_helper/plugin.yaml`
- [ ] Refactorer vers le nouveau modèle :
  - [ ] `__init__.py` avec `init()`, `health()`, `metrics()`
  - [ ] `server/api.py` avec routes enregistrées via Bridge
  - [ ] `cli/commands.py` avec sous-commandes
  - [ ] `web/panels/main.js` pour panneau WebUI
  - [ ] `web/settings_frame.js` pour cadre Settings
  - [ ] `web/lang/en.json`, `fr.json` pour i18n
- [ ] Tests de non-régression
- [ ] Supprimer l'ancien code

### 6.3 Migration des autres plugins
- [ ] Pour chaque plugin existant :
  - [ ] Créer le manifest `plugin.yaml`
  - [ ] Refactorer le code
  - [ ] Créer les fichiers WebUI si UI
  - [ ] Ajouter les traductions i18n
  - [ ] Tests
- [ ] Plugins à migrer (liste à compléter selon audit) :
  - [ ] `code_quality`
  - [ ] `livemap`
  - [ ] `autodiag`
  - [ ] (autres)

### 6.4 Retrait de l'adaptateur legacy
- [ ] Une fois tous les plugins migrés, marquer l'adaptateur comme deprecated
- [ ] Supprimer dans une version future

---

## Phase 7 : Sécurité et sandbox (2-3 semaines)

### 7.1 Permissions granulaires (§3.6)
- [ ] Implémenter la vérification des permissions dans le Bridge :
  - [ ] `fs_read` : autoriser/refuser lecture FS
  - [ ] `fs_write` : autoriser/refuser écriture FS
  - [ ] `run_commands` : autoriser/refuser exécution runner
  - [ ] `network_outbound` : autoriser/refuser appels réseau
  - [ ] `access_meeting` : autoriser/refuser accès Meeting
- [ ] Affichage des permissions demandées lors de l'installation (WebUI)
- [ ] Tests des contrôles de permission

### 7.2 Signature des plugins (§3.9)
- [ ] Créer `jupiter/core/bridge/signature.py` :
  - [ ] `sign_plugin(plugin_path, private_key)` → génère `plugin.sig`
  - [ ] `verify_plugin(plugin_path)` → bool + trust_level
  - [ ] Niveaux : `official`, `verified`, `community`
- [ ] Commande CLI `jupiter plugins sign <path>`
- [ ] Vérification à l'installation :
  - [ ] Mode strict : refuser si invalide
  - [ ] Mode permissif : avertissement + confirmation
- [ ] Flag `allow_unsigned_local_plugins` pour dev
- [ ] Badge de confiance dans la WebUI
- [ ] Tests de signature

### 7.3 Circuit breaker (§10.6)
- [ ] Implémenter le circuit breaker par plugin :
  - [ ] Compter les échecs consécutifs
  - [ ] Seuil configurable
  - [ ] Période de cool-down
- [ ] Afficher l'état du circuit breaker dans `/plugins` et WebUI
- [ ] Tests

### 7.4 Monitoring et limites
- [ ] Monitoring des métriques CPU/RAM par plugin (optionnel v2)
- [ ] Timeouts configurables sur toutes les opérations
- [ ] Logging de toutes les actions sensibles
- [ ] Tests

### 7.5 Gouvernance (§6)
- [ ] Liste blanche/blacklist via config globale
- [ ] Feature flags pour activer/désactiver sans désinstaller
- [ ] Tests

---

## Phase 8 : Hot Reload et mode développeur (1-2 semaines)

### 8.1 Hot Reload (§10.5)
- [ ] Implémenter `bridge.reload_plugin(plugin_id)` :
  - [ ] Dé-enregistrement des contributions
  - [ ] Déchargement modules (`importlib.invalidate_caches()`, `sys.modules`)
  - [ ] Ré-import frais
  - [ ] Ré-appel des entrypoints
  - [ ] Notification WebSocket `PLUGIN_RELOADED`
- [ ] Activer uniquement si `developer_mode: true`
- [ ] Commande CLI `jupiter plugins reload <id>`
- [ ] Bouton dans WebUI (cadre développeur)
- [ ] Tests

### 8.2 Mode développeur
- [ ] Flag `developer_mode` dans `global_config.yaml`
- [ ] Activer :
  - [ ] Hot reload
  - [ ] Logs DEBUG par défaut
  - [ ] Plugins non signés acceptés sans confirmation
  - [ ] Console de test pour exécuter commandes plugin manuellement
- [ ] Désactiver en production
- [ ] Tests

### 8.3 Idées complémentaires (§10.4)
- [ ] Notifications par plugin :
  - [ ] Émission de notifications (toast, badge sur icône)
  - [ ] Types : info, warning, error, action requise
  - [ ] Configurable par utilisateur (désactiver par plugin)
- [ ] Statistiques d'utilisation par plugin :
  - [ ] Nombre d'exécutions, dernière exécution, durée moyenne
  - [ ] Affichées dans Settings ou widget dédié
- [ ] Rapport d'erreur intégré :
  - [ ] Bouton "Signaler un problème" sur erreur critique
  - [ ] Génère rapport anonymisé (logs, config, version)
- [ ] Tests

---

## Phase 9 : Marketplace et distribution (3-4 semaines)

### 9.1 Installation depuis source externe (§6)
- [ ] `jupiter plugins install <url>` :
  - [ ] Télécharger le paquet (zip)
  - [ ] Vérifier signature si présente
  - [ ] Valider manifest
  - [ ] Vérifier dépendances
  - [ ] Installer sous `jupiter/plugins/<id>/`
  - [ ] Journaliser l'installation
- [ ] `jupiter plugins install <path>` : installation locale
- [ ] Option `--install-deps` : installer les dépendances manquantes
- [ ] Option `--dry-run` : simuler sans installer
- [ ] Rollback en cas d'échec
- [ ] Tests

### 9.2 Désinstallation
- [ ] `jupiter plugins uninstall <id>` :
  - [ ] Vérifier qu'aucun autre plugin n'en dépend
  - [ ] Décharger le plugin
  - [ ] Supprimer les fichiers
  - [ ] Journaliser
- [ ] Confirmation utilisateur
- [ ] Tests

### 9.3 Mise à jour
- [ ] `jupiter plugins update <id>` :
  - [ ] Vérifier le registre/marketplace
  - [ ] Télécharger la nouvelle version
  - [ ] Backup de l'ancienne version
  - [ ] Installer la nouvelle version
  - [ ] Rollback si échec
- [ ] `jupiter plugins check-updates` : vérifier toutes les mises à jour
- [ ] Boutons "Check for update" / "Update" dans WebUI
- [ ] Tests

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
- [ ] Scénario : installation d'un plugin depuis zéro
- [ ] Scénario : utilisation complète d'un plugin (CLI, API, WebUI)
- [ ] Scénario : mise à jour d'un plugin
- [ ] Scénario : échec et recovery
- [ ] Scénario : jobs longs avec annulation
- [ ] Tests de performance

### 11.2 Documentation finale
- [ ] Mettre à jour `docs/plugins_architecture.md` avec retours d'implémentation
- [ ] Mettre à jour `docs/plugin_model/` avec exemples finaux
- [ ] Créer `docs/PLUGIN_DEVELOPER_GUIDE.md` complet
- [ ] Mettre à jour `Manual.md` avec nouvelles commandes
- [ ] Mettre à jour `README.md`
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
- Les tests sont obligatoires à chaque phase.

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
