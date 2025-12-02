# Changelog – jupiter/server/routers/autodiag.py

## Version 1.1.0 (2025-12-02) – Phase 4: Autodiag Run Endpoint
- Added `POST /diag/run` endpoint to trigger autodiag from API
  - Query params: skip_cli, skip_api, skip_plugins, timeout
  - Returns AutoDiagReport as JSON
  - Uses project root from main app state
  - Runs synchronous wrapper (run_autodiag_sync)

## Version 1.0.0 (2025-12-02) – Initial Release (Phase 3)

### Purpose
Dedicated FastAPI router for autodiagnostic endpoints, designed to run on a separate localhost-only port for security.

### Endpoints Added
- `GET /diag/introspect`: Returns all registered routes from the main API
  - Route path, HTTP methods, endpoint function name
  - Filters out diag and openapi routes
  
- `GET /diag/handlers`: Aggregates all registered handlers
  - API handlers from route registry
  - CLI handlers from CLI_HANDLERS
  - Plugin handlers from plugin manager
  
- `GET /diag/functions`: Lists functions with usage confidence scores
  - Integrates with Python analyzer's FunctionUsageInfo
  - Returns status, confidence, and reasons for each function
  
- `POST /diag/validate-unused`: Validates unused functions against handlers
  - Cross-references detected unused functions with registered handlers
  - Returns false positives (functions registered as handlers but detected unused)
  
- `GET /diag/stats`: Runtime statistics
  - Uptime (seconds since server start)
  - Memory usage (MB)
  - Total route count
  - Registered handler counts
  
- `GET /diag/health`: Simple health check
  - Returns `{"status": "ok", "service": "autodiag"}`

### Dependencies
- FastAPI `APIRouter`
- `jupiter.server.routers` for API_HANDLERS registry
- `jupiter.cli.main` for CLI_HANDLERS registry
- `jupiter.core.plugin_manager` for PluginManager
- `psutil` for memory usage (optional, graceful fallback)

### Security
- Router designed to run on localhost-only port (127.0.0.1)
- No authentication required (local access assumption)
- No sensitive data exposure (code analysis only)
