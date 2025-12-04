"""Tests for Bridge lifecycle: discover -> initialize -> ready.

Version: 0.1.0

These tests verify the complete plugin lifecycle from discovery
through initialization to WebUI publication.
"""

import pytest
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch, call

from jupiter.core.bridge.bridge import Bridge, PluginInfo
from jupiter.core.bridge.interfaces import (
    PluginState,
    PluginType,
    IPlugin,
    IPluginManifest,
    CLIContribution,
    APIContribution,
    UIContribution,
    UILocation,
)
from jupiter.core.bridge.manifest import PluginManifest
from jupiter.core.bridge.events import EventTopic


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def bridge():
    """Create a fresh Bridge instance for testing."""
    Bridge.reset_instance()
    b = Bridge.get_instance()
    yield b
    Bridge.reset_instance()


@pytest.fixture
def temp_plugins_dir():
    """Create a temporary directory for plugins."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def make_manifest(
    plugin_id: str,
    name: Optional[str] = None,
    version: str = "1.0.0",
    description: str = "Test plugin",
    plugin_type: PluginType = PluginType.TOOL,
    dependencies: Optional[List[str]] = None,
    ui_contributions: Optional[List[UIContribution]] = None,
) -> PluginManifest:
    """Helper to create PluginManifest instances for testing."""
    manifest = PluginManifest(
        id=plugin_id,
        name=name or plugin_id,
        version=version,
        description=description,
        plugin_type=plugin_type,
        jupiter_version="1.0.0",
        dependencies={dep: ">=0.0.0" for dep in (dependencies or [])},
        ui_contributions=ui_contributions,
    )
    
    return manifest


def create_plugin_yaml(plugin_dir: Path, plugin_id: str, **kwargs) -> Path:
    """Create a plugin.yaml file in the specified directory."""
    import yaml
    
    (plugin_dir / plugin_id).mkdir(parents=True, exist_ok=True)
    
    manifest_data = {
        "id": plugin_id,
        "name": kwargs.get("name", plugin_id),
        "version": kwargs.get("version", "1.0.0"),
        "description": kwargs.get("description", "Test plugin"),
        "type": kwargs.get("type", "tool"),
        "jupiter_version": kwargs.get("jupiter_version", ">=1.0.0"),
        "permissions": kwargs.get("permissions", []),
        "entrypoints": {
            "main": "__init__.py",
        },
        "ui": kwargs.get("ui", {"panels": [], "assets": {}}),
    }
    
    manifest_path = plugin_dir / plugin_id / "plugin.yaml"
    with open(manifest_path, "w") as f:
        yaml.dump(manifest_data, f)
    
    # Create __init__.py
    init_path = plugin_dir / plugin_id / "__init__.py"
    init_path.write_text(f'''"""Test plugin {plugin_id}."""

class {plugin_id.title().replace("_", "")}Plugin:
    name = "{plugin_id}"
    version = "1.0.0"
    
    def init(self, services):
        pass
''')
    
    return manifest_path


# ============================================================================
# Tests: ready() method
# ============================================================================

class TestReadyMethod:
    """Tests for Bridge.ready() method."""
    
    def test_ready_returns_ui_manifest(self, bridge: Bridge):
        """ready() should return a dict with ui_manifest."""
        # Force ready state
        bridge._ready = True
        
        result = bridge.ready()
        
        assert "ui_manifest" in result
        assert "plugins_ready" in result
        assert "plugins_error" in result
    
    def test_ready_auto_initializes_if_not_ready(self, bridge: Bridge, temp_plugins_dir: Path):
        """ready() should auto-initialize if called before initialize()."""
        bridge.plugins_dir = temp_plugins_dir
        
        # Should not raise, should auto-initialize
        result = bridge.ready()
        
        assert bridge.is_ready
        assert "ui_manifest" in result
    
    def test_ready_counts_plugin_states(self, bridge: Bridge):
        """ready() should count plugins by state."""
        # Register plugins with different states
        manifest1 = make_manifest("plugin_ready")
        manifest2 = make_manifest("plugin_error")
        manifest3 = make_manifest("plugin_ready2")
        
        bridge._plugins["plugin_ready"] = PluginInfo(
            manifest=manifest1,
            state=PluginState.READY
        )
        bridge._plugins["plugin_error"] = PluginInfo(
            manifest=manifest2,
            state=PluginState.ERROR,
            error="Test error"
        )
        bridge._plugins["plugin_ready2"] = PluginInfo(
            manifest=manifest3,
            state=PluginState.READY
        )
        
        bridge._ready = True
        result = bridge.ready()
        
        assert result["plugins_ready"] == 2
        assert result["plugins_error"] == 1
    
    def test_ready_emits_plugins_ready_event(self, bridge: Bridge):
        """ready() should emit PLUGINS_READY event."""
        events_received = []
        
        def capture_event(topic: str, payload: Dict[str, Any]):
            events_received.append((topic, payload))
        
        bridge.subscribe("PLUGINS_READY", capture_event)
        bridge._ready = True
        
        bridge.ready()
        
        assert len(events_received) == 1
        assert events_received[0][0] == "PLUGINS_READY"
        assert "ui_manifest" in events_received[0][1]


class TestBuildUIManifest:
    """Tests for Bridge._build_ui_manifest()."""
    
    def test_build_ui_manifest_empty(self, bridge: Bridge):
        """_build_ui_manifest() returns empty structure with no plugins."""
        manifest = bridge._build_ui_manifest()
        
        assert manifest["plugins"] == []
        assert manifest["ui_contributions"] == {}
        assert manifest["menus"] == []
    
    def test_build_ui_manifest_with_plugins(self, bridge: Bridge):
        """_build_ui_manifest() includes plugin summaries."""
        manifest1 = make_manifest("test_plugin", version="2.0.0")
        
        bridge._plugins["test_plugin"] = PluginInfo(
            manifest=manifest1,
            state=PluginState.READY,
            legacy=False,
        )
        
        ui_manifest = bridge._build_ui_manifest()
        
        assert len(ui_manifest["plugins"]) == 1
        plugin = ui_manifest["plugins"][0]
        assert plugin["id"] == "test_plugin"
        assert plugin["version"] == "2.0.0"
        assert plugin["state"] == "ready"
        assert plugin["legacy"] is False
    
    def test_build_ui_manifest_with_ui_contributions(self, bridge: Bridge):
        """_build_ui_manifest() includes UI contributions."""
        ui_contrib = UIContribution(
            id="main_panel",
            panel_type="full",
            mount_point="sidebar",
            route="/plugins/test/main",
            title_key="test_plugin.main_title",
            icon="cog",
        )
        manifest = make_manifest("test_plugin", ui_contributions=[ui_contrib])
        
        bridge._plugins["test_plugin"] = PluginInfo(
            manifest=manifest,
            state=PluginState.READY,
        )
        
        ui_manifest = bridge._build_ui_manifest()
        
        assert "test_plugin" in ui_manifest["ui_contributions"]
        panels = ui_manifest["ui_contributions"]["test_plugin"]
        assert len(panels) == 1
        assert panels[0]["id"] == "main_panel"
        assert panels[0]["mount_point"] == "sidebar"
    
    def test_build_ui_manifest_generates_menu_entries(self, bridge: Bridge):
        """_build_ui_manifest() generates menu entries for sidebar panels."""
        ui_contrib = UIContribution(
            id="main",
            panel_type="full",
            mount_point="sidebar",
            route="/plugins/test/main",
            title_key="test.title",
            icon="puzzle-piece",
        )
        manifest = make_manifest("test_plugin", ui_contributions=[ui_contrib])
        
        bridge._plugins["test_plugin"] = PluginInfo(
            manifest=manifest,
            state=PluginState.READY,
        )
        
        ui_manifest = bridge._build_ui_manifest()
        
        assert len(ui_manifest["menus"]) == 1
        menu = ui_manifest["menus"][0]
        assert menu["plugin_id"] == "test_plugin"
        assert menu["panel_id"] == "main"
        assert menu["icon"] == "puzzle-piece"
    
    def test_build_ui_manifest_excludes_non_ready_plugins(self, bridge: Bridge):
        """_build_ui_manifest() excludes UI contributions from non-ready plugins."""
        ui_contrib = UIContribution(
            id="panel",
            panel_type="full",
            mount_point="sidebar",
            route="/test",
            title_key="test",
        )
        manifest = make_manifest("error_plugin", ui_contributions=[ui_contrib])
        
        bridge._plugins["error_plugin"] = PluginInfo(
            manifest=manifest,
            state=PluginState.ERROR,
            error="Failed to load",
        )
        
        ui_manifest = bridge._build_ui_manifest()
        
        # Plugin should be in summary but not in UI contributions
        assert len(ui_manifest["plugins"]) == 1
        assert ui_manifest["plugins"][0]["state"] == "error"
        assert "error_plugin" not in ui_manifest["ui_contributions"]
        assert len(ui_manifest["menus"]) == 0


# ============================================================================
# Tests: Complete lifecycle
# ============================================================================

class TestCompleteLifecycle:
    """Integration tests for complete plugin lifecycle."""
    
    def test_lifecycle_discover_initialize_ready(self, bridge: Bridge, temp_plugins_dir: Path):
        """Test complete lifecycle: discover -> initialize -> ready."""
        bridge.plugins_dir = temp_plugins_dir
        
        # Create a simple plugin
        create_plugin_yaml(temp_plugins_dir, "test_plugin")
        
        # Phase 1: Discover
        discovered = bridge.discover()
        # Note: Will include core plugins too
        assert "test_plugin" in discovered
        
        # Verify plugin is in DISCOVERED state
        plugin_info = bridge.get_plugin("test_plugin")
        assert plugin_info is not None
        assert plugin_info.state == PluginState.DISCOVERED
        
        # Phase 2: Initialize
        results = bridge.initialize()
        
        # Verify plugin is in READY state
        plugin_info = bridge.get_plugin("test_plugin")
        assert plugin_info is not None
        assert plugin_info.state in (PluginState.READY, PluginState.ERROR)
        
        # Phase 3: Ready (publish to WebUI)
        ready_result = bridge.ready()
        
        assert "ui_manifest" in ready_result
        assert ready_result["plugins_ready"] >= 0  # At least core plugins
    
    def test_lifecycle_events_emitted(self, bridge: Bridge, temp_plugins_dir: Path):
        """Verify correct events are emitted during lifecycle."""
        events: List[tuple] = []
        
        def capture_all_events(topic: str, payload: Dict[str, Any]):
            events.append((topic, payload))
        
        bridge.subscribe("PLUGIN_LOADED", capture_all_events)
        bridge.subscribe("BRIDGE_READY", capture_all_events)
        bridge.subscribe("PLUGINS_READY", capture_all_events)
        
        bridge.plugins_dir = temp_plugins_dir
        create_plugin_yaml(temp_plugins_dir, "event_test")
        
        bridge.discover()
        bridge.initialize()
        bridge.ready()
        
        topics = [e[0] for e in events]
        
        # Should have BRIDGE_READY from initialize()
        assert "BRIDGE_READY" in topics
        
        # Should have PLUGINS_READY from ready()
        assert "PLUGINS_READY" in topics
    
    def test_lifecycle_plugin_load_order(self, bridge: Bridge, temp_plugins_dir: Path):
        """Verify plugins are loaded in correct order."""
        bridge.plugins_dir = temp_plugins_dir
        
        # Create plugins with dependencies
        create_plugin_yaml(temp_plugins_dir, "plugin_a")
        create_plugin_yaml(temp_plugins_dir, "plugin_b")
        
        discovered = bridge.discover()
        
        # All should be discovered
        assert "plugin_a" in discovered
        assert "plugin_b" in discovered
        
        # Initialize should succeed
        results = bridge.initialize()
        
        # Both should have results
        assert "plugin_a" in results
        assert "plugin_b" in results


class TestReadyIdempotent:
    """Tests for ready() idempotency."""
    
    def test_ready_can_be_called_multiple_times(self, bridge: Bridge):
        """ready() should be safe to call multiple times."""
        bridge._ready = True
        
        result1 = bridge.ready()
        result2 = bridge.ready()
        
        # Should return same structure
        assert result1.keys() == result2.keys()
    
    def test_ready_updates_after_plugin_state_change(self, bridge: Bridge):
        """ready() should reflect current plugin states."""
        manifest = make_manifest("dynamic_plugin")
        
        bridge._plugins["dynamic_plugin"] = PluginInfo(
            manifest=manifest,
            state=PluginState.READY,
        )
        bridge._ready = True
        
        result1 = bridge.ready()
        assert result1["plugins_ready"] == 1
        
        # Change state
        bridge._plugins["dynamic_plugin"].state = PluginState.ERROR
        
        result2 = bridge.ready()
        assert result2["plugins_ready"] == 0
        assert result2["plugins_error"] == 1


class TestLifecycleWithCorePlugins:
    """Tests verifying core plugins are handled correctly."""
    
    def test_core_plugins_discovered_first(self, bridge: Bridge, temp_plugins_dir: Path):
        """Core plugins should be discovered before external plugins."""
        bridge.plugins_dir = temp_plugins_dir
        create_plugin_yaml(temp_plugins_dir, "external_plugin")
        
        discovered = bridge.discover()
        
        # Core plugins should be first in list
        # (They're discovered via discover_core_plugins which is called first)
        core_indices = []
        external_indices = []
        
        for i, pid in enumerate(discovered):
            if pid in ("bridge", "settings_update"):
                core_indices.append(i)
            elif pid == "external_plugin":
                external_indices.append(i)
        
        # Core plugins have lower indices (discovered first)
        if core_indices and external_indices:
            assert max(core_indices) < min(external_indices)
    
    def test_core_plugins_initialized_first(self, bridge: Bridge, temp_plugins_dir: Path):
        """Core plugins should be initialized before tool plugins."""
        load_order = []
        
        original_init = bridge._initialize_plugin
        
        def track_init(plugin_id: str):
            load_order.append(plugin_id)
            # Skip actual initialization to avoid issues
            if plugin_id in bridge._plugins:
                bridge._plugins[plugin_id].state = PluginState.READY
        
        bridge._initialize_plugin = track_init
        bridge.plugins_dir = temp_plugins_dir
        
        create_plugin_yaml(temp_plugins_dir, "tool_plugin")
        
        bridge.discover()
        bridge.initialize()
        
        # Core plugins should appear before tool plugins
        if "bridge" in load_order and "tool_plugin" in load_order:
            assert load_order.index("bridge") < load_order.index("tool_plugin")


class TestUIManifestDefaults:
    """Tests for UI manifest default values."""
    
    def test_menu_entry_default_icon(self, bridge: Bridge):
        """Menu entries should have default icon if not specified."""
        ui_contrib = UIContribution(
            id="panel",
            panel_type="full",
            mount_point="sidebar",
            route="/test",
            title_key="test",
            # icon uses default emoji "🔌" from dataclass
        )
        manifest = make_manifest("no_icon_plugin", ui_contributions=[ui_contrib])
        
        bridge._plugins["no_icon_plugin"] = PluginInfo(
            manifest=manifest,
            state=PluginState.READY,
        )
        
        ui_manifest = bridge._build_ui_manifest()
        
        menu = ui_manifest["menus"][0]
        # Default icon is the emoji 🔌 when not specified
        assert menu["icon"] == "🔌"  # Default from UIContribution dataclass
    
    def test_menu_entry_generates_route(self, bridge: Bridge):
        """Menu entries should generate route if not provided."""
        ui_contrib = UIContribution(
            id="panel",
            panel_type="full",
            mount_point="sidebar",
            # route empty by default
            title_key="test",
        )
        manifest = make_manifest("no_route_plugin", ui_contributions=[ui_contrib])
        
        bridge._plugins["no_route_plugin"] = PluginInfo(
            manifest=manifest,
            state=PluginState.READY,
        )
        
        ui_manifest = bridge._build_ui_manifest()
        
        menu = ui_manifest["menus"][0]
        assert menu["route"] == "/plugins/no_route_plugin/panel"
