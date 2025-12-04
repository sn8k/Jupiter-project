"""Tests for Permission System module.

Tests the PermissionChecker functionality for granular permission
verification and enforcement.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from typing import Any, Dict, Optional, Set
from unittest.mock import MagicMock, patch

from jupiter.core.bridge.permissions import (
    PermissionChecker,
    PermissionCheckResult,
    get_permission_checker,
    init_permission_checker,
    shutdown_permission_checker,
    require_permission,
)
from jupiter.core.bridge.interfaces import Permission
from jupiter.core.bridge.exceptions import PermissionDeniedError


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_bridge():
    """Create a mock bridge with plugin permissions."""
    bridge = MagicMock()
    
    # Mock plugin info with permissions - returns PluginInfo-like objects
    def get_plugin(plugin_id: str) -> Optional[MagicMock]:
        plugins = {
            "test_plugin": MagicMock(
                manifest=MagicMock(permissions=[
                    Permission.FS_READ,
                    Permission.FS_WRITE,
                    Permission.EMIT_EVENTS,
                ])
            ),
            "limited_plugin": MagicMock(
                manifest=MagicMock(permissions=[
                    Permission.FS_READ,
                ])
            ),
            "full_plugin": MagicMock(
                manifest=MagicMock(permissions=list(Permission))
            ),
            "no_perms_plugin": MagicMock(
                manifest=MagicMock(permissions=[])
            ),
        }
        return plugins.get(plugin_id)
    
    bridge.get_plugin = get_plugin
    return bridge


@pytest.fixture
def checker(mock_bridge):
    """Create a PermissionChecker with mock bridge."""
    return PermissionChecker(mock_bridge)


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton checker after each test."""
    yield
    shutdown_permission_checker()


# =============================================================================
# TESTS: PERMISSION CHECKER BASIC
# =============================================================================

class TestPermissionCheckerBasic:
    """Basic tests for PermissionChecker."""
    
    def test_checker_creation(self):
        """Test checker can be created."""
        checker = PermissionChecker()
        assert checker is not None
    
    def test_checker_with_bridge(self, mock_bridge):
        """Test checker with bridge."""
        checker = PermissionChecker(mock_bridge)
        assert checker._bridge == mock_bridge
    
    def test_set_bridge(self, mock_bridge):
        """Test setting bridge after creation."""
        checker = PermissionChecker()
        checker.set_bridge(mock_bridge)
        assert checker._bridge == mock_bridge


# =============================================================================
# TESTS: PERMISSION LOOKUP
# =============================================================================

class TestPermissionLookup:
    """Tests for permission lookup."""
    
    def test_get_plugin_permissions(self, checker):
        """Test getting plugin permissions."""
        perms = checker.get_plugin_permissions("test_plugin")
        
        assert Permission.FS_READ in perms
        assert Permission.FS_WRITE in perms
        assert Permission.EMIT_EVENTS in perms
        assert Permission.RUN_COMMANDS not in perms
    
    def test_get_permissions_unknown_plugin(self, checker):
        """Test getting permissions for unknown plugin."""
        perms = checker.get_plugin_permissions("unknown")
        assert perms == set()
    
    def test_get_permissions_no_bridge(self):
        """Test getting permissions with no bridge."""
        checker = PermissionChecker()
        perms = checker.get_plugin_permissions("any_plugin")
        assert perms == set()


# =============================================================================
# TESTS: HAS PERMISSION
# =============================================================================

class TestHasPermission:
    """Tests for has_permission method."""
    
    def test_has_permission_granted(self, checker):
        """Test has_permission returns True when granted."""
        assert checker.has_permission("test_plugin", Permission.FS_READ) is True
    
    def test_has_permission_denied(self, checker):
        """Test has_permission returns False when not granted."""
        assert checker.has_permission("test_plugin", Permission.RUN_COMMANDS) is False
    
    def test_has_permission_limited_plugin(self, checker):
        """Test limited plugin permissions."""
        assert checker.has_permission("limited_plugin", Permission.FS_READ) is True
        assert checker.has_permission("limited_plugin", Permission.FS_WRITE) is False
    
    def test_has_permission_full_plugin(self, checker):
        """Test full plugin has all permissions."""
        for perm in Permission:
            assert checker.has_permission("full_plugin", perm) is True
    
    def test_has_permission_no_perms_plugin(self, checker):
        """Test plugin with no permissions."""
        for perm in Permission:
            assert checker.has_permission("no_perms_plugin", perm) is False


