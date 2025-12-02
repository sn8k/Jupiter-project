# Changelog – jupiter/core/autodiag.py

## Version 1.4.0 (2025-12-02)

### Corrigé
- **Messages d'erreur vides dans les scénarios** : Les scénarios CLI et API échoués n'incluaient pas de message d'erreur
  - CLI : Capture maintenant stderr/stdout comme `error_message` quand `exit_code != 0`
  - API : Inclut maintenant `HTTP {status_code}: {body}` comme `error_message` pour les codes >= 400
- Les erreurs sont maintenant visibles dans la colonne "Error" de l'interface WebUI

---

## Version 1.3.0 (2025-12-02)

### Corrigé
- **Chargement du token d'authentification** : Utilisation de `load_merged_config` au lieu de `load_config`
- Le token est maintenant correctement récupéré depuis la liste `users` du fichier `global_config.yaml`
- Ordre de recherche du token : `security.tokens` → `security.token` → `users` (avec priorité aux admins)
- Les tests API passent maintenant (28/36 réussis, les 8 échecs sont des endpoints avec paramètres dynamiques)

---

## Version 1.2.0 (2025-12-02)

### Ajouté
- **Support du token d'authentification** : Le runner charge automatiquement le token depuis la config
- Paramètre `auth_token` ajouté au constructeur `AutoDiagRunner`
- Les appels API (`_call_api_endpoint`, `_get_api_endpoints`) incluent maintenant le header `Authorization: Bearer <token>`
- Support des tokens multi-utilisateurs (liste `TokenConfig`) avec priorité aux tokens admin

### Corrigé
- **Erreurs 401 sur les endpoints protégés** : Les tests API passaient sans authentification
- Import de `load_config` depuis `jupiter.config` pour charger le token

---

## Version 1.1.0 (2025-12-02)

### Ajouté
- **CallGraphService** : Utilisation du service de graphe d'appels pour une détection plus précise
- La méthode `_run_static_analysis()` utilise maintenant `CallGraphService` par défaut
- Fallback vers `ProjectAnalyzer` si le call graph échoue

---

## Version 1.0.0 (2025-12-02) – Initial Release (Phase 4)

### Purpose
Automated self-analysis runner for Jupiter that compares static analysis results
with dynamic runtime observations to identify false positives in unused function detection.

### Classes Added

#### AutodiagStatus (Enum)
- `SUCCESS`: All scenarios passed
- `PARTIAL`: Some scenarios failed
- `FAILED`: Critical failure
- `SKIPPED`: Autodiag skipped

#### ScenarioResult (Dataclass)
- Stores result of a single test scenario
- Fields: name, status, duration_seconds, triggered_functions, error_message, details

#### FalsePositiveInfo (Dataclass)
- Information about a detected false positive
- Fields: function_name, file_path, reason, scenario, call_count

#### AutoDiagReport (Dataclass)
- Complete report from an autodiag run
- Static analysis metrics
- Dynamic validation results
- False positive detection stats
- Recommendations list

#### AutoDiagRunner (Class)
Main runner class with methods:
- `run()`: Execute full autodiag workflow (async)
- `_run_static_analysis()`: Perform static code analysis
- `_run_cli_scenarios()`: Execute CLI commands
- `_run_api_scenarios()`: Call API endpoints
- `_run_plugin_scenarios()`: Trigger plugin hooks
- `_compare_results()`: Compare static vs dynamic
- `_generate_recommendations()`: Generate actionable advice

### Functions Added
- `run_autodiag_sync()`: Synchronous wrapper for CLI usage

### Dependencies
- asyncio for async execution
- httpx (optional) for API calls
- jupiter.core.scanner, report, analyzer
- jupiter.core.cache, plugin_manager

### Test Scenarios
Default CLI scenarios:
- scan --help
- analyze --help
- ci --help
- snapshots list --help
- server --help
