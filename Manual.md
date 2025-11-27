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
- `python -m jupiter.cli.main scan <racine>` : produit un rapport JSON listant les fichiers et métadonnées basiques.
- `python -m jupiter.cli.main analyze <racine>` : calcule un résumé agrégé (nombre de fichiers, taille totale, extensions).
- `python -m jupiter.cli.main server <racine> --host 0.0.0.0 --port 8000` : lance le stub du serveur API (journalisation uniquement pour l’instant).

## Structure actuelle
- `jupiter/core/` : scanner, analyseur et sérialisation des rapports.
- `jupiter/cli/` : interface en ligne de commande (argparse).
- `jupiter/server/` : stubs serveur et Meeting pour intégration future.
- `jupiter/config/` : configuration minimale (hôte, port, deviceKey Meeting).
- `jupiter/web/` : espace réservé pour l’UI web.

## Prochaines étapes suggérées
1. Brancher un framework ASGI (ex : FastAPI) dans `jupiter/server/api.py`.
2. Ajouter la gestion de configuration YAML/JSON dans `jupiter/config/`.
3. Étendre l’analyse à des langages spécifiques dans `jupiter/core/language/` (dossier à créer).
4. Mettre en place des tests unitaires (pytest) pour le scanner et l’analyseur.

## Notes
- Le code suit les conventions décrites dans `AGENTS.md` (PEP 8, annotations complètes, logging standard).
- Chaque fichier dispose d’un changelog dédié dans `changelogs/`.