# =============================================================================
# TESTS: CHECK PERMISSION (with logging)
# =============================================================================

class TestCheckPermission:
    """Tests for check_permission method."""
    
    def test_check_permission_granted(self, checker):
        """Test check_permission returns granted result."""
        result = checker.check_permission("test_plugin", Permission.FS_READ)
        
        assert result.granted is True
        assert result.permission == Permission.FS_READ
        assert result.plugin_id == "test_plugin"
    
    def test_check_permission_denied(self, checker):
        """Test check_permission returns denied result."""
        result = checker.check_permission("test_plugin", Permission.RUN_COMMANDS)
        
        assert result.granted is False
        assert result.permission == Permission.RUN_COMMANDS
    
    def test_check_permission_with_context(self, checker):
        """Test check_permission with context."""
        result = checker.check_permission(
            "test_plugin",
            Permission.FS_READ,
            context="reading config file"
        )
        
        assert result.granted is True
    
    def test_check_permission_logs_result(self, checker):
        """Test that check_permission logs the result."""
        checker.check_permission("test_plugin", Permission.FS_READ)
        checker.check_permission("test_plugin", Permission.RUN_COMMANDS)
        
        log = checker.get_check_log()
        assert len(log) == 2


# =============================================================================
# TESTS: REQUIRE PERMISSION
# =============================================================================

class TestRequirePermission:
    """Tests for require_permission method."""
    
    def test_require_permission_granted(self, checker):
        """Test require_permission passes when granted."""
        # Should not raise
        checker.require_permission("test_plugin", Permission.FS_READ)
    
    def test_require_permission_denied(self, checker):
        """Test require_permission raises when denied."""
        with pytest.raises(PermissionDeniedError) as exc_info:
            checker.require_permission("test_plugin", Permission.RUN_COMMANDS)
        
        assert "test_plugin" in str(exc_info.value)
        assert "run_commands" in str(exc_info.value).lower()
    
    def test_require_permission_with_context(self, checker):
        """Test require_permission includes context in error."""
        with pytest.raises(PermissionDeniedError) as exc_info:
            checker.require_permission(
                "test_plugin",
                Permission.RUN_COMMANDS,
                context="executing build command"
            )
        
        assert "executing build command" in str(exc_info.value)


# =============================================================================
# TESTS: REQUIRE ANY/ALL PERMISSIONS
# =============================================================================

class TestRequireAnyAllPermissions:
    """Tests for require_any_permission and require_all_permissions."""
    
    def test_require_any_permission_first_granted(self, checker):
        """Test require_any returns first granted permission."""
        result = checker.require_any_permission(
            "test_plugin",
            [Permission.FS_READ, Permission.FS_WRITE]
        )
        assert result == Permission.FS_READ
    
    def test_require_any_permission_second_granted(self, checker):
        """Test require_any when first is denied but second granted."""
        result = checker.require_any_permission(
            "limited_plugin",
            [Permission.FS_WRITE, Permission.FS_READ]  # Write denied, read granted
        )
        assert result == Permission.FS_READ
    
    def test_require_any_permission_none_granted(self, checker):
        """Test require_any raises when none granted."""
        with pytest.raises(PermissionDeniedError):
            checker.require_any_permission(
                "no_perms_plugin",
                [Permission.FS_READ, Permission.FS_WRITE]
            )
    
    def test_require_all_permissions_granted(self, checker):
        """Test require_all passes when all granted."""
        # Should not raise
        checker.require_all_permissions(
            "test_plugin",
            [Permission.FS_READ, Permission.FS_WRITE]
        )
    
    def test_require_all_permissions_partial(self, checker):
        """Test require_all raises when some denied."""
        with pytest.raises(PermissionDeniedError):
            checker.require_all_permissions(
                "test_plugin",
                [Permission.FS_READ, Permission.RUN_COMMANDS]  # RUN_COMMANDS denied
            )


# =============================================================================
# TESTS: SCOPED PERMISSION CHECKS
# =============================================================================

