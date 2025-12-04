"""Tests for Bridge singleton and plugin lifecycle.

Version: 0.1.1
"""

import pytest
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from jupiter.core.bridge.bridge import (
    Bridge,
    PluginInfo,
    ServiceLocator,
    EventBusProxy,
    CORE_PLUGINS,
)
from jupiter.core.bridge.interfaces import (
    PluginState,
    PluginType,
    HealthStatus,
    HealthCheckResult,
    CLIContribution,
    APIContribution,
    UIContribution,
    UILocation,
)
from jupiter.core.bridge.manifest import PluginManifest
from jupiter.core.bridge.exceptions import (
    PluginError,
    ServiceNotFoundError,
    CircularDependencyError,
)


def make_manifest(
    plugin_id: str,
    name: Optional[str] = None,
    version: str = "1.0.0",
    description: str = "Test plugin",
    plugin_type: PluginType = PluginType.TOOL,
    dependencies: Optional[List[str]] = None,
    cli_contributions: Optional[List[CLIContribution]] = None,
    api_contributions: Optional[List[APIContribution]] = None,
    ui_contributions: Optional[List[UIContribution]] = None,
) -> PluginManifest:
    """Helper to create PluginManifest instances for testing."""
    data: Dict[str, Any] = {
        "id": plugin_id,
        "name": name or plugin_id,
        "version": version,
        "description": description,
        "type": plugin_type.value,
        "jupiter_version": ">=0.1.0",
    }
    if dependencies:
        data["dependencies"] = {d: "*" for d in dependencies}
    if cli_contributions:
        data["cli"] = {"commands": [{"name": c.name, "description": c.description, "entrypoint": c.entrypoint} for c in cli_contributions]}
    if api_contributions:
        data["api"] = {"routes": [{"path": a.path, "method": a.method, "entrypoint": a.entrypoint} for a in api_contributions]}
    if ui_contributions:
        data["ui"] = {"panels": [{"id": u.id, "location": u.location.value if u.location else "sidebar", "route": u.route, "title_key": u.title_key} for u in ui_contributions]}
    
    return PluginManifest.from_dict(data)


@pytest.fixture(autouse=True)
def reset_bridge():
    """Reset the Bridge singleton before and after each test."""
    Bridge.reset_instance()
    yield
    Bridge.reset_instance()


class TestBridgeSingleton:
    """Tests for Bridge singleton behavior."""
    
    def test_singleton_returns_same_instance(self):
        """Bridge() should always return the same instance."""
        b1 = Bridge()
        b2 = Bridge()
        assert b1 is b2
    
    def test_get_instance_returns_singleton(self):
        """get_instance() should return the singleton."""
        b1 = Bridge.get_instance()
        b2 = Bridge.get_instance()
        assert b1 is b2
        assert b1 is Bridge()
    
    def test_reset_clears_instance(self):
        """reset_instance() should clear the singleton."""
        b1 = Bridge()
        Bridge.reset_instance()
        b2 = Bridge()
        # Note: Can't directly test identity after reset since
        # the new instance could have same memory address
        # Instead, verify state is fresh
        assert len(b2._plugins) == 0
    
    def test_bridge_initializes_once(self):
        """Bridge should only initialize once."""
        bridge = Bridge()
        # Add a test service instead of corrupting _plugins
        bridge.register_service("test_marker", {"value": True})
        
        # Try to init again
        bridge2 = Bridge()
        # Marker still there since it's the same instance
        assert bridge2.get_service("test_marker")["value"] is True


