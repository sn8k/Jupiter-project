# Manuel utilisateur — Jupiter (v1.8.5)

Ce manuel explique comment installer, configurer et utiliser Jupiter via l’interface Web et la CLI. Il reflète l’état actuel du code (CLI, API FastAPI, Web UI et plugins).

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
```

(*) `--ignore` peut être spécifié plusieurs fois pour ignorer plusieurs patterns.

`scan`, `analyze` et `ci` partagent le même pipeline (plugins, cache, snapshots) pour assurer un comportement uniforme.

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