class TestScopedChecks:
    """Tests for scoped permission check methods."""
    
    def test_check_fs_read(self, checker):
        """Test check_fs_read."""
        assert checker.check_fs_read("test_plugin") is True
        assert checker.check_fs_read("no_perms_plugin") is False
    
    def test_check_fs_read_with_path(self, checker):
        """Test check_fs_read with path."""
        result = checker.check_fs_read("test_plugin", Path("/some/file.txt"))
        assert result is True
    
    def test_check_fs_write(self, checker):
        """Test check_fs_write."""
        assert checker.check_fs_write("test_plugin") is True
        assert checker.check_fs_write("limited_plugin") is False
    
    def test_check_run_command(self, checker):
        """Test check_run_command."""
        assert checker.check_run_command("full_plugin") is True
        assert checker.check_run_command("test_plugin") is False
    
    def test_check_run_command_with_command(self, checker):
        """Test check_run_command with command string."""
        result = checker.check_run_command("full_plugin", "npm install")
        assert result is True
    
    def test_check_network(self, checker):
        """Test check_network."""
        assert checker.check_network("full_plugin") is True
        assert checker.check_network("test_plugin") is False
    
    def test_check_network_with_url(self, checker):
        """Test check_network with URL."""
        result = checker.check_network("full_plugin", "https://api.example.com")
        assert result is True
    
    def test_check_meeting_access(self, checker):
        """Test check_meeting_access."""
        assert checker.check_meeting_access("full_plugin") is True
        assert checker.check_meeting_access("test_plugin") is False
    
    def test_check_config_access(self, checker):
        """Test check_config_access."""
        assert checker.check_config_access("full_plugin") is True
        assert checker.check_config_access("test_plugin") is False
    
    def test_check_emit_events(self, checker):
        """Test check_emit_events."""
        assert checker.check_emit_events("test_plugin") is True
        assert checker.check_emit_events("no_perms_plugin") is False


# =============================================================================
# TESTS: LOGGING AND AUDIT
# =============================================================================

class TestLogging:
    """Tests for permission check logging."""
    
    def test_check_log_empty(self, checker):
        """Test log is empty initially."""
        log = checker.get_check_log()
        assert log == []
    
    def test_check_log_populated(self, checker):
        """Test log is populated after checks."""
        checker.check_permission("test_plugin", Permission.FS_READ)
        checker.check_permission("test_plugin", Permission.FS_WRITE)
        
        log = checker.get_check_log()
        assert len(log) == 2
    
    def test_check_log_filter_by_plugin(self, checker):
        """Test filtering log by plugin."""
        checker.check_permission("test_plugin", Permission.FS_READ)
        checker.check_permission("limited_plugin", Permission.FS_READ)
        
        log = checker.get_check_log(plugin_id="test_plugin")
        assert len(log) == 1
        assert log[0].plugin_id == "test_plugin"
    
    def test_check_log_filter_by_permission(self, checker):
        """Test filtering log by permission."""
        checker.check_permission("test_plugin", Permission.FS_READ)
        checker.check_permission("test_plugin", Permission.FS_WRITE)
        
        log = checker.get_check_log(permission=Permission.FS_READ)
        assert len(log) == 1
        assert log[0].permission == Permission.FS_READ
    
    def test_check_log_filter_granted_only(self, checker):
        """Test filtering log for granted only."""
        checker.check_permission("test_plugin", Permission.FS_READ)  # Granted
        checker.check_permission("test_plugin", Permission.RUN_COMMANDS)  # Denied
        
        log = checker.get_check_log(granted_only=True)
        assert len(log) == 1
        assert log[0].granted is True
    
    def test_check_log_filter_denied_only(self, checker):
        """Test filtering log for denied only."""
        checker.check_permission("test_plugin", Permission.FS_READ)  # Granted
        checker.check_permission("test_plugin", Permission.RUN_COMMANDS)  # Denied
        
        log = checker.get_check_log(denied_only=True)
        assert len(log) == 1
        assert log[0].granted is False
    
    def test_check_log_limit(self, checker):
        """Test log limit parameter."""
        for i in range(10):
            checker.check_permission("test_plugin", Permission.FS_READ)
        
        log = checker.get_check_log(limit=5)
        assert len(log) == 5
    
    def test_clear_log(self, checker):
        """Test clearing the log."""
        checker.check_permission("test_plugin", Permission.FS_READ)
        checker.clear_log()
        
        log = checker.get_check_log()
        assert log == []


# =============================================================================
# TESTS: STATISTICS
# =============================================================================

