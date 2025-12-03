## 1. Les points très bien posés

### 1.1. Distinction **core / system / tool**

Tu as clarifié un truc important par rapport à la v d’avant : la séparation entre :

* **core plugins** (Bridge, settings_update)
* **system plugins** (meeting_adapter, indexeurs, connecteurs)
* **tool plugins** (ai_helper, export, qualité, etc.)

En plus tu précises que **seuls `system` et `tool` existent dans l’API / WebUI**, les core sont transparents → très bon choix. Ça colle bien avec la situation actuelle où :

* certaines briques sont déjà “structurelles” (ProjectManager, MeetingAdapter, HistoryManager, etc.),
* alors que les plugins actuels sont des classes chargées via `PluginManager` qui exposent des hooks `on_scan` / `on_analyze` et sont configurés dans `<project>.jupiter.yaml`.

Là tu poses enfin une vraie hiérarchie, lisible pour les humains *et* pour le runtime.

---

### 1.2. WebUI comme “shell + réceptacle de plugins”

Tu vas encore plus loin que la version précédente :

* **Contrat UI clair** dans le manifest (`ui.panels`, `widgets`, `settings_frame`).
* **Namespacing strict** :

  * routes `/plugins/<plugin_id>…`,
  * clés i18n `plugin.<plugin_id>.*`,
  * IDs DOM préfixés `plugin-<plugin_id>-…`.
* **Contraintes de design** alignées avec le UI‑GUIDE (dark par défaut, composants homogènes, pas de CSS sauvage). 
* **Lazy‑load des bundles JS** pour éviter l’énorme `app.js`, ce qui répond pile à ton problème de “500Mo de app.js”.

Et la présence de `window.jupiterBridge` côté front pour :

* appels API homogènes,
* abonnement WS,
* i18n / notifications / thème,

est super cohérente avec l’architecture actuelle où la WebUI parle déjà à FastAPI + `/ws` pour les événements (SCAN, RUN, etc.).

---

### 1.3. Bridge en **core**, avec entrypoints et compatibilité

Très bonne clarification : Bridge n’est plus juste “un plugin système”, mais **un module core chargé hors cycle**.

Le manifest unifié est bien pensé :

* `entrypoints` explicites (`server`, `cli`, `init`, `health`, `metrics`) → ça évite d’importer un module entier juste pour deviner ce qu’il expose.
* `jupiter.version` pour la compatibilité minimale/maximale.
* `config_schema.version` pour supporter les migrations de config proprement (super important vu la séparation config globale / projet / multi‑projets).

Et le Bridge qui enregistre :

```python
bridge.register_cli_contribution(...)
bridge.register_api_contribution(...)
bridge.register_ui_contribution(...)
```

est parfaitement aligné avec l’état actuel où :

* la CLI expose déjà des commandes (`scan`, `analyze`, `server`, `gui`, `ci`…),
* l’API expose `/scan`, `/analyze`, `/run`, `/snapshots`, `/simulate/remove`, `/graph`, `/plugins`, etc.,
* et la WebUI se repose sur ces endpoints pour tout faire.

Là tu standardises enfin la passerelle CLI/API/UI.

---

### 1.4. Dépendances, extensions et **“extends”**

La section 3.8 est bien plus mature :

* dépendances avec contraintes de version
* support des **dépendances optionnelles** (`optional: true`)
* champ `extends` pour dire “je ne fais que compléter tel plugin”

Ça permet par exemple :

* un plugin `export_advanced` qui **étend** `ai_helper` si présent,
* un plugin `dashboard` qui agrège les métriques de plusieurs plugins.

Et le fait de :

* **détecter les cycles** au stade `discover`,
* calculer un **ordre topologique** de chargement,

est crucial pour ne pas finir dans un enfer de dépendances circulaires.

---

### 1.5. Signature, niveaux de confiance et mode dev

La section 3.9 est vraiment propre :

* `plugin.sig`, hash signé, clés publiques enregistrées sur le marketplace.
* niveaux de confiance : `official`, `verified`, `community`.
* mode strict vs permissif à l’installation.
* **flag de dev** `allow_unsigned_local_plugins: true` → exactement ce qu’il faut pour développer à la main sans se battre avec la signature.

Ça s’aligne bien avec le modèle de sécurité déjà présent (tokens API, `security.allow_run`, `allowed_commands`, etc.).

