# Audit des plugins Jupiter existants

Version : 1.0.0

Ce document inventorie tous les plugins actuels et documente leurs caractéristiques pour faciliter la migration vers l'architecture v2.

## 1. Inventaire des plugins

### 1.1 Plugins système (core)

| Plugin | Version | Fichier | Description |
|--------|---------|---------|-------------|
| `bridge_plugin` | 1.0.2 | `bridge_plugin.py` | Gateway vers les services core Jupiter |
| `settings_update` | 1.0.0 | `settings_update.py` | Auto-update depuis ZIP/Git |
| `watchdog` | 1.0.2 | `watchdog_plugin.py` | Surveillance et rechargement automatique des plugins |

### 1.2 Plugins outils (tools)

| Plugin | Version | Fichier | Description | Trust Level |
|--------|---------|---------|-------------|-------------|
| `ai_helper` | 0.3.1 | `ai_helper.py` | Suggestions IA pour le code | experimental |
| `autodiag` | 1.1.0 | `autodiag_plugin.py` | Diagnostic automatique, faux positifs | stable |
| `code_quality` | 0.8.1 | `code_quality.py` | Complexité, duplication, maintenabilité | - |
| `example_plugin` | 0.1.1 | `example_plugin.py` | Plugin exemple/template | - |
| `livemap` | 0.3.0 | `livemap.py` | Graphe de dépendances D3.js | - |
| `notifications_webhook` | 0.2.2 | `notifications_webhook.py` | Notifications via webhook | trusted |
| `pylance_analyzer` | 0.5.2 | `pylance_analyzer.py` | Analyse statique via Pyright | stable |

---

## 2. Hooks actuels par plugin

### 2.1 Hooks supportés

| Plugin | `on_scan` | `on_analyze` | `configure` | `register_cli` | `register_api` | UI |
|--------|:---------:|:------------:|:-----------:|:--------------:|:--------------:|:--:|
| `ai_helper` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `autodiag` | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ (BOTH) |
| `bridge_plugin` | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ (SETTINGS) |
| `code_quality` | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ (BOTH) |
| `example_plugin` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `livemap` | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ (SIDEBAR) |
| `notifications_webhook` | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ (SETTINGS) |
| `pylance_analyzer` | ✅ | ❌ | ✅ | ❌ | ❌ | ✅ (SIDEBAR) |
| `settings_update` | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ (SETTINGS) |
| `watchdog` | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ (SETTINGS) |

---

## 3. Contributions UI par plugin

### 3.1 Configuration PluginUIConfig

| Plugin | `ui_type` | `menu_icon` | `menu_label_key` | `menu_order` | `view_id` |
|--------|-----------|-------------|------------------|--------------|-----------|
| `autodiag` | BOTH | 🔬 | `autodiag_view` | 65 | `autodiag` |
| `bridge_plugin` | SETTINGS | ⚙️ | `bridge_settings` | 100 | `bridge` |
| `code_quality` | BOTH | 📊 | `quality_view` | 70 | `quality` |
| `livemap` | SIDEBAR | 🗺️ | `livemap_view` | 40 | `livemap` |
| `notifications_webhook` | SETTINGS | 🔔 | `notifications_settings` | 50 | `notifications` |
| `pylance_analyzer` | SIDEBAR | 🔍 | `pylance_view` | 75 | `pylance` |
| `settings_update` | SETTINGS | 🔄 | `update_settings` | 90 | `update` |
| `watchdog` | SETTINGS | 👁️ | `watchdog_view` | 999 | None |

---

## 4. Dépendances inter-plugins

### 4.1 Dépendances directes

- `notifications_webhook` → `jupiter.core.events` (JupiterEvent, PLUGIN_NOTIFICATION)
- `notifications_webhook` → `jupiter.server.ws` (WebSocket manager)
- `code_quality` → `jupiter.core.quality.complexity`
- `code_quality` → `jupiter.core.quality.duplication`
- `pylance_analyzer` → subprocess (pyright externe)
- `autodiag` → `jupiter/server/routers/autodiag.py`

### 4.2 Dépendances vers core modules

