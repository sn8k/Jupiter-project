"""Tests for jupiter.core.bridge.api_registry module.

Version: 0.1.0

Tests for the API Registry functionality.
"""

import pytest
from typing import Any
from unittest.mock import MagicMock

from jupiter.core.bridge.api_registry import (
    APIRegistry,
    HTTPMethod,
    RegisteredRoute,
    PluginRouter,
    get_api_registry,
    reset_api_registry,
)
from jupiter.core.bridge.interfaces import (
    APIContribution,
    Permission,
)
from jupiter.core.bridge.exceptions import (
    PermissionDeniedError,
    ValidationError,
)


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset the global API registry before and after each test."""
    reset_api_registry()
    yield
    reset_api_registry()


@pytest.fixture
def registry() -> APIRegistry:
    """Create a fresh API registry."""
    return APIRegistry()


@pytest.fixture
def handler() -> MagicMock:
    """Create a mock route handler."""
    return MagicMock(return_value={"status": "ok"})


# =============================================================================
# HTTPMethod Tests
# =============================================================================

class TestHTTPMethod:
    """Tests for HTTPMethod enum."""
    
    def test_standard_methods_defined(self):
        """Standard HTTP methods should be defined."""
        assert HTTPMethod.GET.value == "GET"
        assert HTTPMethod.POST.value == "POST"
        assert HTTPMethod.PUT.value == "PUT"
        assert HTTPMethod.PATCH.value == "PATCH"
        assert HTTPMethod.DELETE.value == "DELETE"
        assert HTTPMethod.HEAD.value == "HEAD"
        assert HTTPMethod.OPTIONS.value == "OPTIONS"


# =============================================================================
# RegisteredRoute Tests
# =============================================================================

class TestRegisteredRoute:
    """Tests for RegisteredRoute dataclass."""
    
    def test_creates_with_required_fields(self, handler):
        """Should create route with required fields."""
        route = RegisteredRoute(
            plugin_id="test_plugin",
            path="/analyze",
            method=HTTPMethod.POST,
            handler=handler,
        )
        
        assert route.plugin_id == "test_plugin"
        assert route.path == "/analyze"
        assert route.method == HTTPMethod.POST
        assert route.handler is handler
    
    def test_full_path_includes_prefix(self, handler):
        """full_path should include plugin prefix."""
        route = RegisteredRoute(
            plugin_id="test",
            path="/run",
            method=HTTPMethod.GET,
            handler=handler,
        )
        
        assert route.full_path == "/plugins/test/run"
    
    def test_to_dict_serializes_all_fields(self, handler):
        """to_dict should serialize all fields."""
        route = RegisteredRoute(
            plugin_id="test_plugin",
            path="/endpoint",
            method=HTTPMethod.POST,
            handler=handler,
            description="Test endpoint",
            summary="Short summary",
            tags=["tag1", "tag2"],
            auth_required=True,
            deprecated=True,
        )
        
        data = route.to_dict()
        
        assert data["plugin_id"] == "test_plugin"
        assert data["path"] == "/endpoint"
        assert data["full_path"] == "/plugins/test_plugin/endpoint"
        assert data["method"] == "POST"
        assert data["description"] == "Test endpoint"
        assert data["summary"] == "Short summary"
        assert data["tags"] == ["tag1", "tag2"]
        assert data["auth_required"] is True
        assert data["deprecated"] is True


# =============================================================================
# PluginRouter Tests
# =============================================================================

class TestPluginRouter:
    """Tests for PluginRouter dataclass."""
    
    def test_creates_with_required_fields(self):
        """Should create router with required fields."""
        router = PluginRouter(
            plugin_id="test",
            prefix="/plugins/test",
        )
        
        assert router.plugin_id == "test"
        assert router.prefix == "/plugins/test"
        assert router.tags == []
        assert router.routes == []
    
    def test_route_count(self, handler):
        """route_count should return number of routes."""
        router = PluginRouter(
            plugin_id="test",
            prefix="/plugins/test",
            routes=[
                RegisteredRoute("test", "/a", HTTPMethod.GET, handler),
                RegisteredRoute("test", "/b", HTTPMethod.POST, handler),
            ]
        )
        
        assert router.route_count == 2
    
    def test_to_dict(self, handler):
        """to_dict should serialize fields."""
        route = RegisteredRoute("test", "/a", HTTPMethod.GET, handler)
        router = PluginRouter(
            plugin_id="test",
            prefix="/plugins/test",
            tags=["plugin:test"],
            routes=[route],
        )
        
        data = router.to_dict()
        
        assert data["plugin_id"] == "test"
        assert data["prefix"] == "/plugins/test"
        assert data["tags"] == ["plugin:test"]
        assert data["route_count"] == 1
        assert len(data["routes"]) == 1


# =============================================================================
# APIRegistry Permission Tests
# =============================================================================

class TestAPIRegistryPermissions:
    """Tests for API Registry permission checks."""
    
    def test_register_requires_permission(self, registry, handler):
        """Registration should require REGISTER_API permission."""
        with pytest.raises(PermissionDeniedError) as exc:
            registry.register_route(
                plugin_id="test",
                path="/test",
                method=HTTPMethod.GET,
                handler=handler,
            )
        
        assert "REGISTER_API" in str(exc.value) or "permission" in str(exc.value).lower()
    
    def test_register_with_permission_succeeds(self, registry, handler):
        """Registration should succeed with permission."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_API})
        
        route = registry.register_route(
            plugin_id="test",
            path="/test",
            method=HTTPMethod.GET,
            handler=handler,
        )
        
        assert route is not None
        assert route.path == "/test"
    
    def test_check_permissions_can_be_bypassed(self, registry, handler):
        """check_permissions=False should bypass check."""
        route = registry.register_route(
            plugin_id="test",
            path="/test",
            method=HTTPMethod.GET,
            handler=handler,
            check_permissions=False,
        )
        
        assert route is not None
    
    def test_enable_standard_endpoints_requires_permission(self, registry):
        """Enabling standard endpoints should require permission."""
        with pytest.raises(PermissionDeniedError):
            registry.enable_standard_endpoints("test")


