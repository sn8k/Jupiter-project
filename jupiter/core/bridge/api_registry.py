"""API Registry for Jupiter Plugin Bridge.

Version: 0.1.0

This module provides a registry for API contributions from plugins.
It allows plugins to register FastAPI routes that are dynamically
mounted by the server.

Features:
- Register and unregister API routes per plugin
- Automatic route prefixing under /plugins/<plugin_id>/
- Permission checking for route registration
- Standard plugin endpoints (health, metrics, config, logs)
- OpenAPI schema integration
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from jupiter.core.bridge.interfaces import APIContribution, Permission
from jupiter.core.bridge.exceptions import (
    PluginError,
    PermissionDeniedError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class HTTPMethod(str, Enum):
    """Supported HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass
class RegisteredRoute:
    """Represents a registered API route."""
    
    plugin_id: str
    path: str
    method: HTTPMethod
    handler: Callable[..., Any]
    description: str = ""
    summary: str = ""
    tags: List[str] = field(default_factory=list)
    auth_required: bool = False
    deprecated: bool = False
    response_model: Optional[Any] = None
    
    @property
    def full_path(self) -> str:
        """Get full path including plugin prefix."""
        return f"/plugins/{self.plugin_id}{self.path}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "plugin_id": self.plugin_id,
            "path": self.path,
            "full_path": self.full_path,
            "method": self.method.value,
            "description": self.description,
            "summary": self.summary,
            "tags": self.tags,
            "auth_required": self.auth_required,
            "deprecated": self.deprecated,
        }


@dataclass
class PluginRouter:
    """Represents a plugin's router configuration."""
    
    plugin_id: str
    prefix: str
    tags: List[str] = field(default_factory=list)
    routes: List[RegisteredRoute] = field(default_factory=list)
    
    @property
    def route_count(self) -> int:
        """Get number of routes."""
        return len(self.routes)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "plugin_id": self.plugin_id,
            "prefix": self.prefix,
            "tags": self.tags,
            "route_count": self.route_count,
            "routes": [r.to_dict() for r in self.routes],
        }