class TestPluginRegistration:
    """Tests for plugin registration and lookup."""
    
    def test_get_plugin_not_found(self):
        """get_plugin should return None for unknown plugins."""
        bridge = Bridge()
        assert bridge.get_plugin("nonexistent") is None
    
    def test_get_all_plugins_empty(self):
        """get_all_plugins should return empty list initially."""
        bridge = Bridge()
        assert bridge.get_all_plugins() == []
    
    def test_register_plugin(self):
        """_register_plugin should add plugin to registry."""
        bridge = Bridge()
        
        manifest = make_manifest(
            plugin_id="test_plugin",
            name="Test Plugin",
            version="1.0.0",
            plugin_type=PluginType.TOOL,
        )
        
        bridge._register_plugin(manifest)
        
        info = bridge.get_plugin("test_plugin")
        assert info is not None
        assert info.manifest.id == "test_plugin"
        assert info.state == PluginState.DISCOVERED
    
    def test_register_duplicate_plugin_skipped(self):
        """Registering same plugin twice should skip."""
        bridge = Bridge()
        
        manifest = make_manifest(
            plugin_id="dupe",
            name="Duplicate",
            version="1.0.0",
        )
        
        bridge._register_plugin(manifest)
        
        # Try to register again
        manifest2 = make_manifest(
            plugin_id="dupe",
            name="Different Name",
            version="2.0.0",
        )
        bridge._register_plugin(manifest2)
        
        # Should keep first registration
        info = bridge.get_plugin("dupe")
        assert info is not None
        assert info.manifest.version == "1.0.0"
    
    def test_get_plugins_by_state(self):
        """Should filter plugins by state."""
        bridge = Bridge()
        
        for i, state in enumerate([PluginState.DISCOVERED, PluginState.READY, PluginState.ERROR]):
            manifest = make_manifest(plugin_id=f"p{i}", name=f"Plugin {i}", version="1.0.0")
            bridge._register_plugin(manifest)
            bridge._plugins[f"p{i}"].state = state
        
        discovered = bridge.get_plugins_by_state(PluginState.DISCOVERED)
        assert len(discovered) == 1
        assert discovered[0].manifest.id == "p0"
    
    def test_get_plugins_by_type(self):
        """Should filter plugins by type."""
        bridge = Bridge()
        
        for ptype in [PluginType.CORE, PluginType.SYSTEM, PluginType.TOOL]:
            manifest = make_manifest(
                plugin_id=f"p_{ptype.value}",
                name=f"Plugin {ptype.value}",
                version="1.0.0",
                plugin_type=ptype,
            )
            bridge._register_plugin(manifest)
        
        tools = bridge.get_plugins_by_type(PluginType.TOOL)
        assert len(tools) == 1
        assert tools[0].manifest.plugin_type == PluginType.TOOL
    
    def test_is_plugin_enabled(self):
        """Should check if plugin is enabled and ready."""
        bridge = Bridge()
        
        manifest = make_manifest(plugin_id="test", name="Test", version="1.0.0")
        bridge._register_plugin(manifest)
        
        assert not bridge.is_plugin_enabled("test")  # DISCOVERED
        
        bridge._plugins["test"].state = PluginState.READY
        assert bridge.is_plugin_enabled("test")
        
        assert not bridge.is_plugin_enabled("nonexistent")


class TestPluginInfoSerialization:
    """Tests for PluginInfo serialization."""
    
    def test_plugin_info_to_dict(self):
        """PluginInfo should serialize to dict."""
        manifest = make_manifest(
            plugin_id="test_plugin",
            name="Test Plugin",
            version="1.0.0",
            description="A test plugin",
            plugin_type=PluginType.TOOL,
        )
        
        info = PluginInfo(
            manifest=manifest,
            state=PluginState.READY,
            legacy=False,
        )
        
        d = info.to_dict()
        
        assert d["id"] == "test_plugin"
        assert d["name"] == "Test Plugin"
        assert d["version"] == "1.0.0"
        assert d["description"] == "A test plugin"
        assert d["type"] == "tool"
        assert d["state"] == "ready"
        assert d["legacy"] is False


