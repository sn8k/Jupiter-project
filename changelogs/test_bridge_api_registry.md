# Changelog – tests/test_bridge_api_registry.py

## v0.2.0

### Added
- **Permission Validation Tests**
  - `TestRoutePermissionConfig` (2 tests):
    - test_creates_with_required_fields
    - test_creates_with_all_options
  - `TestPermissionValidationResult` (3 tests):
    - test_creates_allowed_result
    - test_creates_denied_result
    - test_to_dict_serializes_result
  - `TestAPIPermissionValidator` (14 tests):
    - test_creates_with_registry
    - test_creates_with_permission_checker
    - test_extract_plugin_id_from_path
    - test_extract_plugin_id_returns_none_for_non_plugin_paths
    - test_should_bypass_standard_paths
    - test_should_bypass_plugin_health_metrics
    - test_should_not_bypass_regular_plugin_routes
    - test_add_and_remove_bypass_path
    - test_validate_allows_non_plugin_routes
    - test_validate_allows_bypass_paths
    - test_validate_denies_unregistered_plugin
    - test_validate_allows_with_permissions
    - test_validate_denies_without_permissions
    - test_configure_route_permissions
    - test_set_plugin_requirements
    - test_get_stats_returns_statistics
    - test_reset_stats
  - `TestAPIPermissionValidatorMiddleware` (3 tests):
    - test_middleware_allows_valid_request
    - test_middleware_denies_unauthorized_request
    - test_middleware_bypasses_health
  - `TestRequirePluginPermissionDecorator` (3 tests):
    - test_allows_with_all_permissions
    - test_denies_missing_permissions
    - test_allows_with_any_permission_when_require_all_false
  - `TestGlobalPermissionValidator` (2 tests):
    - test_get_permission_validator_returns_singleton
    - test_reset_clears_permission_validator

### Changed
- Updated imports to include new permission validation classes
- Tests now use `request=request` keyword argument for decorator tests

### Stats
- Total tests: 71 (was 41)
- New tests added: 30

---

## v0.1.0

### Initial Implementation
- 41 tests covering:
  - HTTPMethod enum
  - RegisteredRoute dataclass
  - PluginRouter dataclass
  - APIRegistry class (permissions, routes, validation, endpoints, queries, unregister, serialization)
  - Global registry functions
