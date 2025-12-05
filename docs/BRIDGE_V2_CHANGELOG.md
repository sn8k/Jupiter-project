# Changelog – Bridge v2 Plugin System

Ce changelog résume toutes les phases de la refonte du système de plugins Jupiter vers l'architecture Bridge v2.

**Version finale** : 1.8.53  
**Total tests Bridge** : 1500+  
**Conformité** : plugins_architecture.md v0.6.0

---

## Résumé des Phases

| Phase | Nom | Status | Tests |
|-------|-----|--------|-------|
| 0 | Préparation | ✅ Complete | 43 |
| 1 | Bridge Core | ✅ Complete | 180+ |
| 2 | Plugins Core | ✅ Complete | 51 |
| 3 | CLI Contributions | ✅ Complete | 76 |
| 4 | API Contributions | ✅ Complete | 219 |
| 5 | WebUI Contributions | ✅ Complete | - |
| 6 | Migration Plugins | ✅ Complete | 50 |
| 7 | Sécurité & Sandbox | ✅ Complete | 285 |
| 8 | Hot Reload & Dev Mode | ✅ Complete | 291 |
| 9 | Marketplace | ✅ Complete | 14+ |
| 10 | Meeting | ⏸️ Conditionnel | - |
| 11 | Finalisation | ✅ Complete | 22 |

---

## Phase 0 : Préparation

### Modules créés
- `jupiter/core/bridge/` - Dossier racine du Bridge
- `jupiter/core/bridge/interfaces.py` - Interfaces ABC (IPlugin, IPluginManifest, IPluginContribution, IPluginHealth, IPluginMetrics)
- `jupiter/core/bridge/exceptions.py` - Exceptions (PluginError, ManifestError, DependencyError, CircularDependencyError)
- `jupiter/core/bridge/schemas/plugin_manifest.json` - JSON Schema pour validation

### Documentation
- `docs/plugins_architecture.md` v0.4.0 → v0.6.0
- `docs/PLUGIN_AUDIT.md` - Inventaire des plugins existants
- `docs/PLUGIN_MIGRATION_GUIDE.md` - Guide de migration v1 → v2

---

## Phase 1 : Bridge Core

### Modules créés
- `jupiter/core/bridge/bridge.py` v0.1.0 - Classe Bridge singleton, registres
- `jupiter/core/bridge/manifest.py` - Parsing et validation des manifests
- `jupiter/core/bridge/services.py` v0.1.0 - Service Locator (37 tests)
  - `get_logger()`, `get_runner()`, `get_history()`, `get_graph()`
  - `get_project_manager()`, `get_event_bus()`, `get_config()`
  - `SecureRunner` avec vérification permissions
- `jupiter/core/bridge/events.py` v0.1.0 - Event bus pub/sub (48 tests)
- `jupiter/core/bridge/bootstrap.py` v0.1.0 - Initialisation système (10 tests)
- `jupiter/core/bridge/ws_bridge.py` v0.1.0 - WebSocket propagation

### Lifecycle
- `discover()` - Scan plugins, validation manifests
- `initialize()` - Chargement avec tri topologique
- `register()` - Enregistrement contributions
- `ready()` - Publication WebUI

---

## Phase 2 : Plugins Core

### Modules créés
- `jupiter/core/bridge/core_plugins/` - Plugins système hard-codés
- `jupiter/core/bridge/core_plugins/settings_update_plugin.py` v0.1.0

### Configuration
- Fusion config globale + overrides projet
- Support `enabled: true/false` par projet
- Tests: 27 (test_bridge_plugin_config.py)

---

## Phase 3 : CLI Contributions

### Modules créés
- `jupiter/core/bridge/cli_registry.py` v0.1.0 (44 tests)
  - `register_cli_contribution()`
  - Résolution dynamique des entrypoints
  - Commandes préfixées `p:plugin_id:cmd`

### Commandes système
- `jupiter plugins list`
- `jupiter plugins info <id>`
- `jupiter plugins enable/disable <id>`
- `jupiter plugins status`
- `jupiter plugins install <source>`
- `jupiter plugins uninstall <id>`
- `jupiter plugins scaffold <id>`
- `jupiter plugins reload <id>`

