# Changelog – Settings UX Refactor & Project Performance

## 2025-12-02 – v1.3.1

### Vue Settings refactorée

#### Boutons Save individuels par section
- **Réseau**: Bouton Save avec status indicator `#network-settings-status`
- **Interface**: Bouton Save avec status indicator `#ui-settings-status`  
- **Sécurité**: Bouton Save avec status indicator `#security-settings-status`
- Suppression du bouton "Enregistrer" global en haut de page
- Chaque section sauvegarde uniquement ses propres paramètres

#### Nouvelles fonctions JavaScript (`app.js`)
- `setSettingsStatus(statusId, text, variant)` – Helper pour afficher le statut (✓ / ✗)
- `saveNetworkSettings()` – Sauvegarde host/port serveur et GUI
- `saveUISettings()` – Sauvegarde thème et langue
- `saveSecuritySettings()` – Sauvegarde allow_run
- `saveProjectPerformanceSettings()` – Sauvegarde les settings performance du projet

### Performance déplacée vers Projects

Le cadre Performance (parallel scan, workers, timeout, graph settings) a été déplacé de la page Settings vers la page Projects, dans la section "Projet Actif".

**Justification**: Ces paramètres sont spécifiques au projet en cours, pas globaux.

#### Nouvelle section dans index.html (Projects view)
```html
<!-- Performance Section (Project-specific) -->
<div style="margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid var(--border);">
  <h4 data-i18n="settings_perf_title">⚡ Performance</h4>
  ...
</div>
```

#### Nouvelle fonction de chargement
- `loadProjectPerformanceConfig()` – Charge les settings performance depuis `/config`
- Appelée dans `loadProjects()` après `loadProjectApiConfig()`

### Bugs corrigés

#### Config API projet non restaurée au démarrage
- `loadProjectApiConfig()` est maintenant appelée correctement
- `loadProjectPerformanceConfig()` ajoutée pour charger les settings performance

#### Sauvegarde Code Quality plugin
- Correction de l'endpoint `/plugins/{name}/config` : ajout de `Body(...)` 
- Le paramètre `config: Dict[str, Any]` était interprété comme query param au lieu de body

### Fichiers modifiés

- `jupiter/web/index.html` – Restructuration des sections Settings, déplacement Performance
- `jupiter/web/app.js` – Nouvelles fonctions save individuelles, handlers d'action
- `jupiter/server/routers/system.py` – Fix Body() sur configure_plugin
- `jupiter/web/lang/fr.json` – Clés i18n pour performance
- `jupiter/web/lang/en.json` – Clés i18n pour performance

### Nouvelles clés i18n

```json
"project_perf_hint": "Paramètres de performance pour ce projet.",
"perf_parallel_scan": "Scan parallèle",
"perf_max_workers": "Workers max (0 = Auto)",
"perf_scan_timeout": "Timeout scan (sec)",
"perf_graph_simplification": "Simplification graphe",
"perf_max_graph_nodes": "Nœuds max graphe"
```
