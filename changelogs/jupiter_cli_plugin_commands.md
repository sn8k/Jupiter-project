# Changelog - jupiter/cli/plugin_commands.py

Ce fichier documente les modifications apportées au module de commandes CLI pour les plugins.

## [0.5.0] - Phase 9: Marketplace Commands

### Ajouté
- **`_install_plugin_dependencies(plugin_path)`** : Installation des dépendances Python
  - Exécute `pip install -r requirements.txt` du plugin
  - Gestion des erreurs avec warning (non bloquant)

- **`handle_plugins_update(args)`** : Mise à jour de plugins
  - Création de backup avant mise à jour (sauf `--no-backup`)
  - Rollback automatique en cas d'échec
  - Vérification de signature sur la nouvelle version
  - Support de `--source` pour source personnalisée
  - Support de `--install-deps` pour dépendances Python
  - Comparaison de versions avec option `--force`

- **`handle_plugins_check_updates(args)`** : Vérification des mises à jour
  - Liste tous les plugins avec leurs versions
  - Affiche la source de mise à jour si disponible
  - Support `--json` pour sortie machine
  - Note: Nécessite un registre/marketplace pour détection automatique

### Modifié
- **`handle_plugins_install(args)`** :
  - Support `--install-deps` : Installe les dépendances Python
  - Support `--dry-run` : Simule l'installation sans modifier le système
  - Affiche la présence de requirements.txt
  - Mode dry-run avec indicateur [DRY RUN] dans les messages

## [0.4.0] - Phase 7.2: Vérification de signature à l'installation

### Ajouté
- **`_verify_plugin_signature(plugin_path, force)`** : Vérification de signature lors de l'installation
  - Vérifie la signature d'un plugin avant de procéder à l'installation
  - Gestion des niveaux de confiance avec affichage coloré :
    - 🏆 OFFICIAL : Toujours autorisé (vert)
    - ✓ VERIFIED : Toujours autorisé (vert)
    - 🌐 COMMUNITY : Toujours autorisé (jaune) avec avertissement
    - ⚠️ UNSIGNED : Requiert confirmation (rouge)
  - Mode développeur (`is_dev_mode()`) : Autorise les plugins non signés sans confirmation
  - Option `--force` : Contourne les vérifications de confiance
  - Prompt interactif pour plugins non signés hors dev mode

### Modifié
- **`handle_plugins_install(args)`** : Intégration de la vérification de signature
  - Appel à `_verify_plugin_signature()` après validation du manifest
  - Annulation de l'installation si la vérification échoue

### Tests
- 32 tests E2E dans `tests/test_cli_plugin_commands.py`:
  - TestPluginsSign: 6 tests (sign success, path errors, trust levels)
  - TestPluginsVerify: 3 tests (verify unsigned, path not found, require level)
  - TestSignAndVerifyIntegration: 1 test (sign then verify)
  - TestPluginsList: 3 tests (no bridge, with bridge, json output)
  - TestPluginsInfo: 2 tests (not found, found)
  - TestPluginsEnableDisable: 3 tests (enable, enable not found, disable)
  - TestPluginsStatus: 2 tests (no bridge, with bridge)
  - TestPluginsScaffold: 2 tests (new plugin, already exists)
  - TestPluginsInstall: 2 tests (local path, invalid source)
  - TestPluginsUninstall: 2 tests (not found, success)
  - TestPluginsReload: 2 tests (not in dev mode, in dev mode)
  - TestVerifyPluginSignatureHelper: 4 tests (dev mode, force, signed, official)

## [0.3.0] - Phase 7.2: Plugin Signing Commands

### Ajouté
- **`handle_plugins_sign(args)`** : Signature cryptographique de plugins
  - Validation du chemin et de la structure du plugin
  - Support des manifests: plugin.yaml, plugin.json, manifest.json
  - Configuration du signataire via arguments ou variables d'environnement:
    - `--signer-id` / `$JUPITER_SIGNER_ID` (default: "local-developer")
    - `--signer-name` / `$JUPITER_SIGNER_NAME` (default: "Local Developer")
  - Niveaux de confiance: official, verified, community
  - Support optionnel de clé privée avec `--key`
  - Création du fichier `plugin.sig` dans le répertoire plugin

- **`handle_plugins_verify(args)`** : Vérification de signature de plugins
  - Affichage du niveau de confiance avec emojis
  - Affichage des informations de signature (signataire, algorithme, timestamp)
  - Affichage des warnings et erreurs
  - Option `--require-level` pour valider un niveau minimum
    - Exit code 1 si le niveau n'est pas atteint

