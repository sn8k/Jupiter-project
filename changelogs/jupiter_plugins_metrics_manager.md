# Changelog – jupiter/plugins/metrics_manager

Ce fichier documente les modifications apportées au plugin Metrics Manager.

---

## [1.0.0] - Création initiale

### Ajouts
- **Plugin complet Metrics Manager** pour observation et gestion des métriques Jupiter
  - Architecture Bridge v2 conforme à `plugins_architecture.md v0.6.0`
  - Intégration avec `jupiter.core.bridge.metrics.MetricsCollector`

### Fichiers créés
- `plugin.yaml` - Manifest v2 avec:
  - Permissions: fs_read, emit_events, register_api, register_ui
  - Capacités: metrics, jobs, health_check
  - Configuration schema avec JSON Schema pour Auto-UI
  - Support i18n (en, fr)

- `__init__.py` - Module principal:
  - Lifecycle hooks: `init()`, `shutdown()`, `health()`, `metrics()`
  - Event handlers pour plugin.loaded, plugin.error, metrics.recorded
  - Fonctions: `collect_all_metrics()`, `get_metric_history()`, `export_metrics()`
  - Système d'alertes avec seuils configurables

- `server/api.py` - Endpoints FastAPI:
  - Standard: `/health`, `/metrics`, `/logs`, `/logs/stream`, `/changelog`
  - Spécifiques: `/all`, `/system`, `/plugins`, `/counters`, `/history/{name}`
  - Actions: `/record`, `/reset`, `/export`
  - Alertes: `/alerts` (GET, DELETE)
  - Streaming: `/stream` (SSE)

- `web/panels/main.js` - Interface WebUI:
  - Dashboard métriques système (uptime, collected, unique, counters)
  - Section alertes actives avec niveaux de sévérité
  - Tables counters et gauges
  - Graphique historique avec rendu canvas natif
  - Accordéon métriques plugins
  - Viewer logs temps réel avec filtrage
  - Statistiques plugin dans sidebar
  - Panel d'aide

- `web/lang/en.json` - Traductions anglaises (100+ clés)
- `web/lang/fr.json` - Traductions françaises (100+ clés)
- `config.yaml` - Configuration par défaut
- `README.md` - Documentation utilisateur
- `CHANGELOG.md` - Historique des versions

### Caractéristiques techniques
- Thread-safe metric collection
- SSE streaming pour logs et métriques temps réel
- Pas de dépendances JS externes (charts en canvas natif)
- Auto-refresh configurable (défaut: 10s)
- Export JSON et Prometheus

### Tests
- Tests unitaires à ajouter dans `tests/`

## [1.0.3] - Base API et garde-fous

### Corrections
- Résolution explicite de l'URL de base API (avec mappage 8050/8081 → 8000) avant d'ouvrir le flux SSE des logs, évitant les 404 quand l'UI tourne sur le port GUI/diag.
- Protection contre les payloads de métriques vides ou invalides pour ne plus casser l'UI; l'état affiche désormais une erreur claire.
- Badge UI mis à jour en v1.0.3 pour refléter la version courante du panneau.

## [1.0.4] - Garde-fous metrics plugins

### Corrections
- Filtrage des entrées de métriques plugins nulles/invalides avant `Object.entries` pour éviter les `TypeError` lors du rendu.
- Les lignes de jauges ignorent désormais les métriques non-objets, affichant un état vide propre si aucune donnée exploitable.
