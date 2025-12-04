# Changelog – jupiter/core/bridge/api_registry.py

## v0.2.0

### Added
- **Runtime Permission Validation System**
  - `RoutePermissionConfig`: Dataclass for route-level permission configuration
  - `PermissionValidationResult`: Class to represent validation results with details
  - `APIPermissionValidator`: Complete runtime permission validator class with:
    - Plugin ID extraction from request paths
    - Configurable bypass paths (health, metrics, docs)
    - Route-specific permission requirements
    - Plugin-level permission requirements
    - Validation statistics tracking
    - FastAPI middleware support
  - `require_plugin_permission`: Decorator for enforcing permissions on route handlers
  - `get_permission_validator()`: Global singleton accessor
  - Updated `reset_api_registry()` to also reset the permission validator

### Enhanced
- Exports updated in `bridge/__init__.py` to include:
  - `RoutePermissionConfig`
  - `PermissionValidationResult`
  - `APIPermissionValidator`
  - `require_plugin_permission`
  - `get_permission_validator`

### Tests
- Added 30 new tests for permission validation:
  - `TestRoutePermissionConfig` (2 tests)
  - `TestPermissionValidationResult` (3 tests)
  - `TestAPIPermissionValidator` (14 tests)
  - `TestAPIPermissionValidatorMiddleware` (3 tests)
  - `TestRequirePluginPermissionDecorator` (3 tests)
  - `TestGlobalPermissionValidator` (2 tests)
- Total tests in test_bridge_api_registry.py: 71

---

## v0.1.0

### Initial Implementation
- `HTTPMethod`: Enum for HTTP methods
- `RegisteredRoute`: Dataclass for registered routes
- `PluginRouter`: Dataclass for plugin router configuration
- `APIRegistry`: Main registry class with:
  - Route registration with permission checking
  - Standard endpoints (health, metrics, config, logs)
  - Route querying and filtering
  - OpenAPI schema generation
- Global `get_api_registry()` and `reset_api_registry()` functions