---

### 1.6. Cycle de vie + santé + statuts UI

Très propre :

* Phases : `discover → initialize → register → ready`.
* Statuts par plugin : `loading | ready | error | disabled` exposés via `/plugins`.
* Healthchecks obligatoires pour les systèmes, optionnels pour les outils, avec rappel périodique.

Ça complète bien l’existant ( `/health`, `/metrics`, `/plugins`) tout en ajoutant une vraie notion d’état par plugin.

---

### 1.7. DX & ops : configs, métriques, logs, scaffold

J’aime beaucoup :

* **Config hybride** (fichier par plugin + métadonnées globales pour enabled/disabled).
* `metrics()` standard + intégration dans `/metrics`.
* **logs par plugin** + panneau logs temps réel dans la WebUI + export.
* Scaffold `jupiter plugins scaffold` qui génère tout le squelette.

C’est exactement dans l’esprit des guides dev / agents GPT-5 actuels (forte importance à la structure, aux tests, au changelog par fichier…).

---

## 2. Points à clarifier / risques

### 2.1. Alignement `core/system/tool` vs `type` dans le manifest

Tu expliques bien la distinction **interne** (core/system/tool) puis tu dis que `plugin.yaml.type` = `system|tool`.

À clarifier pour les devs :

* Où vivent les **plugins core** ?

  * Option A : pas de `plugin.yaml`, ils sont déclarés dans `core_plugins` du `global_config.yaml`. 
  * Option B : ils ont un manifest mais **type = system** + un flag `core: true`.

Ça a un impact direct sur :

* le chargement (ordre core → system → tool),
* la gestion par Bridge (certains ne doivent jamais être désactivables).

Je te conseillerais d’être explicite dans la spec, même si c’est “seulement interne”.

---

### 2.2. Scope global vs **par projet / backend**

Aujourd’hui Jupiter gère :

* des **projets multiples**,
* des **backends** locaux et distants (`local_fs`, `remote_jupiter_api`),
* avec configs globales dans `~/.jupiter/global_config.yaml` et configs projet dans `<project>.jupiter.yaml`.

Pour les plugins, il faut préciser :

* Est‑ce que la **liste de plugins installés** est **globale** à l’install Jupiter, ou par projet ?
* Est‑ce qu’un plugin outil peut être **activé pour certains projets et pas d’autres** ? (Probable.)
* Où se stocke `jupiter/plugins/<plugin_id>/config.yaml` quand tu as plusieurs projets ?

  * un fichier unique mais avec un **namespace par projet**,
  * ou des configs par projet dans `.jupiter/plugins/...` côté projet.

Si ce n’est pas cadré, tu peux te retrouver avec :

* un plugin mal configuré pour un projet mais actif pour tous,
* ou un plugin qui ne fonctionne pas avec certains backends distants, mais quand même affiché comme dispo partout.

---

### 2.3. Permissions vs réalité Python (sandbox “soft”)

Tu définis des permissions très bien (fs_read, fs_write, run_commands, network_outbound, access_meeting), mais tu le sais : **dans un seul process Python, ce n’est pas enforceable à 100 %**.

C’est très bien que tu envisages une v2 avec process séparé, mais dans la v1 :

* un plugin malveillant peut toujours `import os, socket` et faire sa vie.
* Bridge peut **loguer, guider, documenter, checker les permissions déclarées vs réelles**, mais pas empêcher un plugin d’être “méchant” si l’auteur veut contourner.

Je te conseille de le dire explicitement dans le doc :

* “sandbox logique” vs “sandbox technique”,
* confiance basée sur signature / provenance / review,
* plus que sur des garde‑fous runtime.

---

### 2.4. Manifest : éviter qu’il soit intimidant

Ton `plugin.yaml` est très riche (entrypoints, jupiter.version, config_schema, capabilities, permissions, dependencies, extends, i18n…).

C’est génial pour un plugin avancé, mais pour un simple plugin, ça peut faire peur.

Je recommanderais de définir :

* un **profil minimal** (quelques champs obligatoires + defaults intelligents),
* une **version “full”** pour les plugins plus sophistiqués.

Le scaffold `jupiter plugins scaffold` ira dans ce sens, mais c’est bien de le dire : “Voici le manifest minimal viable.”

---

### 2.5. Meeting & remote_actions : limiter le périmètre v1