---

## Phase 4 : API Contributions

### Modules créés
- `jupiter/core/bridge/api_registry.py` v0.2.0 (71 tests)
  - `register_api_contribution()`
  - `APIPermissionValidator`
  - `@require_plugin_permission()`
- `jupiter/core/bridge/metrics.py` v0.1.0 (30 tests)
- `jupiter/core/bridge/alerting.py` v0.1.0 (53 tests)
- `jupiter/core/bridge/jobs.py` v0.3.0 (34 tests)
  - States: pending, running, completed, failed, cancelled
  - Circuit breaker par plugin
  - Export jobs vers fichier

### Endpoints standard
- `/plugins/<id>/health`
- `/plugins/<id>/metrics`
- `/plugins/<id>/logs`
- `/plugins/<id>/logs/stream`
- `/plugins/<id>/config`
- `/plugins/<id>/reset-settings`
- `/jobs`, `/jobs/{id}`, `/jobs/{id}/cancel`

---

## Phase 5 : WebUI Contributions

### Modules JavaScript créés
- `jupiter/web/js/plugin_container.js` v0.1.0
- `jupiter/web/js/plugin_integration.js` v0.2.0
- `jupiter/web/js/jupiter_bridge.js` v0.1.0 (window.jupiterBridge)
- `jupiter/web/js/auto_form.js` v0.2.0
- `jupiter/web/js/metrics_widget.js` v0.1.0
- `jupiter/web/js/logs_panel.js` v0.2.0
- `jupiter/web/js/logs_central_panel.js` v0.1.0
- `jupiter/web/js/plugin_settings_frame.js` v0.4.0
- `jupiter/web/js/i18n_loader.js` v0.2.0
- `jupiter/web/js/help_panel.js` v0.1.0
- `jupiter/web/js/data_export.js` v0.1.0
- `jupiter/web/js/ux_utils.js` v0.1.0

### Backend
- `jupiter/core/bridge/ui_registry.py` v0.1.0 (54 tests)

---

## Phase 6 : Migration Plugins

### Modules créés
- `jupiter/core/bridge/legacy_adapter.py` v0.2.0 (50 tests)
  - `LegacyPluginWrapper`
  - `LegacyAdapter`
  - Deprecated en v1.8.52

### Plugins migrés vers v2
- `ai_helper` v1.1.0
- `code_quality` v0.8.1
- `livemap` v0.3.0
- `autodiag` v1.1.0
- `pylance_analyzer` v1.0.0
- `notifications_webhook` v1.0.0
- `watchdog` v1.0.0

---

## Phase 7 : Sécurité & Sandbox

### Modules créés
- `jupiter/core/bridge/permissions.py` v0.1.0 (52 tests)
  - `PermissionChecker`
  - `@require_permission()`
  - Checks: fs_read, fs_write, run_command, network, meeting, config, emit_events
- `jupiter/core/bridge/signature.py` v0.1.0 (58 tests)
  - `TrustLevel`: OFFICIAL, VERIFIED, COMMUNITY, UNSIGNED
  - `SignatureVerifier`, `PluginSigner`
- `jupiter/core/bridge/monitoring.py` v0.1.0 (50 tests)
  - `AuditLogger`
  - `TimeoutConfig`, `with_timeout()`
  - `RateLimiter`
- `jupiter/core/bridge/governance.py` v0.1.0 (75 tests)
  - Whitelist/Blacklist
  - Feature flags

### CLI sécurité
- `jupiter plugins sign <path>`
- `jupiter plugins verify <path>`

---

## Phase 8 : Hot Reload & Dev Mode

### Modules créés
- `jupiter/core/bridge/hot_reload.py` v0.2.0 (61 tests)
  - `HotReloader`
  - `reload()`, `can_reload()`
  - Thread safety, blacklist, callbacks
- `jupiter/core/bridge/dev_mode.py` v0.1.0 (61 tests)
  - `DeveloperMode`
  - `PluginFileHandler` pour file watching
- `jupiter/core/bridge/notifications.py` v0.1.0 (79 tests)
  - Types: info, success, warning, error, action_required
  - Priorités: LOW, NORMAL, HIGH, URGENT
  - Canaux: TOAST, BADGE, ALERT, SILENT
