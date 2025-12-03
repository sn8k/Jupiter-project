# Architecture des plugins Jupiter

Version : 0.4.0 (2025-12-03)

Ce document décrit le modèle actuel des plugins dans Jupiter et propose une refonte pour distinguer clairement les plugins système des plugins outils, aligner la WebUI autour d'un « réceptacle » de plugins, et introduire un plugin système unifié « Bridge » pour relier la CLI, la WebUI et les plugins.

Le but final sera d'alleger la "base" (app.js surtout) afin de simplifier la maintenance, deboggage et developpement. Cela permettra egalement d'avoir plus de possibilités pour les fonctionnalités à venir.

**Le maitre mot est "prévoir pour un futur qu'on ne connait pas encore"**

## 1. Modèle actuel

- Concepts clés :
  - Découverte des plugins via `jupiter/plugins/`.
  - Chargement par le gestionnaire de plugins (hooks simples de cycle de vie : init/register).
  - Les plugins peuvent exposer des fonctionnalités d’analyse, des helpers, ou de petits endpoints UI.

- Plugins exemples :
  - `ai_helper` (plugin outil) :
    - But : fonctionnalités d’aide optionnelles (indices assistés par IA, résumés, insights de code).
    - Caractéristiques : non essentiel ; apparaît dans les menus ou actions optionnelles ; peut exposer des endpoints ou sous-commandes CLI via enregistrement.
  - `settings_update` (plugin système) :
    - But : gérer et appliquer les mises à jour de configuration côté CLI/serveur ; normaliser les configurations.
    - Caractéristiques : obligatoire ; s’exécute au démarrage ; participe au cycle de vie de la config pour rester cohérent avec `<project>.jupiter.yaml` et la config globale.

- Intégrations actuelles :
  - La CLI enregistre des commandes fournies par les plugins via des hooks `register_cli()`.
  - Le serveur/API expose des routes via `register_api(app)`.
  - La WebUI consomme ces endpoints API ; injection UI directe limitée ; les textes proviennent de `web/lang/*.json`.

## 2. Limites observées

- L’intégration UI n’est pas standardisée ; les plugins ne peuvent pas « monter » proprement des panneaux.
- La distinction entre plugins système (obligatoires) et plugins outils (optionnels) n’est pas nette.
- La coordination CLI ↔ API ↔ WebUI repose sur des patterns ad hoc.
- Les contrats de cycle de vie et de capacités sont peu stricts, causant de la variabilité.

## 3. Refonte proposée

### 3.1 Types de plugins clairs

**Clarification importante** : En interne, Jupiter distingue 3 catégories, même si seules 2 sont exposées aux utilisateurs.

- Plugins core (internes, non désactivables) :
  - Exemples : `bridge`, `settings_update`.
  - Position : font partie du bootstrap de Jupiter ; chargés hors cycle normal des plugins.
  - Ne peuvent pas être désinstallés ni désactivés par l'utilisateur.
  - **Pas de `plugin.yaml`** : ces composants sont hard-codés dans le noyau (`jupiter/core/`) et ne passent pas par le système de manifest.
  - Liste définie dans le code source (ex: `CORE_PLUGINS = ["bridge", "settings_update"]`).

- Plugins système (désactivables via config) :
  - Exemples : `meeting_adapter`, registre/indexeur, connecteurs.
  - Responsabilités : gestion de cycle de vie, enforcement de config, enregistrement des capacités, câblage cross-surface.
  - Garanties : chargés après les core, vérifiés (healthcheck) ; en cas d'échec, mode dégradé ou arrêt contrôlé.
  - Désactivables via `global_config.yaml` ou feature flags, mais considérés comme « requis » pour l'expérience complète.

- Plugins outils (optionnels) :
  - Exemples : `ai_helper`, qualité de code, export.
  - Responsabilités : contribuer des fonctionnalités (analyses, vues, commandes) sans affecter le démarrage du cœur.
  - Garanties : enregistrement sandboxé ; échec isolé sans casser le noyau.

**Note pour l'API et la WebUI** : Seuls `system` et `tool` sont exposés dans `/plugins` et l'UI. Les plugins core sont transparents pour l'utilisateur.

### 3.1.1 Scope : global vs par projet

- Plugins **installés** = global à l'installation Jupiter (`jupiter/plugins/`).
- Plugins **activés** = configurable par projet via `<project>.jupiter.yaml` :
  ```yaml
  plugins:
    ai_helper:
      enabled: true
    code_quality:
      enabled: false
  ```
- Config plugin = globale par défaut (`jupiter/plugins/<plugin_id>/config.yaml`), avec possibilité d'**overrides par projet** dans `<project>.jupiter.yaml` :
  ```yaml
  plugins:
    ai_helper:
      enabled: true
      config_overrides:
        verbose: true
        api_endpoint: "https://custom.api.com"
  ```
- Résolution : Bridge fusionne la config globale du plugin avec les overrides projet au chargement.

### 3.2 WebUI comme réceptacle de plugins

