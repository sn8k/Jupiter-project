# Changelog – Example Plugin (Modèle v2)

## [0.4.0] – Conforme à plugins_architecture.md v0.6.0

### Ajouté
- Documentation des nouvelles fonctionnalités Bridge v2 complètes
- Section Monitoring dans plugin.yaml (rate_limit, timeouts)
- Section Governance dans plugin.yaml (feature_flags, protected)
- Capabilities health intégré dans capabilities au lieu de healthcheck séparé
- Documentation CLI complète (install, uninstall, reload, sign, verify, etc.)
- Références aux nouveaux modules : notifications, usage_stats, error_report
- Support du dry-run dans le cadre Settings
- Support des logs centralisés multi-plugin
- Documentation circuit breaker et rate limiting
- Documentation permissions preview lors installation

### Modifié
- plugin.yaml : version 0.3.0 → 0.4.0
- __init__.py : version 0.3.0 → 0.4.0
- README.md : mise à jour complète pour v0.6.0
- jupiter.version : ">=1.8.0,<3.0.0"

## [0.3.0] – 2025-12-03

### Ajouté (conforme à plugins_architecture.md v0.4.0)
- `plugin.yaml` : structure `jupiter.version` (obligatoire) au lieu de `jupiter_version`.
- `plugin.yaml` : `config_schema.schema` (JSON Schema) pour génération Auto-UI (§3.4.3).
- `plugin.yaml` : `entrypoints` explicites pour tous les hooks.
- `plugin.yaml` : `capabilities.jobs` (timeout, max_concurrent) pour tâches longues (§10.6).
- `plugin.yaml` : `capabilities.ui.panels` avec structure complète (mount_point, route, title_key).
- `plugin.yaml` : permissions granulaires standardisées (`fs_read`, `fs_write`, `run_commands`, `network_outbound`, `access_meeting`).
- `plugin.yaml` : `healthcheck.interval_seconds` et `timeout_seconds`.
- `__init__.py` : support `bridge.services.*` comme Service Locator (§3.3.1).
- `__init__.py` : référence globale `_bridge` pour accès aux services.
- `__init__.py` : `submit_long_task()` et `_long_running_handler()` pour jobs async (§10.6).
- `__init__.py` : pattern d'annulation coopérative (`job.is_cancelled()`).
- `server/api.py` : endpoints `/jobs` (GET, POST, DELETE) pour gestion des jobs (§10.6).
- `server/api.py` : endpoint `/metrics` dédié.
- `server/api.py` : endpoint `/changelog` pour affichage dans modale.
- `server/api.py` : injection du Bridge dans `register_api_contribution()`.
- `core/logic.py` : fonction `validate_config()` pour validation avant sauvegarde.
- `core/logic.py` : fonction `process_item()` pour jobs async.
- `core/logic.py` : support optionnel du Bridge dans les fonctions.
- `README.md` : documentation complète des nouveautés v0.4.0.

### Modifié
- `plugin.yaml` : version 0.1.0 → 0.3.0.
- `__init__.py` : version 0.2.0 → 0.3.0.
- `__init__.py` : `reset_settings()` n'a plus besoin de `bridge` en argument (utilise `_bridge` global).
- `server/api.py` : version 0.1.0 → 0.3.0.
- `core/logic.py` : version 0.1.0 → 0.3.0.
- `README.md` : restructuration complète avec sections détaillées.

## [0.2.0] – 2025-12-03

### Ajouté
- `__init__.py` : fonction `metrics()` pour exposer les statistiques du plugin.
- `__init__.py` : logger dédié (`logging.getLogger`).
- `__init__.py` : fonction `reset_settings()` pour réinitialisation.
- `plugin.yaml` : capability `metrics` avec route `/metrics`.
- `plugin.yaml` : routes logs (`/logs`, `/logs/stream`).
- `plugin.yaml` : placeholder signature (`plugin.sig`).
- `web/panels/main.js` : section Logs temps réel avec recherche, pause/reprise, téléchargement.
- `web/panels/main.js` : section Statistiques (exécutions totales, dernière exécution, durée moyenne).
- `web/settings_frame.js` : toggle Mode debug.
- `web/settings_frame.js` : toggle Notifications.
- `web/settings_frame.js` : bouton Voir changelog (modale).
- `web/settings_frame.js` : bouton Reset settings avec confirmation.
- `web/lang/en.json` : nouvelles clés pour logs, stats, settings avancées, changelog.
- `web/lang/fr.json` : traductions françaises correspondantes.

### Modifié
- README.md : mise à jour des points clés et de la structure.

## [0.1.0] – 2025-12-03

### Ajouté
- Structure initiale du plugin modèle v2 pour documentation.
- `plugin.yaml` : manifest complet avec permissions, capabilities, i18n.
- `__init__.py` : hooks `init()` et `health()`.
- `server/api.py` : endpoints GET/POST et healthcheck.
- `server/events.py` : exemple pub/sub avec schéma de payload.
- `cli/commands.py` : sous-commandes `example run` et `example status`.
- `core/logic.py` : logique métier isolée.
- `core/runner_access.py` : exemple d'appel médié au runner via Bridge.
- `web/panels/main.js` : panneau principal avec aide à droite, export fichier/IA.
- `web/settings_frame.js` : cadre de configuration auto-ajouté à Settings.
- `web/assets/style.css` : styles spécifiques au plugin.
- `web/lang/en.json` et `fr.json` : traductions i18n.
- `tests/test_basic.py` : tests unitaires de base.