### Tests
- 10 tests dans `tests/test_cli_plugin_commands.py`:
  - TestPluginsSign: 6 tests (success, path not found, not directory, no manifest, invalid trust level, default signer)
  - TestPluginsVerify: 3 tests (unsigned plugin, path not found, require level not met)
  - TestSignAndVerifyIntegration: 1 test (sign then verify)

## [0.2.0] - Phase 3.2: Plugin Management Commands

### Ajouté
- **`handle_plugins_install(args)`** : Installation de plugins depuis diverses sources
  - Support URL HTTP/HTTPS vers fichier ZIP
  - Support URL Git (clone avec `--depth 1`)
  - Support chemin local (répertoire ou ZIP)
  - Validation du manifest.json avant installation
  - Option `--force` pour écraser un plugin existant

- **`handle_plugins_uninstall(args)`** : Désinstallation de plugins
  - Protection des plugins core (non supprimables)
  - Confirmation interactive (sauf avec `--force`)
  - Suppression du répertoire plugin

- **`handle_plugins_scaffold(args)`** : Génération de squelette pour nouveau plugin
  - Création de `manifest.json` avec métadonnées par défaut
  - Création de `plugin.py` avec classe de base implémentant `IPlugin`
  - Création de `README.md` avec documentation de base
  - Option `--output` pour spécifier le répertoire de sortie

- **`handle_plugins_reload(args)`** : Hot-reload de plugin en mode développeur
  - Vérification que `developer_mode` est activé
  - Support via `Bridge.reload_plugin()` ou événement de reload

### Fonctions utilitaires ajoutées
- `_get_plugins_dir()` : Récupère le répertoire des plugins
- `_download_from_url(url, dest)` : Télécharge un fichier depuis URL
- `_extract_zip(zip_path, dest_dir)` : Extrait une archive ZIP
- `_clone_git_repo(git_url, dest)` : Clone un dépôt Git
- `_validate_plugin_manifest(plugin_dir)` : Valide le manifest d'un plugin

### Imports ajoutés
- `os`, `shutil`, `tempfile`, `zipfile` pour gestion fichiers
- `urllib.parse.urlparse` pour parsing d'URLs

## [0.1.1] - Corrections Pylance

### Corrigé
- Utilisation de `getattr()` pour accéder aux attributs optionnels (`icon`, `author`, `homepage`, `license`)
- Correction des appels `enable_plugin` et `disable_plugin` via `getattr()` pour éviter les erreurs de type
- Ajout de `TYPE_CHECKING` pour l'import conditionnel de `PluginManifest`

## [0.1.0] - Création du module

### Ajouté
- **`plugin_commands.py`** (v0.1.0) - Commandes CLI pour la gestion des plugins Bridge v2
  - `handle_plugins_list(args)` : Liste tous les plugins enregistrés
    - Support JSON avec `--json`
    - Affichage groupé par type (core, system, external, legacy)
    - Comptage des contributions (CLI, API, UI) par plugin
    - Résumé avec états (ready, error, disabled)
  
  - `handle_plugins_info(args)` : Détails complets d'un plugin
    - Métadonnées (id, version, type, state, description, author...)
    - Permissions et dépendances
    - Liste des contributions enregistrées
    - Support JSON avec `--json`
  
  - `handle_plugins_enable(args)` : Active un plugin désactivé
    - Vérification de l'existence du plugin
    - Future-proof (prêt pour Bridge.enable_plugin())
  
  - `handle_plugins_disable(args)` : Désactive un plugin
    - Protection des plugins core (non désactivables)
    - Future-proof (prêt pour Bridge.disable_plugin())
  
  - `handle_plugins_status(args)` : Statut du système Bridge
    - Version du Bridge
    - Comptage des plugins par état
    - Comptage des contributions totales

### Fonctions utilitaires
- `get_bridge()` : Récupère le singleton Bridge
- `get_cli_registry()` / `get_api_registry()` / `get_ui_registry()` : Récupèrent les registries
- `format_state_emoji(state)` : Emoji pour l'état du plugin
- `format_type_emoji(type)` : Emoji pour le type du plugin

### Intégration CLI
- Ajout au `CLI_HANDLERS` dans `main.py`
- Sous-commandes : `jupiter plugins list|info|enable|disable|status`
- Arguments : `--json` pour sortie JSON, `plugin_id` pour info/enable/disable