Tu définis une API `bridge.remote_actions.register(...)` et un modèle de “plan d’action” signé envoyé par Meeting → c’est ambitieux, dans le bon sens.

Mais comme Meeting est déjà la brique qui gate les licences et l’accès à certaines fonctionnalités (`run`, `watch`…), et que l’API actuelle est déjà un peu sensible,

je recommanderais d’être encore plus strict dans v1 :

* limiter les actions distantes à :

  * `reset_plugin_settings`,
  * `toggle_plugin`,
  * `install_official_plugin`,
* et **d’exiger une confirmation locale** systématique, comme tu le suggères déjà (pas de “forcer” complet en v1).

---

### 2.6. Gestion du long‑running & backpressure

Les plugins pourront :

* lancer des analyses lourdes,
* exporter de gros rapports,
* écouter beaucoup d’événements.

Il manque peut‑être une petite mention :

* soit d’un **modèle d’async / tâches longues** (job que la WebUI suit via id + WS),
* soit au moins de limites basiques (timeouts, circuit breaker par plugin, que tu mentionnes un peu côté sandbox).

Sans ça, un plugin UI mal foutu pourrait déclencher des requêtes lourdes en boucle et faire ramer l’instance.

---

## 3. Idées concrètes à ajouter / préciser

### 3.1. Bridge comme **service locator** officiel

Tu donnes déjà `bridge.plugins.get(plugin_id)`. J’irais un peu plus loin avec un namespace `bridge.services` :

```python
services = bridge.services

logger = services.get_logger(plugin_id)
runner = services.get_runner()        # wrapper sur core.runner avec security checks
history = services.get_history()
graph = services.get_graph()
projects = services.get_project_manager()
events = services.get_event_bus()
```

Ça évite que les plugins importent `jupiter.core.*` en direct, et c’est très aligné avec l’architecture actuelle : scanner, analyzer, runner, history, graph, project manager, meeting_adapter.

---

### 3.2. Auto‑UI pour Settings / Metrics / Logs

Tu le suggères déjà, mais je le rendrais *vraiment* contractuel :

* Si un plugin déclare `config_schema` → la WebUI **génère automatiquement** le formulaire de Settings du plugin.
* Si un plugin a `metrics.enabled` → la WebUI affiche automatiquement une mini‑carte “Stats” (nombre d’exécutions, erreurs, temps moyen).
* Tous les panneaux plugins réutilisent un composant `<PluginLogsPanel pluginId="...">` qui se branche au `log_stream` WS.

Résultat :

* les devs de plugins UI se concentrent sur leur **panneau métier**, pas sur la plomberie Settings/Logs/Metrics,
* l’UX est homogène pour tous les plugins.

---

### 3.3. Dev mode & **hot reload** de plugin

Tu mentionnes un mode développeur, je proposerais de le cadrer un peu :

* flag global `developer_mode: true` dans `global_config.yaml`, 
* un bouton “Reload plugin” dans le panneau Settings d’un plugin qui :

  1. demande à Bridge de dé‑enregistrer les contributions (CLI/API/UI) de ce plugin,
  2. re‑importe le module,
  3. re‑appelle ses entrypoints.

En WebUI, on peut :

* afficher “(Dev)” sur les plugins non signés + `allow_unsigned_local_plugins: true`,
* donner un petit panneau “Dev tools” (voir manifest brut, voir config_schema, etc.).

---

### 3.4. Marketplace MVP très simple

Pour ne pas sur‑spécifier trop tôt :

* côté Bridge :

  * `install_from_url(url)` qui télécharge un ZIP → vérifie `plugin.yaml` + signature → installe dans `jupiter/plugins/<id>/`.
* côté WebUI :

  * une simple liste de plugins provenant d’un JSON statique (ou mock) avec `Install` / `Update` / `Remove`.

Ça te permet de tester très vite le *cycle complet* : install → vérif manifest/signature → deps → chargement → panneau UI.

---

### 3.5. Alignement avec la **sécurité actuelle** (RBAC + tokens)

Tu as déjà :

* tokens + rôles admin/viewer,
* endpoints `/run`, `/update`, `/plugins/{name}/toggle` protégés.

Ça vaut le coup de préciser dans cette spec plugin :

* quelles actions de Bridge sont réservées `admin` (install/uninstall plugins, toggle system plugins, remote_actions Meeting),
* comment la WebUI indique le **rôle** de l’utilisateur (par ex. masquer certains boutons si “viewer”).