| Plugin | Modules core utilisés |
|--------|----------------------|
| `bridge_plugin` | Tous (gateway) |
| `code_quality` | `core.quality.complexity`, `core.quality.duplication` |
| `livemap` | Analyse imports (interne) |
| `notifications_webhook` | `core.events`, `server.ws` |
| `autodiag` | `core.autodiag`, `server.routers.autodiag` |
| `settings_update` | filesystem, subprocess |
| `watchdog` | `core.plugin_manager` |

---

## 5. Évaluation de complexité de migration

### 5.1 Matrice de complexité

| Plugin | Complexité | Lignes | Raison |
|--------|------------|--------|--------|
| `example_plugin` | 🟢 Simple | ~35 | Minimal, template idéal |
| `ai_helper` | 🟢 Simple | ~196 | Hooks simples, pas d'UI complexe |
| `notifications_webhook` | 🟢 Simple | ~506 | Hooks simples, Settings UI basique |
| `settings_update` | 🟢 Simple | ~435 | Logique isolée, Settings UI |
| `watchdog` | 🟡 Moyen | ~710 | Threading, monitoring, Settings UI |
| `pylance_analyzer` | 🟡 Moyen | ~1069 | Subprocess, parsing, Sidebar UI |
| `autodiag` | 🟡 Moyen | ~1523 | UI riche, API endpoints, BOTH mode |
| `livemap` | 🟡 Moyen | ~1245 | D3.js, graphe, Sidebar UI |
| `bridge_plugin` | 🔴 Complexe | ~1235 | Architecture core, services registry |
| `code_quality` | 🔴 Complexe | ~2276 | Analyse approfondie, UI riche, API |

### 5.2 Ordre de migration recommandé

1. **Phase 1** (Simple) : `example_plugin`, `ai_helper`, `notifications_webhook`
2. **Phase 2** (Settings UI) : `settings_update`, `watchdog`
3. **Phase 3** (Sidebar UI) : `pylance_analyzer`, `livemap`
4. **Phase 4** (UI Riche) : `autodiag`, `code_quality`
5. **Phase 5** (Core) : `bridge_plugin` (à transformer en Bridge v2)

---

## 6. Interfaces existantes

### 6.1 Protocol Plugin (`jupiter/plugins/__init__.py`)

```python
@runtime_checkable
class Plugin(Protocol):
    name: str
    version: str
    description: str

    def on_scan(self, report: dict[str, Any]) -> None: ...
    def on_analyze(self, summary: dict[str, Any]) -> None: ...
    def configure(self, config: dict[str, Any]) -> None: ...
```

### 6.2 Protocol UIPlugin

```python
class UIPlugin(Protocol):
    name: str
    version: str
    description: str
    ui_config: PluginUIConfig
    
    def get_ui_html(self) -> str: ...
    def get_ui_js(self) -> str: ...
    def get_settings_html(self) -> str: ...
    def get_settings_js(self) -> str: ...
```

### 6.3 PluginUIConfig

```python
@dataclass
class PluginUIConfig:
    ui_type: PluginUIType  # NONE, SIDEBAR, SETTINGS, BOTH
    menu_icon: str
    menu_label_key: str
    menu_order: int
    settings_section: Optional[str]
    view_id: Optional[str]
```

---

## 7. Points d'attention pour la migration

### 7.1 Compatibilité ascendante

- Le nouveau Bridge doit supporter les anciens hooks (`on_scan`, `on_analyze`)
- L'adaptateur legacy doit wrapper les plugins existants automatiquement
- Les `PluginUIConfig` actuels doivent être convertibles en manifest YAML

### 7.2 Breaking changes potentiels

- Nouveau format de manifest `plugin.yaml` (vs attributs de classe)
- Nouvelle structure de fichiers (`server/`, `cli/`, `web/` par plugin)
- Nouvelles interfaces (`init()`, `health()`, `metrics()`)
- Enregistrement des routes API via Bridge (vs injection directe)

### 7.3 Tests requis

- Tests unitaires pour chaque plugin migré
- Tests d'intégration pour le cycle de vie
- Tests de non-régression pour les hooks existants
- Tests UI (manuels ou automatisés)

---

## Changelog

### 1.0.0
- Création initiale de l'audit
- Inventaire de 10 plugins
- Documentation des hooks, UI, dépendances
- Évaluation de complexité de migration
