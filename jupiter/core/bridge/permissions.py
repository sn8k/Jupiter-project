"""Permission System for Jupiter Plugin Bridge.

Version: 0.1.0

This module provides granular permission checking and enforcement for plugins.
It implements the permission model defined in the plugin architecture spec.

Permissions:
- FS_READ: Allow reading files from the filesystem
- FS_WRITE: Allow writing files to the filesystem  
- RUN_COMMANDS: Allow executing shell commands via runner
- NETWORK_OUTBOUND: Allow making outbound HTTP requests
- ACCESS_MEETING: Allow accessing Meeting adapter
- ACCESS_CONFIG: Allow reading/writing configuration
- EMIT_EVENTS: Allow emitting events on the event bus
- REGISTER_API: Allow registering API routes
- REGISTER_CLI: Allow registering CLI commands
- REGISTER_UI: Allow registering UI components

The PermissionChecker class provides:
- Central permission verification
- Logging of permission checks (for audit)
- Permission enforcement with clear error messages
- Scoped permission checking for specific operations
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, TYPE_CHECKING
from functools import wraps

from jupiter.core.bridge.interfaces import Permission
from jupiter.core.bridge.exceptions import PermissionDeniedError

if TYPE_CHECKING:
    from jupiter.core.bridge.bridge import Bridge

logger = logging.getLogger(__name__)

__version__ = "0.1.0"


# =============================================================================
# PERMISSION CHECKER
# =============================================================================

@dataclass
class PermissionCheckResult:
    """Result of a permission check."""
    
    granted: bool
    permission: Permission
    plugin_id: str
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "granted": self.granted,
            "permission": self.permission.value,
            "plugin_id": self.plugin_id,
            "reason": self.reason,
        }


class PermissionChecker:
    """Central permission checking service.
    
    The PermissionChecker provides:
    - Verification that plugins have required permissions
    - Logging of all permission checks for audit trails
    - Enforcement via exceptions or return values
    - Scoped checks for specific operation types
    
    Usage:
        checker = PermissionChecker(bridge)
        
        # Check permission
        if checker.has_permission("my_plugin", Permission.FS_READ):
            # Read file...
        
        # Require permission (raises on failure)
        checker.require_permission("my_plugin", Permission.RUN_COMMANDS)
        
        # Check with context
        result = checker.check_permission("my_plugin", Permission.NETWORK_OUTBOUND)
        if not result.granted:
            logger.warning(f"Denied: {result.reason}")
    """
    
    def __init__(self, bridge: Optional["Bridge"] = None):
        """Initialize the permission checker.
        
        Args:
            bridge: Bridge instance for plugin permission lookup.
                   If None, all permissions are denied by default.
        """
        self._bridge = bridge
        self._check_log: List[PermissionCheckResult] = []
        self._max_log_size = 1000
        
        logger.debug("PermissionChecker initialized")
    
    def set_bridge(self, bridge: "Bridge") -> None:
        """Set the bridge instance.
        
        Args:
            bridge: Bridge instance.
        """
        self._bridge = bridge
    
    def get_plugin_permissions(self, plugin_id: str) -> Set[Permission]:
        """Get the permissions granted to a plugin.
        
        Args:
            plugin_id: Plugin identifier.
            
        Returns:
            Set of granted permissions.
        """
        if not self._bridge:
            return set()
        
        plugin_info = self._bridge.get_plugin(plugin_id)
        if not plugin_info:
            return set()
        
        # Get permissions from manifest (PluginInfo has manifest attribute)
        if hasattr(plugin_info, "manifest") and plugin_info.manifest:
            manifest = plugin_info.manifest
            if hasattr(manifest, "permissions"):
                return set(manifest.permissions)
        
        return set()
    
    def has_permission(self, plugin_id: str, permission: Permission) -> bool:
        """Check if a plugin has a specific permission.
        
        This method does NOT log the check. Use check_permission() for
        logged checks.
        
        Args:
            plugin_id: Plugin identifier.
            permission: Permission to check.
            
        Returns:
            True if the plugin has the permission.
        """
        permissions = self.get_plugin_permissions(plugin_id)
        return permission in permissions
    
    def check_permission(
        self,
        plugin_id: str,
        permission: Permission,
        context: str = "",
    ) -> PermissionCheckResult:
        """Check a permission and log the result.
        
        Args:
            plugin_id: Plugin identifier.
            permission: Permission to check.
            context: Optional context string for logging.
            
        Returns:
            PermissionCheckResult with granted status and reason.
        """
        granted = self.has_permission(plugin_id, permission)
        
        if granted:
            reason = f"Permission {permission.value} granted"
        else:
            reason = f"Permission {permission.value} not granted to plugin {plugin_id}"
        
        result = PermissionCheckResult(
            granted=granted,
            permission=permission,
            plugin_id=plugin_id,
            reason=reason,
        )
        
        # Log the check
        self._log_check(result, context)
        
        return result
    
    def require_permission(
        self,
        plugin_id: str,
        permission: Permission,
        context: str = "",
    ) -> None:
        """Require a plugin to have a permission, raise if not.
        
        Args:
            plugin_id: Plugin identifier.
            permission: Required permission.
            context: Optional context string for error message.
            
        Raises:
            PermissionDeniedError: If the plugin lacks the permission.
        """
        result = self.check_permission(plugin_id, permission, context)
        
        if not result.granted:
            raise PermissionDeniedError(
                f"Plugin '{plugin_id}' lacks required permission: {permission.value}"
                + (f" (context: {context})" if context else ""),
                plugin_id=plugin_id,
                permission=permission.value,
            )
    
    def require_any_permission(
        self,
        plugin_id: str,
        permissions: List[Permission],
        context: str = "",
    ) -> Permission:
        """Require at least one of the given permissions.
        
        Args:
            plugin_id: Plugin identifier.
            permissions: List of acceptable permissions.
            context: Optional context string.
            
        Returns:
            The first permission found to be granted.
            
        Raises:
            PermissionDeniedError: If none of the permissions are granted.
        """
        for perm in permissions:
            if self.has_permission(plugin_id, perm):
                self._log_check(
                    PermissionCheckResult(
                        granted=True,
                        permission=perm,
                        plugin_id=plugin_id,
                        reason=f"Has one of required permissions: {perm.value}",
                    ),
                    context,
                )
                return perm
        
        perm_names = [p.value for p in permissions]
        raise PermissionDeniedError(
            f"Plugin '{plugin_id}' lacks any of required permissions: {perm_names}",
            plugin_id=plugin_id,
            permission=perm_names[0] if perm_names else "unknown",
        )
    
    def require_all_permissions(
        self,
        plugin_id: str,
        permissions: List[Permission],
        context: str = "",
    ) -> None:
        """Require all of the given permissions.
        
        Args:
            plugin_id: Plugin identifier.
            permissions: List of required permissions.
            context: Optional context string.
            
        Raises:
            PermissionDeniedError: If any permission is missing.
        """
        for perm in permissions:
            self.require_permission(plugin_id, perm, context)
    
    # =========================================================================
    # SCOPED PERMISSION CHECKS
    # =========================================================================
    
    def check_fs_read(self, plugin_id: str, path: Optional[Path] = None) -> bool:
        """Check if plugin can read from filesystem.
        
        Args:
            plugin_id: Plugin identifier.
            path: Optional path being read (for logging).
            
        Returns:
            True if read is allowed.
        """
        context = f"read {path}" if path else "filesystem read"
        result = self.check_permission(plugin_id, Permission.FS_READ, context)
        return result.granted
    
    def check_fs_write(self, plugin_id: str, path: Optional[Path] = None) -> bool:
        """Check if plugin can write to filesystem.
        
        Args:
            plugin_id: Plugin identifier.
            path: Optional path being written (for logging).
            
        Returns:
            True if write is allowed.
        """
        context = f"write {path}" if path else "filesystem write"
        result = self.check_permission(plugin_id, Permission.FS_WRITE, context)
        return result.granted
    
    def check_run_command(self, plugin_id: str, command: str = "") -> bool:
        """Check if plugin can execute shell commands.
        
        Args:
            plugin_id: Plugin identifier.
            command: Optional command being run (for logging).
            
        Returns:
            True if command execution is allowed.
        """
        context = f"run command: {command[:50]}..." if command else "command execution"
        result = self.check_permission(plugin_id, Permission.RUN_COMMANDS, context)
        return result.granted
    
    def check_network(self, plugin_id: str, url: str = "") -> bool:
        """Check if plugin can make outbound network requests.
        
        Args:
            plugin_id: Plugin identifier.
            url: Optional URL being accessed (for logging).
            
        Returns:
            True if network access is allowed.
        """
        context = f"network request to {url}" if url else "network access"
        result = self.check_permission(plugin_id, Permission.NETWORK_OUTBOUND, context)
        return result.granted
    
    def check_meeting_access(self, plugin_id: str) -> bool:
        """Check if plugin can access Meeting adapter.
        
        Args:
            plugin_id: Plugin identifier.
            
        Returns:
            True if Meeting access is allowed.
        """
        result = self.check_permission(plugin_id, Permission.ACCESS_MEETING, "Meeting access")
        return result.granted
    
    def check_config_access(self, plugin_id: str, operation: str = "") -> bool:
        """Check if plugin can access configuration.
        
        Args:
            plugin_id: Plugin identifier.
            operation: Optional operation type (read/write).
            
        Returns:
            True if config access is allowed.
        """
        context = f"config {operation}" if operation else "config access"
        result = self.check_permission(plugin_id, Permission.ACCESS_CONFIG, context)
        return result.granted
    
    def check_emit_events(self, plugin_id: str, topic: str = "") -> bool:
        """Check if plugin can emit events.
        
        Args:
            plugin_id: Plugin identifier.
            topic: Optional event topic (for logging).
            
        Returns:
            True if event emission is allowed.
        """
        context = f"emit event: {topic}" if topic else "event emission"
        result = self.check_permission(plugin_id, Permission.EMIT_EVENTS, context)
        return result.granted
    
    # =========================================================================
    # LOGGING AND AUDIT
    # =========================================================================
    
    def _log_check(self, result: PermissionCheckResult, context: str = "") -> None:
        """Log a permission check result.
        
        Args:
            result: The check result.
            context: Optional context string.
        """
        # Add to in-memory log
        self._check_log.append(result)
        
        # Trim log if too large
        if len(self._check_log) > self._max_log_size:
            self._check_log = self._check_log[-self._max_log_size:]
        
        # Log to logger
        if result.granted:
            logger.debug(
                "Permission check: %s granted %s%s",
                result.plugin_id,
                result.permission.value,
                f" ({context})" if context else "",
            )
        else:
            logger.warning(
                "Permission check: %s DENIED %s%s",
                result.plugin_id,
                result.permission.value,
                f" ({context})" if context else "",
            )
    
    def get_check_log(
        self,
        plugin_id: Optional[str] = None,
        permission: Optional[Permission] = None,
        granted_only: bool = False,
        denied_only: bool = False,
        limit: int = 100,
    ) -> List[PermissionCheckResult]:
        """Get permission check log with optional filters.
        
        Args:
            plugin_id: Filter by plugin ID.
            permission: Filter by permission type.
            granted_only: Only return granted checks.
            denied_only: Only return denied checks.
            limit: Maximum number of results.
            
        Returns:
            List of matching PermissionCheckResult entries.
        """
        results = self._check_log.copy()
        
        if plugin_id:
            results = [r for r in results if r.plugin_id == plugin_id]
        
        if permission:
            results = [r for r in results if r.permission == permission]
        
        if granted_only:
            results = [r for r in results if r.granted]
        elif denied_only:
            results = [r for r in results if not r.granted]
        
        return results[-limit:]
    
    def clear_log(self) -> None:
        """Clear the permission check log."""
        self._check_log.clear()
        logger.debug("Permission check log cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get permission check statistics.
        
        Returns:
            Dictionary with check statistics.
        """
        total = len(self._check_log)
        granted = sum(1 for r in self._check_log if r.granted)
        denied = total - granted
        
        # Count by permission
        by_permission: Dict[str, Dict[str, int]] = {}
        for result in self._check_log:
            perm = result.permission.value
            if perm not in by_permission:
                by_permission[perm] = {"granted": 0, "denied": 0}
            if result.granted:
                by_permission[perm]["granted"] += 1
            else:
                by_permission[perm]["denied"] += 1
        
        return {
            "total_checks": total,
            "granted": granted,
            "denied": denied,
            "grant_rate": granted / total if total > 0 else 0,
            "by_permission": by_permission,
        }


