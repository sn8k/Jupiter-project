# Connecteurs de Projet Jupiter

Ce module contient les adaptateurs ("connecteurs") permettant à Jupiter d'interagir avec différents types de backends de projet.

## Architecture

L'interface de base est définie dans `base.py` via la classe abstraite `BaseConnector`.
Tout connecteur doit implémenter les méthodes suivantes :

- `scan(options: Dict[str, Any]) -> Dict[str, Any]` : Effectue un scan du projet et retourne un rapport JSON.
- `analyze(options: Dict[str, Any]) -> Dict[str, Any]` : Effectue une analyse (statistiques, hotspots) et retourne un résumé JSON.
- `run_command(command: list[str], with_dynamic: bool) -> Dict[str, Any]` : Exécute une commande dans le contexte du projet.
- `get_api_base_url() -> Optional[str]` : Retourne l'URL de base de l'API si applicable.

## Connecteurs disponibles

### `local_fs` (`local.py`)
Connecteur par défaut. Il opère directement sur le système de fichiers local où Jupiter est exécuté.
Il utilise les modules internes `ProjectScanner`, `ProjectAnalyzer` et `Runner`.

### `remote_jupiter_api` (`remote.py`)
Connecteur permettant de piloter une instance Jupiter distante via son API HTTP.
Il agit comme un proxy, transmettant les requêtes de scan/analyse/run à l'instance distante.

## Extension future

Pour supporter d'autres types de projets (ex: une API custom qui expose déjà ses métriques), il suffit de :
1. Créer une nouvelle classe héritant de `BaseConnector`.
2. Implémenter les méthodes requises (en adaptant les réponses au format attendu par Jupiter).
3. Enregistrer le nouveau type dans `jupiter/server/manager.py`.