# =============================================================================
# APIRegistry Route Registration Tests
# =============================================================================

class TestAPIRegistryRegisterRoute:
    """Tests for route registration."""
    
    def test_register_basic_route(self, registry, handler):
        """Should register a basic route."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_API})
        
        route = registry.register_route(
            plugin_id="test",
            path="/analyze",
            method=HTTPMethod.POST,
            handler=handler,
            description="Run analysis",
        )
        
        assert route.plugin_id == "test"
        assert route.path == "/analyze"
        assert route.method == HTTPMethod.POST
        assert route.description == "Run analysis"
    
    def test_register_route_with_all_options(self, registry, handler):
        """Should register route with all options."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_API})
        
        route = registry.register_route(
            plugin_id="test",
            path="/endpoint",
            method=HTTPMethod.PUT,
            handler=handler,
            description="Detailed description",
            summary="Short summary",
            tags=["custom-tag"],
            auth_required=True,
            deprecated=True,
        )
        
        assert route.summary == "Short summary"
        assert "custom-tag" in route.tags
        assert route.auth_required is True
        assert route.deprecated is True
    
    def test_register_creates_router(self, registry, handler):
        """Registration should create a router for the plugin."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_API})
        
        registry.register_route("test", "/test", HTTPMethod.GET, handler)
        
        router = registry.get_router("test")
        assert router is not None
        assert router.plugin_id == "test"
    
    def test_register_from_contribution(self, registry, handler):
        """Should register from APIContribution."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_API})
        
        contribution = APIContribution(
            path="/analyze",
            method="POST",
            entrypoint="my_plugin:analyze",
            tags=["analysis"],
            auth_required=True,
        )
        
        route = registry.register_from_contribution(
            plugin_id="test",
            contribution=contribution,
            handler=handler,
        )
        
        assert route.path == "/analyze"
        assert route.method == HTTPMethod.POST
        assert "analysis" in route.tags
        assert route.auth_required is True
    
    def test_register_contribution_requires_handler(self, registry):
        """register_from_contribution should require handler."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_API})
        
        contribution = APIContribution(
            path="/test",
            method="GET",
            entrypoint="test:handler",
        )
        
        with pytest.raises(ValidationError):
            registry.register_from_contribution(
                plugin_id="test",
                contribution=contribution,
                handler=None,
            )


# =============================================================================
# APIRegistry Validation Tests
# =============================================================================

class TestAPIRegistryValidation:
    """Tests for route path validation."""
    
    def test_empty_path_rejected(self, registry, handler):
        """Empty path should be rejected."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_API})
        
        with pytest.raises(ValidationError):
            registry.register_route(
                plugin_id="test",
                path="",
                method=HTTPMethod.GET,
                handler=handler,
            )
    
    def test_path_must_start_with_slash(self, registry, handler):
        """Path must start with /."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_API})
        
        with pytest.raises(ValidationError):
            registry.register_route(
                plugin_id="test",
                path="no-slash",
                method=HTTPMethod.GET,
                handler=handler,
            )
    
    def test_path_traversal_rejected(self, registry, handler):
        """Path traversal should be rejected."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_API})
        
        with pytest.raises(ValidationError):
            registry.register_route(
                plugin_id="test",
                path="/../../etc/passwd",
                method=HTTPMethod.GET,
                handler=handler,
            )


