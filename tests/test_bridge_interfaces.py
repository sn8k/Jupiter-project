"""Tests for Jupiter Plugin Bridge interfaces.

Version: 0.1.0

This module tests the ABC interfaces and data classes defined in
jupiter/core/bridge/interfaces.py and jupiter/core/bridge/exceptions.py.
"""

from __future__ import annotations

import pytest
from typing import Any, Dict, List
from dataclasses import asdict

# Import interfaces
from jupiter.core.bridge.interfaces import (
    # Enums
    PluginState,
    PluginType,
    Permission,
    UILocation,
    HealthStatus,
    # Data classes
    PluginCapabilities,
    CLIContribution,
    APIContribution,
    UIContribution,
    HealthCheckResult,
    PluginMetrics,
    # ABCs
    IPlugin,
    IPluginManifest,
    IPluginContribution,
    IPluginHealth,
    IPluginMetrics as IPluginMetricsInterface,
    # Protocols
    LegacyPlugin,
    ConfigurablePlugin,
)

# Import exceptions
from jupiter.core.bridge.exceptions import (
    BridgeError,
    PluginError,
    ManifestError,
    DependencyError,
    CircularDependencyError,
    ServiceNotFoundError,
    PermissionDeniedError,
    LifecycleError,
    ValidationError,
    SignatureError,
)


# =============================================================================
# ENUM TESTS
# =============================================================================

class TestPluginState:
    """Tests for PluginState enum."""
    
    def test_all_states_defined(self):
        """All expected states should be defined."""
        assert PluginState.DISCOVERED == "discovered"
        assert PluginState.LOADING == "loading"
        assert PluginState.READY == "ready"
        assert PluginState.ERROR == "error"
        assert PluginState.DISABLED == "disabled"
        assert PluginState.UNLOADING == "unloading"
    
    def test_state_count(self):
        """Should have exactly 6 states."""
        assert len(PluginState) == 6


class TestPluginType:
    """Tests for PluginType enum."""
    
    def test_all_types_defined(self):
        """All expected types should be defined."""
        assert PluginType.CORE == "core"
        assert PluginType.SYSTEM == "system"
        assert PluginType.TOOL == "tool"
    
    def test_type_count(self):
        """Should have exactly 3 types."""
        assert len(PluginType) == 3


class TestPermission:
    """Tests for Permission enum."""
    
    def test_filesystem_permissions(self):
        """Filesystem permissions should be defined."""
        assert Permission.FS_READ == "fs_read"
        assert Permission.FS_WRITE == "fs_write"
    
    def test_execution_permissions(self):
        """Execution permissions should be defined."""
        assert Permission.RUN_COMMANDS == "run_commands"
        assert Permission.NETWORK_OUTBOUND == "network_outbound"
    
    def test_registration_permissions(self):
        """Registration permissions should be defined."""
        assert Permission.REGISTER_API == "register_api"
        assert Permission.REGISTER_CLI == "register_cli"
        assert Permission.REGISTER_UI == "register_ui"
    
    def test_permission_count(self):
        """Should have exactly 10 permissions."""
        assert len(Permission) == 10


class TestUILocation:
    """Tests for UILocation enum."""
    
    def test_all_locations_defined(self):
        """All UI locations should be defined."""
        assert UILocation.NONE == "none"
        assert UILocation.SIDEBAR == "sidebar"
        assert UILocation.SETTINGS == "settings"
        assert UILocation.BOTH == "both"


class TestHealthStatus:
    """Tests for HealthStatus enum."""
    
    def test_all_statuses_defined(self):
        """All health statuses should be defined."""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"
        assert HealthStatus.UNKNOWN == "unknown"


# =============================================================================
# DATA CLASS TESTS
# =============================================================================

