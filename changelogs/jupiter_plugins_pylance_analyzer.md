# Changelog – jupiter/plugins/pylance_analyzer.py

## [0.5.2] – 2025-12-01
- La configuration, la détection Pyright et l'exécution du binaire loggent désormais l'ensemble des paramètres (fichiers tronqués, commande Pyright, nombre de diagnostics) lorsque le niveau DEBUG est actif.
- Les sorties `on_scan`/`on_analyze` ajoutent des payloads détaillés au log DEBUG pour accélérer le troubleshooting lorsque Pyright renvoie des erreurs ou qu'aucun fichier Python n'est trouvé.

## [0.5.1] – 2025-12-02
- Ajout d'un état d'interface dédié expliquant qu'aucun fichier Python n'est présent lorsque Pyright est ignoré avec `reason = no_python_files`.
- Mise à jour des traductions anglaises et françaises pour refléter le nouvel état informatif.

## [0.5.0] – 2025-12-01
- Affectation d'une version dédiée (`0.5.0`) au plugin Pylance pour synchroniser l'affichage de la Web UI Plugins avec l'évolution réelle du module.

## [1.0.0] – 2024-12-01

### Added
- Initial implementation of the Pylance/Pyright analyzer plugin
- Integration with Pyright CLI for static type analysis
- `PylanceDiagnostic` dataclass for individual diagnostics (file, line, column, severity, message, rule)
- `PylanceFileReport` dataclass for per-file diagnostic summaries
- `PylanceSummary` dataclass for project-wide analysis summary
- `PylanceAnalyzerPlugin` class implementing the Jupiter Plugin protocol

### Features
- Runs Pyright in JSON output mode during `on_scan` hook
- Parses diagnostics and enriches scan reports with type errors and warnings
- Configurable options:
  - `enabled`: Enable/disable the plugin
  - `strict`: Use Pyright strict mode
  - `include_warnings`: Include warning-level diagnostics
  - `include_info`: Include informational diagnostics
  - `max_files`: Limit number of files to analyze
  - `timeout`: Timeout in seconds for Pyright execution
  - `extra_args`: Additional Pyright CLI arguments
- Graceful fallback when Pyright is not installed
- Integration with Jupiter's quality metrics

### Notes
- Pyright must be installed separately: `pip install pyright`
- The plugin is optional and will skip analysis if Pyright is unavailable
- Diagnostics are attached to scan reports under the `pylance` key