- `jupiter/core/bridge/usage_stats.py` v0.1.0 (91 tests)
  - Stats par plugin et méthode
  - Agrégations temporelles
  - Persistance disque
- `jupiter/core/bridge/error_report.py` v0.1.0 (85 tests)
  - Anonymisation données sensibles
  - Déduplication
  - Export multi-format

---

## Phase 9 : Marketplace

### Fonctionnalités CLI
- `jupiter plugins install <url>` - Installation depuis URL/path
- `jupiter plugins uninstall <id>` - Désinstallation
- `jupiter plugins update <id>` - Mise à jour
- `jupiter plugins check-updates` - Vérification mises à jour
- Options: `--install-deps`, `--dry-run`, `--force`, `--no-backup`
- Rollback automatique en cas d'échec

### WebUI
- Boutons "Check for update" / "Update" dans plugin_settings_frame.js
- Aperçu des permissions lors de l'installation

---

## Phase 10 : Meeting (Conditionnel)

> ⚠️ Phase spéculative, dépend de la disponibilité de Meeting.

- Actions distantes avec confirmation locale
- Reset distant avec plan d'action signé
- Audit trail complet

---

## Phase 11 : Finalisation

### Tests d'intégration
- 22 tests dans `tests/test_plugin_integration.py`
- Scénarios: installation, utilisation, mise à jour, échec/recovery, jobs, hot reload, API

### Documentation
- `docs/plugins_architecture.md` v0.6.0
- `docs/PLUGIN_DEVELOPER_GUIDE.md` v1.0.0 (1050 lignes)
- `docs/PLUGIN_MIGRATION_GUIDE.md` v0.2.0
- `docs/plugin_model/` v0.4.0
- `Manual.md` et `README.md` mis à jour

---

## Exports bridge/__init__.py

Version finale: v0.20.0

```python
# Interfaces
from .interfaces import IPlugin, IPluginManifest, IPluginContribution, IPluginHealth, IPluginMetrics

# Core
from .bridge import Bridge
from .manifest import PluginManifest
from .services import ServiceLocator, SecureRunner

# Events
from .events import EventBus, EventPriority

# Registries
from .cli_registry import CLIRegistry
from .api_registry import APIRegistry, APIPermissionValidator
from .ui_registry import UIRegistry

# Jobs
from .jobs import JobManager, JobStatus, JobInfo

# Security
from .permissions import PermissionChecker, Permission
from .signature import SignatureVerifier, PluginSigner, TrustLevel
from .monitoring import PluginMonitor, AuditLogger, RateLimiter
from .governance import GovernanceManager, ListMode

# Dev
from .hot_reload import HotReloader
from .dev_mode import DeveloperMode

# Features
from .notifications import NotificationManager, NotificationType, NotificationPriority
from .usage_stats import UsageStatsManager
from .error_report import ErrorReportManager

# Alerting & Metrics
from .alerting import AlertManager, AlertRule, AlertSeverity
from .metrics import MetricsCollector

# Legacy (deprecated)
from .legacy_adapter import LegacyAdapter, LegacyPluginWrapper
```

---

## Statistiques finales

- **Modules Bridge** : 25+
- **Tests Bridge** : 1500+
- **Plugins migrés** : 7
- **Commandes CLI** : 15+
- **Endpoints API** : 20+
- **Modules JS WebUI** : 12+
- **Traductions i18n** : 1000+ clés (en/fr)

---

## Migration v1 → v2

Pour migrer un plugin existant, voir `docs/PLUGIN_MIGRATION_GUIDE.md`.

Checklist rapide:
1. Créer le répertoire `jupiter/plugins/<id>/`
2. Ajouter `plugin.yaml` avec manifest complet
3. Refactorer `__init__.py` avec `init()`, `health()`, `metrics()`
4. Utiliser `bridge.services.*` au lieu d'imports directs
5. Créer `server/api.py` si routes API
6. Créer `cli/commands.py` si commandes CLI
7. Créer `web/panels/*.js` si WebUI
8. Ajouter traductions `web/lang/*.json`
9. Tests dans `tests/`
10. (Optionnel) Signer avec `jupiter plugins sign`