- Introduire un conteneur de plugins dans la WebUI :
  - Une zone « Plugins » dynamique où les plugins outils montent des panneaux, des menus et des vues.
  - Contrat UI standard : métadonnées (`name`, `icon`, clés i18n), routes, panneaux et hooks d'événements.
  - i18n : les plugins fournissent des fragments `lang/<locale>.json` fusionnés au runtime ; pas de textes codés en dur.

- Types de contributions UI (déclarées dans le manifest) :
  ```yaml
  ui:
    panels:
      - id: "main"
        mount_point: "main_area"      # ex: "analysis", "dashboard", "new_tab"
        route: "/plugins/ai_helper"
        title_key: "plugin.ai_helper.title"
    widgets:
      - id: "ai_suggestions_summary"
        mount_point: "dashboard.right_column"
    settings_frame: true
  ```

- Règles strictes pour les plugins UI :
  - Nombre d'onglets max par plugin : preferer 1 principal + widgets, mais l'usage d'onglets est autorisé, et peut en avoir autant que necessaire.
  - Interdiction de réécrire le layout global ou d'injecter du CSS qui casse le design system (`UI-GUIDE.md`).
  - Rendu paresseux (lazy load) : chaque panel plugin = bundle JS chargé à la demande.
  - Respect du thème dark par défaut, typographie et composants uniformes.

- Namespace obligatoire :
  - Clés i18n : `plugin.<plugin_id>.<key>` (ex: `plugin.ai_helper.settings.title`).
  - Routes UI : `/plugins/<plugin_id>`, `/plugins/<plugin_id>/tab/xxx`.
  - IDs d'éléments HTML : préfixés par `plugin-<plugin_id>-`.

- API front commune :
  - Exposer globalement `window.jupiterBridge` pour que tous les panels plugins :
    - fassent leurs appels API via la même couche (logs, auth, erreurs),
    - s'abonnent aux events WS de manière homogène (`jupiterBridge.events.subscribe('SCAN_FINISHED', ...)`),
    - accèdent aux services partagés (i18n, notifications, thème).

### 3.3 Plugin système Bridge

**Clarification** : Le Bridge est techniquement un plugin « core » (cf. §3.1), chargé hors cycle normal. Jupiter ne peut pas fonctionner sans lui. Il est hard-codé dans le bootstrap, et les autres plugins (système puis outils) se branchent ensuite.

- Rôle : liaison autoritative entre CLI, WebUI et plugins.
  - Expose un registre des plugins actifs, de leurs capacités, endpoints et versions.
  - Fournit des canaux d'événements/messaging (pub/sub) pour coordonner les actions cross-surface.
  - Applique la sécurité et les feature flags ; s'aligne avec `security.allow_run` et les commandes autorisées.

- Interfaces d'enregistrement (contrat typé) :
  ```python
  bridge.register_cli_contribution(
      plugin_id="ai_helper",
      commands=[
          {
              "name": "ai-suggest",
              "entrypoint": "jupiter.plugins.ai_helper.cli:ai_suggest",
              "help": "Generate AI suggestions for the last scan",
          }
      ],
  )
  
  bridge.register_api_contribution(plugin_id, routes)
  bridge.register_ui_contribution(plugin_id, panels, menus)
  ```

- Événements pub/sub :
  - `events.emit(topic, payload)` et `events.subscribe(topic, callback)` (côté serveur).
  - Propagation vers la WebUI via WebSocket.

- Accès inter-plugins :
  ```python
  if bridge.plugins.has("ai_helper"):
      helper_api = bridge.plugins.get("ai_helper")
      helper_api.provide_suggestions(...)
  ```

- Actions distantes (via Meeting) – **spéculatif, Meeting non encore prêt** :
  ```python
  bridge.remote_actions.register(
      id="reset_plugin_settings",
      plugin_id="ai_helper",
      requires_confirmation=True,
  )
  ```

### 3.3.1 Bridge comme Service Locator

Le Bridge expose un namespace `bridge.services` pour éviter que les plugins importent directement `jupiter.core.*` :

```python
services = bridge.services

logger = services.get_logger(plugin_id)       # logger préconfiguré
runner = services.get_runner()                 # wrapper sécurisé sur core.runner
history = services.get_history()               # accès au HistoryManager
graph = services.get_graph()                   # accès au GraphManager
projects = services.get_project_manager()      # accès au ProjectManager
events = services.get_event_bus()              # bus d'événements pub/sub
config = services.get_config(plugin_id)        # config du plugin
```

**Bénéfices** :
- Découplage : les plugins ne dépendent pas de la structure interne de `jupiter.core`.
- Sécurité : le Bridge peut appliquer des contrôles d'accès (permissions déclarées vs demandées).
- Testabilité : les services peuvent être mockés facilement dans les tests de plugins.

### 3.4 Manifest unifié de plugin

**Note** : Les plugins core (§3.1) n'ont pas de manifest ; cette section concerne les plugins `system` et `tool` uniquement.

#### 3.4.1 Manifest minimal (démarrage rapide)

Pour un plugin simple, seuls quelques champs sont requis. Le Bridge applique des defaults sûrs pour le reste :