class TestPluginLoadOrder:
    """Tests for plugin load order sorting."""
    
    def test_sort_by_type_priority(self):
        """Plugins should load in order: core, system, tool."""
        bridge = Bridge()
        
        # Register in random order
        for ptype, name in [
            (PluginType.TOOL, "tool1"),
            (PluginType.CORE, "core1"),
            (PluginType.SYSTEM, "sys1"),
        ]:
            manifest = make_manifest(
                plugin_id=name,
                name=name,
                version="1.0.0",
                plugin_type=ptype,
            )
            bridge._register_plugin(manifest)
        
        order = bridge._sort_by_load_order(["tool1", "core1", "sys1"])
        
        assert order[0] == "core1"
        assert order[1] == "sys1"
        assert order[2] == "tool1"
    
    def test_sort_respects_dependencies(self):
        """Dependencies should load first within same category."""
        bridge = Bridge()
        
        # Plugin A depends on B
        manifest_a = make_manifest(
            plugin_id="plugin_a",
            name="Plugin A",
            version="1.0.0",
            plugin_type=PluginType.TOOL,
            dependencies=["plugin_b"],
        )
        manifest_b = make_manifest(
            plugin_id="plugin_b",
            name="Plugin B",
            version="1.0.0",
            plugin_type=PluginType.TOOL,
        )
        
        bridge._register_plugin(manifest_a)
        bridge._register_plugin(manifest_b)
        
        order = bridge._sort_by_load_order(["plugin_a", "plugin_b"])
        
        assert order.index("plugin_b") < order.index("plugin_a")
    
    def test_circular_dependency_raises_error(self):
        """Circular dependencies should raise error."""
        bridge = Bridge()
        
        manifest_a = make_manifest(
            plugin_id="a",
            name="A",
            version="1.0.0",
            dependencies=["b"],
        )
        manifest_b = make_manifest(
            plugin_id="b",
            name="B",
            version="1.0.0",
            dependencies=["a"],
        )
        
        bridge._register_plugin(manifest_a)
        bridge._register_plugin(manifest_b)
        
        with pytest.raises(CircularDependencyError):
            bridge._sort_by_load_order(["a", "b"])


class TestContributions:
    """Tests for contribution registries."""
    
    def test_register_cli_contribution(self):
        """CLI contributions should be registered."""
        bridge = Bridge()
        
        cli = CLIContribution(
            name="test-cmd",
            description="Test command",
            entrypoint="module.handler",
        )
        # Create manifest with CLI contribution
        manifest = make_manifest(
            plugin_id="test",
            name="Test",
            version="1.0.0",
            cli_contributions=[cli],
        )
        
        info = PluginInfo(manifest=manifest, state=PluginState.LOADING)
        bridge._plugins["test"] = info
        bridge._register_contributions(info)
        
        contributions = bridge.get_cli_contributions()
        assert "test.test-cmd" in contributions
    
    def test_register_api_contribution(self):
        """API contributions should be registered."""
        bridge = Bridge()
        
        api = APIContribution(
            path="/api/test",
            method="GET",
            entrypoint="module.handler",
        )
        manifest = make_manifest(
            plugin_id="test",
            name="Test",
            version="1.0.0",
            api_contributions=[api],
        )
        
        info = PluginInfo(manifest=manifest)
        bridge._plugins["test"] = info
        bridge._register_contributions(info)
        
        contributions = bridge.get_api_contributions()
        assert "test./api/test" in contributions
    
    def test_register_ui_contribution(self):
        """UI contributions should be registered."""
        bridge = Bridge()
        
        ui = UIContribution(
            id="test-panel",
            location=UILocation.SIDEBAR,
            route="/test",
            title_key="test_panel_title",
        )
        manifest = make_manifest(
            plugin_id="test",
            name="Test",
            version="1.0.0",
            ui_contributions=[ui],
        )
        
        info = PluginInfo(manifest=manifest)
        bridge._plugins["test"] = info
        bridge._register_contributions(info)
        
        contributions = bridge.get_ui_contributions()
        assert "test.test-panel" in contributions


