"""Tests for jupiter.core.bridge.cli_registry module.

Version: 0.1.0

Tests for the CLI Registry functionality.
"""

import pytest
from typing import Any
from unittest.mock import MagicMock

from jupiter.core.bridge.cli_registry import (
    CLIRegistry,
    RegisteredCommand,
    CommandGroup,
    get_cli_registry,
    reset_cli_registry,
)
from jupiter.core.bridge.interfaces import (
    CLIContribution,
    Permission,
)
from jupiter.core.bridge.exceptions import (
    PermissionDeniedError,
    ValidationError,
)


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset the global CLI registry before and after each test."""
    reset_cli_registry()
    yield
    reset_cli_registry()


@pytest.fixture
def registry() -> CLIRegistry:
    """Create a fresh CLI registry."""
    return CLIRegistry()


@pytest.fixture
def handler() -> MagicMock:
    """Create a mock command handler."""
    return MagicMock(return_value=0)


# =============================================================================
# RegisteredCommand Tests
# =============================================================================

class TestRegisteredCommand:
    """Tests for RegisteredCommand dataclass."""
    
    def test_creates_with_required_fields(self, handler):
        """Should create command with required fields."""
        cmd = RegisteredCommand(
            plugin_id="test_plugin",
            name="analyze",
            handler=handler,
        )
        
        assert cmd.plugin_id == "test_plugin"
        assert cmd.name == "analyze"
        assert cmd.handler is handler
    
    def test_full_name_without_parent(self, handler):
        """full_name should return name without parent."""
        cmd = RegisteredCommand(
            plugin_id="test",
            name="run",
            handler=handler,
        )
        
        assert cmd.full_name == "run"
    
    def test_full_name_with_parent(self, handler):
        """full_name should include parent."""
        cmd = RegisteredCommand(
            plugin_id="test",
            name="list",
            handler=handler,
            parent="plugins",
        )
        
        assert cmd.full_name == "plugins list"
    
    def test_to_dict_serializes_all_fields(self, handler):
        """to_dict should serialize all fields."""
        cmd = RegisteredCommand(
            plugin_id="test_plugin",
            name="cmd",
            handler=handler,
            description="Test command",
            help_text="Detailed help",
            arguments=[{"name": "file"}],
            options=[{"name": "--verbose"}],
            aliases=["c", "command"],
            hidden=True,
            parent="group",
        )
        
        data = cmd.to_dict()
        
        assert data["plugin_id"] == "test_plugin"
        assert data["name"] == "cmd"
        assert data["full_name"] == "group cmd"
        assert data["description"] == "Test command"
        assert data["help_text"] == "Detailed help"
        assert data["arguments"] == [{"name": "file"}]
        assert data["options"] == [{"name": "--verbose"}]
        assert data["aliases"] == ["c", "command"]
        assert data["hidden"] is True
        assert data["parent"] == "group"


class TestCommandGroup:
    """Tests for CommandGroup dataclass."""
    
    def test_creates_with_required_fields(self):
        """Should create group with required fields."""
        group = CommandGroup(
            plugin_id="test",
            name="mygroup",
        )
        
        assert group.plugin_id == "test"
        assert group.name == "mygroup"
        assert group.description == ""
        assert group.commands == []
    
    def test_to_dict(self):
        """to_dict should serialize fields."""
        group = CommandGroup(
            plugin_id="test",
            name="mygroup",
            description="My command group",
            commands=["cmd1", "cmd2"],
        )
        
        data = group.to_dict()
        
        assert data["plugin_id"] == "test"
        assert data["name"] == "mygroup"
        assert data["description"] == "My command group"
        assert data["commands"] == ["cmd1", "cmd2"]


# =============================================================================
# CLIRegistry Permission Tests
# =============================================================================

class TestCLIRegistryPermissions:
    """Tests for CLI Registry permission checks."""
    
    def test_register_requires_permission(self, registry, handler):
        """Registration should require REGISTER_CLI permission."""
        with pytest.raises(PermissionDeniedError) as exc:
            registry.register_command(
                plugin_id="test",
                name="cmd",
                handler=handler,
            )
        
        assert "REGISTER_CLI" in str(exc.value) or "permission" in str(exc.value).lower()
    
    def test_register_with_permission_succeeds(self, registry, handler):
        """Registration should succeed with permission."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        
        cmd = registry.register_command(
            plugin_id="test",
            name="cmd",
            handler=handler,
        )
        
        assert cmd is not None
        assert cmd.name == "cmd"
    
    def test_check_permissions_can_be_bypassed(self, registry, handler):
        """check_permissions=False should bypass check."""
        cmd = registry.register_command(
            plugin_id="test",
            name="cmd",
            handler=handler,
            check_permissions=False,
        )
        
        assert cmd is not None
    
    def test_register_group_requires_permission(self, registry):
        """Group registration should require permission."""
        with pytest.raises(PermissionDeniedError):
            registry.register_group(
                plugin_id="test",
                name="mygroup",
            )
    
    def test_register_group_with_permission(self, registry):
        """Group registration should succeed with permission."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        
        group = registry.register_group(
            plugin_id="test",
            name="mygroup",
            description="Test group",
        )
        
        assert group is not None
        assert group.name == "mygroup"


# =============================================================================
# CLIRegistry Command Registration Tests
# =============================================================================

class TestCLIRegistryRegisterCommand:
    """Tests for command registration."""
    
    def test_register_basic_command(self, registry, handler):
        """Should register a basic command."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        
        cmd = registry.register_command(
            plugin_id="test",
            name="custom-analyze",
            handler=handler,
            description="Run analysis",
        )
        
        assert cmd.plugin_id == "test"
        assert cmd.name == "custom-analyze"
        assert cmd.description == "Run analysis"
    
    def test_register_command_with_all_options(self, registry, handler):
        """Should register command with all options."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        
        cmd = registry.register_command(
            plugin_id="test",
            name="cmd",
            handler=handler,
            description="Short desc",
            help_text="Long help text",
            arguments=[{"name": "file", "type": "str"}],
            options=[{"name": "--verbose", "flag": True}],
            aliases=["c"],
            hidden=True,
            parent="group",
        )
        
        assert cmd.help_text == "Long help text"
        assert len(cmd.arguments) == 1
        assert len(cmd.options) == 1
        assert cmd.aliases == ["c"]
        assert cmd.hidden is True
        assert cmd.parent == "group"
    
    def test_register_from_contribution(self, registry, handler):
        """Should register from CLIContribution."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        
        contribution = CLIContribution(
            name="custom-analyze",
            description="Run analysis",
            entrypoint="my_plugin:analyze",
        )
        
        cmd = registry.register_from_contribution(
            plugin_id="test",
            contribution=contribution,
            handler=handler,
        )
        
        assert cmd.name == "custom-analyze"
        assert cmd.description == "Run analysis"
    
    def test_register_contribution_requires_handler(self, registry):
        """register_from_contribution should require handler."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        
        contribution = CLIContribution(name="cmd", description="", entrypoint="test:cmd")
        
        with pytest.raises(ValidationError):
            registry.register_from_contribution(
                plugin_id="test",
                contribution=contribution,
                handler=None,
            )


# =============================================================================
# CLIRegistry Validation Tests
# =============================================================================

class TestCLIRegistryValidation:
    """Tests for command name validation."""
    
    def test_empty_name_rejected(self, registry, handler):
        """Empty command name should be rejected."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        
        with pytest.raises(ValidationError):
            registry.register_command(
                plugin_id="test",
                name="",
                handler=handler,
            )
    
    def test_invalid_characters_rejected(self, registry, handler):
        """Invalid characters should be rejected."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        
        with pytest.raises(ValidationError):
            registry.register_command(
                plugin_id="test",
                name="cmd@name",
                handler=handler,
            )
    
    def test_hyphens_and_underscores_allowed(self, registry, handler):
        """Hyphens and underscores should be allowed."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        
        cmd = registry.register_command(
            plugin_id="test",
            name="my-command_name",
            handler=handler,
        )
        
        assert cmd.name == "my-command_name"
    
    def test_protected_commands_rejected(self, registry, handler):
        """Protected command names should be rejected."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        
        for protected in ["scan", "analyze", "server", "gui", "plugins"]:
            with pytest.raises(ValidationError) as exc:
                registry.register_command(
                    plugin_id="test",
                    name=protected,
                    handler=handler,
                )
            assert "protected" in str(exc.value).lower() or "reserved" in str(exc.value).lower()
    
    def test_protected_allowed_as_subcommand(self, registry, handler):
        """Protected names should be allowed as subcommands."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        
        # "list" as a subcommand under a parent
        cmd = registry.register_command(
            plugin_id="test",
            name="list",
            handler=handler,
            parent="mygroup",
        )
        
        assert cmd.name == "list"
    
    def test_duplicate_in_same_plugin_rejected(self, registry, handler):
        """Duplicate command in same plugin should be rejected."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        
        registry.register_command(
            plugin_id="test",
            name="mycommand",
            handler=handler,
        )
        
        with pytest.raises(ValidationError):
            registry.register_command(
                plugin_id="test",
                name="mycommand",
                handler=handler,
            )
    
    def test_same_name_different_plugins_allowed(self, registry, handler):
        """Same command name in different plugins should be allowed."""
        registry.set_plugin_permissions("plugin_a", {Permission.REGISTER_CLI})
        registry.set_plugin_permissions("plugin_b", {Permission.REGISTER_CLI})
        
        cmd_a = registry.register_command(
            plugin_id="plugin_a",
            name="custom-cmd",
            handler=handler,
        )
        
        cmd_b = registry.register_command(
            plugin_id="plugin_b",
            name="custom-cmd",
            handler=handler,
        )
        
        assert cmd_a.plugin_id == "plugin_a"
        assert cmd_b.plugin_id == "plugin_b"


# =============================================================================
# CLIRegistry Query Tests
# =============================================================================

class TestCLIRegistryQueries:
    """Tests for querying registered commands."""
    
    def test_get_command_returns_registered(self, registry, handler):
        """get_command should return registered command."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        registry.register_command("test", "cmd", handler)
        
        cmd = registry.get_command("test", "cmd")
        
        assert cmd is not None
        assert cmd.name == "cmd"
    
    def test_get_command_returns_none_for_unknown(self, registry):
        """get_command should return None for unknown."""
        assert registry.get_command("test", "unknown") is None
    
    def test_get_plugin_commands(self, registry, handler):
        """get_plugin_commands should return all for plugin."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        registry.register_command("test", "cmd1", handler)
        registry.register_command("test", "cmd2", handler)
        
        commands = registry.get_plugin_commands("test")
        
        assert len(commands) == 2
        names = {c.name for c in commands}
        assert names == {"cmd1", "cmd2"}
    
    def test_get_plugin_commands_empty_for_unknown(self, registry):
        """get_plugin_commands should return empty for unknown plugin."""
        commands = registry.get_plugin_commands("unknown")
        assert commands == []
    
    def test_get_all_commands(self, registry, handler):
        """get_all_commands should return all registered."""
        registry.set_plugin_permissions("p1", {Permission.REGISTER_CLI})
        registry.set_plugin_permissions("p2", {Permission.REGISTER_CLI})
        
        registry.register_command("p1", "cmd1", handler)
        registry.register_command("p2", "cmd2", handler)
        registry.register_command("p2", "cmd3", handler)
        
        commands = registry.get_all_commands()
        
        assert len(commands) == 3
    
    def test_get_visible_commands_filters_hidden(self, registry, handler):
        """get_visible_commands should filter hidden."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        registry.register_command("test", "visible", handler, hidden=False)
        registry.register_command("test", "hidden", handler, hidden=True)
        
        visible = registry.get_visible_commands()
        
        assert len(visible) == 1
        assert visible[0].name == "visible"
    
    def test_get_group(self, registry):
        """get_group should return registered group."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        registry.register_group("test", "mygroup", "Description")
        
        group = registry.get_group("test", "mygroup")
        
        assert group is not None
        assert group.name == "mygroup"
    
    def test_get_all_groups(self, registry):
        """get_all_groups should return all groups."""
        registry.set_plugin_permissions("p1", {Permission.REGISTER_CLI})
        registry.set_plugin_permissions("p2", {Permission.REGISTER_CLI})
        
        registry.register_group("p1", "group1")
        registry.register_group("p2", "group2")
        
        groups = registry.get_all_groups()
        
        assert len(groups) == 2
    
    def test_resolve_command_by_path(self, registry, handler):
        """resolve_command should find by full path."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        registry.register_command("test", "custom-analyze", handler)
        
        cmd = registry.resolve_command("plugins:test:custom-analyze")
        
        assert cmd is not None
        assert cmd.name == "custom-analyze"
    
    def test_resolve_command_returns_none_for_unknown(self, registry):
        """resolve_command should return None for unknown."""
        cmd = registry.resolve_command("plugins:unknown:cmd")
        assert cmd is None
    
    def test_find_commands_by_name(self, registry, handler):
        """find_commands_by_name should find across plugins."""
        registry.set_plugin_permissions("p1", {Permission.REGISTER_CLI})
        registry.set_plugin_permissions("p2", {Permission.REGISTER_CLI})
        
        registry.register_command("p1", "custom-analyze", handler)
        registry.register_command("p2", "custom-analyze", handler)
        
        commands = registry.find_commands_by_name("custom-analyze")
        
        assert len(commands) == 2
    
    def test_find_commands_by_alias(self, registry, handler):
        """find_commands_by_name should find by alias."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        registry.register_command("test", "custom-analyze", handler, aliases=["a"])
        
        commands = registry.find_commands_by_name("a")
        
        assert len(commands) == 1
        assert commands[0].name == "custom-analyze"
    
    def test_get_plugins_with_commands(self, registry, handler):
        """get_plugins_with_commands should return plugin IDs."""
        registry.set_plugin_permissions("p1", {Permission.REGISTER_CLI})
        registry.set_plugin_permissions("p2", {Permission.REGISTER_CLI})
        
        registry.register_command("p1", "cmd1", handler)
        registry.register_command("p2", "cmd2", handler)
        
        plugins = registry.get_plugins_with_commands()
        
        assert set(plugins) == {"p1", "p2"}


# =============================================================================
# CLIRegistry Unregister Tests
# =============================================================================

class TestCLIRegistryUnregister:
    """Tests for unregistering commands."""
    
    def test_unregister_command(self, registry, handler):
        """unregister_command should remove command."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        registry.register_command("test", "cmd", handler)
        
        result = registry.unregister_command("test", "cmd")
        
        assert result is True
        assert registry.get_command("test", "cmd") is None
    
    def test_unregister_returns_false_if_not_found(self, registry):
        """unregister_command should return False if not found."""
        result = registry.unregister_command("unknown", "cmd")
        assert result is False
    
    def test_unregister_removes_from_global(self, registry, handler):
        """unregister should remove from global namespace."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        registry.register_command("test", "cmd", handler)
        
        registry.unregister_command("test", "cmd")
        
        cmd = registry.resolve_command("plugins:test:cmd")
        assert cmd is None
    
    def test_unregister_plugin_removes_all(self, registry, handler):
        """unregister_plugin should remove all commands."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        registry.register_command("test", "cmd1", handler)
        registry.register_command("test", "cmd2", handler)
        registry.register_group("test", "group1")
        
        count = registry.unregister_plugin("test")
        
        assert count == 3
        assert registry.get_plugin_commands("test") == []
        assert registry.get_all_groups() == []
    
    def test_unregister_plugin_returns_zero_if_none(self, registry):
        """unregister_plugin should return 0 if no commands."""
        count = registry.unregister_plugin("unknown")
        assert count == 0


