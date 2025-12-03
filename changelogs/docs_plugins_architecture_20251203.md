# Docs: Architecture des plugins (2025-12-03)

**Version 0.4.0** – Intégration complète de l'analyse externe avec clarifications validées.

## Ajouts et clarifications majeurs (v0.4.0)

### §3.1 Types de plugins – clarification core plugins
- Plugins **core** : **pas de `plugin.yaml`**, hard-codés dans le noyau (`jupiter/core/`).
- Liste définie dans le code source (ex: `CORE_PLUGINS = ["bridge", "settings_update"]`).
- Ne passent pas par le système de manifest.

### §3.1.1 Scope : global vs par projet (NOUVEAU)
- Plugins **installés** = global à l'installation Jupiter.
- Plugins **activés** = configurable par projet via `<project>.jupiter.yaml`.
- Config plugin = globale par défaut avec possibilité d'**overrides par projet**.
- Résolution : Bridge fusionne config globale + overrides projet au chargement.

### §3.3.1 Bridge comme Service Locator (NOUVEAU)
- Namespace `bridge.services` pour découplage des plugins de `jupiter.core.*`.
- Méthodes : `get_logger()`, `get_runner()`, `get_history()`, `get_graph()`, `get_project_manager()`, `get_event_bus()`, `get_config()`.
- Bénéfices : découplage, sécurité (contrôle d'accès), testabilité (mock facile).

### §3.4 Manifest – profils minimal et complet (NOUVEAU)
- **Profil minimal** (§3.4.1) : démarrage rapide avec ~5 champs, defaults sûrs appliqués.
- **Profil complet** (§3.4.2) : toutes les options pour plugins avancés.
- Les deux approches documentées avec exemples YAML.

### §3.4.3 Auto-UI : génération automatique (NOUVEAU)
- Si `config_schema.schema` (JSON Schema) présent → formulaire auto-généré dans Settings.
- Si `capabilities.metrics.enabled` → carte de stats auto-générée.
- Composant de logs partagé injecté automatiquement.
- Permet une UI fonctionnelle sans JavaScript.

### §8 Meeting – reformulation spéculative (MODIFIÉ)
- Encart **⚠️ SPÉCULATIF** ajouté en tête de section.
- Meeting non encore prêt ; fonctionnalités sont des réflexions v2+.
- §8.1 Scope v1 limité : lecture seule + confirmation locale obligatoire.
- §8.2 Considérations futures séparées.

### §10.5 Hot Reload dev mode (NOUVEAU)
- Workflow de rechargement : dé-enregistrement → déchargement module → ré-import → ré-appel entrypoints.
- Activation via `developer_mode: true` ou CLI `jupiter plugins reload <id>`.
- Limitations documentées : état perdu, connexions interrompues.
- Sécurité : uniquement en dev mode, logs complets.

### §10.6 Modèle async et tâches longues (NOUVEAU)
- Jobs asynchrones avec ID unique et états (`pending`, `running`, `completed`, `failed`, `cancelled`).
- Suivi temps réel via WebSocket (`JOB_STARTED`, `JOB_PROGRESS`, `JOB_COMPLETED`, `JOB_FAILED`).
- Timeouts configurables (global + par plugin dans manifest).
- **Circuit Breaker** par plugin : échecs répétés → jobs refusés temporairement.
- Pattern d'annulation coopératif (`job.is_cancelled()`).
- Exemple d'implémentation Python inclus.

---

## Ajouts et clarifications majeurs (v0.3.0)

### §3.1 Types de plugins – 3 catégories internes
- Clarification : 3 catégories internes (`core`, `system`, `tool`), seules 2 exposées aux utilisateurs.
- Plugins **core** (non désactivables) : Bridge, settings_update. Chargés hors cycle normal.
- Plugins **system** (désactivables) : meeting_adapter, connecteurs. Requis pour l'expérience complète.
- Plugins **tool** (optionnels) : ai_helper, etc. Échec isolé sans casser le noyau.

### §3.2 WebUI comme réceptacle – règles strictes
- Types de contributions UI déclarées dans le manifest (panels, widgets, mount_points).
- Règles strictes : 1 onglet max par plugin, pas de CSS sauvage, lazy load obligatoire.
- Namespace obligatoire : `plugin.<plugin_id>.*` pour i18n, routes, IDs HTML.
- API front commune : `window.jupiterBridge` exposé globalement.

### §3.3 Bridge – clarification de position
- Bridge = plugin **core**, chargé hors cycle (hard-codé dans bootstrap).
- Contrat d'enregistrement typé avec exemples Python.
- Accès inter-plugins via `bridge.plugins.get(plugin_id)`.
- Remote actions standardisées via `bridge.remote_actions.register()`.

### §3.4 Manifest unifié – enrichissements
- Champ `jupiter.version` obligatoire pour compatibilité (ex: `">=1.1.0,<2.0.0"`).
- Champ `config_schema.version` pour migrations de configuration.
- Champ `entrypoints` explicites (évite l'exécution de code arbitraire pour découvrir).
- Permissions granulaires standardisées : `fs_read`, `fs_write`, `run_commands`, `network_outbound`, `access_meeting`.

### §3.5 Cycle de vie – état par plugin
- État `status` par plugin : `loading`, `ready`, `error`, `disabled`.
- Exposé via `/plugins` pour UI (griser plugin en erreur, etc.).
- `health()` rappelé à intervalle régulier avec timeout.

### §3.6 Sécurité – niveaux d'isolation
- Court terme : isolation logique (runner médié, timeouts, circuit breaker).
- Long terme (v2) : process séparé pour plugins « low trust » (JSON-RPC/gRPC).
- Limitations Python documentées (même process = risques CPU/RAM).

### §3.8 Dépendances – gestion des cycles et extensions
- Gestion des cycles : erreur claire si A→B et B→A, les deux désactivés.
- Mode `extends:` pour plugins qui enrichissent un autre plugin.

### §3.9 Signatures – mode dev local
- Flag `allow_unsigned_local_plugins: true` pour développement.
- Badge « Dev / Unsigned » en WebUI sans blocage.

### §4 Migration – compatibilité anciens plugins
- Adaptateur auto-enregistrement pour anciens plugins (`on_scan`/`on_analyze`).
- Flag `legacy: true` dans `/plugins` pour indiquer plugins à migrer.

### §7.1 CLI scaffold
- Commande `jupiter plugins scaffold my_cool_plugin` pour générer l'arborescence complète.
- Options `--type`, `--with-ui`, `--with-cli`.

### §8 Meeting – actions distantes standardisées
- Format standard pour actions distantes via Bridge.
- Meeting envoie un plan d'action signé, Bridge valide et affiche confirmation.

### §10.2 Métriques – performance
- Fréquence de collecte configurable.
- Mode debug-metrics par plugin.

### §10.3 Logs – performance
- Tronquer côté serveur (tail N lignes).
- Limiter flux WS pour éviter spam navigateur.

---

## Historique précédent (v0.1.0 - v0.2.0)

- Ajout de `docs/plugins_architecture.md` (FR) décrivant :
  - Modèle actuel des plugins avec exemples (`ai_helper` outil, `settings_update` système).
  - Refonte proposée :
    - WebUI comme réceptacle/containeur de plugins.
    - Séparation nette `system` vs `tool`.
    - Plugin système obligatoire « bridge » liant CLI, WebUI et plugins.
    - Manifests unifiés, phases de cycle de vie, healthchecks, et médiation de sécurité.
- Brainstorming ajouté :
  - Concept de marketplace avec installation/désinstallation.
  - Prévision d'arborescence de fichiers pour un plugin.
- Avis ajouté (spéculatif Meeting) :
  - Possibilité d'installer/réinstaller/désinstaller des plugins à distance via Meeting.
  - Réinitialisation des paramètres de plugins à distance.
  - Prérequis : signatures, autorisations fortes, audit trail, rollback, dry-run.
- Règles de design WebUI pour plugins :
  - Panneau d'aide à droite, export IA/fichier selon modèle « pylance analyzer ».
  - Comportement de panneau de contrôle (actions, indicateurs).
  - Cadre de configuration auto-ajouté à « Settings » avec sauvegarde dédiée.
  - Affichage de la version du plugin et boutons « Check for update » / « Update plugin ».
- Section 10 ajoutée : Questions d'architecture et recommandations :
  - Stockage settings : fichier dédié par plugin + référence globale.
  - Métriques : optionnelles, collectées via Bridge, export Prometheus/JSON.
  - Logs : dédié par plugin + agrégation globale avec préfixe.
- Sections 3.8 et 3.9 ajoutées :
  - Dépendances inter-plugins : déclaration, vérification à l'installation, accès aux fonctionnalités d'autres plugins.
  - Validation et signature des plugins : workflow de signature, vérification, niveaux de confiance, badges WebUI.
- Section 10.3 enrichie : accès direct aux logs (cadre temps réel + bouton téléchargement).
- Section 10.4 ajoutée : idées complémentaires (notifications, mode debug, stats, changelog intégré, rapport d'erreur, sandbox dev).
- Ajout de `docs/plugin_model/` : plugin modèle complet illustrant l'architecture v2.
- Plugin modèle v0.2.0 avec metrics, logs temps réel, stats, debug mode, changelog.

---

- Pas de changement de comportement runtime pour l'instant ; documentation de préparation aux refactors.