class TestPluginCapabilities:
    """Tests for PluginCapabilities dataclass."""
    
    def test_defaults(self):
        """Should have sensible defaults."""
        caps = PluginCapabilities()
        
        assert caps.metrics_enabled is False
        assert caps.metrics_export_format == "json"
        assert caps.jobs_enabled is False
        assert caps.jobs_max_concurrent == 1
        assert caps.health_check_enabled is True
    
    def test_custom_values(self):
        """Should accept custom values."""
        caps = PluginCapabilities(
            metrics_enabled=True,
            metrics_export_format="prometheus",
            jobs_enabled=True,
            jobs_max_concurrent=5,
            health_check_enabled=False
        )
        
        assert caps.metrics_enabled is True
        assert caps.metrics_export_format == "prometheus"
        assert caps.jobs_max_concurrent == 5
    
    def test_to_dict(self):
        """Should serialize to dict."""
        caps = PluginCapabilities(metrics_enabled=True)
        d = caps.to_dict()
        
        assert isinstance(d, dict)
        assert d["metrics_enabled"] is True


class TestCLIContribution:
    """Tests for CLIContribution dataclass."""
    
    def test_required_fields(self):
        """Should require name, description, entrypoint."""
        cli = CLIContribution(
            name="my-command",
            description="A test command",
            entrypoint="module:func"
        )
        
        assert cli.name == "my-command"
        assert cli.description == "A test command"
        assert cli.entrypoint == "module:func"
    
    def test_optional_fields(self):
        """Should have optional parent and aliases."""
        cli = CLIContribution(
            name="sub-command",
            description="A subcommand",
            entrypoint="module:func",
            parent="parent-command",
            aliases=["sc", "subcom"]
        )
        
        assert cli.parent == "parent-command"
        assert cli.aliases == ["sc", "subcom"]
    
    def test_to_dict(self):
        """Should serialize to dict."""
        cli = CLIContribution(
            name="cmd",
            description="Test",
            entrypoint="m:f"
        )
        d = cli.to_dict()
        
        assert d["name"] == "cmd"
        assert d["entrypoint"] == "m:f"


class TestAPIContribution:
    """Tests for APIContribution dataclass."""
    
    def test_required_fields(self):
        """Should require path, method, entrypoint."""
        api = APIContribution(
            path="/test",
            method="GET",
            entrypoint="module:handler"
        )
        
        assert api.path == "/test"
        assert api.method == "GET"
        assert api.entrypoint == "module:handler"
    
    def test_optional_fields(self):
        """Should have optional tags and auth_required."""
        api = APIContribution(
            path="/secure",
            method="POST",
            entrypoint="m:h",
            tags=["security", "admin"],
            auth_required=True
        )
        
        assert api.tags == ["security", "admin"]
        assert api.auth_required is True


class TestUIContribution:
    """Tests for UIContribution dataclass."""
    
    def test_required_fields(self):
        """Should require id, location, route, title_key."""
        ui = UIContribution(
            id="main-panel",
            location=UILocation.SIDEBAR,
            route="/plugins/test",
            title_key="plugin.test.title"
        )
        
        assert ui.id == "main-panel"
        assert ui.location == UILocation.SIDEBAR
        assert ui.route == "/plugins/test"
        assert ui.title_key == "plugin.test.title"
    
    def test_defaults(self):
        """Should have sensible defaults."""
        ui = UIContribution(
            id="test",
            location=UILocation.SETTINGS,
            route="/test",
            title_key="test"
        )
        
        assert ui.icon == "🔌"
        assert ui.order == 100
        assert ui.settings_section is None
    
    def test_to_dict_serializes_enum(self):
        """Should serialize location enum to string."""
        ui = UIContribution(
            id="test",
            location=UILocation.BOTH,
            route="/test",
            title_key="test"
        )
        d = ui.to_dict()
        
        assert d["location"] == "both"


