# Plugin Migration Guide

Version: 0.1.0

Ce guide explique comment migrer un plugin Jupiter v1 vers l'architecture v2 utilisant le Bridge.

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Différences v1 vs v2](#2-différences-v1-vs-v2)
3. [Structure d'un plugin v2](#3-structure-dun-plugin-v2)
4. [Création du manifest](#4-création-du-manifest)
5. [Migration du code](#5-migration-du-code)
6. [Enregistrement des contributions](#6-enregistrement-des-contributions)
7. [Adaptateur legacy](#7-adaptateur-legacy)
8. [Tests et validation](#8-tests-et-validation)
9. [Exemples complets](#9-exemples-complets)

---

## 1. Vue d'ensemble

### 1.1 Pourquoi migrer ?

L'architecture v2 des plugins offre :
- **Meilleure isolation** : Plugins sandboxés avec permissions explicites
- **UI standardisée** : Intégration native dans la WebUI
- **Hot reload** : Rechargement sans redémarrage de Jupiter
- **Monitoring** : Health checks et métriques intégrés
- **Marketplace** : Distribution facilitée via le registre

### 1.2 Compatibilité

Durant la période de transition :
- Les plugins v1 continuent de fonctionner via l'adaptateur legacy
- L'adaptateur applique des permissions restrictives par défaut
- Les plugins v1 sont marqués `legacy: true` dans l'API

---

## 2. Différences v1 vs v2

### 2.1 Structure des fichiers

**v1 (actuel)** :
```
jupiter/plugins/
└── my_plugin.py          # Tout dans un seul fichier
```

**v2 (nouveau)** :
```
jupiter/plugins/my_plugin/
├── plugin.yaml           # Manifest (nouveau)
├── __init__.py           # Point d'entrée
├── config.yaml           # Config par défaut (optionnel)
├── server/               # Routes API (optionnel)
│   └── api.py
├── cli/                  # Commandes CLI (optionnel)
│   └── commands.py
├── web/                  # Assets WebUI (optionnel)
│   ├── panels/
│   │   └── main.js
│   └── lang/
│       ├── en.json
│       └── fr.json
└── tests/                # Tests unitaires
    └── test_plugin.py
```

### 2.2 Interfaces

**v1** :
```python
class MyPlugin:
    name = "my_plugin"
    version = "1.0.0"
    description = "..."
    
    def on_scan(self, report): ...
    def on_analyze(self, summary): ...
    def configure(self, config): ...
```

**v2** :
```python
from jupiter.core.bridge import IPlugin, IPluginHealth

class MyPlugin(IPlugin):
    def __init__(self):
        self._manifest = PluginManifest.from_yaml("plugin.yaml")
    
    @property
    def manifest(self):
        return self._manifest
    
    def init(self, services):
        # Accès aux services via Bridge
        self.logger = services.get_logger(self.manifest.id)
        self.config = services.get_config(self.manifest.id)
    
    def shutdown(self):
        # Nettoyage des ressources
        pass
```

### 2.3 Hooks vs Events

**v1** : Hooks appelés directement
```python
def on_scan(self, report):
    # Modifie report directement
    report["plugins_data"]["my_plugin"] = {...}
```

**v2** : Events pub/sub
```python
def init(self, services):
    self.events = services.get_event_bus()
    self.events.subscribe("SCAN_FINISHED", self.handle_scan)

def handle_scan(self, topic, payload):
    # Traite l'événement
    self.events.emit("PLUGIN_DATA_READY", {
        "plugin_id": self.manifest.id,
        "data": {...}
    })
```

---

## 3. Structure d'un plugin v2

### 3.1 Fichiers requis

| Fichier | Obligatoire | Description |
|---------|-------------|-------------|
| `plugin.yaml` | ✅ | Manifest décrivant le plugin |
| `__init__.py` | ✅ | Point d'entrée avec classe principale |
| `config.yaml` | ❌ | Configuration par défaut |
| `changelog.md` | ❌ | Historique des versions |
| `README.md` | ❌ | Documentation du plugin |

### 3.2 Fichiers optionnels

```
server/api.py        # Routes FastAPI
cli/commands.py      # Commandes argparse/typer
web/panels/*.js      # Panneaux WebUI
web/lang/*.json      # Traductions i18n
tests/               # Tests unitaires
```

---

## 4. Création du manifest

### 4.1 Manifest minimal

```yaml
# plugin.yaml
id: my_plugin
name: My Plugin
version: 1.0.0
description: A sample Jupiter plugin
type: tool
jupiter_version: ">=1.0.0"
```

### 4.2 Manifest complet

```yaml
id: my_plugin
name: My Plugin
version: 1.0.0
description: A sample Jupiter plugin with all features
type: tool
jupiter_version: ">=1.0.0"

author:
  name: John Doe
  email: john@example.com

license: MIT
trust_level: community

permissions:
  - fs_read
  - emit_events
  - register_api
  - register_ui

dependencies:
  code_quality: ">=0.5.0"

python_dependencies:
  - httpx>=0.24.0

capabilities:
  metrics:
    enabled: true
    export_format: json
  jobs:
    enabled: true
    max_concurrent: 2
    timeout: 300
  health_check:
    enabled: true
    interval: 60

entrypoints:
  init: __init__:MyPlugin.init
  shutdown: __init__:MyPlugin.shutdown
  health: __init__:MyPlugin.health
  metrics: __init__:MyPlugin.metrics

api:
  router: server.api:router
  prefix: /my_plugin
  tags: [my_plugin]

cli:
  commands:
    - name: my-command
      description: Run my plugin
      entrypoint: cli.commands:run

ui:
  panels:
    - id: main
      location: sidebar
      route: /plugins/my_plugin
      title_key: plugin.my_plugin.title
      icon: "🔌"
      order: 50
  i18n:
    path: web/lang
    languages: [en, fr]

config:
  schema:
    type: object
    properties:
      enabled:
        type: boolean
        default: true
      verbose:
        type: boolean
        default: false
  defaults:
    enabled: true
    verbose: false
```

---

## 5. Migration du code

### 5.1 Classe principale

**Avant (v1)** :
```python
class MyPlugin:
    name = "my_plugin"
    version = "1.0.0"
    description = "..."
    
    def __init__(self):
        self.config = {}
    
    def configure(self, config):
        self.config = config
    
    def on_scan(self, report):
        # ...
```

**Après (v2)** :
```python
from jupiter.core.bridge import IPlugin, IPluginHealth, HealthCheckResult, HealthStatus
from jupiter.core.bridge.manifest import PluginManifest

class MyPlugin(IPlugin, IPluginHealth):
    def __init__(self):
        self._manifest = None
        self._services = None
        self._logger = None
    
    @property
    def manifest(self):
        if self._manifest is None:
            self._manifest = PluginManifest.load(__file__)
        return self._manifest
    
    def init(self, services):
        self._services = services
        self._logger = services.get_logger(self.manifest.id)
        self._config = services.get_config(self.manifest.id)
        
        # S'abonner aux événements
        events = services.get_event_bus()
        events.subscribe("SCAN_FINISHED", self._on_scan)
        
        self._logger.info("Plugin initialized")
    
    def shutdown(self):
        self._logger.info("Plugin shutting down")
    
    def health(self) -> HealthCheckResult:
        return HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="Plugin is operational"
        )
    
    def _on_scan(self, topic, payload):
        # Logique de on_scan migrée ici
        report = payload.get("report", {})
        # ...
```

### 5.2 Accès aux services core

**Avant (v1)** : Import direct
```python
from jupiter.core.scanner import scan_project
from jupiter.core.analyzer import analyze
```

**Après (v2)** : Via Service Locator
```python
def init(self, services):
    self.scanner = services.get_service("scanner")
    self.analyzer = services.get_service("analyzer")

def do_something(self, path):
    result = self.scanner.scan(path)
```

---

## 6. Enregistrement des contributions

### 6.1 Routes API

**Fichier** : `server/api.py`
```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def get_status():
    return {"status": "ok"}

@router.post("/analyze")
async def run_analysis(data: dict):
    # ...
```

Le router est automatiquement monté sur `/plugins/my_plugin/`.

### 6.2 Commandes CLI

**Fichier** : `cli/commands.py`
```python
import argparse

def run(args):
    """Execute the plugin command."""
    print(f"Running with: {args}")

def register(subparsers):
    parser = subparsers.add_parser(
        "my-command",
        help="Run my plugin"
    )
    parser.add_argument("--verbose", action="store_true")
    parser.set_defaults(func=run)
```

### 6.3 Panneaux WebUI

**Fichier** : `web/panels/main.js`
```javascript
// Point d'entrée du panneau
export function init(bridge) {
    const container = document.getElementById('plugin-content');
    
    // Utiliser l'API bridge
    bridge.api.get('/my_plugin/status')
        .then(data => {
            container.innerHTML = renderPanel(data);
        });
}

function renderPanel(data) {
    return `
        <div class="plugin-panel">
            <h2>${bridge.i18n.t('plugin.my_plugin.title')}</h2>
            <p>Status: ${data.status}</p>
        </div>
    `;
}
```

---

## 7. Adaptateur legacy

### 7.1 Fonctionnement

L'adaptateur legacy détecte automatiquement les plugins v1 et les wrappe :

```python
# Ce que fait l'adaptateur en interne
class LegacyPluginWrapper(IPlugin):
    def __init__(self, legacy_plugin):
        self._legacy = legacy_plugin
        self._manifest = self._generate_manifest()
    
    def init(self, services):
        if hasattr(self._legacy, 'configure'):
            config = services.get_config(self.manifest.id)
            self._legacy.configure(config)
    
    # Mapping des événements vers hooks
    def _on_scan(self, topic, payload):
        if hasattr(self._legacy, 'on_scan'):
            self._legacy.on_scan(payload['report'])
```

### 7.2 Limitations

Les plugins legacy via l'adaptateur :
- N'ont pas accès aux nouveaux services
- Ne peuvent pas enregistrer de routes API dynamiquement
- Ont des permissions restrictives par défaut
- Sont marqués `legacy: true` dans l'API

---

## 8. Tests et validation

### 8.1 Validation du manifest

```bash
jupiter plugins validate ./my_plugin
```

### 8.2 Tests unitaires

```python
# tests/test_plugin.py
import pytest
from unittest.mock import Mock

from my_plugin import MyPlugin

def test_init():
    plugin = MyPlugin()
    services = Mock()
    services.get_logger.return_value = Mock()
    services.get_config.return_value = {"enabled": True}
    
    plugin.init(services)
    
    assert services.get_logger.called
    assert services.get_config.called

def test_health():
    plugin = MyPlugin()
    plugin.init(Mock())
    
    result = plugin.health()
    
    assert result.status == HealthStatus.HEALTHY
```

### 8.3 Test d'intégration

```bash
# Lancer Jupiter avec le plugin en mode dev
jupiter --dev-mode server

# Dans un autre terminal
curl http://localhost:8000/plugins/my_plugin/status
```

---

## 9. Exemples complets

### 9.1 Plugin minimal

Voir `jupiter/plugins/example_plugin/` pour un exemple minimal migré.

### 9.2 Plugin avec UI

Voir `jupiter/plugins/code_quality/` pour un exemple complet avec :
- Routes API
- Panneau sidebar
- Section settings
- i18n

### 9.3 Plugin système

Voir `jupiter/plugins/settings_update/` pour un plugin système.

---

## Changelog

### 0.1.0
- Création initiale du guide de migration
- Documentation des différences v1/v2
- Exemples de manifest et code migré
