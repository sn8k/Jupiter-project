# Plugin Migration Guide

Version: 0.2.0

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

Cette section contient des exemples détaillés de migration de plugins v1 vers v2.

### 9.1 Exemple : Plugin d'analyse de complexité

#### Plugin v1 (avant migration)

```python
# jupiter/plugins/complexity_analyzer.py
"""
Version: 1.0.0
Plugin d'analyse de complexité cyclomatique.
"""

class ComplexityAnalyzer:
    name = "complexity_analyzer"
    version = "1.0.0"
    description = "Analyse la complexité cyclomatique du code"
    
    def __init__(self):
        self.threshold = 10
        self.results = {}
    
    def configure(self, config):
        """Configure le plugin depuis jupiter.yaml."""
        self.threshold = config.get("complexity_threshold", 10)
    
    def on_scan(self, report):
        """Hook appelé après un scan."""
        files = report.get("files", [])
        for file_info in files:
            if file_info.get("language") == "python":
                complexity = self._analyze_file(file_info["path"])
                self.results[file_info["path"]] = complexity
        
        # Injection directe dans le rapport
        report.setdefault("plugins_data", {})
        report["plugins_data"]["complexity"] = {
            "files": self.results,
            "threshold": self.threshold,
            "warnings": [f for f, c in self.results.items() if c > self.threshold]
        }
    
    def on_analyze(self, summary):
        """Hook appelé après analyse."""
        high_complexity = [f for f, c in self.results.items() if c > self.threshold]
        if high_complexity:
            summary.setdefault("warnings", [])
            summary["warnings"].append({
                "plugin": self.name,
                "message": f"{len(high_complexity)} fichiers dépassent le seuil de complexité"
            })
    
    def _analyze_file(self, path):
        # Logique d'analyse simplifiée
        import ast
        try:
            with open(path) as f:
                tree = ast.parse(f.read())
            return self._count_branches(tree)
        except Exception:
            return 0
    
    def _count_branches(self, node, count=0):
        # Compte simplifié des branches
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                count += 1
        return count
```

#### Plugin v2 (après migration)

**Structure des fichiers:**
```
jupiter/plugins/complexity_analyzer/
├── plugin.yaml           # Manifest v2
├── __init__.py           # Point d'entrée
├── analyzer.py           # Logique métier isolée
├── config.yaml           # Config par défaut
├── server/
│   └── api.py            # Routes API
├── web/
│   ├── panels/
│   │   └── complexity.js # Panneau WebUI
│   └── lang/
│       ├── en.json       # i18n anglais
│       └── fr.json       # i18n français
└── tests/
    └── test_analyzer.py  # Tests unitaires
```

**plugin.yaml:**
```yaml
id: complexity_analyzer
name: Complexity Analyzer
version: 2.0.0
description: Analyse la complexité cyclomatique du code Python

author: Jupiter Team
license: MIT
homepage: https://github.com/jupiter/plugins/complexity

# Version minimale de Jupiter requise
jupiter:
  version: ">=2.0.0"

# Permissions demandées
permissions:
  - fs.read            # Lecture des fichiers sources
  - events.subscribe   # Écoute des événements de scan
  - events.emit        # Émission de résultats

# Points d'entrée
entrypoints:
  init: "__init__:ComplexityPlugin"
  api: "server.api:router"

# Contributions UI
ui:
  panels:
    - id: complexity_panel
      title_key: "complexity.panel_title"
      icon: "chart-bar"
      position: sidebar
      source: "web/panels/complexity.js"

# Configuration par défaut
config:
  defaults:
    threshold: 10
    languages:
      - python
      - javascript
```