# =============================================================================
# APIRegistry Standard Endpoints Tests
# =============================================================================

class TestAPIRegistryStandardEndpoints:
    """Tests for standard plugin endpoints."""
    
    def test_enable_all_standard_endpoints(self, registry):
        """Should enable all standard endpoints by default."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_API})
        
        enabled = registry.enable_standard_endpoints("test")
        
        assert "/health" in enabled
        assert "/metrics" in enabled
        assert "/config" in enabled
        assert "/logs" in enabled
    
    def test_enable_specific_endpoints(self, registry):
        """Should enable only specified endpoints."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_API})
        
        enabled = registry.enable_standard_endpoints("test", ["/health", "/metrics"])
        
        assert "/health" in enabled
        assert "/metrics" in enabled
        assert "/config" not in enabled
        assert "/logs" not in enabled
    
    def test_get_standard_endpoints(self, registry):
        """get_standard_endpoints should return enabled endpoints."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_API})
        registry.enable_standard_endpoints("test", ["/health"])
        
        endpoints = registry.get_standard_endpoints("test")
        
        assert endpoints == {"/health"}
    
    def test_get_standard_endpoints_empty_for_unknown(self, registry):
        """get_standard_endpoints should return empty for unknown plugin."""
        endpoints = registry.get_standard_endpoints("unknown")
        assert endpoints == set()


# =============================================================================
# APIRegistry Query Tests
# =============================================================================

class TestAPIRegistryQueries:
    """Tests for querying registered routes."""
    
    def test_get_route_returns_registered(self, registry, handler):
        """get_route should return registered route."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_API})
        registry.register_route("test", "/endpoint", HTTPMethod.GET, handler)
        
        route = registry.get_route("test", "/endpoint", HTTPMethod.GET)
        
        assert route is not None
        assert route.path == "/endpoint"
    
    def test_get_route_returns_none_for_unknown(self, registry):
        """get_route should return None for unknown."""
        assert registry.get_route("test", "/unknown", HTTPMethod.GET) is None
    
    def test_get_plugin_routes(self, registry, handler):
        """get_plugin_routes should return all for plugin."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_API})
        registry.register_route("test", "/a", HTTPMethod.GET, handler)
        registry.register_route("test", "/b", HTTPMethod.POST, handler)
        
        routes = registry.get_plugin_routes("test")
        
        assert len(routes) == 2
    
    def test_get_plugin_routes_empty_for_unknown(self, registry):
        """get_plugin_routes should return empty for unknown plugin."""
        routes = registry.get_plugin_routes("unknown")
        assert routes == []
    
    def test_get_all_routes(self, registry, handler):
        """get_all_routes should return all registered."""
        registry.set_plugin_permissions("p1", {Permission.REGISTER_API})
        registry.set_plugin_permissions("p2", {Permission.REGISTER_API})
        
        registry.register_route("p1", "/a", HTTPMethod.GET, handler)
        registry.register_route("p2", "/b", HTTPMethod.POST, handler)
        
        routes = registry.get_all_routes()
        
        assert len(routes) == 2
    
    def test_get_router(self, registry, handler):
        """get_router should return plugin router."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_API})
        registry.register_route("test", "/test", HTTPMethod.GET, handler)
        
        router = registry.get_router("test")
        
        assert router is not None
        assert router.plugin_id == "test"
    
    def test_get_all_routers(self, registry, handler):
        """get_all_routers should return all routers."""
        registry.set_plugin_permissions("p1", {Permission.REGISTER_API})
        registry.set_plugin_permissions("p2", {Permission.REGISTER_API})
        
        registry.register_route("p1", "/a", HTTPMethod.GET, handler)
        registry.register_route("p2", "/b", HTTPMethod.GET, handler)
        
        routers = registry.get_all_routers()
        
        assert len(routers) == 2
    
    def test_get_plugins_with_routes(self, registry, handler):
        """get_plugins_with_routes should return plugin IDs."""
        registry.set_plugin_permissions("p1", {Permission.REGISTER_API})
        registry.set_plugin_permissions("p2", {Permission.REGISTER_API})
        
        registry.register_route("p1", "/a", HTTPMethod.GET, handler)
        registry.register_route("p2", "/b", HTTPMethod.GET, handler)
        
        plugins = registry.get_plugins_with_routes()
        
        assert set(plugins) == {"p1", "p2"}
    
    def test_get_routes_by_method(self, registry, handler):
        """get_routes_by_method should filter by method."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_API})
        registry.register_route("test", "/get", HTTPMethod.GET, handler)
        registry.register_route("test", "/post", HTTPMethod.POST, handler)
        registry.register_route("test", "/get2", HTTPMethod.GET, handler)
        
        get_routes = registry.get_routes_by_method(HTTPMethod.GET)
        
        assert len(get_routes) == 2
        assert all(r.method == HTTPMethod.GET for r in get_routes)
    
    def test_get_routes_by_tag(self, registry, handler):
        """get_routes_by_tag should filter by tag."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_API})
        registry.register_route("test", "/a", HTTPMethod.GET, handler, tags=["alpha"])
        registry.register_route("test", "/b", HTTPMethod.GET, handler, tags=["beta"])
        registry.register_route("test", "/c", HTTPMethod.GET, handler, tags=["alpha", "gamma"])
        
        alpha_routes = registry.get_routes_by_tag("alpha")
        
        assert len(alpha_routes) == 2