```yaml
# plugin.yaml – minimal
id: my_simple_plugin
type: tool
version: 0.1.0

jupiter:
  version: ">=1.5.0"

entrypoints:
  init: "jupiter.plugins.my_simple_plugin:init"
```

**Defaults appliqués automatiquement** :
- `permissions` : toutes à `false` (sandbox maximale).
- `capabilities` : aucune contribution CLI/API/UI.
- `config_schema.version` : `1`.
- `dependencies` : aucune.

Ce profil minimal permet de créer un plugin fonctionnel en quelques minutes, puis de l'enrichir progressivement.

#### 3.4.2 Manifest complet (avancé)

Pour un plugin complexe avec toutes les capacités :

```yaml
# plugin.yaml – complet
id: ai_helper
type: tool  # system | tool
version: 1.2.0

# Compatibilité Jupiter (obligatoire)
jupiter:
  version: ">=1.1.0,<2.0.0"

# Schéma de configuration (pour migrations)
config_schema:
  version: 2
  format: yaml
  # Schéma JSON pour génération auto-UI (voir §3.4.3)
  schema:
    type: object
    properties:
      api_key:
        type: string
        title: "Clé API"
        description: "Clé d'accès au service IA"
        format: password
      verbose:
        type: boolean
        title: "Mode verbeux"
        default: false

# Entrypoints explicites (évite l'exécution de code arbitraire pour découvrir)
entrypoints:
  server: "jupiter.plugins.ai_helper.server:register"
  cli: "jupiter.plugins.ai_helper.cli:register"
  init: "jupiter.plugins.ai_helper:init"
  health: "jupiter.plugins.ai_helper:health"
  metrics: "jupiter.plugins.ai_helper:metrics"  # optionnel

# Capacités déclarées
capabilities:
  cli:
    commands: ["ai-suggest", "ai-summary"]
  api:
    routes: ["/ai/suggest", "/ai/summary"]
  ui:
    panels: ["main"]
    settings_frame: true
  metrics:
    enabled: true
    export_format: prometheus

# Permissions granulaires (scopes standardisés)
permissions:
  fs_read: true       # lecture du FS projet
  fs_write: false     # écriture FS
  run_commands: false # exécution via runner
  network_outbound: true  # accès réseau sortant (API IA)
  access_meeting: false   # accès au service Meeting

# i18n
i18n:
  - lang/en.json
  - lang/fr.json

# Dépendances (voir §3.8)
dependencies:
  - id: core_utils
    version: ">=1.0.0"
```

- Bénéfices :
  - Ordre de chargement et validation prévisibles (core → système → outils).
  - Exposition déclarative des fonctionnalités ; le Bridge interprète les manifests pour enregistrer les contributions.
  - Vérification de compatibilité Jupiter avant chargement.
  - Migration de config automatisée via `config_schema.version`.

#### 3.4.3 Auto-UI : génération automatique de formulaires

Le Bridge exploite le `config_schema.schema` (JSON Schema) pour générer automatiquement un formulaire de configuration dans la WebUI :

- Chaque propriété du schéma → un champ de formulaire (input, checkbox, select, password).
- Types supportés : `string`, `boolean`, `integer`, `number`, `array`, `object` (nested).
- Attributs utilisés : `title`, `description`, `default`, `enum`, `format` (password, email, uri...), `minimum`, `maximum`.

**Comportement standard** :
- Si `config_schema.schema` est présent → formulaire auto-généré dans la page Settings, cadre dédié au plugin.
- Si `capabilities.metrics.enabled: true` → carte de statistiques auto-générée (dernière exécution, compteurs, erreurs).
- Composant de logs partagé (§10.3) injecté automatiquement dans chaque page plugin.

Cela permet à un plugin de bénéficier d'une UI fonctionnelle sans écrire de JavaScript, tout en permettant de personnaliser plus tard.

### 3.8 Dépendances inter-plugins

- Déclaration des dépendances :
  - Chaque plugin peut déclarer dans son manifest les plugins dont il dépend :
    ```yaml
    dependencies:
      - id: core_utils
        version: ">=1.0.0"
      - id: ai_helper
        version: ">=0.5.0"
        optional: true  # fonctionnalité enrichie si présent, mais non bloquant
    
    # Mode "extension" : ce plugin enrichit un autre plugin
    extends:
      - id: ai_helper  # explicite que ce plugin ne fait qu'enrichir ai_helper
    ```

- Gestion des cycles :
  - Si A dépend de B et B dépend de A → erreur claire au chargement, les deux plugins désactivés.
  - Le Bridge détecte les cycles lors de la phase `discover` et log l'erreur.

- Vérification à l'installation (WebUI/CLI) :
  - Lors de l'installation d'un plugin, le Bridge vérifie les dépendances.
  - Si des dépendances manquent :
    - WebUI : affiche un avertissement « Attention, ce plugin nécessite que ces autres plugins soient installés : [liste] ».
    - CLI : message similaire avec option `--install-deps` pour installer automatiquement.
  - Si des dépendances optionnelles sont absentes : notification informative sans blocage.

