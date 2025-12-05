# Manuel utilisateur — Jupiter (v1.8.49)

Ce manuel explique comment installer, configurer et utiliser Jupiter via l'interface Web et la CLI. Il reflète l'état actuel du code (CLI, API FastAPI, Web UI et plugins Bridge v2).

> Note roadmap : la transition vers un stockage SQL géré automatiquement (init/migrations/backup) est planifiée dans `TODOs/sql_migration_roadmap.md`. Les workflows actuels restent supportés en mode fichier pendant la migration.

## Prérequis
- Python 3.10+
- Accès en lecture au projet à analyser
- `pip install -r requirements.txt` (ou utilisez l’exécutable Windows)

## Installation & lancement (GUI par défaut)

### Windows (packagé)
Double-cliquez sur `jupiter.exe`. Le navigateur s’ouvre automatiquement.

### Windows (sources)
Double-cliquez sur `Jupiter UI.cmd`. Le script crée/active l’environnement virtuel, installe les dépendances si besoin, démarre l’API et la Web UI.

### Linux/macOS/WSL (développeur)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m jupiter.cli.main             # lance l’API + l’UI et ouvre le navigateur
```

## Gestion des projets (registre multi-projets)

- Le projet actif est lu depuis `~/.jupiter/global_config.yaml` (fallback `global.yaml`) et synchronisé avec `~/.jupiter/state.json`.
- La page **Projects** de la Web UI permet d’ajouter, d’activer ou de supprimer un projet sans redémarrer.
- Les chemins hérités sont normalisés en `<projet>.jupiter.yaml` et stockés en absolu pour éviter les incohérences.

## Flux utilisateur Web UI

1. Lancer Jupiter (commande ci-dessus ou script Windows).
2. Sélectionner ou enregistrer un projet dans **Projects**.
3. Lancer un **Scan** (options ignore globs, hidden, incremental, snapshot label).
4. Consulter le **Dashboard** (résumé, hotspots, plugins), la **History** (snapshots list/diff) et le **Code Quality** (duplication/complexité, liens manuels).
5. Ajuster la configuration dans **Settings** :
   - Logs : niveau (Debug/Info/Warning/Error/Critical) et chemin de fichier.
   - Sécurité : token(s) API, restrictions d’exécution.
   - Plugins : cartes dédiées (Notifications webhook, Code Quality, Live Map, Watchdog, Bridge, Settings Update).
   - Meeting : état de licence, bouton de rafraîchissement.

> Cache navigateur : la Web UI est servie avec `Cache-Control: no-store` / `Pragma: no-cache`. Aucun rafraîchissement forcé n'est requis ; désactivez le cache d'un proxy en amont si vous en utilisez un.

## Commandes CLI principales

```bash
python -m jupiter.cli.main scan [root] [--ignore GLOB]* [--show-hidden] [--incremental] [--no-cache] [--no-snapshot] [--snapshot-label TXT] [--output report.json] [--perf]
python -m jupiter.cli.main analyze [root] [--json] [--top N] [--ignore GLOB]* [--show-hidden] [--incremental] [--no-cache] [--perf]
python -m jupiter.cli.main ci [root] [--json] [--fail-on-complexity N] [--fail-on-duplication N] [--fail-on-unused N]
python -m jupiter.cli.main snapshots list|show|diff [args]
python -m jupiter.cli.main simulate remove <chemin|chemin::fonction> [root] [--json]
python -m jupiter.cli.main server [root] [--host HOST] [--port PORT]
python -m jupiter.cli.main gui [root] [--host HOST] [--port PORT]
python -m jupiter.cli.main run <commande> [root] [--with-dynamic]
python -m jupiter.cli.main watch [root]
python -m jupiter.cli.main meeting check-license [root] [--json]
python -m jupiter.cli.main autodiag [root] [--api-url URL] [--diag-url URL] [--skip-cli] [--skip-api] [--skip-plugins] [--timeout SECONDS]
python -m jupiter.cli.main update <source> [--force]
python -m jupiter.cli.main plugins <subcommand> [args]
```

(*) `--ignore` peut être spécifié plusieurs fois pour ignorer plusieurs patterns.

`scan`, `analyze` et `ci` partagent le même pipeline (plugins, cache, snapshots) pour assurer un comportement uniforme.

## Gestion des plugins (CLI)

Jupiter offre une gestion complète des plugins via la CLI :

```bash
# Lister les plugins installés
jupiter plugins list [--json]

# Informations sur un plugin
jupiter plugins info <id> [--json]

# Activer/Désactiver un plugin
jupiter plugins enable <id>
jupiter plugins disable <id>

# Statut du système Bridge
jupiter plugins status [--json]