class TestHealthCheckResult:
    """Tests for HealthCheckResult dataclass."""
    
    def test_healthy_result(self):
        """Should create healthy result."""
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="All systems operational"
        )
        
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All systems operational"
    
    def test_unhealthy_with_details(self):
        """Should include details for unhealthy result."""
        result = HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            message="Database connection failed",
            details={"error": "Connection refused", "host": "localhost"}
        )
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "error" in result.details
    
    def test_to_dict_serializes_enum(self):
        """Should serialize status enum to string."""
        result = HealthCheckResult(status=HealthStatus.DEGRADED)
        d = result.to_dict()
        
        assert d["status"] == "degraded"


class TestPluginMetrics:
    """Tests for PluginMetrics dataclass."""
    
    def test_defaults(self):
        """Should have zero/empty defaults."""
        metrics = PluginMetrics()
        
        assert metrics.execution_count == 0
        assert metrics.error_count == 0
        assert metrics.last_execution is None
        assert metrics.average_duration_ms == 0.0
        assert metrics.custom == {}
    
    def test_custom_metrics(self):
        """Should accept custom metrics."""
        metrics = PluginMetrics(
            execution_count=100,
            error_count=5,
            average_duration_ms=150.5,
            custom={"cache_hits": 85, "cache_misses": 15}
        )
        
        assert metrics.custom["cache_hits"] == 85


# =============================================================================
# EXCEPTION TESTS
# =============================================================================

class TestBridgeError:
    """Tests for BridgeError base exception."""
    
    def test_basic_message(self):
        """Should store message."""
        err = BridgeError("Something went wrong")
        
        assert str(err) == "Something went wrong"
        assert err.message == "Something went wrong"
    
    def test_with_details(self):
        """Should include details in string representation."""
        err = BridgeError("Error", details={"key": "value"})
        
        assert "key" in str(err)
        assert err.details["key"] == "value"
    
    def test_to_dict(self):
        """Should serialize to dict."""
        err = BridgeError("Test error", details={"foo": "bar"})
        d = err.to_dict()
        
        assert d["error"] == "BridgeError"
        assert d["message"] == "Test error"
        assert d["details"]["foo"] == "bar"


class TestPluginError:
    """Tests for PluginError exception."""
    
    def test_includes_plugin_id(self):
        """Should include plugin_id in message."""
        err = PluginError("Failed to load", plugin_id="my_plugin")
        
        assert "[my_plugin]" in str(err)
        assert err.plugin_id == "my_plugin"
    
    def test_plugin_id_in_details(self):
        """Should add plugin_id to details."""
        err = PluginError("Error", plugin_id="test")
        
        assert err.details["plugin_id"] == "test"


class TestManifestError:
    """Tests for ManifestError exception."""
    
    def test_with_field(self):
        """Should include field name."""
        err = ManifestError(
            "Invalid version format",
            plugin_id="my_plugin",
            field="version"
        )
        
        assert err.field == "version"
        assert err.details["field"] == "version"


class TestDependencyError:
    """Tests for DependencyError exception."""
    
    def test_with_version_info(self):
        """Should include version information."""
        err = DependencyError(
            "Version mismatch",
            plugin_id="my_plugin",
            dependency="other_plugin",
            required_version=">=2.0.0",
            actual_version="1.5.0"
        )
        
        assert err.dependency == "other_plugin"
        assert err.required_version == ">=2.0.0"
        assert err.actual_version == "1.5.0"


class TestCircularDependencyError:
    """Tests for CircularDependencyError exception."""
    
    def test_includes_cycle_path(self):
        """Should include cycle path in message."""
        err = CircularDependencyError(
            plugin_id="plugin_a",
            cycle=["plugin_a", "plugin_b", "plugin_c", "plugin_a"]
        )
        
        assert "plugin_a -> plugin_b -> plugin_c -> plugin_a" in str(err)
        assert err.cycle == ["plugin_a", "plugin_b", "plugin_c", "plugin_a"]


class TestServiceNotFoundError:
    """Tests for ServiceNotFoundError exception."""
    
    def test_includes_service_name(self):
        """Should include service name in message."""
        err = ServiceNotFoundError("scanner")
        
        assert "scanner" in str(err)
        assert err.service_name == "scanner"