- Résolution au chargement :
  - Le Bridge charge les plugins dans l'ordre topologique des dépendances.
  - Si une dépendance obligatoire échoue, le plugin dépendant est marqué inactif.

- Accès aux fonctionnalités d'autres plugins :
  - Un plugin ne doit pas être vu comme isolé : il peut consommer les capacités d'autres plugins chargés.
  - Le Bridge expose `bridge.plugins.get(plugin_id)` pour accéder aux APIs publiques d'un autre plugin.
  - Contrat : le plugin dépendant vérifie la présence avant appel (`if bridge.plugins.has("ai_helper"): ...`).

- Cas d'usage :
  - Plugin « export_advanced » qui utilise `ai_helper` pour générer des résumés si disponible.
  - Plugin « dashboard » qui agrège les métriques de plusieurs plugins outils.

### 3.9 Validation et signature des plugins

- Objectif : garantir l'intégrité et l'authenticité des plugins distribués.

- Workflow de signature (pour créateurs de plugins) :
  - Un outil dédié (`jupiter plugins sign <plugin_path>`) ou un plugin système « plugin_signer » :
    - Calcule le hash du contenu (excluant les fichiers de signature).
    - Signe le hash avec la clé privée du développeur.
    - Génère un fichier `plugin.sig` inclus dans le paquet.
  - Les créateurs peuvent enregistrer leur clé publique sur le marketplace officiel.

- Vérification à l'installation :
  - Le Bridge vérifie `plugin.sig` contre la clé publique connue.
  - Si la signature est invalide ou absente :
    - Mode strict (configurable) : installation refusée.
    - Mode permissif : avertissement « Plugin non signé ou signature invalide » avec confirmation utilisateur.

- Niveaux de confiance :
  - `official` : signé par l'équipe Jupiter.
  - `verified` : signé par un développeur dont la clé est enregistrée sur le marketplace.
  - `community` : non signé ou clé inconnue ; nécessite approbation explicite.

- Mode dev local :
  - Flag `allow_unsigned_local_plugins: true` dans `global_config.yaml`, réservé au développement.
  - La WebUI affiche un badge « Dev / Unsigned » mais n'empêche pas le chargement.
  - En production (flag absent ou `false`), les plugins non signés sont refusés ou nécessitent confirmation.

- Affichage WebUI :
  - Badge de confiance sur chaque plugin (icône verte/orange/rouge).
  - Détails de signature accessibles (auteur, date, empreinte).

### 3.5 Cycle de vie et santé

- Phases :
  - `discover` → validation des manifests, compatibilité Jupiter, détection des cycles de dépendances.
  - `initialize` → plugins core (Bridge) puis système ; mise en place des registres et gardes de config.
  - `register` → plugins outils contribuent CLI/API/UI en sandbox.
  - `ready` → publication de la liste des plugins vers la WebUI via `/plugins` et WS.

- État par plugin :
  - Chaque plugin a un `status` : `loading` | `ready` | `error` | `disabled`.
  - Le Bridge expose cet état via `/plugins` pour que l'UI puisse :
    - griser un plugin en `error` avec un bouton « voir les logs »,
    - afficher un indicateur de chargement pour `loading`,
    - marquer visuellement les plugins `disabled`.

- Healthchecks :
  - Les plugins système **doivent** exposer `health()` ; inclus dans `/health` et l'état UI.
  - Les plugins outils **peuvent** exposer `health()` ; en cas d'échec, marqués inactifs.
  - Le Bridge rappelle `health()` à intervalle régulier (configurable, avec timeout).
  - `health()` doit être rapide et idempotent.

### 3.6 Sécurité et sandbox

- Médiation Runner : les plugins n'exécutent pas directement des commandes ; ils passent par `core/runner.py` via autorisation Bridge.
- Accès configuration : proxys via Bridge avec lectures/écritures bornées (respect de `settings_update`).
- Permissions granulaires (scopes standardisés) :
  - `fs_read` : lecture du système de fichiers projet.
  - `fs_write` : écriture sur le FS.
  - `run_commands` : exécution de commandes via runner.
  - `network_outbound` : accès réseau sortant.
  - `access_meeting` : accès au service Meeting.
  - Le Bridge affiche un diff clair dans l'UI lors de l'installation :
    > Ce plugin demande :
    > – accès lecture au FS de projet
    > – exécution de commandes via `run`
    > – accès réseau sortant

- Niveaux d'isolation :
  - **Court terme (v1)** : isolation logique (runner médié, accès FS et réseau via Bridge, timeouts & circuit breaker par plugin).
  - **Long terme (v2)** : option pour exécuter des plugins « low trust » dans un **process séparé** (ou même un env virtuel), avec un protocole RPC simple (JSON-RPC, gRPC light).
  - Documenter comme « niveau 2 de sandbox » à venir.

- Limitations en Python :
  - Tous les plugins tournent dans le même process → un plugin peut bloquer l'event loop ou monopoliser CPU/RAM.
  - `try/except` et timeouts logiques ne peuvent pas tout empêcher.
  - Solution : monitoring des métriques + kill de plugin si dépassement de seuils.

### 3.7 Versioning et changelogs

