# Changelog – jupiter/plugins/bridge_plugin.py

## Version 1.0.2 – 2025-12-03

**Bridge is now non-restartable by users.**

### Added
- `restartable = False` class attribute to prevent user-initiated restarts
- Bridge can only be restarted by Watchdog or system processes

### Notes
- Bridge is a primary/core plugin that other plugins depend on
- Preventing user restarts avoids cascading issues with dependent plugins
- Watchdog can still restart Bridge during plugin reload operations

---

## Version 1.0.1 – 2025-12-03

**Fixed settings panel API connectivity.**

### Fixed
- Settings JS now uses `state.apiBaseUrl` instead of relative URLs
- Added `getApiBase()` helper to properly retrieve API base URL from global state
- Added `getAuthHeaders()` helper to include authentication token in requests
- All fetch calls now include proper Authorization headers

### Notes
- This fixes the Bridge status panel showing "Failed to load services" when using GUI on port 8050
- API requests now correctly target port 8000 instead of relative URLs

---

## Version 1.0.0 – 2025-12-02

**Plugin Bridge : Passerelle de services centraux pour les plugins Jupiter.**

### Ajouts

- **Architecture Bridge complète** :
  - `ServiceRegistry` : Registre central des services avec lazy loading
  - `ServiceDescriptor` : Métadonnées décrivant chaque service
  - `Capability` : Description des capacités individuelles d'un service
  - `BridgeContext` : Interface principale pour les plugins
  - `BaseService` : Classe de base pour les services

- **Services intégrés** :
  - `EventsService` : Émission et création d'événements Jupiter
  - `ConfigService` : Accès à la configuration projet/globale
  - `ScannerService` : Scan de fichiers et répertoires
  - `CacheService` : Gestion du cache des rapports
  - `HistoryService` : Gestion des snapshots et diff
  - `LoggingService` : Création de loggers pour plugins

- **Système de capacités** :
  - Déclaration déclarative des capacités par service
  - Recherche de services par capacité
  - Invocation générique via `bridge.invoke(capability, *args)`
  - Versioning des capacités

- **UI Settings** :
  - Panneau de statut dans Settings > Plugins
  - Affichage des services disponibles et chargés
  - Liste des capacités globales
  - Bouton de rafraîchissement

- **API Endpoints** :
  - `GET /plugins/bridge/status` : Statut complet du Bridge
  - `GET /plugins/bridge/services` : Liste des services
  - `GET /plugins/bridge/capabilities` : Liste des capacités
  - `GET /plugins/bridge/service/{name}` : Détails d'un service

- **Accès global** :
  - `get_bridge()` : Fonction pour obtenir le BridgeContext
  - `has_bridge()` : Vérifie si le Bridge est disponible
  - Export depuis `jupiter.plugins` pour faciliter l'accès

### Principes de conception

1. **Lazy Loading** : Services instanciés uniquement au premier accès
2. **Découplage** : Les plugins n'importent pas directement les modules core
3. **Versioning** : API versionné (`BRIDGE_API_VERSION`) pour évolutions futures
4. **Extensibilité** : Nouveaux services ajoutables sans modifier les plugins existants
5. **Graceful Degradation** : Gestion propre des services manquants

### Utilisation par les plugins

```python
from jupiter.plugins import get_bridge

def my_plugin_method(self):
    bridge = get_bridge()
    if bridge:
        # Accès à un service
        scanner = bridge.get_service("scanner")
        if scanner:
            files = scanner.list_files(path, [".py"])
        
        # Vérification de capacité
        if bridge.has_capability("emit_event"):
            bridge.invoke("emit_event", "MY_EVENT", {"data": "value"})
```

### Notes techniques

- Le Bridge est un plugin système (`trust_level = "system"`)
- Il est initialisé automatiquement par le PluginManager
- Les services déclarent leurs dépendances pour un chargement ordonné
- Les erreurs de service sont loguées mais ne bloquent pas le Bridge

---

*Ce fichier documente l'évolution du module `jupiter/plugins/bridge_plugin.py`.*
