# Changelog - Security & Hardening

## [Unreleased]

### Added
- **Authentication**: Added `security.token` configuration in `jupiter.yaml`.
- **API Protection**: Protected sensitive endpoints (`/run`, `/update`, `/config`, `/plugins`) with Bearer token authentication.
- **WebSocket Security**: Added token verification for WebSocket connections via query parameter.
- **Meeting Hardening**: Enforced strict validation of `deviceKey` in `MeetingAdapter` to prevent local config bypass.

### Changed
- Updated `docs/api.md`, `docs/dev_guide.md`, and `README.md` to include security information.

### Section 8 Updates (Sandboxing)
- **Configuration de Sécurité** :
  - Ajout de `allow_run` (bool) et `allowed_commands` (list) dans `SecurityConfig`.
  - Permet de désactiver l'exécution de commandes ou de la restreindre à une liste blanche.
- **Politique de Plugins** :
  - Ajout de l'attribut `trust_level` aux plugins.
  - Logging explicite du niveau de confiance lors du chargement.
  - Le plugin `notifications_webhook` est marqué comme "trusted".
- **Sécurité Projets Distants** :
  - Ajout de timeouts explicites (60s pour scan/analyze, 300s pour run) dans `RemoteConnector`.
  - Gestion des erreurs avec masquage des détails sensibles (headers/tokens) dans les logs.
