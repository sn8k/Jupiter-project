"""Service Locator for Jupiter Plugin Bridge.

Version: 0.3.0

This module provides secure, scoped access to Jupiter's core services
for plugins. Each service is wrapped to enforce permissions and provide
plugin-specific configuration.

Services exposed:
- Logger: Pre-configured logger with plugin prefix
- Runner: Secure command execution wrapper
- History: Snapshot and history management
- Graph: Dependency graph builder
- Config: Plugin configuration with project overrides
- Events: Event bus for pub/sub communication
- ProjectManager: Access to project registry

Usage:
    from jupiter.core.bridge import Bridge
    
    bridge = Bridge.get_instance()
    services = bridge.get_services("my_plugin")
    
    logger = services.get_logger()
    logger.info("Plugin initialized")
    
    config = services.get_config()
    print(config.get("api_key"))

Changelog:
    0.3.0: Added global log level floor and per-plugin log level configuration
    0.2.0: Added PluginConfigManager integration
    0.1.0: Initial release with basic services
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from jupiter.core.bridge.exceptions import (
    PermissionDeniedError,
    ServiceNotFoundError,
)
from jupiter.core.bridge.interfaces import Permission

if TYPE_CHECKING:
    from jupiter.core.bridge.bridge import Bridge
    from jupiter.core.bridge.plugin_config import PluginConfigManager
    from jupiter.core.history import HistoryManager
    from jupiter.core.runner import CommandResult
    from jupiter.server.manager import ProjectManager

logger = logging.getLogger(__name__)

# Global log level floor - plugins cannot log below this level
_GLOBAL_LOG_LEVEL_FLOOR: int = logging.DEBUG
# Per-plugin log levels
_PLUGIN_LOG_LEVELS: Dict[str, int] = {}


def set_global_log_level_floor(level: int) -> None:
    """Set the global minimum log level for all plugins.
    
    Plugins cannot log more verbosely than this level.
    For example, if floor is WARNING, plugin DEBUG/INFO logs are suppressed.
    
    Args:
        level: Logging level (e.g., logging.INFO, logging.WARNING)
    """
    global _GLOBAL_LOG_LEVEL_FLOOR
    _GLOBAL_LOG_LEVEL_FLOOR = level


def get_global_log_level_floor() -> int:
    """Get the current global log level floor."""
    return _GLOBAL_LOG_LEVEL_FLOOR


def set_plugin_log_level(plugin_id: str, level: int) -> None:
    """Set the log level for a specific plugin.
    
    This is capped by the global floor - plugin cannot be more verbose
    than the global setting.
    
    Args:
        plugin_id: Plugin identifier
        level: Logging level for this plugin
    """
    _PLUGIN_LOG_LEVELS[plugin_id] = level


def get_plugin_log_level(plugin_id: str) -> Optional[int]:
    """Get the configured log level for a plugin, or None if not set."""
    return _PLUGIN_LOG_LEVELS.get(plugin_id)


def clear_plugin_log_levels() -> None:
    """Clear all per-plugin log level settings."""
    _PLUGIN_LOG_LEVELS.clear()


class PluginLogger:
    """Logger wrapper that prefixes all messages with plugin ID.
    
    This provides consistent logging format across all plugins and
    makes it easy to filter logs by plugin.
    
    Features:
    - All messages prefixed with [plugin:<plugin_id>]
    - Respects global log level floor (plugin cannot be more verbose)
    - Supports per-plugin log level configuration
    - Effective level = max(global_floor, plugin_level)
    """
    
    def __init__(self, plugin_id: str, base_logger: Optional[logging.Logger] = None):
        """Initialize plugin logger.
        
        Args:
            plugin_id: Plugin identifier for log prefix
            base_logger: Optional base logger, uses root if not provided
        """
        self._plugin_id = plugin_id
        self._logger = base_logger or logging.getLogger(f"jupiter.plugins.{plugin_id}")
        # Apply plugin-specific level if configured
        plugin_level = get_plugin_log_level(plugin_id)
        if plugin_level is not None:
            self._apply_effective_level(plugin_level)
    
    @property
    def plugin_id(self) -> str:
        return self._plugin_id
    
    def _format_msg(self, msg: str) -> str:
        return f"[plugin:{self._plugin_id}] {msg}"
    
    def _get_effective_level(self) -> int:
        """Calculate effective log level respecting global floor.
        
        Returns:
            max(global_floor, plugin_level) - ensures plugin isn't more verbose than allowed
        """
        global_floor = get_global_log_level_floor()
        plugin_level = get_plugin_log_level(self._plugin_id)
        
        if plugin_level is None:
            return global_floor
        
        # Plugin cannot be more verbose than the global floor
        return max(global_floor, plugin_level)
    
    def _should_log(self, level: int) -> bool:
        """Check if a message at given level should be logged.
        
        Args:
            level: The logging level of the message
            
        Returns:
            True if message should be logged
        """
        return level >= self._get_effective_level()
    
    def _apply_effective_level(self, level: int) -> None:
        """Apply the effective level, respecting global floor."""
        effective = max(get_global_log_level_floor(), level)
        self._logger.setLevel(effective)
    
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        if self._should_log(logging.DEBUG):
            self._logger.debug(self._format_msg(msg), *args, **kwargs)
    
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        if self._should_log(logging.INFO):
            self._logger.info(self._format_msg(msg), *args, **kwargs)
    
    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        if self._should_log(logging.WARNING):
            self._logger.warning(self._format_msg(msg), *args, **kwargs)
    
    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        if self._should_log(logging.ERROR):
            self._logger.error(self._format_msg(msg), *args, **kwargs)
    
    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        if self._should_log(logging.CRITICAL):
            self._logger.critical(self._format_msg(msg), *args, **kwargs)
    
    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        # Exception logging always includes traceback, should respect level for ERROR
        if self._should_log(logging.ERROR):
            self._logger.exception(self._format_msg(msg), *args, **kwargs)
    
    def setLevel(self, level: int) -> None:
        """Set the logging level for this plugin.
        
        Note: This is capped by the global floor - you cannot make
        the plugin more verbose than the global setting.
        
        Args:
            level: Desired logging level
        """
        # Store the plugin-specific level
        set_plugin_log_level(self._plugin_id, level)
        # Apply effective level (respecting floor)
        self._apply_effective_level(level)
    
    def getEffectiveLevel(self) -> int:
        """Get the effective logging level (considering global floor)."""
        return self._get_effective_level()
    
    def isEnabledFor(self, level: int) -> bool:
        """Check if logging is enabled for a given level.
        
        Args:
            level: Logging level to check
            
        Returns:
            True if messages at this level would be logged
        """
        return self._should_log(level)


class SecureRunner:
    """Secure wrapper around jupiter.core.runner.
    
    Provides command execution with:
    - Permission checking before execution
    - Command allow-list enforcement
    - Timeout management
    - Logging of all executions
    """
    
    def __init__(
        self,
        plugin_id: str,
        permissions: List[Permission],
        allowed_commands: Optional[List[str]] = None,
        default_timeout: int = 300,
    ):
        """Initialize secure runner.
        
        Args:
            plugin_id: Plugin requesting command execution
            permissions: Permissions granted to the plugin
            allowed_commands: Optional allow-list of command prefixes
            default_timeout: Default timeout in seconds
        """
        self._plugin_id = plugin_id
        self._permissions = permissions
        self._allowed_commands = allowed_commands or []
        self._default_timeout = default_timeout
        self._logger = PluginLogger(plugin_id)
    
    def _check_permission(self) -> None:
        """Verify plugin has run_commands permission."""
        if Permission.RUN_COMMANDS not in self._permissions:
            raise PermissionDeniedError(
                "Plugin does not have permission to run commands",
                plugin_id=self._plugin_id,
                permission="run_commands"
            )
    
    def _check_command_allowed(self, command: List[str]) -> None:
        """Verify command is in allow-list if configured."""
        if not self._allowed_commands:
            return  # No allow-list, all commands permitted
        
        cmd_str = " ".join(command)
        for allowed in self._allowed_commands:
            if cmd_str.startswith(allowed):
                return
        
        raise PermissionDeniedError(
            f"Command not in allow-list: {command[0] if command else 'empty'}",
            plugin_id=self._plugin_id,
            permission="run_commands"
        )
    
    def run(
        self,
        command: List[str],
        cwd: Optional[Path] = None,
        with_dynamic: bool = False,
        timeout: Optional[int] = None,
    ) -> "CommandResult":
        """Execute a command securely.
        
        Args:
            command: Command and arguments to execute
            cwd: Working directory (uses project root if not specified)
            with_dynamic: Enable dynamic analysis for Python scripts
            timeout: Timeout in seconds (uses default if not specified)
            
        Returns:
            CommandResult with stdout, stderr, returncode
            
        Raises:
            PermissionDeniedError: If plugin lacks run_commands permission
        """
        from jupiter.core.runner import run_command
        
        self._check_permission()
        self._check_command_allowed(command)
        
        # Use project root as default cwd
        if cwd is None:
            from jupiter.core.state import load_last_root
            cwd = load_last_root()
            if cwd is None:
                cwd = Path(".")
        
        self._logger.info("Executing command: %s", " ".join(command))
        
        # Note: timeout not yet implemented in core runner
        # TODO: Add timeout support to run_command
        result = run_command(command, cwd, with_dynamic=with_dynamic)
        
        if result.returncode != 0:
            self._logger.warning(
                "Command exited with code %d: %s",
                result.returncode,
                result.stderr[:200] if result.stderr else "no stderr"
            )
        
        return result
    
    def run_python(
        self,
        script: str,
        args: Optional[List[str]] = None,
        cwd: Optional[Path] = None,
        with_dynamic: bool = False,
    ) -> "CommandResult":
        """Execute a Python script securely.
        
        Convenience method that constructs the correct Python command.
        
        Args:
            script: Path to Python script
            args: Optional arguments to pass to the script
            cwd: Working directory
            with_dynamic: Enable dynamic analysis
            
        Returns:
            CommandResult
        """
        import sys
        command = [sys.executable, script] + (args or [])
        return self.run(command, cwd=cwd, with_dynamic=with_dynamic)


class ConfigProxy:
    """Proxy for accessing plugin configuration.
    
    Provides merged configuration from:
    1. Plugin defaults (from plugin.yaml config.defaults)
    2. Global plugin config (from jupiter/plugins/<id>/config.yaml)
    3. Project overrides (from <project>.jupiter.yaml plugins.<id>.config_overrides)
    """
    
    def __init__(
        self,
        plugin_id: str,
        defaults: Dict[str, Any],
        global_config: Dict[str, Any],
        project_overrides: Dict[str, Any],
    ):
        """Initialize config proxy.
        
        Args:
            plugin_id: Plugin identifier
            defaults: Default values from manifest
            global_config: Global plugin configuration
            project_overrides: Project-specific overrides
        """
        self._plugin_id = plugin_id
        self._defaults = defaults
        self._global_config = global_config
        self._project_overrides = project_overrides
        self._merged: Optional[Dict[str, Any]] = None
    
    def _merge(self) -> Dict[str, Any]:
        """Merge configuration layers."""
        if self._merged is None:
            self._merged = {
                **self._defaults,
                **self._global_config,
                **self._project_overrides,
            }
        return self._merged
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: Configuration key (supports dot notation for nested values)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        merged = self._merge()
        
        # Support dot notation for nested keys
        if "." in key:
            parts = key.split(".")
            value = merged
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            return value
        
        return merged.get(key, default)
    
    def get_all(self) -> Dict[str, Any]:
        """Get all merged configuration."""
        return self._merge().copy()
    
    def has(self, key: str) -> bool:
        """Check if a configuration key exists."""
        return self.get(key) is not None
    
    def __getitem__(self, key: str) -> Any:
        """Dict-style access to configuration."""
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value
    
    def __contains__(self, key: str) -> bool:
        return self.has(key)


class ServiceLocator:
    """Service locator providing scoped access to Jupiter services.
    
    Each plugin gets its own ServiceLocator instance with appropriate
    permissions and configuration scope.
    
    Example:
        services = bridge.get_services("my_plugin")
        logger = services.get_logger()
        config = services.get_config()
        runner = services.get_runner()
    """
    
    def __init__(
        self,
        plugin_id: str,
        bridge: "Bridge",
        permissions: List[Permission],
        config_defaults: Dict[str, Any],
    ):
        """Initialize service locator.
        
        Args:
            plugin_id: Plugin identifier
            bridge: Reference to the Bridge instance
            permissions: Permissions granted to this plugin
            config_defaults: Default configuration from manifest
        """
        self._plugin_id = plugin_id
        self._bridge = bridge
        self._permissions = permissions
        self._config_defaults = config_defaults
        
        # Cached service instances
        self._logger: Optional[PluginLogger] = None
        self._runner: Optional[SecureRunner] = None
        self._config: Optional[ConfigProxy] = None
    
    @property
    def plugin_id(self) -> str:
        return self._plugin_id
    
    @property
    def permissions(self) -> List[Permission]:
        return self._permissions.copy()
    
    def get_logger(self) -> PluginLogger:
        """Get a pre-configured logger for this plugin.
        
        Returns:
            PluginLogger instance with plugin ID prefix
        """
        if self._logger is None:
            self._logger = PluginLogger(self._plugin_id)
        return self._logger
    
    def get_runner(self) -> SecureRunner:
        """Get a secure command runner.
        
        Returns:
            SecureRunner instance with permission checks
            
        Note:
            Plugin must have 'run_commands' permission to use this service.
            Commands are logged for audit purposes.
        """
        if self._runner is None:
            # Get allowed commands from project config
            allowed_commands: List[str] = []
            try:
                from jupiter.core.state import load_last_root
                from jupiter.config.config import load_config
                
                project_root = load_last_root()
                if project_root:
                    config = load_config(project_root)
                    if hasattr(config, "security") and config.security:
                        if hasattr(config.security, "allowed_commands"):
                            allowed_commands = config.security.allowed_commands or []
            except Exception:
                pass
            
            self._runner = SecureRunner(
                plugin_id=self._plugin_id,
                permissions=self._permissions,
                allowed_commands=allowed_commands,
            )
        return self._runner
    
    def get_history(self) -> "HistoryManager":
        """Get the history manager for snapshot operations.
        
        Returns:
            HistoryManager for the current project
            
        Raises:
            PermissionDeniedError: If plugin lacks fs_read permission
            ServiceNotFoundError: If no active project
        """
        if Permission.FS_READ not in self._permissions:
            raise PermissionDeniedError(
                "Plugin does not have permission to access history",
                plugin_id=self._plugin_id,
                permission="fs_read"
            )
        
        from jupiter.core.history import HistoryManager
        from jupiter.core.state import load_last_root
        
        project_root = load_last_root()
        if project_root is None:
            raise ServiceNotFoundError(
                "history"
            )
        
        return HistoryManager(project_root)
    
    def get_graph(self) -> Any:
        """Get the graph builder for dependency analysis.
        
        Returns:
            GraphBuilder class (requires files to instantiate)
            
        Note:
            This is deprecated in favor of the livemap plugin.
        """
        from jupiter.core.graph import GraphBuilder
        return GraphBuilder  # Return class, not instance
    
    def get_project_manager(self) -> "ProjectManager":
        """Get the project manager.
        
        Returns:
            ProjectManager instance
        """
        from jupiter.server.manager import ProjectManager
        return ProjectManager()
    
    def get_config(self) -> ConfigProxy:
        """Get the plugin configuration.
        
        Returns merged configuration from:
        1. Plugin defaults (manifest)
        2. Global plugin config
        3. Project-specific overrides
        
        Returns:
            ConfigProxy for accessing configuration values
        """
        if self._config is None:
            # Use PluginConfigManager for consistent config loading
            from jupiter.core.bridge.plugin_config import PluginConfigManager
            
            manager = PluginConfigManager(
                plugin_id=self._plugin_id,
                defaults=self._config_defaults,
            )
            
            self._config = ConfigProxy(
                plugin_id=self._plugin_id,
                defaults=self._config_defaults,
                global_config=manager.get_global_config(),
                project_overrides=manager.get_project_overrides(),
            )
        return self._config
    
    def get_config_manager(self) -> "PluginConfigManager":
        """Get the full PluginConfigManager for advanced config operations.
        
        Use this when you need:
        - Per-project enabled state checking
        - Saving global config
        - Setting project-specific enabled state
        
        Returns:
            PluginConfigManager instance
        """
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        return PluginConfigManager(
            plugin_id=self._plugin_id,
            defaults=self._config_defaults,
        )
    
    def is_enabled_for_project(self) -> bool:
        """Check if this plugin is enabled for the current project.
        
        Returns:
            True if enabled, False if disabled
        """
        return self.get_config_manager().is_enabled_for_project()
    
    def get_event_bus(self) -> Any:
        """Get the event bus for pub/sub communication.
        
        Returns:
            EventBusProxy scoped to this plugin, or the bridge's event methods
        """
        # Use the bridge's event bus methods directly
        # The EventBusProxy is created by the bridge on demand
        from jupiter.core.bridge.bridge import EventBusProxy
        return EventBusProxy(self._bridge, self._plugin_id)
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if plugin has a specific permission.
        
        Args:
            permission: Permission to check
            
        Returns:
            True if plugin has the permission
        """
        return permission in self._permissions
    
    def require_permission(self, permission: Permission) -> None:
        """Assert plugin has a permission, raise if not.
        
        Args:
            permission: Permission to require
            
        Raises:
            PermissionDeniedError: If permission not granted
        """
        if not self.has_permission(permission):
            raise PermissionDeniedError(
                f"Plugin requires permission: {permission.value}",
                plugin_id=self._plugin_id,
                permission=permission.value
            )


def create_service_locator(
    plugin_id: str,
    bridge: "Bridge",
    permissions: List[Permission],
    config_defaults: Optional[Dict[str, Any]] = None,
) -> ServiceLocator:
    """Factory function to create a ServiceLocator for a plugin.
    
    Args:
        plugin_id: Plugin identifier
        bridge: Bridge instance
        permissions: Permissions granted to the plugin
        config_defaults: Default configuration values
        
    Returns:
        Configured ServiceLocator instance
    """
    return ServiceLocator(
        plugin_id=plugin_id,
        bridge=bridge,
        permissions=permissions,
        config_defaults=config_defaults or {},
    )