Ça sécurise bien la partie “plugin ops”.

---

### 3.6. Tests & fixtures pour plugins

Tu parles déjà de `tests/test_basic.py` dans la structure, je proposerais :

* un petit **helper de test** fourni par Jupiter, style `from jupiter.testing import PluginTestContext`, qui donne :

  * un Bridge fake,
  * un projet de test,
  * quelques snapshots / reports synthétiques.

Ça permet d’avoir des tests unitaires fiables de plugins, cohérents avec la façon dont le core fonctionne (scanner, analyzer, history, etc.).

---

## 4. Petit “film” pour vérifier que tout se tient

Scénario : installation d’un plugin `export_advanced` qui étend `ai_helper`, et action distante Meeting de reset de config.

1. **Marketplace WebUI** :
   L’utilisateur clique sur `Install "export_advanced"`.

2. WebUI appelle `POST /plugins/install`, Bridge télécharge le ZIP, lit `plugin.yaml` :

   * type `tool`,
   * dépend de `ai_helper >= 0.5.0`,
   * `extends: [ai_helper]`,
   * demande `network_outbound: true` pour envoyer les exports.

3. Bridge vérifie les signatures :

   * `ai_helper` est `verified`, `export_advanced` est `community`.
   * Mode strict → affiche un warning avant import.

4. Bridge résout les dépendances, charge dans l’ordre :

   1. core (Bridge, settings_update, meeting_adapter),
   2. système (`ai_helper` si on l’a reclassé là ou tool, peu importe),
   3. outil `export_advanced`.

   Il appelle les entrypoints `init()`, `server`, `cli`, `ui` pour chaque.

5. `/plugins` retourne maintenant :

   * `ai_helper` (type tool, `status: ready`),
   * `export_advanced` (type tool, `status: ready`, `extends: ai_helper`, `trust: community`).

   La WebUI :

   * ajoute un onglet “Export avancé”,
   * auto‑génère le cadre Settings via `config_schema`,
   * affiche un panneau Logs + Metrics standard.

6. L’utilisateur configure `export_advanced` dans Settings (format de rapport, options, etc.). Bridge écrit `jupiter/plugins/export_advanced/config.yaml` en utilisant `bridge.config.set`.

7. Plus tard, Meeting envoie une demande signée :

   ```json
   {"action": "reset_plugin_settings", "plugin_id": "export_advanced"}
   ```

   * Bridge vérifie la signature,
   * voit que l’action est déclarée avec `requires_confirmation: true`,
   * affiche dans la WebUI une notification “Meeting propose de réinitialiser ce plugin” avec bouton “Accepter / Refuser”.

8. Si l’utilisateur accepte :

   * Bridge appelle `reset_settings("export_advanced")`,
   * efface / remplace `config.yaml` du plugin avec les defaults du `config_schema`,
   * logue l’action dans les logs du plugin **et** dans le log global.

9. Pendant tout ce temps :

   * les métriques de `export_advanced` sont exposées dans `/metrics`,
   * les logs sont consultables dans le panneau Logs du plugin,
   * le panneau “Plugins” affiche son statut `ready` ou `error` si un healthcheck échoue.

Si tu peux dérouler ce scénario dans ta tête sans avoir à “tricher” sur l’archi, c’est que ta spec est bien alignée. Et à la lecture, on y est franchement pas loin.

---

### TL;DR

* La v0.3.0 du doc est très mature :

  * bonne séparation core/system/tool,
  * WebUI réceptacle bien normé,
  * Bridge core central avec entrypoints & compatibilité,
  * manifest riche (capabilities, permissions, deps, config_schema),
  * sécurité via signatures/niveaux de confiance,
  * migrations & compat legacy prévues,
  * métriques, logs, scaffold, dev mode.
* À préciser surtout :

  * gestion exacte des plugins core vs `type` dans le manifest,
  * scopes (global vs par projet/backend),
  * limites réalistes de la “sandbox”,
  * périmètre v1 des remote_actions Meeting,
  * modèle d’async/long‑running pour les plugins.
* Les ajouts qui me semblent les plus utiles :

  * Bridge = service locator officiel,
  * auto‑UI pour Settings/Metrics/Logs,
  * hot‑reload dev,
  * marketplace MVP,
  * helpers de tests de plugins.