class TestEventBus:
    """Tests for event subscription and emission."""
    
    def test_subscribe_and_emit(self):
        """Events should be delivered to subscribers."""
        bridge = Bridge()
        received = []
        
        def callback(topic: str, payload: Dict[str, Any]):
            received.append((topic, payload))
        
        bridge.subscribe("TEST_EVENT", callback)
        bridge.emit("TEST_EVENT", {"data": "test"})
        
        assert len(received) == 1
        assert received[0][0] == "TEST_EVENT"
        assert received[0][1]["data"] == "test"
    
    def test_unsubscribe(self):
        """Unsubscribed callbacks should not receive events."""
        bridge = Bridge()
        received = []
        
        def callback(topic: str, payload: Dict[str, Any]):
            received.append((topic, payload))
        
        bridge.subscribe("TEST", callback)
        bridge.emit("TEST", {"n": 1})
        
        bridge.unsubscribe("TEST", callback)
        bridge.emit("TEST", {"n": 2})
        
        assert len(received) == 1
        assert received[0][1]["n"] == 1
    
    def test_multiple_subscribers(self):
        """Multiple subscribers should all receive events."""
        bridge = Bridge()
        received_a = []
        received_b = []
        
        bridge.subscribe("MULTI", lambda t, p: received_a.append(p))
        bridge.subscribe("MULTI", lambda t, p: received_b.append(p))
        
        bridge.emit("MULTI", {"val": 42})
        
        assert len(received_a) == 1
        assert len(received_b) == 1
    
    def test_callback_error_isolated(self):
        """Errors in callbacks should not affect other subscribers."""
        bridge = Bridge()
        received = []
        
        def bad_callback(t, p):
            raise RuntimeError("Boom!")
        
        def good_callback(t, p):
            received.append(p)
        
        bridge.subscribe("ERR", bad_callback)
        bridge.subscribe("ERR", good_callback)
        
        # Should not raise, and good_callback should still run
        bridge.emit("ERR", {"ok": True})
        
        assert len(received) == 1


class TestServiceLocator:
    """Tests for service registration and lookup."""
    
    def test_register_and_get_service(self):
        """Registered services should be retrievable."""
        bridge = Bridge()
        
        service = {"name": "test_service"}
        bridge.register_service("test", service)
        
        result = bridge.get_service("test")
        assert result is service
    
    def test_get_unknown_service_raises(self):
        """Getting unknown service should raise."""
        bridge = Bridge()
        
        with pytest.raises(ServiceNotFoundError) as exc_info:
            bridge.get_service("nonexistent")
        
        assert "nonexistent" in str(exc_info.value)
    
    def test_service_locator_proxy(self):
        """ServiceLocator should provide scoped access."""
        bridge = Bridge()
        bridge.register_service("config", {"key": "value"})
        
        locator = ServiceLocator(bridge, "test_plugin")
        
        # Should get logger with plugin prefix
        logger = locator.get_logger()
        assert "test_plugin" in logger.name
        
        # Should get service
        config = locator.get_service("config")
        assert config["key"] == "value"


class TestEventBusProxy:
    """Tests for plugin-scoped event bus."""
    
    def test_emit_adds_source_plugin(self):
        """Events emitted via proxy should include source plugin."""
        bridge = Bridge()
        received = []
        
        bridge.subscribe("PROXY_TEST", lambda t, p: received.append(p))
        
        proxy = EventBusProxy(bridge, "my_plugin")
        proxy.emit("PROXY_TEST", {"data": "test"})
        
        assert len(received) == 1
        assert received[0]["_source_plugin"] == "my_plugin"
        assert received[0]["data"] == "test"


class TestRemoteActions:
    """Tests for Meeting integration remote actions."""
    
    def test_register_remote_action(self):
        """Remote actions should be registrable."""
        bridge = Bridge()
        
        def handler(params):
            return "result"
        
        bridge.register_remote_action(
            action_id="test.action",
            plugin_id="test_plugin",
            handler=handler,
            requires_confirmation=True,
        )
        
        actions = bridge.get_remote_actions()
        assert "test.action" in actions
        assert actions["test.action"]["plugin_id"] == "test_plugin"
        assert actions["test.action"]["requires_confirmation"] is True


class TestHealthChecks:
    """Tests for plugin health checking."""
    
    def test_health_check_unknown_plugin(self):
        """Health check for unknown plugin returns UNKNOWN."""
        bridge = Bridge()
        
        result = bridge.health_check("nonexistent")
        assert result.status == HealthStatus.UNKNOWN
    
    def test_health_check_not_ready_plugin(self):
        """Health check for non-ready plugin returns UNHEALTHY."""
        bridge = Bridge()
        
        manifest = make_manifest(plugin_id="test", name="Test", version="1.0.0")
        bridge._register_plugin(manifest)
        bridge._plugins["test"].state = PluginState.ERROR
        bridge._plugins["test"].error = "Init failed"
        
        result = bridge.health_check("test")
        assert result.status == HealthStatus.UNHEALTHY
        assert "error" in result.details
    
    def test_health_check_ready_plugin(self):
        """Health check for ready plugin returns HEALTHY."""
        bridge = Bridge()
        
        manifest = make_manifest(plugin_id="test", name="Test", version="1.0.0")
        bridge._register_plugin(manifest)
        bridge._plugins["test"].state = PluginState.READY
        
        result = bridge.health_check("test")
        assert result.status == HealthStatus.HEALTHY