class APIRegistry:
    """Registry for API contributions from plugins.
    
    The API Registry manages all API routes contributed by plugins.
    It handles:
    - Route registration and unregistration
    - Automatic prefixing under /plugins/<plugin_id>/
    - Permission checking
    - Standard plugin endpoints
    
    Usage:
        registry = APIRegistry()
        
        # Register a route
        registry.register_route(
            plugin_id="my_plugin",
            path="/analyze",
            method=HTTPMethod.POST,
            handler=my_analyze_handler,
            description="Run custom analysis",
        )
        
        # Get all routes for mounting
        routes = registry.get_all_routes()
    """
    
    # Standard plugin endpoints that are auto-generated
    STANDARD_ENDPOINTS = frozenset({
        "/health",
        "/metrics",
        "/config",
        "/logs",
    })
    
    def __init__(self):
        """Initialize the API registry."""
        # plugin_id -> PluginRouter
        self._routers: Dict[str, PluginRouter] = {}
        # Permission tracking: plugin_id -> set of permissions
        self._permissions: Dict[str, Set[Permission]] = {}
        # Track which plugins have standard endpoints enabled
        self._standard_endpoints_enabled: Dict[str, Set[str]] = {}
    
    def set_plugin_permissions(
        self,
        plugin_id: str,
        permissions: Set[Permission],
    ) -> None:
        """Set permissions for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            permissions: Set of granted permissions
        """
        self._permissions[plugin_id] = permissions.copy()
    
    def _check_permission(self, plugin_id: str) -> None:
        """Check if plugin has permission to register API routes.
        
        Args:
            plugin_id: Plugin identifier
            
        Raises:
            PermissionDeniedError: If plugin lacks permission
        """
        perms = self._permissions.get(plugin_id, set())
        if Permission.REGISTER_API not in perms:
            raise PermissionDeniedError(
                f"Plugin '{plugin_id}' does not have permission to register API routes",
                plugin_id=plugin_id,
                permission=Permission.REGISTER_API,
            )
    
    def _ensure_router(self, plugin_id: str) -> PluginRouter:
        """Ensure a router exists for the plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            PluginRouter for the plugin
        """
        if plugin_id not in self._routers:
            self._routers[plugin_id] = PluginRouter(
                plugin_id=plugin_id,
                prefix=f"/plugins/{plugin_id}",
                tags=[f"plugin:{plugin_id}"],
            )
        return self._routers[plugin_id]
    
    def register_route(
        self,
        plugin_id: str,
        path: str,
        method: HTTPMethod,
        handler: Callable[..., Any],
        description: str = "",
        summary: str = "",
        tags: Optional[List[str]] = None,
        auth_required: bool = False,
        deprecated: bool = False,
        response_model: Optional[Any] = None,
        check_permissions: bool = True,
    ) -> RegisteredRoute:
        """Register an API route for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            path: Route path (will be prefixed with /plugins/<plugin_id>)
            method: HTTP method
            handler: Route handler function
            description: Route description for docs
            summary: Short summary for docs
            tags: OpenAPI tags
            auth_required: Whether auth is required
            deprecated: Whether route is deprecated
            response_model: Pydantic model for response
            check_permissions: Whether to check plugin permissions
            
        Returns:
            RegisteredRoute object
            
        Raises:
            PermissionDeniedError: If plugin lacks permission
            ValidationError: If path is invalid or conflicts
        """
        if check_permissions:
            self._check_permission(plugin_id)
        
        # Validate path
        self._validate_path(path, plugin_id)
        
        route = RegisteredRoute(
            plugin_id=plugin_id,
            path=path,
            method=method,
            handler=handler,
            description=description,
            summary=summary,
            tags=tags or [f"plugin:{plugin_id}"],
            auth_required=auth_required,
            deprecated=deprecated,
            response_model=response_model,
        )
        
        router = self._ensure_router(plugin_id)
        router.routes.append(route)
        
        logger.debug(
            "Registered API route %s %s for plugin '%s'",
            method.value,
            route.full_path,
            plugin_id
        )
        
        return route
    
    def register_from_contribution(
        self,
        plugin_id: str,
        contribution: APIContribution,
        handler: Optional[Callable[..., Any]] = None,
        check_permissions: bool = True,
    ) -> RegisteredRoute:
        """Register a route from an APIContribution.
        
        Args:
            plugin_id: Plugin identifier
            contribution: API contribution from manifest
            handler: Handler function (required)
            check_permissions: Whether to check plugin permissions
            
        Returns:
            RegisteredRoute object
        """
        if handler is None:
            raise ValidationError(
                "Handler is required for API contribution registration",
                validation_errors=["handler cannot be None"],
            )
        
        method = HTTPMethod(contribution.method.upper())
        
        return self.register_route(
            plugin_id=plugin_id,
            path=contribution.path,
            method=method,
            handler=handler,
            tags=contribution.tags,
            auth_required=contribution.auth_required,
            check_permissions=check_permissions,
        )
    
    def enable_standard_endpoints(
        self,
        plugin_id: str,
        endpoints: Optional[List[str]] = None,
        check_permissions: bool = True,
    ) -> List[str]:
        """Enable standard plugin endpoints.
        
        Standard endpoints include:
        - /health: Health check
        - /metrics: Plugin metrics
        - /config: Configuration GET/PUT
        - /logs: Log access
        
        Args:
            plugin_id: Plugin identifier
            endpoints: List of endpoints to enable (default: all)
            check_permissions: Whether to check permissions
            
        Returns:
            List of enabled endpoint paths
        """
        if check_permissions:
            self._check_permission(plugin_id)
        
        # Default to all standard endpoints
        to_enable = set(endpoints or self.STANDARD_ENDPOINTS)
        
        # Filter to valid endpoints
        valid = to_enable & self.STANDARD_ENDPOINTS
        
        if plugin_id not in self._standard_endpoints_enabled:
            self._standard_endpoints_enabled[plugin_id] = set()
        
        self._standard_endpoints_enabled[plugin_id].update(valid)
        
        logger.debug(
            "Enabled standard endpoints for plugin '%s': %s",
            plugin_id,
            valid
        )
        
        return list(valid)
    
    def get_standard_endpoints(self, plugin_id: str) -> Set[str]:
        """Get enabled standard endpoints for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Set of enabled endpoint paths
        """
        return self._standard_endpoints_enabled.get(plugin_id, set()).copy()
    
    def unregister_route(
        self,
        plugin_id: str,
        path: str,
        method: HTTPMethod,
    ) -> bool:
        """Unregister an API route.
        
        Args:
            plugin_id: Plugin identifier
            path: Route path
            method: HTTP method
            
        Returns:
            True if route was removed
        """
        if plugin_id not in self._routers:
            return False
        
        router = self._routers[plugin_id]
        for i, route in enumerate(router.routes):
            if route.path == path and route.method == method:
                router.routes.pop(i)
                logger.debug(
                    "Unregistered API route %s %s for plugin '%s'",
                    method.value,
                    path,
                    plugin_id
                )
                return True
        
        return False
    
    def unregister_plugin(self, plugin_id: str) -> int:
        """Unregister all routes for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Number of routes removed
        """
        count = 0
        
        if plugin_id in self._routers:
            count = len(self._routers[plugin_id].routes)
            del self._routers[plugin_id]
        
        # Also clean up standard endpoints and permissions
        self._standard_endpoints_enabled.pop(plugin_id, None)
        self._permissions.pop(plugin_id, None)
        
        if count > 0:
            logger.debug(
                "Unregistered %d API routes for plugin '%s'",
                count,
                plugin_id
            )
        
        return count
    
    def get_route(
        self,
        plugin_id: str,
        path: str,
        method: HTTPMethod,
    ) -> Optional[RegisteredRoute]:
        """Get a registered route.
        
        Args:
            plugin_id: Plugin identifier
            path: Route path
            method: HTTP method
            
        Returns:
            RegisteredRoute or None if not found
        """
        if plugin_id not in self._routers:
            return None
        
        for route in self._routers[plugin_id].routes:
            if route.path == path and route.method == method:
                return route
        
        return None
    
    def get_plugin_routes(self, plugin_id: str) -> List[RegisteredRoute]:
        """Get all routes for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            List of routes
        """
        if plugin_id not in self._routers:
            return []
        return self._routers[plugin_id].routes.copy()
    
    def get_all_routes(self) -> List[RegisteredRoute]:
        """Get all registered routes.
        
        Returns:
            List of all routes
        """
        result = []
        for router in self._routers.values():
            result.extend(router.routes)
        return result
    
    def get_router(self, plugin_id: str) -> Optional[PluginRouter]:
        """Get a plugin's router.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            PluginRouter or None if not found
        """
        return self._routers.get(plugin_id)
    
    def get_all_routers(self) -> List[PluginRouter]:
        """Get all plugin routers.
        
        Returns:
            List of all routers
        """
        return list(self._routers.values())
    
    def get_plugins_with_routes(self) -> List[str]:
        """Get list of plugin IDs that have registered routes.
        
        Returns:
            List of plugin IDs
        """
        return list(self._routers.keys())
    
    def get_routes_by_method(self, method: HTTPMethod) -> List[RegisteredRoute]:
        """Get all routes for a specific method.
        
        Args:
            method: HTTP method
            
        Returns:
            List of routes
        """
        result = []
        for router in self._routers.values():
            for route in router.routes:
                if route.method == method:
                    result.append(route)
        return result
    
    def get_routes_by_tag(self, tag: str) -> List[RegisteredRoute]:
        """Get all routes with a specific tag.
        
        Args:
            tag: OpenAPI tag
            
        Returns:
            List of routes
        """
        result = []
        for router in self._routers.values():
            for route in router.routes:
                if tag in route.tags:
                    result.append(route)
        return result
    
    def _validate_path(self, path: str, plugin_id: str) -> None:
        """Validate a route path.
        
        Args:
            path: Route path
            plugin_id: Plugin identifier
            
        Raises:
            ValidationError: If path is invalid
        """
        if not path:
            raise ValidationError(
                "Route path cannot be empty",
                validation_errors=["path is required"],
            )
        
        if not path.startswith("/"):
            raise ValidationError(
                f"Route path must start with /: {path}",
                validation_errors=["path must start with /"],
            )
        
        # Check for path traversal
        if ".." in path:
            raise ValidationError(
                f"Route path cannot contain '..': {path}",
                validation_errors=["path traversal not allowed"],
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize registry state to dictionary.
        
        Returns:
            Dictionary with routers and settings
        """
        return {
            "routers": {
                plugin_id: router.to_dict()
                for plugin_id, router in self._routers.items()
            },
            "standard_endpoints": {
                plugin_id: list(endpoints)
                for plugin_id, endpoints in self._standard_endpoints_enabled.items()
            },
            "total_routes": sum(r.route_count for r in self._routers.values()),
        }


# Global API registry instance
_api_registry: Optional[APIRegistry] = None


def get_api_registry() -> APIRegistry:
    """Get the global API registry instance.
    
    Returns:
        APIRegistry singleton
    """
    global _api_registry
    if _api_registry is None:
        _api_registry = APIRegistry()
    return _api_registry


def reset_api_registry() -> None:
    """Reset the global API registry (for testing)."""
    global _api_registry
    _api_registry = None