- Version et changelog par plugin sous `changelogs/`.
- Le Bridge publie les versions via `/plugins` et dans le panneau « À propos » de la WebUI.

## 4. Stratégie de migration

### 4.1 Étapes de migration

1. Introduire le plugin core Bridge avec parsing de manifest et registres (chargé hors cycle).
2. Envelopper `settings_update` dans un manifest core et câbler les gardes de config via Bridge.
3. Ajouter le conteneur de plugins dans la WebUI et le chargeur dynamique de menus/panneaux.
4. Migrer `ai_helper` vers un manifest outil ; contribuer un panneau UI et des sous-commandes CLI optionnelles.
5. Refactorer progressivement les plugins existants pour déclarer leurs contributions via manifest.

### 4.2 Compatibilité avec les anciens plugins

- Phase de transition : les anciens plugins (simples classes avec `on_scan`/`on_analyze`) sont auto-enregistrés par un petit adaptateur qui génère un manifest minimal à la volée.
- Flag `legacy: true` dans la réponse `/plugins` pour que l'UI indique clairement quels plugins doivent être migrés.
- L'adaptateur fournit des defaults de sécurité restrictifs pour les plugins legacy.
- Documentation de migration avec exemples concrets.

## 5. Résultats attendus

- La WebUI devient un réceptacle flexible de plugins.
- Séparation nette entre plugins système et outils.
- Bridge unifie l’enregistrement CLI/API/UI et la sécurité.
- Cycle de vie et manifests prévisibles pour une meilleure fiabilité et extensibilité.

## 6. Brainstorming : Marketplace et gestion des plugins

- Marketplace (à moyen/long terme) :
  - Un catalogue de plugins (officiels/communauté) consultable depuis la WebUI.
  - Métadonnées : auteur, version, type (`system`/`tool`), permissions, compatibilité.
  - Notation et vérifications de signature pour la sécurité.

- Installation/Désinstallation :
  - Via WebUI (Bridge orchestre) : télécharger un paquet (zip), vérifier manifest/signature, installer sous `jupiter/plugins/<id>/`.
  - Via CLI : `python -m jupiter.cli.main plugins install <source>` / `uninstall <id>`.
  - Journalisation et rollback en cas d’échec.
  - Cache et mise à jour des dépendances avec validation (dry-run possible).

- Gouvernance :
  - Liste blanche/blacklist via config globale.
  - Feature flags pour activer/désactiver des plugins sans les désinstaller.

## 7. Prévision : arborescence d’un plugin (proposée)

```
jupiter/plugins/<plugin_id>/
├── plugin.yaml               # manifest: id, type, version, capabilities, permissions, i18n
├── __init__.py               # bootstrap léger, export des hooks (optionnel)
├── server/
│   ├── api.py                # registres d’endpoints via Bridge (register_api_contribution)
│   └── events.py             # hooks pub/sub, schémas de payload
├── cli/
│   └── commands.py           # définitions Typer/argparse exposées via Bridge
├── core/
│   ├── logic.py              # logique métier du plugin
│   └── runner_access.py      # appels médiés au runner
├── web/
│   ├── panels/
│   │   └── main.js           # panneau principal (montage dans le réceptacle)
│   ├── assets/               # icônes, CSS spécifiques
│   └── lang/
│       ├── en.json
│       └── fr.json           # fragments i18n du plugin
├── tests/
│   └── test_basic.py         # tests unitaires du plugin
└── changelog.md              # changelog spécifique au plugin
```

- Notes :
  - Les contributions sont déclarées dans `plugin.yaml` et enregistrées via le Bridge.
  - La WebUI charge dynamiquement `web/panels/main.js` si le plugin déclare une contribution UI.
  - Les fichiers de langue sont fusionnés à l'initialisation du plugin dans la WebUI.
  - Fichier `config.yaml` pour les settings du plugin (voir §10.1).

### 7.1 CLI scaffold pour créer un plugin

- Commande pour générer l'arborescence complète :
  ```bash
  jupiter plugins scaffold my_cool_plugin
  ```

- Génère automatiquement :
  - `plugin.yaml` avec id, type `tool`, version `0.1.0`, entrypoints, permissions minimales.
  - `__init__.py` avec `init()`, `health()` et `metrics()` squelettes.
  - `server/api.py`, `cli/commands.py`, `core/logic.py`.
  - `web/panels/main.js`, `web/settings_frame.js`, `web/lang/en.json`.
  - `tests/test_basic.py`, `changelog.md`, `README.md`.

