# Manuel utilisateur – Jupiter

## Pré-requis
- Python 3.10+
- Accès en lecture au projet à analyser
- `requirements.txt` (actuellement vide de dépendances externes) installé si nécessaire

## Installation locale
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Commandes principales
- `python -m jupiter.cli.main scan <racine> [--ignore <pattern>] [--show-hidden] [--output rapport.json]` : produit un rapport JSON listant les fichiers et métadonnées basiques (chemins, tailles, dates). Les motifs `--ignore` peuvent être fournis plusieurs fois et complètent le contenu éventuel d’un fichier `.jupiterignore`.
- `python -m jupiter.cli.main analyze <racine> [--top N] [--json] [--ignore <pattern>] [--show-hidden]` : calcule un résumé agrégé (nombre de fichiers, taille totale, taille moyenne, extensions, fichiers les plus volumineux).
- `python -m jupiter.cli.main server <racine> --host 0.0.0.0 --port 8000` : lance le stub du serveur API (journalisation uniquement pour l’instant).
- `python -m jupiter.cli.main gui <racine> --host 0.0.0.0 --port 8050` : démarre le serveur statique de la GUI. Ouvrez l’URL indiquée puis chargez un rapport JSON généré par `scan` pour afficher les tableaux et indicateurs de synthèse.

### Gestion des exclusions
- Le scanner ignore les fichiers et dossiers cachés par défaut (sauf `--show-hidden`).
- Les glob patterns de `.jupiterignore` sont appliqués automatiquement si le fichier est présent à la racine analysée.
- `--ignore` permet d’ajouter des motifs temporaires sans modifier le fichier `.jupiterignore`.

## Structure actuelle
- `jupiter/core/` : scanner, analyseur et sérialisation des rapports.
- `jupiter/cli/` : interface en ligne de commande (argparse).
- `jupiter/server/` : stubs serveur et Meeting pour intégration future.
- `jupiter/config/` : configuration minimale (hôte, port, deviceKey Meeting).
- `jupiter/web/` : interface graphique statique (HTML/CSS/JS) servie par le nouveau lanceur `gui`.

## Interface graphique (aperçu)
- Lancement : `python -m jupiter.cli.main gui <racine> --host 0.0.0.0 --port 8050`.
- Vue globale : navigation Dashboard / Analyse / Fichiers / Paramètres / Plugins.
- Vue Diagnostic : URL d'API affichée, statut du dernier scan et flux d'événements/logs pour vérifier la connexion.
- Import : glisser-déposer ou sélection d’un rapport JSON produit par `scan` (compatible avec la structure actuelle du rapport).
- Synthèse : cartes de KPI (volumétrie, dernière modif, fichier le plus gros, dernier scan, statut Meeting placeholder), badges de statut.
- Analyse : indicateurs dérivés (extension dominante, taille moyenne, fichier le plus récent), liste de hotspots basée sur les fichiers volumineux (placeholder pour la future analyse dynamique).
- Fichiers : tableau trié par taille (200 premiers éléments) pour inspection rapide.
- Paramètres & Plugins : cartes configurables prêtes à être reliées à l’adaptateur Meeting, au basculeur de thème et aux plugins (actions actuellement en **placeholder**).
- Actions rapides : boutons `Scan / Watch / Run` et bascule Paramètres, tous en placeholder en attendant la connexion API/WS. L'appel `Scan` s'appuie sur l'API FastAPI (CORS activé) et peut être redirigé via `JUPITER_API_BASE`.

## Prochaines étapes suggérées
1. Brancher un framework ASGI (ex : FastAPI) dans `jupiter/server/api.py`.
2. Ajouter la gestion de configuration YAML/JSON dans `jupiter/config/`.
3. Étendre l’analyse à des langages spécifiques dans `jupiter/core/language/` (dossier à créer).
4. Mettre en place des tests unitaires (pytest) pour le scanner et l’analyseur.

## Notes
- Le code suit les conventions décrites dans `AGENTS.md` (PEP 8, annotations complètes, logging standard).
- Chaque fichier dispose d’un changelog dédié dans `changelogs/`.
