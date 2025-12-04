"""API Registry for Jupiter Plugin Bridge.

Version: 0.2.0

This module provides a registry for API contributions from plugins.
It allows plugins to register FastAPI routes that are dynamically
mounted by the server.

Features:
- Register and unregister API routes per plugin
- Automatic route prefixing under /plugins/<plugin_id>/
- Permission checking for route registration
- Runtime permission validation via middleware
- Standard plugin endpoints (health, metrics, config, logs)
- OpenAPI schema integration
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, TYPE_CHECKING

from jupiter.core.bridge.interfaces import APIContribution, Permission
from jupiter.core.bridge.exceptions import (
    PluginError,
    PermissionDeniedError,
    ValidationError,
)

if TYPE_CHECKING:
    from fastapi import Request, Response
    from starlette.middleware.base import RequestResponseEndpoint

logger = logging.getLogger(__name__)

__version__ = "0.2.0"


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


# =============================================================================
# RUNTIME PERMISSION VALIDATION
# =============================================================================

# Pattern to extract plugin_id from path: /plugins/{plugin_id}/...
_PLUGIN_PATH_PATTERN = re.compile(r"^/plugins/([a-zA-Z_][a-zA-Z0-9_]*)(?:/.*)?$")


@dataclass
class RoutePermissionConfig:
    """Configuration for route-level permission requirements."""
    
    plugin_id: str
    path_pattern: str  # regex or exact path
    required_permissions: List[Permission]
    require_all: bool = True  # True=AND, False=OR
    description: str = ""


class PermissionValidationResult:
    """Result of permission validation for an API call."""
    
    def __init__(
        self,
        allowed: bool,
        plugin_id: Optional[str] = None,
        checked_permissions: Optional[List[Permission]] = None,
        denied_permissions: Optional[List[Permission]] = None,
        reason: str = "",
    ):
        self.allowed = allowed
        self.plugin_id = plugin_id
        self.checked_permissions = checked_permissions or []
        self.denied_permissions = denied_permissions or []
        self.reason = reason
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "allowed": self.allowed,
            "plugin_id": self.plugin_id,
            "checked_permissions": [p.value for p in self.checked_permissions],
            "denied_permissions": [p.value for p in self.denied_permissions],
            "reason": self.reason,
        }


class APIPermissionValidator:
    """Runtime permission validator for API routes.
    
    This class provides middleware and utilities for validating
    permissions when plugin API routes are called.
    
    Usage:
        validator = APIPermissionValidator(api_registry, permission_checker)
        
        # In FastAPI app setup
        app.middleware("http")(validator.middleware)
        
        # Or use the dependency
        @app.get("/plugins/{plugin_id}/action")
        async def action(validated: bool = Depends(validator.require_api_permission)):
            ...
    """
    
    def __init__(
        self,
        api_registry: "APIRegistry",
        permission_checker: Optional[Any] = None,
    ):
        """Initialize the validator.
        
        Args:
            api_registry: API registry instance
            permission_checker: PermissionChecker instance (optional)
        """
        self._registry = api_registry
        self._permission_checker = permission_checker
        
        # Route-specific permission requirements
        # path_pattern -> RoutePermissionConfig
        self._route_configs: Dict[str, RoutePermissionConfig] = {}
        
        # Plugin-level permission overrides
        # plugin_id -> set of always-required permissions
        self._plugin_requirements: Dict[str, Set[Permission]] = {}
        
        # Validation statistics
        self._stats = {
            "total_checks": 0,
            "allowed": 0,
            "denied": 0,
            "bypassed": 0,
        }
        
        # Paths that bypass permission checks (e.g., health endpoints)
        self._bypass_paths: Set[str] = {
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/redoc",
        }
        
        logger.debug("APIPermissionValidator initialized")
    
    def set_permission_checker(self, checker: Any) -> None:
        """Set the permission checker.
        
        Args:
            checker: PermissionChecker instance
        """
        self._permission_checker = checker
    
    def add_bypass_path(self, path: str) -> None:
        """Add a path that bypasses permission checks.
        
        Args:
            path: Path to bypass (exact match)
        """
        self._bypass_paths.add(path)
    
    def remove_bypass_path(self, path: str) -> None:
        """Remove a path from bypass list.
        
        Args:
            path: Path to remove
        """
        self._bypass_paths.discard(path)
    
    def configure_route(
        self,
        plugin_id: str,
        path_pattern: str,
        permissions: List[Permission],
        require_all: bool = True,
        description: str = "",
    ) -> None:
        """Configure permission requirements for a specific route.
        
        Args:
            plugin_id: Plugin identifier
            path_pattern: Path pattern (regex supported)
            permissions: Required permissions
            require_all: True to require ALL, False for ANY
            description: Description of the requirement
        """
        config = RoutePermissionConfig(
            plugin_id=plugin_id,
            path_pattern=path_pattern,
            required_permissions=permissions,
            require_all=require_all,
            description=description,
        )
        
        full_pattern = f"/plugins/{plugin_id}{path_pattern}"
        self._route_configs[full_pattern] = config
        
        logger.debug(
            "Configured route permissions: %s requires %s",
            full_pattern,
            [p.value for p in permissions],
        )
    
    def set_plugin_requirements(
        self,
        plugin_id: str,
        permissions: Set[Permission],
    ) -> None:
        """Set base permission requirements for all routes of a plugin.
        
        Args:
            plugin_id: Plugin identifier
            permissions: Set of always-required permissions
        """
        self._plugin_requirements[plugin_id] = permissions.copy()
    
    def extract_plugin_id(self, path: str) -> Optional[str]:
        """Extract plugin ID from request path.
        
        Args:
            path: Request path (e.g., /plugins/my_plugin/action)
            
        Returns:
            Plugin ID or None if not a plugin route
        """
        match = _PLUGIN_PATH_PATTERN.match(path)
        if match:
            return match.group(1)
        return None
    
    def should_bypass(self, path: str) -> bool:
        """Check if path should bypass permission validation.
        
        Args:
            path: Request path
            
        Returns:
            True if should bypass
        """
        # Check exact bypass paths
        if path in self._bypass_paths:
            return True
        
        # Check plugin standard endpoints (health, metrics)
        plugin_id = self.extract_plugin_id(path)
        if plugin_id:
            suffix = path[len(f"/plugins/{plugin_id}"):]
            if suffix in {"/health", "/metrics"}:
                return True
        
        return False
    
    def validate(self, path: str, method: str = "GET") -> PermissionValidationResult:
        """Validate permissions for a request.
        
        Args:
            path: Request path
            method: HTTP method
            
        Returns:
            PermissionValidationResult
        """
        self._stats["total_checks"] += 1
        
        # Check bypass
        if self.should_bypass(path):
            self._stats["bypassed"] += 1
            return PermissionValidationResult(
                allowed=True,
                reason="Path bypasses permission checks",
            )
        
        # Extract plugin ID
        plugin_id = self.extract_plugin_id(path)
        if not plugin_id:
            # Not a plugin route - allow
            self._stats["allowed"] += 1
            return PermissionValidationResult(
                allowed=True,
                reason="Not a plugin route",
            )
        
        # Check if plugin is registered
        if plugin_id not in self._registry._routers:
            self._stats["denied"] += 1
            return PermissionValidationResult(
                allowed=False,
                plugin_id=plugin_id,
                reason=f"Plugin '{plugin_id}' is not registered",
            )
        
        # Get permissions to check
        required: Set[Permission] = set()
        
        # Add plugin-level requirements
        if plugin_id in self._plugin_requirements:
            required.update(self._plugin_requirements[plugin_id])
        
        # Add REGISTER_API as base requirement
        required.add(Permission.REGISTER_API)
        
        # Check route-specific requirements
        for pattern, config in self._route_configs.items():
            if config.plugin_id == plugin_id:
                if re.match(pattern, path):
                    required.update(config.required_permissions)
        
        # Validate permissions
        if not self._permission_checker:
            # No checker - allow but warn
            logger.warning("No permission checker configured, allowing by default")
            self._stats["allowed"] += 1
            return PermissionValidationResult(
                allowed=True,
                plugin_id=plugin_id,
                checked_permissions=list(required),
                reason="Permission checker not configured",
            )
        
        # Check each required permission
        denied = []
        for perm in required:
            if not self._permission_checker.has_permission(plugin_id, perm):
                denied.append(perm)
        
        if denied:
            self._stats["denied"] += 1
            return PermissionValidationResult(
                allowed=False,
                plugin_id=plugin_id,
                checked_permissions=list(required),
                denied_permissions=denied,
                reason=f"Missing permissions: {[p.value for p in denied]}",
            )
        
        self._stats["allowed"] += 1
        return PermissionValidationResult(
            allowed=True,
            plugin_id=plugin_id,
            checked_permissions=list(required),
            reason="All permissions granted",
        )
    
    async def middleware(
        self,
        request: "Request",
        call_next: "RequestResponseEndpoint",
    ) -> "Response":
        """FastAPI middleware for permission validation.
        
        Usage:
            app.middleware("http")(validator.middleware)
        """
        from fastapi import HTTPException
        from starlette.responses import JSONResponse
        
        path = request.url.path
        method = request.method
        
        result = self.validate(path, method)
        
        if not result.allowed:
            logger.warning(
                "Permission denied for %s %s: %s",
                method,
                path,
                result.reason,
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Permission denied",
                    "detail": result.reason,
                    "plugin_id": result.plugin_id,
                    "denied_permissions": [p.value for p in result.denied_permissions],
                },
            )
        
        return await call_next(request)
    
    def get_stats(self) -> Dict[str, int]:
        """Get validation statistics.
        
        Returns:
            Dictionary with stats
        """
        return self._stats.copy()
    
    def reset_stats(self) -> None:
        """Reset validation statistics."""
        self._stats = {
            "total_checks": 0,
            "allowed": 0,
            "denied": 0,
            "bypassed": 0,
        }


def require_plugin_permission(
    *permissions: Permission,
    require_all: bool = True,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to require specific permissions for a route handler.
    
    This decorator wraps a route handler and validates that the calling
    plugin has the required permissions.
    
    Args:
        *permissions: Required permissions
        require_all: True to require ALL permissions, False for ANY
        
    Returns:
        Decorated function
        
    Usage:
        @router.get("/dangerous")
        @require_plugin_permission(Permission.RUN_COMMANDS, Permission.FS_WRITE)
        async def dangerous_action(request: Request):
            ...
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            from fastapi import HTTPException, Request
            
            # Try to get request from args or kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get("request")
            
            if not request:
                # No request context - allow (might be called internally)
                return await func(*args, **kwargs)
            
            # Get permission validator from app state
            validator = getattr(request.app.state, "permission_validator", None)
            if not validator:
                # No validator configured - allow
                return await func(*args, **kwargs)
            
            # Extract plugin ID from path
            plugin_id = validator.extract_plugin_id(str(request.url.path))
            if not plugin_id:
                # Not a plugin route
                return await func(*args, **kwargs)
            
            # Check permissions
            checker = validator._permission_checker
            if not checker:
                return await func(*args, **kwargs)
            
            missing = []
            granted = []
            for perm in permissions:
                if checker.has_permission(plugin_id, perm):
                    granted.append(perm)
                else:
                    missing.append(perm)
            
            # Evaluate requirement
            if require_all and missing:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Permission denied",
                        "plugin_id": plugin_id,
                        "required_permissions": [p.value for p in permissions],
                        "missing_permissions": [p.value for p in missing],
                    },
                )
            elif not require_all and not granted:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Permission denied",
                        "plugin_id": plugin_id,
                        "required_one_of": [p.value for p in permissions],
                    },
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Global API registry instance
_api_registry: Optional[APIRegistry] = None

# Global permission validator instance
_permission_validator: Optional[APIPermissionValidator] = None


def get_api_registry() -> APIRegistry:
    """Get the global API registry instance.
    
    Returns:
        APIRegistry singleton
    """
    global _api_registry
    if _api_registry is None:
        _api_registry = APIRegistry()
    return _api_registry


def get_permission_validator() -> APIPermissionValidator:
    """Get the global permission validator instance.
    
    Returns:
        APIPermissionValidator singleton
    """
    global _permission_validator, _api_registry
    if _permission_validator is None:
        if _api_registry is None:
            _api_registry = APIRegistry()
        _permission_validator = APIPermissionValidator(_api_registry)
    return _permission_validator


def reset_api_registry() -> None:
    """Reset the global API registry (for testing)."""
    global _api_registry, _permission_validator
    _api_registry = None
    _permission_validator = None