class TestStatistics:
    """Tests for permission check statistics."""
    
    def test_stats_empty(self, checker):
        """Test stats when no checks made."""
        stats = checker.get_stats()
        
        assert stats["total_checks"] == 0
        assert stats["granted"] == 0
        assert stats["denied"] == 0
    
    def test_stats_after_checks(self, checker):
        """Test stats after making checks."""
        checker.check_permission("test_plugin", Permission.FS_READ)  # Granted
        checker.check_permission("test_plugin", Permission.FS_WRITE)  # Granted
        checker.check_permission("test_plugin", Permission.RUN_COMMANDS)  # Denied
        
        stats = checker.get_stats()
        
        assert stats["total_checks"] == 3
        assert stats["granted"] == 2
        assert stats["denied"] == 1
        assert stats["grant_rate"] == 2 / 3
    
    def test_stats_by_permission(self, checker):
        """Test stats breakdown by permission."""
        checker.check_permission("test_plugin", Permission.FS_READ)
        checker.check_permission("limited_plugin", Permission.FS_READ)
        checker.check_permission("test_plugin", Permission.RUN_COMMANDS)
        
        stats = checker.get_stats()
        
        assert "fs_read" in stats["by_permission"]
        assert stats["by_permission"]["fs_read"]["granted"] == 2


# =============================================================================
# TESTS: MODULE FUNCTIONS
# =============================================================================

class TestModuleFunctions:
    """Tests for module-level functions."""
    
    def test_get_permission_checker_singleton(self):
        """Test get_permission_checker returns singleton."""
        checker1 = get_permission_checker()
        checker2 = get_permission_checker()
        
        assert checker1 is checker2
    
    def test_init_permission_checker(self, mock_bridge):
        """Test init_permission_checker."""
        checker = init_permission_checker(mock_bridge)
        
        assert checker is not None
        assert checker._bridge == mock_bridge
        assert get_permission_checker() is checker
    
    def test_shutdown_permission_checker(self, mock_bridge):
        """Test shutdown_permission_checker."""
        init_permission_checker(mock_bridge)
        shutdown_permission_checker()
        
        # After shutdown, new checker should be created
        new_checker = get_permission_checker()
        assert new_checker._bridge is None


# =============================================================================
# TESTS: DECORATOR
# =============================================================================

class TestRequirePermissionDecorator:
    """Tests for require_permission decorator."""
    
    def test_decorator_passes_when_granted(self, mock_bridge):
        """Test decorator passes when permission granted."""
        init_permission_checker(mock_bridge)
        
        @require_permission(Permission.FS_READ)
        def read_data(plugin_id: str) -> str:
            return "data"
        
        result = read_data(plugin_id="test_plugin")
        assert result == "data"
    
    def test_decorator_raises_when_denied(self, mock_bridge):
        """Test decorator raises when permission denied."""
        init_permission_checker(mock_bridge)
        
        @require_permission(Permission.RUN_COMMANDS)
        def run_cmd(plugin_id: str) -> str:
            return "output"
        
        with pytest.raises(PermissionDeniedError):
            run_cmd(plugin_id="test_plugin")
    
    def test_decorator_with_positional_plugin_id(self, mock_bridge):
        """Test decorator with positional plugin_id."""
        init_permission_checker(mock_bridge)
        
        @require_permission(Permission.FS_READ)
        def read_file(plugin_id: str, path: str) -> str:
            return f"content of {path}"
        
        result = read_file("test_plugin", "/path/to/file")
        assert "content of" in result
    
    def test_decorator_without_plugin_id(self, mock_bridge):
        """Test decorator raises when plugin_id missing."""
        init_permission_checker(mock_bridge)
        
        @require_permission(Permission.FS_READ)
        def bad_function() -> str:
            return "data"
        
        with pytest.raises(ValueError) as exc_info:
            bad_function()
        
        assert "plugin_id is required" in str(exc_info.value)


# =============================================================================
# TESTS: PERMISSION CHECK RESULT
# =============================================================================

class TestPermissionCheckResult:
    """Tests for PermissionCheckResult dataclass."""
    
    def test_result_to_dict(self):
        """Test result serialization."""
        result = PermissionCheckResult(
            granted=True,
            permission=Permission.FS_READ,
            plugin_id="test_plugin",
            reason="Permission granted",
        )
        
        data = result.to_dict()
        
        assert data["granted"] is True
        assert data["permission"] == "fs_read"
        assert data["plugin_id"] == "test_plugin"
        assert data["reason"] == "Permission granted"