- Options :
  - `--type system|tool` : type de plugin.
  - `--with-ui` / `--no-ui` : inclure ou non les fichiers WebUI.
  - `--with-cli` / `--no-cli` : inclure ou non les commandes CLI.

  ## 9. Règles de design WebUI pour les plugins

  - Panneau d’aide (à droite) :
    - Chaque plugin avec une page WebUI doit afficher une explication claire, pédagogique et accessible aux novices sur le côté droit de la fenêtre (panneau d’aide/contextuel).
    - Le contenu provient de fragments i18n du plugin (`web/lang/*.json`) et peut inclure des liens vers la documentation.

  - Export de données vers agents IA et fichiers :
    - Si des exports sont nécessaires (vers un agent IA), suivre le modèle existant du module « pylance analyzer » (fonction `export`) : format JSON structuré, schéma documenté, endpoint dédié.
    - Offrir systématiquement une option d’export vers un fichier téléchargeable (ex. `.json`/`.ndjson`), avec indication de taille et prévisualisation rapide.

  - Vrai panneau de contrôle :
    - Éviter la simple table : chaque plugin doit proposer des contrôles adaptés à sa fonction (actions, filtres, status, indicateurs).
    - Fournir une ergonomie orientée tâche : boutons d’exécution, retours d’état, logs succincts et indicateurs de progression.

  - Cadre de configuration auto-ajouté aux « Settings » :
    - Tout plugin doit déclarer un cadre de configuration (scopé) qui s'auto-intègre dans la page « Settings » de la WebUI via le Bridge.
    - Chaque cadre dispose de son propre bouton de sauvegarde, avec validation et feedback (succès/erreur), et support de `dry-run` quand pertinent.
    - Les réglages sont versionnés, exportables/importables (fichier), et respectent les politiques de sécurité.
    - Version et mise à jour :
      - Afficher la version du plugin (depuis `plugin.yaml`) dans l'en-tête du cadre.
      - Bouton « Check for update » : interroge le registre/marketplace pour vérifier si une version plus récente existe.
      - Bouton « Update plugin » : déclenche le téléchargement et l'installation de la mise à jour (via Bridge, avec confirmation et rollback possible).


## 8. Avis et considérations : opérations à distance via Meeting (SPÉCULATIF)

> **⚠️ Note importante** : Cette section est **spéculative**. Le service Meeting n'est pas encore prêt et les fonctionnalités décrites ci-dessous sont des réflexions pour une version future (v2+). Aucune de ces capacités ne doit être implémentée tant que Meeting n'est pas opérationnel et que le modèle de sécurité n'est pas validé.

### 8.1 Scope v1 limité (si Meeting devient disponible)

En première version, les opérations à distance seraient **strictement limitées** :
- Uniquement des actions **lecture seule** (status, métriques).
- **Confirmation locale obligatoire** : toute action modifiante nécessite une validation explicite de l'utilisateur sur l'instance Jupiter locale.
- Pas d'installation/désinstallation automatique sans interaction utilisateur.

### 8.2 Considérations pour versions futures

### 8.2 Considérations pour versions futures

