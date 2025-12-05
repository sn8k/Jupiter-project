# Jupiter Plugin Developer Guide

Version: 1.0.0

Ce guide complet explique comment créer, développer et distribuer des plugins pour Jupiter en utilisant l'architecture Bridge v2.

## Table des matières

1. [Introduction](#1-introduction)
2. [Démarrage rapide](#2-démarrage-rapide)
3. [Architecture des plugins](#3-architecture-des-plugins)
4. [Le manifest (plugin.yaml)](#4-le-manifest-pluginyaml)
5. [Développement du plugin](#5-développement-du-plugin)
6. [Services du Bridge](#6-services-du-bridge)
7. [Contributions CLI](#7-contributions-cli)
8. [Contributions API](#8-contributions-api)
9. [Contributions WebUI](#9-contributions-webui)
10. [Jobs asynchrones](#10-jobs-asynchrones)
11. [Permissions et sécurité](#11-permissions-et-sécurité)
12. [Tests](#12-tests)
13. [Distribution](#13-distribution)
14. [Mode développeur](#14-mode-développeur)
15. [Référence API](#15-référence-api)

---

## 1. Introduction

### 1.1 Qu'est-ce qu'un plugin Jupiter ?

Un plugin Jupiter étend les fonctionnalités de Jupiter en ajoutant :
- **Analyses** : Nouveaux types d'analyse de code
- **Commandes CLI** : Nouvelles commandes en ligne de commande
- **Endpoints API** : Nouvelles routes REST
- **Panneaux WebUI** : Nouvelles interfaces utilisateur

### 1.2 Types de plugins

| Type | Description | Healthcheck | Désactivable |
|------|-------------|-------------|--------------|
| `core` | Plugins système essentiels | Optionnel | Non |
| `system` | Plugins importants mais non essentiels | Obligatoire | Oui |
| `tool` | Outils additionnels | Optionnel | Oui |

### 1.3 Prérequis

- Jupiter v0.25.0 ou supérieur
- Python 3.10+
- Connaissance basique de Python et de la structure Jupiter

---

## 2. Démarrage rapide

### 2.1 Créer un plugin avec le scaffold

Le moyen le plus simple de créer un plugin est d'utiliser la commande scaffold :

```bash
# Créer un plugin basique
jupiter plugins scaffold mon_plugin

# Créer un plugin avec interface WebUI
jupiter plugins scaffold mon_plugin --with-ui

# Spécifier le répertoire de sortie
jupiter plugins scaffold mon_plugin --output ./mes-plugins
```

Cela génère la structure complète du plugin avec :
- `manifest.json` : Configuration du plugin
- `plugin.py` : Code principal
- `README.md` : Documentation

### 2.2 Structure générée

```
mon_plugin/
├── manifest.json     # Identité et configuration
├── plugin.py         # Code principal
└── README.md         # Documentation
```

### 2.3 Premier test

```bash
# Installer le plugin
jupiter plugins install ./mon_plugin

# Vérifier qu'il est chargé
jupiter plugins list

# Voir les détails
jupiter plugins info mon_plugin
```

---

## 3. Architecture des plugins

### 3.1 Structure complète

Un plugin v2 complet a la structure suivante :

```
mon_plugin/
├── plugin.yaml           # Manifest (ou manifest.json)
├── __init__.py           # Point d'entrée principal
├── config.yaml           # Configuration par défaut (optionnel)
├── requirements.txt      # Dépendances Python (optionnel)
├── server/               # Contributions API
│   └── api.py
├── cli/                  # Contributions CLI
│   └── commands.py
├── core/                 # Logique métier
│   └── logic.py
├── web/                  # Contributions WebUI
│   ├── panels/
│   │   └── main.js
│   └── lang/
│       ├── en.json
│       └── fr.json
└── tests/
    └── test_plugin.py
```

### 3.2 Cycle de vie

1. **Discovery** : Le Bridge scanne le répertoire plugins et lit les manifests
2. **Validation** : Vérification du manifest et des permissions
3. **Load** : Import du module Python
4. **Initialize** : Appel de `init()` avec les services
5. **Register** : Enregistrement des contributions (CLI, API, UI)
6. **Ready** : Plugin opérationnel

### 3.3 États possibles

| État | Description |
|------|-------------|
| `discovered` | Manifest lu, pas encore chargé |
| `loading` | En cours de chargement |
| `ready` | Opérationnel |
| `error` | Erreur lors du chargement |
| `disabled` | Désactivé par l'utilisateur |

---

## 4. Le manifest (plugin.yaml)

### 4.1 Manifest minimal

```yaml
id: mon_plugin
name: Mon Plugin
version: 1.0.0
description: Un plugin exemple
type: tool
entrypoints:
  main: __init__.py
```

### 4.2 Manifest complet

```yaml
id: mon_plugin
name: Mon Plugin
version: 1.0.0
description: Un plugin exemple pour Jupiter
author: Votre Nom
homepage: https://github.com/vous/mon-plugin
repository: https://github.com/vous/mon-plugin.git
license: MIT

type: tool
jupiter_version: ">=0.25.0"

entrypoints:
  main: __init__.py
  api: server/api.py
  cli: cli/commands.py

permissions:
  - fs_read
  - network_outbound

capabilities:
  health:
    enabled: true
    interval: 60
  metrics:
    enabled: true
  ui:
    panels:
      - id: main
        route: /plugins/mon_plugin
        title_key: plugin.mon_plugin.panel_title
        mount_point: plugin-container
    settings_frame: true
  jobs:
    timeout: 300
    max_concurrent: 2

config_schema:
  schema:
    type: object
    properties:
      enabled:
        type: boolean
        default: true
        description: Activer le plugin
      api_key:
        type: string
        description: Clé API externe
        format: password

i18n:
  default_lang: en
  supported:
    - en
    - fr

dependencies:
  - requests>=2.28.0
  - pyyaml>=6.0
```

### 4.3 Permissions disponibles

| Permission | Description |
|------------|-------------|
| `fs_read` | Lecture de fichiers du projet |
| `fs_write` | Écriture de fichiers |
| `run_commands` | Exécution de commandes shell |
| `network_outbound` | Requêtes réseau sortantes |
| `access_meeting` | Accès au service Meeting |
| `config_access` | Accès à la configuration globale |
| `emit_events` | Émission d'événements sur le bus |

---

## 5. Développement du plugin

### 5.1 Point d'entrée (`__init__.py`)

```python
"""Mon Plugin pour Jupiter.

Version: 1.0.0
"""

from typing import Any, Dict, Optional

# État global du plugin
_services = None
_logger = None
_config = None


def init(services) -> bool:
    """Initialiser le plugin.
    
    Args:
        services: ServiceLocator fourni par le Bridge
        
    Returns:
        True si l'initialisation réussit
    """
    global _services, _logger, _config
    
    _services = services
    _logger = services.get_logger("mon_plugin")
    _config = services.get_config("mon_plugin")
    
    _logger.info("Plugin initialisé avec succès")
    return True


def health() -> Dict[str, Any]:
    """Vérifier l'état de santé du plugin.
    
    Returns:
        Dict avec status, message, et détails optionnels
    """
    return {
        "status": "healthy",
        "message": "Plugin opérationnel",
        "details": {
            "version": "1.0.0",
        }
    }


def metrics() -> Dict[str, Any]:
    """Retourner les métriques du plugin.
    
    Returns:
        Dict avec les métriques d'utilisation
    """
    return {
        "executions": 0,
        "errors": 0,
        "last_execution": None,
        "avg_duration_ms": 0,
    }


def reset_settings() -> bool:
    """Réinitialiser les paramètres aux valeurs par défaut.
    
    Returns:
        True si la réinitialisation réussit
    """
    global _config
    # Recharger la config par défaut
    if _services:
        _config = _services.get_config("mon_plugin", use_defaults=True)
    return True


# Hooks d'analyse (optionnels)
def on_scan(report: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Hook appelé après un scan.
    
    Args:
        report: Rapport de scan complet
        
    Returns:
        Données supplémentaires à ajouter au rapport
    """
    if _logger:
        _logger.debug("Scan reçu avec %d fichiers", len(report.get("files", [])))
    return None


def on_analyze(summary: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Hook appelé après une analyse.
    
    Args:
        summary: Résumé d'analyse
        
    Returns:
        Données supplémentaires à ajouter au résumé
    """
    return None
```

### 5.2 Logique métier (`core/logic.py`)

Isolez votre logique métier dans un module séparé :

```python
"""Logique métier de mon plugin."""

from typing import List, Dict, Any


def process_files(files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Traiter une liste de fichiers.
    
    Args:
        files: Liste des fichiers à traiter
        
    Returns:
        Résultats du traitement
    """
    results = []
    for file in files:
        # Votre logique ici
        result = analyze_file(file)
        results.append(result)
    
    return {
        "total": len(files),
        "processed": len(results),
        "results": results,
    }


def analyze_file(file: Dict[str, Any]) -> Dict[str, Any]:
    """Analyser un fichier individuel."""
    return {
        "path": file.get("path"),
        "status": "ok",
    }
```

---

## 6. Services du Bridge

Le Bridge fournit des services aux plugins via le `ServiceLocator`.

### 6.1 Logger

```python
logger = services.get_logger("mon_plugin")
logger.debug("Message de debug")
logger.info("Information")
logger.warning("Avertissement")
logger.error("Erreur")
```

Le logger préfixe automatiquement les messages avec `[plugin:mon_plugin]`.

### 6.2 Configuration

```python
# Obtenir la configuration fusionnée (global + projet)
config = services.get_config("mon_plugin")

# Valeurs avec défauts
enabled = config.get("enabled", True)
api_key = config.get("api_key")
```

### 6.3 Runner (exécution de commandes)

```python
# Obtenir le runner sécurisé
runner = services.get_runner()

# Exécuter une commande (vérifie les permissions)
result = await runner.run("python --version", timeout=30)

if result.success:
    print(result.stdout)
else:
    print(f"Erreur: {result.stderr}")
```

### 6.4 Event Bus

```python
# Obtenir le bus d'événements
event_bus = services.get_event_bus()

# S'abonner à un événement
def on_scan_complete(data):
    print(f"Scan terminé: {data}")

event_bus.subscribe("scan.complete", on_scan_complete)

# Émettre un événement (nécessite permission emit_events)
event_bus.emit("mon_plugin.action", {"key": "value"})
```

### 6.5 History Manager

```python
history = services.get_history()

# Lister les snapshots
snapshots = history.list_snapshots()

# Obtenir un snapshot
snapshot = history.get_snapshot("scan-20240101-120000")

# Comparer deux snapshots
diff = history.diff("snapshot1", "snapshot2")
```

---

## 7. Contributions CLI

### 7.1 Définir des commandes (`cli/commands.py`)

```python
"""Commandes CLI de mon plugin."""

from typing import Any


def register_cli_contribution(subparsers) -> None:
    """Enregistrer les commandes CLI.
    
    Args:
        subparsers: Sous-parsers argparse
    """
    # Créer le groupe de commandes
    parser = subparsers.add_parser(
        "monplugin",
        help="Commandes de mon plugin"
    )
    
    sub = parser.add_subparsers(dest="monplugin_command")
    
    # Commande: monplugin run
    run_cmd = sub.add_parser("run", help="Exécuter une action")
    run_cmd.add_argument("target", help="Cible de l'action")
    run_cmd.add_argument("--verbose", "-v", action="store_true")
    
    # Commande: monplugin status
    sub.add_parser("status", help="Afficher le statut")


def handle_command(args) -> int:
    """Gérer l'exécution des commandes.
    
    Args:
        args: Arguments parsés
        
    Returns:
        Code de retour (0 = succès)
    """
    if args.monplugin_command == "run":
        return handle_run(args)
    elif args.monplugin_command == "status":
        return handle_status(args)
    return 1


def handle_run(args) -> int:
    """Gérer la commande 'run'."""
    target = args.target
    verbose = args.verbose
    
    print(f"Exécution sur {target}...")
    # Votre logique ici
    
    return 0


def handle_status(args) -> int:
    """Gérer la commande 'status'."""
    print("Statut: OK")
    return 0
```

### 7.2 Usage

```bash
jupiter monplugin run ./src --verbose
jupiter monplugin status
```

---

## 8. Contributions API

### 8.1 Définir des routes (`server/api.py`)

```python
"""Routes API de mon plugin."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional


router = APIRouter(prefix="/monplugin", tags=["mon-plugin"])


class ActionRequest(BaseModel):
    target: str
    options: Optional[dict] = None


class ActionResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


@router.get("/status")
async def get_status():
    """Obtenir le statut du plugin."""
    return {"status": "ok", "version": "1.0.0"}


@router.post("/action", response_model=ActionResponse)
async def run_action(request: ActionRequest):
    """Exécuter une action."""
    try:
        # Votre logique ici
        result = process_action(request.target, request.options)
        return ActionResponse(
            success=True,
            message="Action exécutée",
            data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def register_api_contribution(app, bridge) -> None:
    """Enregistrer les routes API.
    
    Args:
        app: Instance FastAPI
        bridge: Instance du Bridge
    """
    app.include_router(router)


def process_action(target: str, options: dict) -> dict:
    """Traiter l'action."""
    return {"processed": target}
```

### 8.2 Usage

```bash
# GET status
curl http://localhost:8000/monplugin/status

# POST action
curl -X POST http://localhost:8000/monplugin/action \
  -H "Content-Type: application/json" \
  -d '{"target": "./src"}'
```

---

## 9. Contributions WebUI

### 9.1 Panneau principal (`web/panels/main.js`)

```javascript
/**
 * Panneau principal de mon plugin.
 * Version: 1.0.0
 */

// État du panneau
let bridge = null;
let container = null;

/**
 * Monter le panneau dans le conteneur.
 * @param {HTMLElement} containerEl - Conteneur cible
 * @param {Object} bridgeApi - API du bridge (window.jupiterBridge)
 */
export function mount(containerEl, bridgeApi) {
    bridge = bridgeApi;
    container = containerEl;
    
    render();
    loadData();
}

/**
 * Démonter le panneau.
 * @param {HTMLElement} containerEl - Conteneur
 */
export function unmount(containerEl) {
    containerEl.innerHTML = '';
    bridge = null;
    container = null;
}

function render() {
    container.innerHTML = `
        <div class="plugin-panel">
            <h2>${bridge.i18n.t('plugin.mon_plugin.title')}</h2>
            <div class="plugin-content">
                <div id="status-card" class="card">
                    <h3>${bridge.i18n.t('plugin.mon_plugin.status')}</h3>
                    <div id="status-content">Chargement...</div>
                </div>
                <div class="actions">
                    <button id="run-btn" class="btn btn-primary">
                        ${bridge.i18n.t('plugin.mon_plugin.run_action')}
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // Event listeners
    container.querySelector('#run-btn').addEventListener('click', runAction);
}

async function loadData() {
    try {
        const data = await bridge.api.get('/monplugin/status');
        document.getElementById('status-content').textContent = 
            `Status: ${data.status}`;
    } catch (error) {
        bridge.notify.error('Erreur de chargement');
    }
}

async function runAction() {
    try {
        const result = await bridge.api.post('/monplugin/action', {
            target: './src'
        });
        bridge.notify.success(result.message);
    } catch (error) {
        bridge.notify.error(error.message);
    }
}
```

### 9.2 Traductions (`web/lang/en.json`)

```json
{
    "plugin.mon_plugin.title": "My Plugin",
    "plugin.mon_plugin.status": "Status",
    "plugin.mon_plugin.run_action": "Run Action",
    "plugin.mon_plugin.success": "Action completed successfully",
    "plugin.mon_plugin.error": "An error occurred"
}
```

### 9.3 Traductions (`web/lang/fr.json`)

```json
{
    "plugin.mon_plugin.title": "Mon Plugin",
    "plugin.mon_plugin.status": "Statut",
    "plugin.mon_plugin.run_action": "Exécuter l'action",
    "plugin.mon_plugin.success": "Action terminée avec succès",
    "plugin.mon_plugin.error": "Une erreur s'est produite"
}
```

---

## 10. Jobs asynchrones

Pour les tâches longues, utilisez le système de jobs.

### 10.1 Soumettre un job

```python
async def start_long_task(params: dict) -> str:
    """Démarrer une tâche longue.
    
    Returns:
        ID du job
    """
    from jupiter.core.bridge import get_job_manager
    
    job_manager = get_job_manager()
    job_id = await job_manager.submit(
        plugin_id="mon_plugin",
        handler=process_long_task,
        params=params,
        description="Traitement de fichiers"
    )
    return job_id


async def process_long_task(job, params):
    """Handler du job.
    
    Args:
        job: Objet Job avec méthodes de contrôle
        params: Paramètres du job
    """
    files = params.get("files", [])
    total = len(files)
    
    for i, file in enumerate(files):
        # Vérifier annulation
        if job.is_cancelled():
            return {"status": "cancelled", "processed": i}
        
        # Traiter le fichier
        await process_file(file)
        
        # Mettre à jour la progression
        job.update_progress(
            progress=((i + 1) / total) * 100,
            message=f"Traitement {i + 1}/{total}"
        )
    
    return {"status": "completed", "processed": total}
```

### 10.2 API Jobs

```python
# Route pour soumettre un job
@router.post("/jobs")
async def submit_job(request: Request):
    job_id = await start_long_task(request.json())
    return {"job_id": job_id}

# Route pour obtenir le statut
@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    job_manager = get_job_manager()
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job.to_dict()

# Route pour annuler
@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    job_manager = get_job_manager()
    success = job_manager.cancel(job_id)
    return {"cancelled": success}
```

---

## 11. Permissions et sécurité

### 11.1 Déclarer les permissions

Dans le manifest :

```yaml
permissions:
  - fs_read       # Lecture de fichiers
  - fs_write      # Écriture de fichiers
  - run_commands  # Exécution de commandes
  - network_outbound  # Requêtes HTTP sortantes
```

### 11.2 Vérification runtime

```python
from jupiter.core.bridge.permissions import require_permission, Permission

@require_permission(Permission.RUN_COMMANDS)
async def run_shell_command(cmd: str):
    """Cette fonction nécessite la permission run_commands."""
    runner = services.get_runner()
    return await runner.run(cmd)
```

### 11.3 Signature du plugin

Pour distribuer votre plugin de manière sécurisée :

```bash
# Signer le plugin
jupiter plugins sign ./mon_plugin \
    --signer-id "votre-id" \
    --signer-name "Votre Nom" \
    --trust-level community

# Vérifier la signature
jupiter plugins verify ./mon_plugin
```

---

## 12. Tests

### 12.1 Tests unitaires (`tests/test_plugin.py`)

```python
"""Tests unitaires de mon plugin."""

import pytest
from unittest.mock import Mock, patch


class TestPlugin:
    """Tests du plugin principal."""
    
    def test_init_success(self):
        """Test d'initialisation réussie."""
        from mon_plugin import init
        
        mock_services = Mock()
        mock_services.get_logger.return_value = Mock()
        mock_services.get_config.return_value = {}
        
        result = init(mock_services)
        
        assert result is True
        mock_services.get_logger.assert_called_once_with("mon_plugin")
    
    def test_health_returns_healthy(self):
        """Test de health check."""
        from mon_plugin import health
        
        result = health()
        
        assert result["status"] == "healthy"
        assert "message" in result


class TestLogic:
    """Tests de la logique métier."""
    
    def test_process_files_empty(self):
        """Test avec liste vide."""
        from mon_plugin.core.logic import process_files
        
        result = process_files([])
        
        assert result["total"] == 0
        assert result["processed"] == 0
    
    def test_process_files_with_data(self):
        """Test avec des fichiers."""
        from mon_plugin.core.logic import process_files
        
        files = [
            {"path": "file1.py"},
            {"path": "file2.py"},
        ]
        
        result = process_files(files)
        
        assert result["total"] == 2
        assert result["processed"] == 2
```

### 12.2 Exécuter les tests

```bash
# Depuis le répertoire du plugin
pytest tests/ -v

# Avec couverture
pytest tests/ --cov=. --cov-report=html
```

---

## 13. Distribution

### 13.1 Préparer le plugin

1. **Mettre à jour le manifest** avec la bonne version
2. **Écrire le changelog**
3. **Tester complètement**
4. **Signer le plugin**

### 13.2 Installation

```bash
# Depuis un répertoire local
jupiter plugins install ./mon_plugin

# Depuis une URL ZIP
jupiter plugins install https://example.com/mon_plugin.zip

# Depuis un repo Git
jupiter plugins install https://github.com/vous/mon-plugin.git

# Avec les dépendances
jupiter plugins install ./mon_plugin --install-deps

# Mode simulation
jupiter plugins install ./mon_plugin --dry-run
```

### 13.3 Mise à jour

```bash
# Mettre à jour depuis la source
jupiter plugins update mon_plugin --source https://github.com/vous/mon-plugin.git

# Forcer la mise à jour
jupiter plugins update mon_plugin --force

# Vérifier les mises à jour disponibles
jupiter plugins check-updates
```

### 13.4 Désinstallation

```bash
jupiter plugins uninstall mon_plugin
```

---

## 14. Mode développeur

### 14.1 Activer le mode développeur

Dans `global_config.yaml` ou via l'API :

```yaml
developer_mode: true
```

### 14.2 Hot Reload

```bash
# Recharger un plugin sans redémarrer
jupiter plugins reload mon_plugin
```

Ou via l'API :
```bash
curl -X POST http://localhost:8000/plugins/v2/mon_plugin/reload
```

En mode développeur :
- Les plugins non signés sont acceptés
- Le hot reload est disponible
- Les logs sont plus verbeux

---

## 15. Référence API

### 15.1 ServiceLocator

| Méthode | Description |
|---------|-------------|
| `get_logger(plugin_id)` | Logger préconfiguré |
| `get_config(plugin_id)` | Configuration fusionnée |
| `get_runner()` | Runner sécurisé |
| `get_event_bus()` | Bus d'événements |
| `get_history()` | HistoryManager |
| `get_graph()` | GraphManager |
| `get_project_manager()` | ProjectManager |

### 15.2 Hooks disponibles

| Hook | Quand | Arguments |
|------|-------|-----------|
| `init(services)` | Initialisation | ServiceLocator |
| `health()` | Health check | - |
| `metrics()` | Collecte métriques | - |
| `reset_settings()` | Reset config | - |
| `on_scan(report)` | Après scan | Report dict |
| `on_analyze(summary)` | Après analyse | Summary dict |

### 15.3 window.jupiterBridge (WebUI)

| API | Description |
|-----|-------------|
| `api.get(path)` | GET request |
| `api.post(path, data)` | POST request |
| `ws.connect(path)` | WebSocket |
| `events.subscribe(topic, cb)` | Subscribe to events |
| `i18n.t(key)` | Translation |
| `notify.info(msg)` | Notification info |
| `notify.success(msg)` | Notification success |
| `notify.error(msg)` | Notification error |
| `modal.show(options)` | Show modal |

---

## Ressources

- [Architecture des plugins](plugins_architecture.md)
- [Guide de migration v1→v2](PLUGIN_MIGRATION_GUIDE.md)
- [Plugin modèle](plugin_model/)
- [API REST Jupiter](api.md)

---

© Jupiter Project