# =============================================================================
# DECORATORS
# =============================================================================

def require_permission(permission: Permission):
    """Decorator to require a permission for a function call.
    
    The decorated function must have 'plugin_id' as a keyword argument
    or first positional argument.
    
    Usage:
        @require_permission(Permission.FS_READ)
        def read_file(plugin_id: str, path: Path) -> str:
            ...
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Get plugin_id from kwargs or first arg
            plugin_id = kwargs.get("plugin_id")
            if plugin_id is None and args:
                plugin_id = args[0]
            
            if not plugin_id:
                raise ValueError("plugin_id is required for permission check")
            
            # Get global checker
            checker = get_permission_checker()
            checker.require_permission(plugin_id, permission, func.__name__)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# =============================================================================
# MODULE-LEVEL SINGLETON
# =============================================================================

_checker: Optional[PermissionChecker] = None


def get_permission_checker() -> PermissionChecker:
    """Get the global PermissionChecker instance.
    
    Returns:
        The singleton PermissionChecker.
    """
    global _checker
    if _checker is None:
        _checker = PermissionChecker()
    return _checker


def init_permission_checker(bridge: Optional["Bridge"] = None) -> PermissionChecker:
    """Initialize the global PermissionChecker.
    
    Args:
        bridge: Optional Bridge instance.
        
    Returns:
        The initialized PermissionChecker.
    """
    global _checker
    _checker = PermissionChecker(bridge)
    logger.info("PermissionChecker initialized")
    return _checker


def shutdown_permission_checker() -> None:
    """Shutdown the global PermissionChecker."""
    global _checker
    if _checker:
        _checker.clear_log()
        _checker = None
        logger.info("PermissionChecker shutdown")
