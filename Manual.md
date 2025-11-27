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
- Fonctions disponibles :
  - chargement d’un rapport JSON produit par `scan` (drag-and-drop ou sélection de fichier),
  - affichage des indicateurs (nombre de fichiers, taille totale, fichier le plus volumineux, dernière mise à jour),
  - tableau trié par taille (200 premiers fichiers pour rester lisible).
- L’UI reste purement statique pour l’instant ; la connexion à l’API se fera dans une itération ultérieure.

## Prochaines étapes suggérées
1. Brancher un framework ASGI (ex : FastAPI) dans `jupiter/server/api.py`.
2. Ajouter la gestion de configuration YAML/JSON dans `jupiter/config/`.
3. Étendre l’analyse à des langages spécifiques dans `jupiter/core/language/` (dossier à créer).
4. Mettre en place des tests unitaires (pytest) pour le scanner et l’analyseur.

## Notes
- Le code suit les conventions décrites dans `AGENTS.md` (PEP 8, annotations complètes, logging standard).
- Chaque fichier dispose d’un changelog dédié dans `changelogs/`.
