"""CLI Registry for Jupiter Plugin Bridge.

Version: 0.1.0

This module provides a registry for CLI contributions from plugins.
It allows plugins to register commands that are dynamically loaded
by the CLI system.

Features:
- Register and unregister CLI contributions per plugin
- Command namespace isolation (prefixed with plugin ID)
- Dynamic entrypoint resolution
- Command validation and conflict detection
- Help text and argument parsing integration
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Type

from jupiter.core.bridge.interfaces import CLIContribution, Permission
from jupiter.core.bridge.exceptions import (
    PluginError,
    PermissionDeniedError,
    ValidationError,
)

logger = logging.getLogger(__name__)


@dataclass
class RegisteredCommand:
    """Represents a registered CLI command."""
    
    plugin_id: str
    name: str
    handler: Callable[..., Any]
    description: str = ""
    help_text: str = ""
    arguments: List[Dict[str, Any]] = field(default_factory=list)
    options: List[Dict[str, Any]] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    hidden: bool = False
    parent: Optional[str] = None  # For subcommands
    
    @property
    def full_name(self) -> str:
        """Get full command name including parent."""
        if self.parent:
            return f"{self.parent} {self.name}"
        return self.name
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "plugin_id": self.plugin_id,
            "name": self.name,
            "full_name": self.full_name,
            "description": self.description,
            "help_text": self.help_text,
            "arguments": self.arguments,
            "options": self.options,
            "aliases": self.aliases,
            "hidden": self.hidden,
            "parent": self.parent,
        }


@dataclass
class CommandGroup:
    """Represents a command group (subcommand parent)."""
    
    plugin_id: str
    name: str
    description: str = ""
    commands: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "plugin_id": self.plugin_id,
            "name": self.name,
            "description": self.description,
            "commands": self.commands,
        }


class CLIRegistry:
    """Registry for CLI contributions from plugins.
    
    The CLI Registry manages all CLI commands contributed by plugins.
    It handles:
    - Command registration and unregistration
    - Namespace management (plugins/<id>/* commands)
    - Conflict detection
    - Dynamic command loading
    
    Usage:
        registry = CLIRegistry()
        
        # Register a command
        registry.register_command(
            plugin_id="my_plugin",
            name="analyze",
            handler=my_analyze_function,
            description="Run custom analysis",
        )
        
        # Get all commands
        commands = registry.get_all_commands()
        
        # Get command by name
        cmd = registry.get_command("my_plugin", "analyze")
    """
    
    # Commands that cannot be overridden by plugins
    PROTECTED_COMMANDS = frozenset({
        "scan",
        "analyze",
        "server",
        "gui",
        "ci",
        "plugins",
        "config",
        "version",
        "help",
    })
    
    def __init__(self):
        """Initialize the CLI registry."""
        # plugin_id -> command_name -> RegisteredCommand
        self._commands: Dict[str, Dict[str, RegisteredCommand]] = {}
        # command_name -> plugin_id (for top-level commands)
        self._global_commands: Dict[str, str] = {}
        # plugin_id -> CommandGroup
        self._groups: Dict[str, Dict[str, CommandGroup]] = {}
        # Permission tracking: plugin_id -> set of permissions
        self._permissions: Dict[str, Set[Permission]] = {}
    
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
        """Check if plugin has permission to register CLI commands.
        
        Args:
            plugin_id: Plugin identifier
            
        Raises:
            PermissionDeniedError: If plugin lacks permission
        """
        perms = self._permissions.get(plugin_id, set())
        if Permission.REGISTER_CLI not in perms:
            raise PermissionDeniedError(
                f"Plugin '{plugin_id}' does not have permission to register CLI commands",
                plugin_id=plugin_id,
                permission=Permission.REGISTER_CLI,
            )
    
    def register_command(
        self,
        plugin_id: str,
        name: str,
        handler: Callable[..., Any],
        description: str = "",
        help_text: str = "",
        arguments: Optional[List[Dict[str, Any]]] = None,
        options: Optional[List[Dict[str, Any]]] = None,
        aliases: Optional[List[str]] = None,
        hidden: bool = False,
        parent: Optional[str] = None,
        check_permissions: bool = True,
    ) -> RegisteredCommand:
        """Register a CLI command for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            name: Command name
            handler: Function to call when command is invoked
            description: Short description for help
            help_text: Detailed help text
            arguments: List of positional arguments
            options: List of optional flags/options
            aliases: Alternative names for the command
            hidden: Whether to hide from help
            parent: Parent command for subcommands
            check_permissions: Whether to check plugin permissions
            
        Returns:
            RegisteredCommand object
            
        Raises:
            PermissionDeniedError: If plugin lacks permission
            ValidationError: If command name is invalid or conflicts
        """
        if check_permissions:
            self._check_permission(plugin_id)
        
        # Validate command name
        self._validate_command_name(name, plugin_id, parent)
        
        command = RegisteredCommand(
            plugin_id=plugin_id,
            name=name,
            handler=handler,
            description=description,
            help_text=help_text,
            arguments=arguments or [],
            options=options or [],
            aliases=aliases or [],
            hidden=hidden,
            parent=parent,
        )
        
        # Initialize plugin's command dict if needed
        if plugin_id not in self._commands:
            self._commands[plugin_id] = {}
        
        # Store command
        self._commands[plugin_id][name] = command
        
        # Register in global namespace if top-level
        if not parent:
            full_name = f"plugins:{plugin_id}:{name}"
            self._global_commands[full_name] = plugin_id
            
            # Also register aliases
            for alias in aliases or []:
                alias_full = f"plugins:{plugin_id}:{alias}"
                self._global_commands[alias_full] = plugin_id
        
        logger.debug(
            "Registered CLI command '%s' for plugin '%s'",
            command.full_name,
            plugin_id
        )
        
        return command
    
    def register_from_contribution(
        self,
        plugin_id: str,
        contribution: CLIContribution,
        handler: Optional[Callable[..., Any]] = None,
        check_permissions: bool = True,
    ) -> RegisteredCommand:
        """Register a command from a CLIContribution.
        
        Args:
            plugin_id: Plugin identifier
            contribution: CLI contribution from manifest
            handler: Handler function (required if not in contribution)
            check_permissions: Whether to check plugin permissions
            
        Returns:
            RegisteredCommand object
        """
        if handler is None:
            raise ValidationError(
                "Handler is required for CLI contribution registration",
                validation_errors=["handler cannot be None"],
            )
        
        return self.register_command(
            plugin_id=plugin_id,
            name=contribution.name,
            handler=handler,
            description=contribution.description,
            aliases=contribution.aliases,
            parent=contribution.parent,
            check_permissions=check_permissions,
        )
    
    def register_group(
        self,
        plugin_id: str,
        name: str,
        description: str = "",
        check_permissions: bool = True,
    ) -> CommandGroup:
        """Register a command group (for subcommands).
        
        Args:
            plugin_id: Plugin identifier
            name: Group name
            description: Group description
            check_permissions: Whether to check plugin permissions
            
        Returns:
            CommandGroup object
        """
        if check_permissions:
            self._check_permission(plugin_id)
        
        # Validate group name
        self._validate_command_name(name, plugin_id, None)
        
        group = CommandGroup(
            plugin_id=plugin_id,
            name=name,
            description=description,
        )
        
        if plugin_id not in self._groups:
            self._groups[plugin_id] = {}
        
        self._groups[plugin_id][name] = group
        
        logger.debug(
            "Registered CLI command group '%s' for plugin '%s'",
            name,
            plugin_id
        )
        
        return group
    
    def unregister_command(
        self,
        plugin_id: str,
        name: str,
    ) -> bool:
        """Unregister a CLI command.
        
        Args:
            plugin_id: Plugin identifier
            name: Command name
            
        Returns:
            True if command was removed
        """
        if plugin_id not in self._commands:
            return False
        
        if name not in self._commands[plugin_id]:
            return False
        
        command = self._commands[plugin_id][name]
        
        # Remove from global namespace
        full_name = f"plugins:{plugin_id}:{name}"
        self._global_commands.pop(full_name, None)
        
        # Remove aliases
        for alias in command.aliases:
            alias_full = f"plugins:{plugin_id}:{alias}"
            self._global_commands.pop(alias_full, None)
        
        # Remove command
        del self._commands[plugin_id][name]
        
        logger.debug(
            "Unregistered CLI command '%s' for plugin '%s'",
            name,
            plugin_id
        )
        
        return True
    
    def unregister_plugin(self, plugin_id: str) -> int:
        """Unregister all commands for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Number of commands removed
        """
        count = 0
        
        # Remove all commands
        if plugin_id in self._commands:
            for name in list(self._commands[plugin_id].keys()):
                if self.unregister_command(plugin_id, name):
                    count += 1
            del self._commands[plugin_id]
        
        # Remove all groups
        if plugin_id in self._groups:
            count += len(self._groups[plugin_id])
            del self._groups[plugin_id]
        
        # Remove permissions
        self._permissions.pop(plugin_id, None)
        
        if count > 0:
            logger.debug(
                "Unregistered %d CLI contributions for plugin '%s'",
                count,
                plugin_id
            )
        
        return count
    
    def get_command(
        self,
        plugin_id: str,
        name: str,
    ) -> Optional[RegisteredCommand]:
        """Get a registered command.
        
        Args:
            plugin_id: Plugin identifier
            name: Command name
            
        Returns:
            RegisteredCommand or None if not found
        """
        if plugin_id not in self._commands:
            return None
        return self._commands[plugin_id].get(name)
    
    def get_plugin_commands(self, plugin_id: str) -> List[RegisteredCommand]:
        """Get all commands for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            List of commands
        """
        if plugin_id not in self._commands:
            return []
        return list(self._commands[plugin_id].values())
    
    def get_all_commands(self) -> List[RegisteredCommand]:
        """Get all registered commands.
        
        Returns:
            List of all commands
        """
        result = []
        for commands in self._commands.values():
            result.extend(commands.values())
        return result
    
    def get_visible_commands(self) -> List[RegisteredCommand]:
        """Get all non-hidden commands.
        
        Returns:
            List of visible commands
        """
        return [cmd for cmd in self.get_all_commands() if not cmd.hidden]
    
    def get_group(
        self,
        plugin_id: str,
        name: str,
    ) -> Optional[CommandGroup]:
        """Get a command group.
        
        Args:
            plugin_id: Plugin identifier
            name: Group name
            
        Returns:
            CommandGroup or None if not found
        """
        if plugin_id not in self._groups:
            return None
        return self._groups[plugin_id].get(name)
    
    def get_all_groups(self) -> List[CommandGroup]:
        """Get all command groups.
        
        Returns:
            List of all groups
        """
        result = []
        for groups in self._groups.values():
            result.extend(groups.values())
        return result
    
    def resolve_command(
        self,
        command_path: str,
    ) -> Optional[RegisteredCommand]:
        """Resolve a command by its full path.
        
        Args:
            command_path: Command path (e.g., "plugins:my_plugin:analyze")
            
        Returns:
            RegisteredCommand or None if not found
        """
        if command_path in self._global_commands:
            plugin_id = self._global_commands[command_path]
            # Extract command name from path
            parts = command_path.split(":")
            if len(parts) == 3:
                _, _, name = parts
                return self.get_command(plugin_id, name)
        return None
    
    def find_commands_by_name(self, name: str) -> List[RegisteredCommand]:
        """Find all commands with a given name (across plugins).
        
        Args:
            name: Command name to search
            
        Returns:
            List of matching commands
        """
        result = []
        for plugin_id, commands in self._commands.items():
            if name in commands:
                result.append(commands[name])
            else:
                # Check aliases
                for cmd in commands.values():
                    if name in cmd.aliases:
                        result.append(cmd)
        return result
    
    def get_plugins_with_commands(self) -> List[str]:
        """Get list of plugin IDs that have registered commands.
        
        Returns:
            List of plugin IDs
        """
        return list(self._commands.keys())
    
    def _validate_command_name(
        self,
        name: str,
        plugin_id: str,
        parent: Optional[str],
    ) -> None:
        """Validate a command name.
        
        Args:
            name: Command name
            plugin_id: Plugin identifier
            parent: Parent command name
            
        Raises:
            ValidationError: If name is invalid
        """
        if not name:
            raise ValidationError(
                "Command name cannot be empty",
                validation_errors=["name is required"],
            )
        
        if not name.replace("-", "").replace("_", "").isalnum():
            raise ValidationError(
                f"Command name '{name}' contains invalid characters",
                validation_errors=["name must contain only alphanumeric characters, hyphens, and underscores"],
            )
        
        # Check for protected commands (only for top-level)
        if not parent and name in self.PROTECTED_COMMANDS:
            raise ValidationError(
                f"Command name '{name}' is reserved and cannot be overridden",
                validation_errors=[f"'{name}' is a protected Jupiter command"],
            )
        
        # Check for duplicates within the same plugin
        if plugin_id in self._commands and name in self._commands[plugin_id]:
            raise ValidationError(
                f"Command '{name}' is already registered for plugin '{plugin_id}'",
                validation_errors=["duplicate command name"],
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize registry state to dictionary.
        
        Returns:
            Dictionary with commands and groups
        """
        return {
            "commands": {
                plugin_id: {
                    name: cmd.to_dict()
                    for name, cmd in commands.items()
                }
                for plugin_id, commands in self._commands.items()
            },
            "groups": {
                plugin_id: {
                    name: group.to_dict()
                    for name, group in groups.items()
                }
                for plugin_id, groups in self._groups.items()
            },
            "global_commands": dict(self._global_commands),
        }


# Global CLI registry instance
_cli_registry: Optional[CLIRegistry] = None


def get_cli_registry() -> CLIRegistry:
    """Get the global CLI registry instance.
    
    Returns:
        CLIRegistry singleton
    """
    global _cli_registry
    if _cli_registry is None:
        _cli_registry = CLIRegistry()
    return _cli_registry


def reset_cli_registry() -> None:
    """Reset the global CLI registry (for testing)."""
    global _cli_registry
    _cli_registry = None
