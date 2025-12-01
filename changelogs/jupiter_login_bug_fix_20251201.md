# Login Bug Fix - 2024-12-01

## Problèmes corrigés

### 1. Utilisateurs non pris en compte lors du login
- **Cause racine**: La fonction `load_merged_config` ne fusionnait pas les champs `users`, `security`, et `logging` depuis la configuration globale (`global_config.yaml`).
- **Correction**: Ajout de la fusion de `users`, `security`, et `logging` dans `load_merged_config` (`jupiter/config/config.py`).

### 2. Settings > Users n'affichait plus de données
- **Cause racine**: Le manager utilisait `load_config` au lieu de `load_merged_config` lors du changement de projet actif, donc les utilisateurs de la config globale n'étaient pas chargés.
- **Correction**: Modification de `manager.set_active_project` pour utiliser `load_merged_config` (`jupiter/server/manager.py`).

### 3. Identifiants invalides au login
- **Cause racine**: Même problème que ci-dessus - le config du project_manager ne contenait pas la liste des utilisateurs définis dans `global_config.yaml`.
- **Correction**: Avec les corrections ci-dessus, les utilisateurs sont maintenant correctement chargés.

### 4. Échap ferme la modale de login sans authentification
- **Cause racine**: Le gestionnaire d'événement `cancel` était ajouté à chaque appel de `openLoginModal()`, créant des doublons et potentiellement des comportements incohérents.
- **Correction**: Le gestionnaire d'événement est maintenant ajouté une seule fois avec un flag (`loginModalCancelHandlerAttached`) dans `jupiter/web/app.js`.

## Fichiers modifiés

- `jupiter/config/config.py`: `load_merged_config` fusionne maintenant `users`, `security` et `logging`
- `jupiter/server/manager.py`: `set_active_project` utilise maintenant `load_merged_config`
- `jupiter/web/app.js`: Correction du handler Escape sur la modale de login

## Test de validation

1. Démarrer le serveur Jupiter (`python -m jupiter.cli.main gui`)
2. Vérifier que la modale de login s'affiche
3. Vérifier qu'appuyer sur Échap ne ferme pas la modale
4. Se connecter avec les identifiants définis dans `global_config.yaml`
5. Vérifier dans Settings > Users que la liste des utilisateurs s'affiche