class TestBridgeProperties:
    """Tests for Bridge property accessors."""
    
    def test_plugins_dir_default(self):
        """plugins_dir should have a sensible default."""
        bridge = Bridge()
        assert bridge.plugins_dir.name == "plugins"
    
    def test_plugins_dir_setter(self):
        """plugins_dir should be settable."""
        bridge = Bridge()
        bridge.plugins_dir = Path("/custom/path")
        assert bridge.plugins_dir == Path("/custom/path")
    
    def test_developer_mode_default(self):
        """developer_mode should default to False."""
        bridge = Bridge()
        assert bridge.developer_mode is False
    
    def test_developer_mode_setter(self):
        """developer_mode should be settable."""
        bridge = Bridge()
        bridge.developer_mode = True
        assert bridge.developer_mode is True
    
    def test_is_ready_default(self):
        """is_ready should be False initially."""
        bridge = Bridge()
        assert bridge.is_ready is False


class TestBridgeDiscovery:
    """Tests for plugin discovery (with mocked filesystem)."""
    
    def test_discover_empty_dir(self, tmp_path):
        """Discover should handle empty directory (but still include core plugins)."""
        bridge = Bridge()
        bridge.plugins_dir = tmp_path
        
        discovered = bridge.discover()
        # Core plugins are always included
        assert "settings_update" in discovered
        # No additional plugins discovered
        assert len(discovered) == 1
    
    def test_discover_nonexistent_dir(self, tmp_path):
        """Discover should handle nonexistent directory (but still include core plugins)."""
        bridge = Bridge()
        bridge.plugins_dir = tmp_path / "nonexistent"
        
        discovered = bridge.discover()
        # Core plugins are always included
        assert "settings_update" in discovered
        # No additional plugins discovered
        assert len(discovered) == 1
    
    def test_discover_v2_plugin(self, tmp_path):
        """Should discover v2 plugin with manifest."""
        bridge = Bridge()
        bridge.plugins_dir = tmp_path
        
        # Create plugin directory with manifest
        plugin_dir = tmp_path / "my_plugin"
        plugin_dir.mkdir()
        
        manifest_content = """
id: my_plugin
name: My Plugin
version: 1.0.0
description: Test plugin
type: tool
jupiter_version: ">=0.1.0"
"""
        (plugin_dir / "plugin.yaml").write_text(manifest_content)
        
        discovered = bridge.discover()
        
        assert "my_plugin" in discovered
        assert bridge.get_plugin("my_plugin") is not None


class TestLegacyPluginDetection:
    """Tests for legacy plugin class detection."""
    
    def test_is_legacy_plugin_class_valid(self):
        """Should detect valid legacy plugin classes."""
        bridge = Bridge()
        
        class ValidPlugin:
            name = "valid"
            version = "1.0.0"
            
            def on_scan(self, report):
                pass
        
        assert bridge._is_legacy_plugin_class(ValidPlugin)
    
    def test_is_legacy_plugin_class_no_hooks(self):
        """Should reject classes without hook methods."""
        bridge = Bridge()
        
        class NoHooks:
            name = "no_hooks"
            version = "1.0.0"
        
        assert not bridge._is_legacy_plugin_class(NoHooks)
    
    def test_is_legacy_plugin_class_no_version(self):
        """Should reject classes without version."""
        bridge = Bridge()
        
        class NoVersion:
            name = "no_version"
            
            def on_scan(self, report):
                pass
        
        assert not bridge._is_legacy_plugin_class(NoVersion)
    
    def test_is_legacy_plugin_class_instance(self):
        """Should reject instances (not classes)."""
        bridge = Bridge()
        
        class Plugin:
            name = "plugin"
            version = "1.0.0"
            
            def on_scan(self, report):
                pass
        
        assert not bridge._is_legacy_plugin_class(Plugin())


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