# Installation de plugins
jupiter plugins install <source> [--force] [--install-deps] [--dry-run]
# <source> peut être : chemin local, URL ZIP, URL Git (.git)

# Mise à jour de plugins
jupiter plugins update <id> [--source URL] [--force] [--install-deps] [--no-backup]
jupiter plugins check-updates [--json]

# Désinstallation
jupiter plugins uninstall <id> [--force]

# Création de plugin (scaffold)
jupiter plugins scaffold <id> [--output DIR]

# Hot reload (mode développeur uniquement)
jupiter plugins reload <id>

# Signature et vérification
jupiter plugins sign <path> [--signer-id ID] [--signer-name NAME] [--trust-level LEVEL]
jupiter plugins verify <path> [--require-level LEVEL]

# Gestion des jobs (tâches longues)
jupiter plugins jobs [--json]                 # Lister les jobs actifs
jupiter plugins jobs <job_id>                 # Détails d'un job
jupiter plugins jobs cancel <job_id>          # Annuler un job
```

## Mode développeur

Le mode développeur (`developer_mode: true` dans `global_config.yaml`) active des fonctionnalités avancées :

- **Hot Reload** : rechargement de plugins sans redémarrer Jupiter
- **Plugins non signés** : acceptés sans confirmation
- **Logs verbeux** : niveau DEBUG par défaut
- **Endpoints debug** : routes de diagnostic supplémentaires

**Note** : Le hot reload (`jupiter plugins reload <id>`) nécessite le mode développeur. En production, cette commande échoue avec un message explicatif.

## Snapshots & cache

- Rapport courant : `.jupiter/cache/last_scan.json`.
- Snapshots : `.jupiter/snapshots/scan-*.json` (désactiver avec `--no-snapshot`, libellé via `--snapshot-label`).
- Consultation : CLI (`snapshots list|show|diff`), API (`/snapshots`, `/snapshots/{id}`, `/snapshots/diff`), Web UI (History).

## Simulation d’impact

`simulate remove` (CLI ou `/simulate/remove`) estime les imports cassés et les fonctions touchées avant une suppression réelle.

## Sécurité et exécution de commandes

- Définir `security.token` ou des utilisateurs avec rôles dans `<projet>.jupiter.yaml`.
- Désactiver ou restreindre l’exécution via `security.allow_run` et `security.allowed_commands` (affecte `/run` et la CLI `run`).
- WebSocket `/ws` accepte le token en paramètre quand la sécurité est activée.

## Meeting (licence optionnelle)

- Ajoutez `deviceKey` dans `~/.jupiter/global_config.yaml` pour activer la vérification.
- CLI : `meeting check-license` ; API : `/license/status`, `/license/refresh`.
- En mode non licencié, Jupiter fonctionne en mode restreint (période limitée).

## Plugins fournis

- **Code Quality** : duplication/complexité, exports, liens manuels (`/plugins/code_quality/manual-links`).
- **Live Map** : graphes de dépendances, config via `/plugins/livemap/config`.
- **Notifications webhook** : envoi d’événements scan/analyze/CI.
- **Pylance analyzer** : diagnostics Python (explicite quand aucun fichier `.py`).
- **AI Helper** : suggestions de duplication avec preuves fichier:ligne.
- **Watchdog** : rechargement automatique des plugins modifiés.
- **Bridge** : passerelle de services (scan/cache/events/config/historique).
- **Settings Update** : support de mise à jour des paramètres via archive.

## Points de terminaison API (résumé)

- Base : `http://127.0.0.1:8000`
- Auth : `/login`, `/users`, `/me` (tokens/roles).
- Scan/Analyse/CI : `/scan` (POST), `/analyze` (GET), `/ci` (POST), `/reports/last`.
- Snapshots : `/snapshots`, `/snapshots/{id}`, `/snapshots/diff`.
- Simulation : `/simulate/remove`.
- Projets & config : `/projects`, `/projects/{id}/activate`, `/config`, `/config/root`, `/config/raw`, `/backends`, `/project/root-entries`.
- Plugins : `/plugins`, `/plugins/{name}/toggle|config|test`, `/plugins/code_quality/manual-links`, `/plugins/livemap/*`, `/plugins/watchdog/*`, `/plugins/bridge/*`, `/plugins/settings_update/*`.
- Meeting : `/license/status`, `/license/refresh`.
- Watch : `/watch/start|stop|status|calls`, `/watch/calls/reset`.
- Système : `/health`, `/metrics`, `/fs/list`, `/update`, `/run`.

Consultez `docs/api.md` pour les payloads détaillés, les rôles requis et des exemples `curl`.