# =============================================================================
# CLIRegistry Serialization Tests
# =============================================================================

class TestCLIRegistrySerialization:
    """Tests for registry serialization."""
    
    def test_to_dict_empty(self, registry):
        """to_dict should work with empty registry."""
        data = registry.to_dict()
        
        assert data["commands"] == {}
        assert data["groups"] == {}
        assert data["global_commands"] == {}
    
    def test_to_dict_with_commands(self, registry, handler):
        """to_dict should serialize commands."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_CLI})
        registry.register_command("test", "cmd", handler, description="Test")
        registry.register_group("test", "grp", "Group")
        
        data = registry.to_dict()
        
        assert "test" in data["commands"]
        assert "cmd" in data["commands"]["test"]
        assert data["commands"]["test"]["cmd"]["description"] == "Test"
        
        assert "test" in data["groups"]
        assert "grp" in data["groups"]["test"]


# =============================================================================
# Global Registry Tests
# =============================================================================

class TestGlobalCLIRegistry:
    """Tests for global CLI registry functions."""
    
    def test_get_cli_registry_returns_singleton(self):
        """get_cli_registry should return same instance."""
        r1 = get_cli_registry()
        r2 = get_cli_registry()
        
        assert r1 is r2
    
    def test_reset_cli_registry_creates_new(self):
        """reset_cli_registry should create new instance."""
        r1 = get_cli_registry()
        reset_cli_registry()
        r2 = get_cli_registry()
        
        assert r1 is not r2