**__init__.py:**
```python
"""
Complexity Analyzer Plugin v2

Analyse la complexité cyclomatique du code.
"""

__version__ = "2.0.0"

from typing import Optional
from pathlib import Path

from jupiter.core.bridge import (
    IPlugin, 
    IPluginHealth, 
    IPluginMetrics,
    HealthCheckResult,
    HealthStatus,
    MetricsResult,
)
from jupiter.core.bridge.manifest import PluginManifest

from .analyzer import ComplexityAnalyzer


class ComplexityPlugin(IPlugin, IPluginHealth, IPluginMetrics):
    """Plugin v2 d'analyse de complexité."""
    
    def __init__(self):
        self._manifest: Optional[PluginManifest] = None
        self._services = None
        self._logger = None
        self._config = None
        self._analyzer: Optional[ComplexityAnalyzer] = None
        self._results = {}
        self._scan_count = 0
    
    @property
    def manifest(self) -> PluginManifest:
        if self._manifest is None:
            self._manifest = PluginManifest.load(Path(__file__).parent)
        return self._manifest
    
    def init(self, services) -> None:
        """Initialisation du plugin."""
        self._services = services
        self._logger = services.get_logger(self.manifest.id)
        self._config = services.get_config(self.manifest.id)
        
        # Créer l'analyseur avec la config
        self._analyzer = ComplexityAnalyzer(
            threshold=self._config.get("threshold", 10),
            languages=self._config.get("languages", ["python"])
        )
        
        # S'abonner aux événements (au lieu des hooks directs)
        events = services.get_event_bus()
        events.subscribe("SCAN_FINISHED", self._on_scan_finished)
        events.subscribe("ANALYZE_FINISHED", self._on_analyze_finished)
        
        self._logger.info("ComplexityPlugin initialized")
    
    def shutdown(self) -> None:
        """Nettoyage des ressources."""
        self._logger.info("ComplexityPlugin shutting down")
        self._results.clear()
    
    def health(self) -> HealthCheckResult:
        """Vérification de santé."""
        if self._analyzer is None:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message="Analyzer not initialized"
            )
        return HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="Plugin operational",
            details={
                "threshold": self._config.get("threshold"),
                "files_analyzed": len(self._results)
            }
        )
    
    def metrics(self) -> MetricsResult:
        """Métriques du plugin."""
        return MetricsResult(
            metrics={
                "scans_processed": self._scan_count,
                "files_analyzed": len(self._results),
                "high_complexity_files": len([
                    f for f, c in self._results.items() 
                    if c > self._config.get("threshold", 10)
                ])
            }
        )
    
    def _on_scan_finished(self, topic: str, payload: dict) -> None:
        """Gestionnaire d'événement SCAN_FINISHED."""
        report = payload.get("report", {})
        files = report.get("files", [])
        
        self._scan_count += 1
        self._results.clear()
        
        for file_info in files:
            lang = file_info.get("language", "")
            if lang in self._config.get("languages", ["python"]):
                try:
                    complexity = self._analyzer.analyze_file(file_info["path"])
                    self._results[file_info["path"]] = complexity
                except Exception as e:
                    self._logger.warning(f"Error analyzing {file_info['path']}: {e}")
        
        # Émettre les résultats via event bus
        events = self._services.get_event_bus()
        events.emit("PLUGIN_DATA_READY", {
            "plugin_id": self.manifest.id,
            "data_type": "complexity_analysis",
            "data": {
                "files": self._results,
                "threshold": self._config.get("threshold"),
                "warnings": self._get_warnings()
            }
        })
        
        self._logger.info(f"Analyzed {len(self._results)} files")
    
    def _on_analyze_finished(self, topic: str, payload: dict) -> None:
        """Gestionnaire d'événement ANALYZE_FINISHED."""
        warnings = self._get_warnings()
        if warnings:
            events = self._services.get_event_bus()
            events.emit("ANALYSIS_WARNING", {
                "plugin_id": self.manifest.id,
                "message": f"{len(warnings)} fichiers dépassent le seuil de complexité",
                "details": warnings
            })
    
    def _get_warnings(self) -> list:
        """Retourne la liste des fichiers dépassant le seuil."""
        threshold = self._config.get("threshold", 10)
        return [f for f, c in self._results.items() if c > threshold]
```

**analyzer.py** (logique métier isolée):
```python
"""Logique d'analyse de complexité."""

import ast
from pathlib import Path
from typing import List


class ComplexityAnalyzer:
    """Analyseur de complexité cyclomatique."""
    
    def __init__(self, threshold: int = 10, languages: List[str] = None):
        self.threshold = threshold
        self.languages = languages or ["python"]
    
    def analyze_file(self, path: str) -> int:
        """Analyse un fichier et retourne sa complexité."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        content = path.read_text(encoding="utf-8")
        tree = ast.parse(content)
        return self._count_branches(tree)
    
    def _count_branches(self, node: ast.AST) -> int:
        """Compte les branches dans l'AST."""
        count = 0
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                count += 1
            elif isinstance(child, (ast.And, ast.Or)):
                count += 1
        return count
```