class TestPermissionDeniedError:
    """Tests for PermissionDeniedError exception."""
    
    def test_includes_permission(self):
        """Should include permission in details."""
        err = PermissionDeniedError(
            "Cannot write to filesystem",
            plugin_id="my_plugin",
            permission="fs_write"
        )
        
        assert err.permission == "fs_write"
        assert err.details["permission"] == "fs_write"


class TestLifecycleError:
    """Tests for LifecycleError exception."""
    
    def test_includes_state_info(self):
        """Should include state transition info."""
        err = LifecycleError(
            "Invalid state transition",
            plugin_id="my_plugin",
            current_state="error",
            target_state="ready"
        )
        
        assert err.current_state == "error"
        assert err.target_state == "ready"


class TestValidationError:
    """Tests for ValidationError exception."""
    
    def test_with_validation_errors(self):
        """Should include list of validation errors."""
        err = ValidationError(
            "Schema validation failed",
            validation_errors=[
                "Field 'version' is required",
                "Field 'id' must match pattern"
            ]
        )
        
        assert len(err.validation_errors) == 2
        assert "version" in err.validation_errors[0]


# =============================================================================
# PROTOCOL TESTS
# =============================================================================

class TestLegacyPluginProtocol:
    """Tests for LegacyPlugin protocol detection."""
    
    def test_detects_legacy_plugin(self):
        """Should detect a class matching the legacy interface."""
        class MyLegacyPlugin:
            name = "legacy"
            version = "1.0.0"
            description = "A legacy plugin"
            
            def on_scan(self, report: Dict[str, Any]) -> None:
                pass
            
            def on_analyze(self, summary: Dict[str, Any]) -> None:
                pass
        
        plugin = MyLegacyPlugin()
        assert isinstance(plugin, LegacyPlugin)
    
    def test_rejects_non_legacy(self):
        """Should not match classes without required methods."""
        class NotAPlugin:
            name = "not_a_plugin"
        
        obj = NotAPlugin()
        assert not isinstance(obj, LegacyPlugin)


class TestConfigurablePluginProtocol:
    """Tests for ConfigurablePlugin protocol detection."""
    
    def test_detects_configurable(self):
        """Should detect a class with configure method."""
        class ConfigurableClass:
            def configure(self, config: Dict[str, Any]) -> None:
                pass
        
        obj = ConfigurableClass()
        assert isinstance(obj, ConfigurablePlugin)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestInterfaceUsage:
    """Integration tests for using interfaces together."""
    
    def test_contribution_serialization(self):
        """All contributions should serialize consistently."""
        cli = CLIContribution(name="cmd", description="Test", entrypoint="m:f")
        api = APIContribution(path="/test", method="GET", entrypoint="m:h")
        ui = UIContribution(
            id="panel",
            location=UILocation.SIDEBAR,
            route="/plugins/test",
            title_key="test"
        )
        
        # All should have to_dict method
        assert callable(getattr(cli, "to_dict", None))
        assert callable(getattr(api, "to_dict", None))
        assert callable(getattr(ui, "to_dict", None))
        
        # All should return dicts
        assert isinstance(cli.to_dict(), dict)
        assert isinstance(api.to_dict(), dict)
        assert isinstance(ui.to_dict(), dict)
    
    def test_error_hierarchy(self):
        """All errors should inherit from BridgeError."""
        errors = [
            PluginError("test", plugin_id="p"),
            ManifestError("test", plugin_id="p"),
            DependencyError("test", plugin_id="p"),
            CircularDependencyError(plugin_id="p", cycle=["a", "b", "a"]),
            ServiceNotFoundError("svc"),
            PermissionDeniedError("test", plugin_id="p", permission="fs_read"),
            LifecycleError("test", plugin_id="p"),
            ValidationError("test"),
            SignatureError("test", plugin_id="p"),
        ]
        
        for err in errors:
            assert isinstance(err, BridgeError)
            assert hasattr(err, "to_dict")
            assert isinstance(err.to_dict(), dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
