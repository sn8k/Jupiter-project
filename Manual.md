# Manuel utilisateur – Jupiter

## Pré-requis
- Python 3.10+
- Accès en lecture au projet à analyser
- `requirements.txt` (actuellement vide de dépendances externes) installé si nécessaire

## Installation utilisateur (Windows)
Si vous avez récupéré le projet sous forme d'archive :
1. Décompressez l'archive.
2. Si vous avez l'exécutable `jupiter.exe`, double-cliquez simplement dessus.
3. Sinon, double-cliquez sur **`Jupiter UI.cmd`**.
   - Cela installera automatiquement les dépendances (Python requis) au premier lancement.
   - L'interface s'ouvrira dans votre navigateur.

Pour lancer uniquement le serveur (sans ouvrir le navigateur), utilisez **`Jupiter Server.cmd`**.

## Installation locale (Développeur)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Démarrage rapide (Mode Utilisateur)
Pour lancer Jupiter avec l'interface graphique complète :
```bash
python -m jupiter.cli.main
```
Cela va :
1. Charger la configuration.
2. Démarrer le serveur API et l'interface Web.
3. Ouvrir votre navigateur par défaut.

Si aucun projet n'est configuré, un assistant vous proposera de créer une configuration par défaut.

## Gestion des Projets (Nouveau v1.1.0)
Jupiter supporte désormais la gestion de plusieurs projets.
- Au premier lancement, si aucun projet n'est configuré, l'interface web s'ouvre et un assistant interactif vous guide pour ajouter votre premier projet.
- Chaque projet possède sa propre configuration (`<projet>.jupiter.yaml`) et son propre cache.
- La configuration globale (liste des projets) est stockée dans `~/.jupiter/global_config.yaml` (lecture de secours de l'ancien `global.yaml` maintenue).
- Lorsque vous activez un projet depuis l'interface Web, le registre global et `~/.jupiter/state.json` sont synchronisés automatiquement afin que le prochain démarrage (CLI ou GUI) rouvre le même projet sans paramètre supplémentaire.
- Les registres hérités sont normalisés automatiquement : si un projet pointe encore vers `jupiter.yaml`, il est réécrit en `<projet>.jupiter.yaml` et le chemin est stocké en absolu pour éviter les erreurs d'activation/suppression après mise à jour.

## Versionnage visible (Nouveau)
- La barre supérieure affiche maintenant le numéro issu du fichier `VERSION` juste à côté du logo **Jupiter**.
- Le panneau **Settings > Mise à jour** répète cette information pour vérifier rapidement la version avant de charger un paquet ZIP.
- L'onglet **Plugins** liste la version propre à chaque module (code_quality, pylance, notifications, etc.) afin de distinguer les cycles de vie des extensions du cœur de Jupiter.
- La vue **Pylance** indique explicitement lorsqu'un projet ne contient aucun fichier `.py`, ce qui évite de confondre l'absence de données avec un scan non exécuté.

## Commandes avancées (CLI)
Les commandes suivantes sont disponibles pour un usage avancé ou scripté :

- `python -m jupiter.cli.main scan <racine> [--ignore <pattern>] [--show-hidden] [--output rapport.json] [--incremental]` : produit un rapport JSON listant les fichiers et métadonnées basiques.
- `python -m jupiter.cli.main analyze <racine> [--top N] [--json] [--ignore <pattern>] [--show-hidden] [--incremental]` : calcule un résumé agrégé.
- `python -m jupiter.cli.main server <racine> --host 0.0.0.0 --port 8000` : lance le serveur API.
- `python -m jupiter.cli.main gui <racine> --host 0.0.0.0 --port 8050` : démarre le serveur statique de la GUI.
- `python -m jupiter.cli.main ci [--json] [--fail-on-complexity 20] [--fail-on-duplication 5] [--fail-on-unused 50]` : exécute la même pipeline de scan/analyse en appliquant les seuils CI.

> La racine servie et les données du dernier rapport (`.jupiter/cache/last_scan.json`) sont désormais restaurées automatiquement lors d'un redémarrage : Jupiter privilégie le projet actif déclaré dans le registre global (`~/.jupiter/global_config.yaml` ou `global.yaml` legacy) puis synchronise `~/.jupiter/state.json`.
> Le cache normalise aussi les métadonnées (plugins, fichiers) avant écriture, ce qui évite les erreurs `/reports/last` lorsque le schéma évolue entre deux versions.
- `python -m jupiter.cli.main update <source> [--force]` : met à jour Jupiter depuis un fichier ZIP ou un dépôt Git.
- `python -m jupiter.cli.main --version` : affiche la version actuelle.
- (Interne) `scan`, `analyze` **et** `ci` partagent désormais la même initialisation (plugins, cache, perf, snapshots). Toutes les commandes produisent donc exactement le même rapport et la même instrumentation, qu'on demande un JSON, un résumé humain ou une exécution CI.

### Historique des scans et snapshots

- Chaque `scan` lancé par la CLI, l'API ou la GUI crée par défaut un fichier dans `.jupiter/snapshots/scan-*.json` contenant le rapport complet et des métadonnées (racine, nombre de fichiers, fonctions détectées, etc.).

## Logging paramétrable (Nouveau)
- L'onglet **Settings** expose désormais un champ **Log Level** (Debug, Info, Warning, Error, Critic) appliqué au serveur FastAPI, à Uvicorn et à la CLI.
- La valeur est stockée dans `logging.level` du fichier `<projet>.jupiter.yaml` (sauvegarde automatique via l'UI).
- Le filtre de logs du tableau de bord utilise la même valeur pour rester cohérent avec la verbosité active.
- Un champ **Chemin du fichier log** permet de définir la destination du fichier (laisser vide pour désactiver l'écriture fichier).
- Tous les plugins embarqués respectent désormais ce niveau : en mode INFO ils résument les actions (scan, webhooks, suggestions) et en mode DEBUG ils journalisent les payloads complets pour faciliter l'investigation.

## Paramètres plugins persistants (Nouveau)
- La page **Settings** a été réorganisée en deux colonnes : la grille principale rassemble Réseau/UI/Meeting/Performance/Sécurité/Utilisateurs tandis que la colonne latérale conserve la carte **Mise à jour** et ses actions.
- Les sections dynamiques injectées par les plugins (Notifications, Code Quality, etc.) apparaissent immédiatement sous le layout principal dans des cartes dédiées (`plugin-settings-card`).
- Chaque panneau plugin tire désormais sa configuration depuis le registre global/projet (`~/.jupiter/global_config.yaml` + `<projet>.jupiter.yaml`) et réécrit automatiquement les valeurs lors des sauvegardes.
- Les boutons **Save** exposent un indicateur d'état (en cours, succès, erreur) pour confirmer la prise en compte de la configuration sans quitter la page.
- Lorsque vous changez de projet, les panneaux sont vidés, rechargés et resynchronisés avec les paramètres réellement stockés afin d'éviter les résidus d'UI.

## Configuration de la Sécurité

Jupiter supporte un mode multi-utilisateurs simple via des tokens d'accès.

### Configuration (<projet>.jupiter.yaml)

```yaml
# Gestion des utilisateurs (Recommandé)
users:
  - name: "admin"
    token: "admin-secret"
    role: "admin"
  - name: "dev"
    token: "dev-secret"
    role: "viewer"

security:
  # Token unique (Legacy - déprécié)
  token: "mon-secret-admin"
```

### Rôles
- **admin** : Accès complet (scan, run, config, update, gestion utilisateurs).
- **viewer** : Accès en lecture seule (voir les rapports, graphiques, fichiers).

## Licence Meeting / DeviceKey Jupiter

Jupiter peut vérifier sa licence via l'API Meeting. Cette vérification est optionnelle mais recommandée pour un usage en production.

### Règle Métier
Une licence Jupiter est considérée **valide** si :
- L'API Meeting retourne HTTP 200 pour `GET /api/devices/{device_key}`
- Le champ `authorized` est `true`
- Le champ `device_type` est `"Jupiter"`
- Le champ `token_count` est supérieur à 0

### Configuration (~/.jupiter/global_config.yaml)

La configuration Meeting se fait dans le fichier de configuration globale :

```yaml
meeting:
  enabled: true
  deviceKey: "C86015A0C19686A1C7ECE6CC7C8F4874"  # Votre clé device Meeting
  base_url: "https://meeting.ygsoft.fr/api"      # URL de l'API Meeting
  device_type: "Jupiter"                          # Type de device attendu
  timeout_seconds: 5.0                            # Timeout des requêtes HTTP
  # auth_token: ""                                # Optionnel: token d'authentification
```

### Vérification via CLI

Utilisez la commande suivante pour vérifier l'état de la licence :

```bash
python -m jupiter.cli.main meeting check-license [--json]
```

Cette commande retourne :
- Code 0 : Licence valide
- Code 1 : Licence invalide
- Code 2 : Erreur de configuration (pas de deviceKey)
- Code 3 : Erreur réseau

Exemple de sortie :
```
✅ License Check: VALID
   Message: License valid: authorized, correct device_type, tokens > 0.
   Device Key: C86015A0C19686A1C7ECE6CC7C8F4874
   Meeting API: https://meeting.ygsoft.fr/api
   HTTP Status: 200
   Authorized: True
   Device Type: Jupiter (expected: Jupiter)
   Token Count: 10
   Checked At: 2025-06-01T12:00:00
```

### Endpoint API

L'API Jupiter expose un endpoint pour consulter l'état de la licence :

- `GET /license/status` : Retourne l'état détaillé de la vérification Meeting
- `POST /license/refresh` : Force une re-vérification (requiert le rôle admin)

Exemple de réponse JSON :
```json
{
  "status": "valid",
  "message": "License valid: authorized, correct device_type, tokens > 0.",
  "device_key": "C86015A0C19686A1C7ECE6CC7C8F4874",
  "http_status": 200,
  "authorized": true,
  "device_type": "Jupiter",
  "token_count": 10,
  "checked_at": "2025-06-01T12:00:00",
  "meeting_base_url": "https://meeting.ygsoft.fr/api",
  "device_type_expected": "Jupiter"
}
```

### Mode Restreint

Si la licence n'est pas valide ou si aucune `deviceKey` n'est configurée :
- Jupiter démarre en **mode restreint** (trial)
- Une période de grâce de 10 minutes est accordée
- Après expiration, certaines fonctionnalités (run, watch, dynamic_scan) sont bloquées
- Le message d'erreur indique clairement la raison de l'invalidité

### Interface Web (Settings > Meeting License)

La page Paramètres de l'interface web inclut une section dédiée à la gestion de la licence Meeting :

- **Indicateur de statut** : Affiche visuellement l'état de la licence avec un code couleur :
  - 🟢 Vert : Licence valide
  - 🔴 Rouge : Licence invalide
  - 🟠 Orange : Erreur réseau
  - 🟣 Violet : Erreur de configuration

- **Champs de configuration** :
  - Activer/Désactiver Meeting
  - Device Key (clé d'identification)
  - Auth Token (optionnel, si requis par l'API)

- **Actions** :
  - **Vérifier la licence** : Force une nouvelle vérification auprès de l'API Meeting
  - **Actualiser** : Rafraîchit l'affichage du statut actuel

- **Dernière réponse** : Affiche les détails bruts de la dernière réponse de l'API Meeting (status, authorized, device_type, token_count, etc.)

### Démarrage du Serveur

Pour démarrer le serveur API correctement en chargeant la configuration du dossier courant :

```bash
# Via le script (Windows)
"Jupiter Server.cmd"

# Via la ligne de commande
python -m jupiter.cli.main server
```

> **Note** : Ne pas ajouter d'argument après `server` sauf si vous souhaitez spécifier un dossier racine différent du dossier courant. La commande `server start` est incorrecte si le dossier `start` n'existe pas.

### Mise à jour de la racine via l'API `/config/root`
- Le serveur recharge désormais automatiquement les connecteurs, le PluginManager et l'adaptateur Meeting dès que la racine change.
- Si la nouvelle configuration ne possède pas de `deviceKey`, Jupiter réutilise celui de l'ancienne racine pour éviter les coupures de licence.
- L'historique (`HistoryManager`) est synchronisé sur le nouveau dossier afin que les snapshots correspondent immédiatement à la nouvelle racine.

- Ajoutez `--snapshot-label "Nom du jalon"` à `scan` pour annoter un point clé, ou `--no-snapshot` pour désactiver ponctuellement l'enregistrement.
- Inspectez l'historique directement depuis la CLI :

```bash
python -m jupiter.cli.main snapshots list            # vues synthétiques
python -m jupiter.cli.main snapshots show <id>       # métadonnées + rapport (via --report)
python -m jupiter.cli.main snapshots diff A B        # delta fichiers/fonctions entre deux scans
```

Les mêmes données sont exposées via l'API (`/snapshots`, `/snapshots/{id}`, `/snapshots/diff`) et alimentent la nouvelle vue Historique dans la GUI.

### Gestion des exclusions
- Le scanner ignore les fichiers et dossiers cachés par défaut (sauf `--show-hidden`).
- Les glob patterns de `.jupiterignore` sont appliqués automatiquement si le fichier est présent à la racine analysée.
- `--ignore` permet d’ajouter des motifs temporaires sans modifier le fichier `.jupiterignore`.

### Support Polyglotte (Nouveau)
Jupiter supporte désormais l'analyse des projets **JavaScript et TypeScript** (en plus de Python).
- Les fichiers `.js`, `.ts`, `.jsx`, `.tsx` sont détectés automatiquement.
- Les fonctions et imports sont extraits (via heuristiques regex).
- Les métriques JS/TS apparaissent dans le rapport d'analyse et la Live Map (nœuds jaunes).

### Performance & Gros Projets
Pour les projets contenant des milliers de fichiers, Jupiter propose des options d'optimisation :
- **Scan parallèle** : Activé par défaut, utilise plusieurs threads pour accélérer la lecture des fichiers.
- **Mode Performance** : Utilisez le flag `--perf` avec `scan` ou `analyze` pour afficher des métriques de temps d'exécution détaillées.
- **Simplification du Graphe** : La Live Map simplifie automatiquement le graphe (regroupement par dossier) si le nombre de nœuds dépasse un seuil (défaut: 1000).
- **Configuration** : Ajustez les paramètres dans `<projet>.jupiter.yaml` sous la section `performance` :
  ```yaml
  performance:
    parallel_scan: true
    max_workers: 8
    graph_simplification: true
    max_graph_nodes: 1000
  ```

### Intégration CI/CD
Jupiter peut être intégré dans vos pipelines CI/CD pour garantir la qualité du code.
Utilisez la commande `ci` pour exécuter une analyse et vérifier les seuils de qualité.

Exemple de configuration `<projet>.jupiter.yaml` :
```yaml
ci:
  fail_on:
    max_complexity: 20
    max_duplication_clusters: 5
    max_unused_functions: 50
```

Commande CI :
```bash
jupiter ci --json
```
Si un seuil est dépassé, la commande retourne un code d'erreur `1`, ce qui bloquera le pipeline.

## Structure actuelle
- `jupiter/core/` : scanner, analyseur, runner, qualité, plugins.
- `jupiter/cli/` : interface en ligne de commande.
- `jupiter/server/` : serveur API (FastAPI) et Meeting adapter.
- `jupiter/config/` : configuration (YAML).
- `jupiter/web/` : interface graphique.
- `jupiter/plugins/` : plugins (ex: code_quality, ai_helper, pylance_analyzer).

- **Lancement** : `python -m jupiter.cli.main` (ou via CLI `gui`).
- **Projets** : Tableau de bord dédié (vue "Projects") avec résumé du projet actif, racine servie, dernier scan et actions rapides (scanner, éditer la config .jupiter.yaml, basculer/supprimer).
- Dans la page Projets, vous pouvez éditer les motifs d’ignore (globs, ex. `node_modules/**,dist/**`) propres à chaque projet ; ils sont appliqués automatiquement aux scans/analyses de ce projet.
- Les paramètres d’inspection API (connector, app_var, chemin) sont désormais éditables dans la page Projets et sauvegardés par projet, sans passer par la page Settings.
- **Dashboard** : Vue d'ensemble, badges de statut, statistiques et panneau de surveillance temps réel ("Live Watch").
- **Projets (Backends)** : Sélecteur en haut de page pour basculer entre le projet local et des projets distants (configurés dans `<projet>.jupiter.yaml`).
- **Scan** : Lancement de scans avec options (fichiers cachés, incrémental, exclusions) via une modale dédiée, désormais mieux structurée et capable de mémoriser vos derniers réglages.
- **Run** : Exécution de commandes arbitraires avec option d'analyse dynamique.
- **Paramètres** : Édition complète de la configuration (`<projet>.jupiter.yaml`), gestion du thème et de la langue.
- **Historique** : Liste chronologique des snapshots avec vue diff (fichiers ajoutés/supprimés/modifiés, delta fonctions). Deux sélecteurs permettent de choisir les snapshots à comparer et un panneau détaille le diff.
- **Mise à jour** : Interface pour déclencher une mise à jour depuis un ZIP ou Git.
- **Plugins** : Liste et état des plugins. Configuration des plugins (ex: URL Webhook) directement depuis l'interface.
- **Analyse & Code Quality** : Les métriques avancées restent accessibles depuis la vue Analyse tandis que l'ancienne page Qualité vit désormais dans l'onglet *Dashboard* du plugin Code Quality (mêmes tableaux complexité/duplication, export et alertes, alimentés automatiquement après chaque Scan/Watch).
- **API** : Vue listant les endpoints de l'API du projet (si configurée).
- **Live Map** : Visualisation graphique interactive des dépendances du projet (fichiers, imports, fonctions). Permet de naviguer visuellement dans la structure du code.
- **Simulation** : Dans les vues "Fichiers" et "Fonctions", un bouton "Corbeille" permet de simuler la suppression d'un élément et d'afficher les impacts potentiels (liens brisés, code orphelin).
- **Modales** : Les fenêtres (Scan, Run, etc.) sont masquées par défaut via la classe `.hidden` et ne s'affichent que lorsqu'une action explicite les ouvre.
- **Chargement JS** : Depuis la 0.1.5, la logique `startScan` est unique pour éviter les collisions ES Modules ; en cas de souci d'affichage, recharger en vidant le cache.

## Plugins
Jupiter est extensible via des plugins.
- **Notifications Webhook** : Envoie un payload JSON à une URL configurée à la fin de chaque scan. Configurable dans l'onglet "Plugins".
  - Si aucune URL n'est fournie, le plugin publie une notification locale (WebSocket + panneau "Live Events") au lieu de tenter une requête HTTP invalide.
  - La section de configuration dispose maintenant d'un bouton **Enregistrer** explicite qui écrit la configuration via `/plugins/notifications_webhook/config` et recharge les valeurs au chargement de la page.
  - Un nouveau type d'événement **API connectée** diffuse automatiquement l'état du connecteur API (en ligne / hors ligne) vers le webhook et les notifications locales.
  - Toute notification (scan, API, qualité, etc.) apparaît également sous forme de popup (toast) dans l'interface, visible sur toutes les vues.
- **Code Quality** : Mesure la complexité, la duplication et l'indice de maintenabilité et expose une vue dédiée dans la barre latérale.
  - Le nouvel onglet **Dashboard** reprend l'ancienne page Qualité (top complexité + clusters de duplication, export JSON) pour garder toutes les métriques au même endroit que les onglets Issues/Files/Duplication/Recommendations.
  - L'onglet **Duplication** permet désormais de **lier manuellement des clusters détectés** : cochez au moins deux clusters, cliquez sur **Link Selected**, attribuez un libellé facultatif et Jupiter regénère un bloc unique qui couvre l'ensemble des lignes (ex. lignes 71‑77 plutôt que 71‑76 / 72‑77 séparés).
  - Les liaisons sont vérifiées à chaque `Analyze` et peuvent être relancées sans rescanner via **Re-check Linked Blocks** (ou l'endpoint `POST /plugins/code_quality/manual-links/recheck`). Un badge `Linked` + un badge de statut (verified / missing / diverged) indique si les occurrences sont toujours identiques.
  - Les définitions sont persistées dans `.jupiter/manual_duplication_links.json`. Le fichier est créé automatiquement et peut être édité à la main ou approvisionné via la configuration (`plugins.code_quality.manual_duplication_links`). Exemple :

    ```json
    {
      "links": [
        {
          "id": "cli-scan-options",
          "label": "Options scan/analyze CLI",
          "occurrences": [
            {"path": "jupiter/cli/command_handlers.py", "start_line": 71, "end_line": 77, "label": "_build_scan_options"},
            {"path": "jupiter/cli/command_handlers.py", "start_line": 154, "end_line": 160, "label": "_build_services_from_args"},
            {"path": "jupiter/cli/command_handlers.py", "start_line": 228, "end_line": 234, "label": "handle_scan"},
            {"path": "jupiter/cli/command_handlers.py", "start_line": 307, "end_line": 313, "label": "handle_analyze"}
          ]
        }
      ]
    }
    ```
  - Les occurrences configurées (ou créées via l'UI) sont réutilisées dans les rapports `/analyze`, exportées dans `duplication_clusters` et ne faussent pas le pourcentage de duplication.
- **AI Helper** : Analyse le code pour suggérer des refactorings, des améliorations de documentation ou détecter des problèmes de sécurité. Les suggestions apparaissent dans l'onglet "Suggestions IA" du rapport.
  - Les alertes de duplication listent désormais précisément les fichiers et lignes concernés pour rendre le rapport actionnable (y compris dans l'export JSON des suggestions).
  - Chaque duplication inclut aussi le nom de la fonction la plus proche et un extrait du bloc concerné pour que vous sachiez immédiatement quoi refactorer.
- **Refactorings internes** : les flux CLI/API et la gestion des projets côté UI réutilisent désormais des helpers partagés (options de scan, gestion d'historique, requêtes projet) pour éviter les duplications de code et réduire les risques de divergence.

## Configuration Multi-Projets
Jupiter supporte plusieurs backends de projet. Vous pouvez les configurer dans `<projet>.jupiter.yaml` :

```yaml
backends:
  - name: "local"
    type: "local_fs"
    path: "."
  - name: "remote-prod"
    type: "remote_jupiter_api"
    api_url: "http://prod-server:8000"
    api_key: "optional-token"

project_api:
  type: "openapi"
  base_url: "http://localhost:8000"
  openapi_url: "/openapi.json"
```

Dans l'interface Web, utilisez le menu déroulant en haut pour changer de contexte.

## Tests & CI
- Tests unitaires et d'intégration : `pytest tests/`.
- CI : GitHub Actions configuré dans `.github/workflows/ci.yml`.

## Notes
- Le code suit les conventions décrites dans `AGENTS.md`.
- Chaque fichier dispose d’un changelog dédié dans `changelogs/`.