# =============================================================================
# APIRegistry Unregister Tests
# =============================================================================

class TestAPIRegistryUnregister:
    """Tests for unregistering routes."""
    
    def test_unregister_route(self, registry, handler):
        """unregister_route should remove route."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_API})
        registry.register_route("test", "/endpoint", HTTPMethod.GET, handler)
        
        result = registry.unregister_route("test", "/endpoint", HTTPMethod.GET)
        
        assert result is True
        assert registry.get_route("test", "/endpoint", HTTPMethod.GET) is None
    
    def test_unregister_returns_false_if_not_found(self, registry):
        """unregister_route should return False if not found."""
        result = registry.unregister_route("unknown", "/test", HTTPMethod.GET)
        assert result is False
    
    def test_unregister_plugin_removes_all(self, registry, handler):
        """unregister_plugin should remove all routes."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_API})
        registry.register_route("test", "/a", HTTPMethod.GET, handler)
        registry.register_route("test", "/b", HTTPMethod.POST, handler)
        registry.enable_standard_endpoints("test")
        
        count = registry.unregister_plugin("test")
        
        assert count == 2
        assert registry.get_plugin_routes("test") == []
        assert registry.get_standard_endpoints("test") == set()
    
    def test_unregister_plugin_returns_zero_if_none(self, registry):
        """unregister_plugin should return 0 if no routes."""
        count = registry.unregister_plugin("unknown")
        assert count == 0


# =============================================================================
# APIRegistry Serialization Tests
# =============================================================================

class TestAPIRegistrySerialization:
    """Tests for registry serialization."""
    
    def test_to_dict_empty(self, registry):
        """to_dict should work with empty registry."""
        data = registry.to_dict()
        
        assert data["routers"] == {}
        assert data["standard_endpoints"] == {}
        assert data["total_routes"] == 0
    
    def test_to_dict_with_routes(self, registry, handler):
        """to_dict should serialize routes."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_API})
        registry.register_route("test", "/endpoint", HTTPMethod.GET, handler)
        registry.enable_standard_endpoints("test", ["/health"])
        
        data = registry.to_dict()
        
        assert "test" in data["routers"]
        assert data["routers"]["test"]["route_count"] == 1
        assert "test" in data["standard_endpoints"]
        assert "/health" in data["standard_endpoints"]["test"]
        assert data["total_routes"] == 1


# =============================================================================
# Global Registry Tests
# =============================================================================

class TestGlobalAPIRegistry:
    """Tests for global API registry functions."""
    
    def test_get_api_registry_returns_singleton(self):
        """get_api_registry should return same instance."""
        r1 = get_api_registry()
        r2 = get_api_registry()
        
        assert r1 is r2
    
    def test_reset_api_registry_creates_new(self):
        """reset_api_registry should create new instance."""
        r1 = get_api_registry()
        reset_api_registry()
        r2 = get_api_registry()
        
        assert r1 is not r2