- Installation/Réinstallation/Désinstallation à distance :
  - Faisable si Meeting expose des commandes signées et vérifiées côté Jupiter (via le plugin système `meeting_adapter` et le `bridge`).
  - Requiert un modèle d'autorisation fort (jetons courts, liste blanche de plugins, signatures, journalisation et rollback).
  - Doit respecter les gardes de sécurité (pas d'exécution non médiée, validation des manifests, contrôle des permissions). Principe : « secure by default » et opt-in explicite.

  - Réinitialisation des paramètres de plugins à distance :
    - Possible via commandes Meeting qui invoquent des resets idempotents exposés par chaque plugin outil/système (API du Bridge: `reset_settings(plugin_id)` avec scopes et confirmation).
    - Nécessite un schéma de configuration versionné, des defaults sûrs, et un audit trail (qui a déclenché, quand, quoi).
    - Devrait supporter le mode dégradé : si Meeting indisponible, aucune opération forcée n’est exécutée.

  - Recommandations générales :
    - Commencer par un mode « demande / approbation locale » (l'utilisateur confirme) avant d'autoriser le « forcer » complet.
    - Limiter les opérations à distance aux plugins de confiance (signés, vérifiés) et aux actions réversibles.
    - Intégrer des alertes UI/CLI et un mécanisme de « dry-run » pour visualiser les effets.

  - Standardisation des actions distantes via Bridge :
    ```python
    bridge.remote_actions.register(
        id="reset_plugin_settings",
        plugin_id="ai_helper",
        requires_confirmation=True,
    )
    ```
    - Meeting envoie un « plan d'action » signé (ex: `{"action": "reset_plugin_settings", "plugin_id": "ai_helper"}`).
    - Bridge valide (signature, plugin présent, permissions), affiche dans l'UI comme demande à accepter, exécute si confirmé.

## 10. Questions d'architecture et recommandations

### 10.1 Stockage des settings des plugins

**Question** : Chaque plugin sauvegarde-t-il sa config dans son propre fichier, ou centralise-t-on dans `global_config.yaml` ?

**Recommandation** : Approche hybride.

- Stockage dédié par plugin :
  - Chaque plugin stocke ses paramètres dans `jupiter/plugins/<plugin_id>/config.yaml` (ou `.json`).
  - Avantages : isolation, portabilité (copier un plugin = copier sa config), pas de pollution du fichier global.
  - Le Bridge expose `bridge.config.get(plugin_id)` et `bridge.config.set(plugin_id, data)` qui accèdent à ce fichier dédié.

- Référence dans `global_config.yaml` :
  - Seules les métadonnées globales y figurent : plugins activés/désactivés, feature flags, overrides de sécurité.
  - Exemple :
    ```yaml
    plugins:
      ai_helper:
        enabled: true
        # pas de settings détaillés ici
      code_quality:
        enabled: false
    ```

- Export/import unifié :
  - Le Bridge peut générer un export consolidé de tous les plugins (pour backup ou migration) en agrégeant les `config.yaml` individuels.

### 10.2 Métriques des plugins

**Question** : Les plugins doivent-ils remonter des métriques ?

**Recommandation** : Oui, de manière optionnelle et standardisée.

- Contrat de métriques :
  - Les plugins peuvent exposer une fonction `metrics() -> dict` retournant des indicateurs clés (compteurs, durées, états).
  - Le Bridge collecte ces métriques et les expose via `/metrics` (format Prometheus ou JSON).

- Cas d'usage :
  - Observabilité : nombre d'exécutions, erreurs, latence moyenne.
  - Dashboards WebUI : widgets affichant l'activité des plugins.
  - Alerting : seuils configurables déclenchant des notifications.

- Déclaration dans le manifest :
  ```yaml
  capabilities:
    metrics:
      enabled: true
      export_format: prometheus  # ou json
  ```

- Mode opt-in : si un plugin ne déclare pas `metrics`, aucune collecte n'est effectuée.

- Performance :
  - Collecter les métriques de tous les plugins à haute fréquence peut coûter cher.
  - Fréquence de collecte configurable par plugin et globalement.
  - Option « mode debug-metrics » par plugin pour collecte intensive temporaire.

### 10.3 Logs des plugins

**Question** : Log dédié par plugin, log global, ou les deux ?

**Recommandation** : Les deux, avec agrégation.

- Log dédié par plugin :
  - Chaque plugin écrit dans `jupiter/plugins/<plugin_id>/logs/plugin.log` (rotation, niveau configurable).
  - Utile pour le debug isolé et l'audit spécifique.

- Log global :
  - Les messages importants (INFO+) sont également envoyés au logger global Jupiter (`logs/jupiter.log`).
  - Le Bridge injecte un logger configuré avec le préfixe `[plugin:<plugin_id>]` pour traçabilité.

- Niveaux et filtrage :
  - Le niveau de log par plugin est configurable dans son `config.yaml` ou via la page Settings.
  - Le niveau global (dans `global_config.yaml`) agit comme plancher : un plugin ne peut pas être plus verbeux que le global en production.

- Accès direct aux logs dans la WebUI (obligatoire pour chaque plugin) :
  - Cadre de logs temps réel :
    - Chaque plugin avec une page WebUI doit inclure un panneau « Logs » affichant les logs du plugin en temps réel (via WebSocket).
    - Filtrage par niveau (DEBUG, INFO, WARNING, ERROR) et recherche textuelle.
    - Pause/reprise du flux, auto-scroll configurable.
  - Bouton de téléchargement :
    - Bouton « Télécharger les logs » permettant d'exporter le fichier `plugin.log` complet (ou une plage de dates).
    - Format : `.log` ou `.txt`, avec option de compression (`.zip`) pour les logs volumineux.
  - Performance :
    - Tronquer côté serveur (tail sur les N dernières lignes, configurable).
    - Limiter le flux WS pour éviter de spammer le navigateur sur de gros projets.

- WebUI globale :
  - Panneau « Logs » centralisé permettant de filtrer par plugin, niveau, plage de temps.
  - Export des logs filtrés vers fichier.

- Implémentation suggérée :
  ```python
  # Dans __init__.py du plugin
  def init(bridge):
      logger = bridge.get_logger("example_plugin")
      logger.info("Plugin initialized")
  ```

### 10.4 Idées complémentaires

- Notifications et alertes par plugin :
  - Les plugins peuvent émettre des notifications (toast WebUI, badge sur l'icône du plugin).
  - Types : info, warning, error, action requise.
  - Configurable : l'utilisateur peut désactiver les notifications d'un plugin spécifique.

- Mode debug par plugin :
  - Bouton « Activer le mode debug » dans le cadre Settings du plugin.
  - Augmente temporairement le niveau de log à DEBUG, active des traces supplémentaires.
  - Désactivation automatique après un délai configurable (ex. 30 min) pour éviter la pollution.

- Statistiques d'utilisation :
  - Chaque plugin peut exposer des stats simples : nombre d'exécutions, dernière exécution, durée moyenne.
  - Affichées dans le cadre Settings ou un widget dédié.
  - Utile pour identifier les plugins peu utilisés ou problématiques.

- Changelog intégré dans la WebUI :
  - Bouton « Voir les nouveautés » affichant le `changelog.md` du plugin dans une modale.
  - Mise en évidence des changements depuis la dernière version installée.

- Rapport d'erreur intégré :
  - Si un plugin rencontre une erreur critique, proposer un bouton « Signaler un problème ».
  - Génère un rapport anonymisé (logs récents, config, version) exportable ou envoyable au développeur.

- Sandbox de test (pour développeurs) :
  - Mode « développeur » permettant de recharger un plugin à chaud sans redémarrer Jupiter.
  - Console de test pour exécuter des commandes du plugin manuellement.
  - Accessible via feature flag ou config globale `developer_mode: true`.

### 10.5 Hot Reload en mode développement

**Question** : Comment faciliter le développement de plugins sans redémarrer Jupiter ?

**Recommandation** : Implémenter un mécanisme de rechargement à chaud contrôlé.

- Activation :
  - Flag `developer_mode: true` dans `global_config.yaml`.
  - CLI : `jupiter plugins reload <plugin_id>`.
  - WebUI : bouton « Recharger » dans le cadre développeur du plugin (visible uniquement en `developer_mode`).

- Workflow de rechargement :
  1. **Dé-enregistrement** : le Bridge supprime les contributions du plugin (routes API, commandes CLI, panneaux UI).
  2. **Déchargement module** : invalidation du cache Python (`importlib.invalidate_caches()`, suppression des modules du plugin de `sys.modules`).
  3. **Ré-import** : chargement frais du code du plugin.
  4. **Ré-appel des entrypoints** : `init()`, `register_api_contribution()`, etc.
  5. **Notification WS** : la WebUI reçoit un événement `PLUGIN_RELOADED` et rafraîchit les éléments concernés.

- Limitations :
  - État en mémoire perdu (objets singleton, caches internes du plugin).
  - Les connexions actives (WS sessions liées au plugin) peuvent être interrompues.
  - Ne fonctionne pas si le plugin a des threads/processus enfants non gérés.

- Sécurité :
  - Disponible uniquement en `developer_mode`.
  - Log de toutes les opérations de reload.
  - En production, le reload nécessite un redémarrage complet de Jupiter.

- Implémentation suggérée :
  ```python
  # Dans bridge.py
  def reload_plugin(plugin_id: str) -> bool:
      if not config.developer_mode:
          raise SecurityError("Hot reload disabled in production")
      
      plugin = self.plugins.get(plugin_id)
      if not plugin:
          return False
      
      # 1. Dé-enregistrement
      self._unregister_contributions(plugin_id)
      
      # 2. Déchargement
      self._unload_modules(plugin.module_path)
      
      # 3. Ré-import et init
      plugin = self._load_plugin(plugin_id)
      
      # 4. Notification
      self.events.emit("PLUGIN_RELOADED", {"plugin_id": plugin_id})
      
      return True
  ```

### 10.6 Modèle async et tâches longues

**Question** : Comment gérer les opérations longues (scans, analyses IA, exports) sans bloquer l'interface ?

**Recommandation** : Modèle de jobs asynchrones avec suivi via WebSocket.

- Architecture :
  - Les plugins soumettent des tâches longues au Bridge via `bridge.jobs.submit()`.
  - Chaque job reçoit un ID unique et un état (`pending`, `running`, `completed`, `failed`, `cancelled`).
  - Le Bridge gère une file d'exécution avec limites de concurrence par plugin.

- Suivi en temps réel :
  - WebSocket : événements `JOB_STARTED`, `JOB_PROGRESS`, `JOB_COMPLETED`, `JOB_FAILED`.
  - Payload :
    ```json
    {
      "job_id": "abc123",
      "plugin_id": "ai_helper",
      "progress": 45,
      "message": "Analyse en cours...",
      "eta_seconds": 120
    }
    ```
  - La WebUI affiche une barre de progression et permet l'annulation.

- Timeouts :
  - Timeout global configurable par type de job (`global_config.yaml`).
  - Timeout spécifique déclarable dans le manifest du plugin :
    ```yaml
    capabilities:
      jobs:
        default_timeout: 300  # secondes
        max_concurrent: 2
    ```
  - Dépassement → job marqué `failed`, notification utilisateur, log d'erreur.

- Circuit Breaker par plugin :
  - Si un plugin échoue N fois consécutivement (configurable), ses jobs sont temporairement refusés.
  - Période de « cool-down » avant réactivation.
  - Évite qu'un plugin bugué ne spam le système.
  - État du circuit breaker visible dans `/plugins` et la WebUI.

- Annulation :
  - API : `DELETE /jobs/{job_id}` ou `bridge.jobs.cancel(job_id)`.
  - Le plugin doit vérifier régulièrement `job.is_cancelled()` et terminer proprement.
  - Pattern coopératif (pas de kill brutal).

- Implémentation plugin :
  ```python
  async def long_analysis(bridge, params):
      job = bridge.jobs.current()
      
      for i, item in enumerate(params["items"]):
          if job.is_cancelled():
              return {"status": "cancelled"}
          
          # Traitement
          result = await process_item(item)
          
          # Mise à jour progression
          job.update_progress(
              progress=int((i + 1) / len(params["items"]) * 100),
              message=f"Traitement {i + 1}/{len(params['items'])}"
          )
      
      return {"status": "completed", "results": results}
  ```

- Persistance (optionnel) :
  - Les jobs terminés peuvent être stockés temporairement pour consultation ultérieure.
  - Nettoyage automatique après N heures/jours.
  - Export des résultats de job vers fichier.

