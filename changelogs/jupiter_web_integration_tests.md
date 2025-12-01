# Changelog - WebUI Integration Tests

## Added
- Added `tests/test_web_integration.py` to verify WebUI serving and API integration.
- Added `/reports/last` endpoint to `jupiter/server/api.py` to support WebUI dashboard.

## Fixed
- Fixed `jupiter/server/api.py` to correctly serve the last report from cache.
- Verified API endpoints used by WebUI (`/config`, `/plugins`, `/snapshots`).
- Ajout d'une assertion sur `jupiter_version` dans `tests/test_web_integration.py` pour garantir que le WebUI context expose bien la version globale.
