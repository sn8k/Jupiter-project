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
- Chaque projet possède sa propre configuration (`jupiter.yaml`) et son propre cache.
- La configuration globale (liste des projets) est stockée dans `~/.jupiter/global.yaml`.

## Commandes avancées (CLI)
Les commandes suivantes sont disponibles pour un usage avancé ou scripté :

- `python -m jupiter.cli.main scan <racine> [--ignore <pattern>] [--show-hidden] [--output rapport.json] [--incremental]` : produit un rapport JSON listant les fichiers et métadonnées basiques.
- `python -m jupiter.cli.main analyze <racine> [--top N] [--json] [--ignore <pattern>] [--show-hidden] [--incremental]` : calcule un résumé agrégé.
- `python -m jupiter.cli.main server <racine> --host 0.0.0.0 --port 8000` : lance le serveur API.
- `python -m jupiter.cli.main gui <racine> --host 0.0.0.0 --port 8050` : démarre le serveur statique de la GUI.
- `python -m jupiter.cli.main ci [--json] [--fail-on-complexity 20] [--fail-on-duplication 5] [--fail-on-unused 50]` : exécute la même pipeline de scan/analyse en appliquant les seuils CI.

> La racine servie et les données du dernier rapport (`.jupiter/cache/last_scan.json`) sont désormais restaurées automatiquement lors d'un redémarrage, en se basant sur la valeur enregistrée dans `~/.jupiter/state.json`.
> Le cache normalise aussi les métadonnées (plugins, fichiers) avant écriture, ce qui évite les erreurs `/reports/last` lorsque le schéma évolue entre deux versions.
- `python -m jupiter.cli.main update <source> [--force]` : met à jour Jupiter depuis un fichier ZIP ou un dépôt Git.
- `python -m jupiter.cli.main --version` : affiche la version actuelle.
- (Interne) `scan`, `analyze` **et** `ci` partagent désormais la même initialisation (plugins, cache, perf, snapshots). Toutes les commandes produisent donc exactement le même rapport et la même instrumentation, qu'on demande un JSON, un résumé humain ou une exécution CI.

### Historique des scans et snapshots

- Chaque `scan` lancé par la CLI, l'API ou la GUI crée par défaut un fichier dans `.jupiter/snapshots/scan-*.json` contenant le rapport complet et des métadonnées (racine, nombre de fichiers, fonctions détectées, etc.).

## Configuration de la Sécurité

Jupiter supporte un mode multi-utilisateurs simple via des tokens d'accès.

### Configuration (jupiter.yaml)

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
- **Configuration** : Ajustez les paramètres dans `jupiter.yaml` sous la section `performance` :
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

Exemple de configuration `jupiter.yaml` :
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
- `jupiter/plugins/` : plugins (ex: code_quality_stub).

## Interface graphique (aperçu)
- **Lancement** : `python -m jupiter.cli.main` (ou via CLI `gui`).
- **Dashboard** : Vue d'ensemble, badges de statut, statistiques et panneau de surveillance temps réel ("Live Watch").
- **Projets (Backends)** : Sélecteur en haut de page pour basculer entre le projet local et des projets distants (configurés dans `jupiter.yaml`).
- **Scan** : Lancement de scans avec options (fichiers cachés, incrémental, exclusions) via une modale dédiée, désormais mieux structurée et capable de mémoriser vos derniers réglages.
- **Run** : Exécution de commandes arbitraires avec option d'analyse dynamique.
- **Paramètres** : Édition complète de la configuration (`jupiter.yaml`), gestion du thème et de la langue.
- **Historique** : Liste chronologique des snapshots avec vue diff (fichiers ajoutés/supprimés/modifiés, delta fonctions). Deux sélecteurs permettent de choisir les snapshots à comparer et un panneau détaille le diff.
- **Mise à jour** : Interface pour déclencher une mise à jour depuis un ZIP ou Git.
- **Plugins** : Liste et état des plugins. Configuration des plugins (ex: URL Webhook) directement depuis l'interface.
- **Analyse & Qualité** : Vues détaillées des métriques et hotspots, avec le panneau Qualité mis à jour automatiquement après chaque Scan (y compris en mode Watch).
- **API** : Vue listant les endpoints de l'API du projet (si configurée).
- **Live Map** : Visualisation graphique interactive des dépendances du projet (fichiers, imports, fonctions). Permet de naviguer visuellement dans la structure du code.
- **Simulation** : Dans les vues "Fichiers" et "Fonctions", un bouton "Corbeille" permet de simuler la suppression d'un élément et d'afficher les impacts potentiels (liens brisés, code orphelin).
- **Modales** : Les fenêtres (Scan, Run, etc.) sont masquées par défaut via la classe `.hidden` et ne s'affichent que lorsqu'une action explicite les ouvre.
- **Chargement JS** : Depuis la 0.1.5, la logique `startScan` est unique pour éviter les collisions ES Modules ; en cas de souci d'affichage, recharger en vidant le cache.

## Plugins
Jupiter est extensible via des plugins.
- **Notifications Webhook** : Envoie un payload JSON à une URL configurée à la fin de chaque scan. Configurable dans l'onglet "Plugins".
  - Si aucune URL n'est fournie, le plugin publie une notification locale (WebSocket + panneau "Live Events") au lieu de tenter une requête HTTP invalide.
- **AI Helper** : Analyse le code pour suggérer des refactorings, des améliorations de documentation ou détecter des problèmes de sécurité. Les suggestions apparaissent dans l'onglet "Suggestions IA" du rapport.

## Configuration Multi-Projets
Jupiter supporte plusieurs backends de projet. Vous pouvez les configurer dans `jupiter.yaml` :

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