**server/api.py:**
```python
"""Routes API du plugin complexité."""

from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter()

# Référence au plugin (injectée par le Bridge)
_plugin = None

def set_plugin(plugin):
    global _plugin
    _plugin = plugin


@router.get("/status")
async def get_status():
    """Statut du plugin."""
    if _plugin is None:
        raise HTTPException(503, "Plugin not initialized")
    return {
        "status": "ok",
        "files_analyzed": len(_plugin._results),
        "threshold": _plugin._config.get("threshold")
    }


@router.get("/results")
async def get_results(min_complexity: Optional[int] = None):
    """Résultats d'analyse."""
    if _plugin is None:
        raise HTTPException(503, "Plugin not initialized")
    
    results = _plugin._results
    if min_complexity is not None:
        results = {f: c for f, c in results.items() if c >= min_complexity}
    
    return {
        "files": results,
        "threshold": _plugin._config.get("threshold"),
        "total": len(results)
    }


@router.get("/warnings")
async def get_warnings():
    """Fichiers dépassant le seuil."""
    if _plugin is None:
        raise HTTPException(503, "Plugin not initialized")
    return {
        "warnings": _plugin._get_warnings(),
        "threshold": _plugin._config.get("threshold")
    }
```

**web/lang/en.json:**
```json
{
    "complexity": {
        "panel_title": "Complexity Analysis",
        "threshold": "Complexity Threshold",
        "files_analyzed": "Files Analyzed",
        "high_complexity": "High Complexity Files",
        "no_warnings": "No complexity warnings",
        "warning_count": "{count} file(s) exceed the complexity threshold"
    }
}
```

**web/lang/fr.json:**
```json
{
    "complexity": {
        "panel_title": "Analyse de Complexité",
        "threshold": "Seuil de Complexité",
        "files_analyzed": "Fichiers Analysés",
        "high_complexity": "Fichiers à Haute Complexité",
        "no_warnings": "Aucun avertissement de complexité",
        "warning_count": "{count} fichier(s) dépassent le seuil de complexité"
    }
}
```

### 9.2 Points clés de la migration

| Aspect | v1 | v2 |
|--------|----|----|
| **Structure** | Fichier unique | Répertoire avec manifest |
| **Config** | `configure(config)` direct | Via `services.get_config()` |
| **Hooks** | `on_scan()`, `on_analyze()` | Events `SCAN_FINISHED`, etc. |
| **API** | Non supporté nativement | Router FastAPI déclaratif |
| **UI** | Non supporté | Panneaux déclarés dans manifest |
| **i18n** | Non supporté | Fichiers `web/lang/*.json` |
| **Permissions** | Implicites | Explicites dans manifest |
| **Santé** | Non supporté | Interface `IPluginHealth` |
| **Métriques** | Non supporté | Interface `IPluginMetrics` |

### 9.3 Checklist de migration

Utilisez cette checklist pour migrer un plugin :

```markdown
## Migration de [nom_plugin]

### Préparation
- [ ] Créer le répertoire `jupiter/plugins/<plugin_id>/`
- [ ] Identifier toutes les fonctionnalités actuelles
- [ ] Lister les dépendances vers le core Jupiter

### Fichiers requis
- [ ] `plugin.yaml` - Manifest complet
- [ ] `__init__.py` - Classe implémentant IPlugin
- [ ] `config.yaml` - Configuration par défaut (si applicable)

### Migration du code
- [ ] Convertir `configure()` → `init(services)` + `get_config()`
- [ ] Convertir `on_scan()` → abonnement à `SCAN_FINISHED`
- [ ] Convertir `on_analyze()` → abonnement à `ANALYZE_FINISHED`
- [ ] Implémenter `shutdown()` pour le nettoyage
- [ ] Implémenter `health()` si besoin
- [ ] Implémenter `metrics()` si besoin

### Contributions (optionnel)
- [ ] Routes API dans `server/api.py`
- [ ] Commandes CLI dans `cli/commands.py`
- [ ] Panneau UI dans `web/panels/`
- [ ] Traductions dans `web/lang/`

### Validation
- [ ] Tests unitaires passent
- [ ] `jupiter plugins validate ./plugin_id` OK
- [ ] Test manuel en mode dev
- [ ] Vérifier les permissions demandées
```

### 9.4 Plugin avec UI complète

Voir le plugin `settings_update` dans `jupiter/plugins/core_plugins/` pour un exemple de plugin système avec :
- Interface `IPluginHealth` et `IPluginMetrics`
- Routes API déclaratives
- Panneau WebUI dans Settings
- Intégration complète avec le Bridge

---

## Changelog

### 0.2.0
- Ajout d'exemples concrets de migration (§9)
- Exemple complet avant/après pour plugin d'analyse
- Checklist de migration
- Points clés de comparaison v1/v2

### 0.1.0
- Création initiale du guide de migration
- Documentation des différences v1/v2
- Exemples de manifest et code migré
