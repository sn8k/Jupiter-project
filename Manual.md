# Manuel utilisateur – Jupiter

## Pré-requis
- Python 3.10+
- Accès en lecture au projet à analyser
- `requirements.txt` (actuellement vide de dépendances externes) installé si nécessaire

## Installation utilisateur (Windows)
Si vous avez récupéré le projet sous forme d'archive :
1. Décompressez l'archive.
2. Double-cliquez sur **`Jupiter UI.cmd`**.
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

## Commandes avancées (CLI)
Les commandes suivantes sont disponibles pour un usage avancé ou scripté :

- `python -m jupiter.cli.main scan <racine> [--ignore <pattern>] [--show-hidden] [--output rapport.json] [--incremental]` : produit un rapport JSON listant les fichiers et métadonnées basiques.
- `python -m jupiter.cli.main analyze <racine> [--top N] [--json] [--ignore <pattern>] [--show-hidden] [--incremental]` : calcule un résumé agrégé.
- `python -m jupiter.cli.main server <racine> --host 0.0.0.0 --port 8000` : lance le serveur API.
- `python -m jupiter.cli.main gui <racine> --host 0.0.0.0 --port 8050` : démarre le serveur statique de la GUI.

> La racine servie et les données du dernier rapport (`.jupiter/cache/last_scan.json`) sont désormais restaurées automatiquement lors d'un redémarrage, en se basant sur la valeur enregistrée dans `~/.jupiter/state.json`.
- `python -m jupiter.cli.main update <source> [--force]` : met à jour Jupiter depuis un fichier ZIP ou un dépôt Git.
- `python -m jupiter.cli.main --version` : affiche la version actuelle.

### Gestion des exclusions
- Le scanner ignore les fichiers et dossiers cachés par défaut (sauf `--show-hidden`).
- Les glob patterns de `.jupiterignore` sont appliqués automatiquement si le fichier est présent à la racine analysée.
- `--ignore` permet d’ajouter des motifs temporaires sans modifier le fichier `.jupiterignore`.

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
- **Scan** : Lancement de scans avec options (fichiers cachés, incrémental, exclusions) via une modale dédiée.
- **Run** : Exécution de commandes arbitraires avec option d'analyse dynamique.
- **Paramètres** : Édition complète de la configuration (`jupiter.yaml`), gestion du thème et de la langue.
- **Mise à jour** : Interface pour déclencher une mise à jour depuis un ZIP ou Git.
- **Plugins** : Liste et état des plugins.
- **Analyse & Qualité** : Vues détaillées des métriques et hotspots.
- **Modales** : Les fenêtres (Scan, Run, etc.) sont masquées par défaut via la classe `.hidden` et ne s'affichent que lorsqu'une action explicite les ouvre.
- **Chargement JS** : Depuis la 0.1.5, la logique `startScan` est unique pour éviter les collisions ES Modules ; en cas de souci d'affichage, recharger en vidant le cache.

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
```

Dans l'interface Web, utilisez le menu déroulant en haut pour changer de contexte.

## Tests & CI
- Tests unitaires et d'intégration : `pytest tests/`.
- CI : GitHub Actions configuré dans `.github/workflows/ci.yml`.

## Notes
- Le code suit les conventions décrites dans `AGENTS.md`.
- Chaque fichier dispose d’un changelog dédié dans `changelogs/`.
