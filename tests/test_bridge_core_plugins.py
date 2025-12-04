"""Tests for jupiter.core.bridge.core_plugins module.

Version: 0.1.0

Tests for built-in core plugins in the Bridge v2 system.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Any


# =============================================================================
# Core Plugins Registry Tests
# =============================================================================

class TestCorePluginsRegistry:
    """Tests for the core_plugins module."""
    
    def test_get_core_plugin_ids(self):
        """Should return list of core plugin IDs."""
        from jupiter.core.bridge.core_plugins import get_core_plugin_ids
        
        ids = get_core_plugin_ids()
        assert isinstance(ids, list)
        assert "settings_update" in ids
    
    def test_get_core_plugins_returns_instances(self):
        """Should return list of plugin instances."""
        from jupiter.core.bridge.core_plugins import get_core_plugins
        from jupiter.core.bridge.interfaces import IPlugin
        
        plugins = get_core_plugins()
        assert isinstance(plugins, list)
        assert len(plugins) > 0
        
        for plugin in plugins:
            # Check it has a manifest
            assert hasattr(plugin, "manifest")
            assert plugin.manifest is not None


# =============================================================================
# Settings Update Plugin Tests
# =============================================================================

class TestSettingsUpdateManifest:
    """Tests for SettingsUpdateManifest."""
    
    def test_manifest_fields(self):
        """Should have correct manifest fields."""
        from jupiter.core.bridge.core_plugins.settings_update_plugin import SettingsUpdateManifest
        from jupiter.core.bridge.interfaces import PluginType, Permission
        
        manifest = SettingsUpdateManifest()
        
        assert manifest.id == "settings_update"
        assert manifest.name == "Settings Update"
        assert manifest.plugin_type == PluginType.CORE
        assert manifest.trust_level == "official"
        assert Permission.FS_READ in manifest.permissions
        assert Permission.FS_WRITE in manifest.permissions
    
    def test_manifest_icon(self):
        """Should have icon property."""
        from jupiter.core.bridge.core_plugins.settings_update_plugin import SettingsUpdateManifest
        
        manifest = SettingsUpdateManifest()
        assert manifest.icon == "🔄"


class TestSettingsUpdatePlugin:
    """Tests for SettingsUpdatePlugin."""
    
    @pytest.fixture
    def plugin(self):
        """Create a fresh plugin instance."""
        from jupiter.core.bridge.core_plugins.settings_update_plugin import SettingsUpdatePlugin
        return SettingsUpdatePlugin()
    
    def test_init_creates_manifest(self, plugin):
        """Should create manifest on init."""
        assert plugin.manifest is not None
        assert plugin.manifest.id == "settings_update"
    
    def test_configure_sets_enabled(self, plugin):
        """Should configure enabled state."""
        plugin.configure({"enabled": False})
        assert plugin._enabled is False
        
        plugin.configure({"enabled": True})
        assert plugin._enabled is True
    
    def test_configure_with_none(self, plugin):
        """Should handle None config."""
        plugin.configure(None)
        assert plugin._enabled is True  # Default
    
    def test_health_returns_healthy(self, plugin):
        """Should return healthy status when enabled."""
        from jupiter.core.bridge.interfaces import HealthStatus
        
        plugin.configure({"enabled": True})
        result = plugin.health()
        
        assert result.status == HealthStatus.HEALTHY
        assert "operational" in result.message.lower()
    
    def test_health_returns_unhealthy_when_disabled(self, plugin):
        """Should return unhealthy when disabled."""
        from jupiter.core.bridge.interfaces import HealthStatus
        
        plugin.configure({"enabled": False})
        result = plugin.health()
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "disabled" in result.message.lower()
    
    def test_metrics_returns_data(self, plugin):
        """Should return metrics data."""
        metrics = plugin.metrics()
        
        assert metrics.execution_count == 0
        assert metrics.error_count == 0
        assert "enabled" in metrics.custom
    
    def test_get_api_contribution(self, plugin):
        """Should return API contribution."""
        from jupiter.core.bridge.interfaces import APIContribution
        
        contrib = plugin.get_api_contribution()
        
        assert isinstance(contrib, APIContribution)
        assert contrib.plugin_id == "settings_update"
        assert "/plugins/settings_update" in contrib.prefix
    
    def test_get_ui_contribution(self, plugin):
        """Should return UI contribution."""
        from jupiter.core.bridge.interfaces import UIContribution
        
        contrib = plugin.get_ui_contribution()
        
        assert isinstance(contrib, UIContribution)
        assert contrib.plugin_id == "settings_update"
        assert contrib.panel_type == "settings"
    
    def test_get_current_version(self, plugin, tmp_path):
        """Should read version from file."""
        # Create a VERSION file
        version_file = tmp_path / "VERSION"
        version_file.write_text("1.2.3")
        
        # Mock the path
        with patch.object(
            plugin,
            "get_current_version",
            return_value="1.2.3"
        ):
            version = plugin.get_current_version()
            assert version == "1.2.3"
    
    def test_get_settings_html(self, plugin):
        """Should return HTML content."""
        html = plugin.get_settings_html()
        
        assert "update-settings" in html
        assert "update-source-input" in html
        assert "update-apply-btn" in html
    
    def test_get_settings_js(self, plugin):
        """Should return JavaScript content."""
        js = plugin.get_settings_js()
        
        assert "updateSettings" in js
        assert "applyUpdate" in js
        assert "loadVersion" in js


class TestSettingsUpdatePluginUpdateLogic:
    """Tests for update logic in SettingsUpdatePlugin."""
    
    @pytest.fixture
    def plugin(self):
        """Create a fresh plugin instance."""
        from jupiter.core.bridge.core_plugins.settings_update_plugin import SettingsUpdatePlugin
        plugin = SettingsUpdatePlugin()
        plugin.configure({"enabled": True})
        return plugin
    
    def test_apply_update_raises_when_disabled(self, plugin):
        """Should raise error when plugin is disabled."""
        plugin.configure({"enabled": False})
        
        with pytest.raises(RuntimeError, match="disabled"):
            plugin.apply_update("test.zip", force=False)
    
    def test_apply_update_invalid_source(self, plugin):
        """Should raise error for invalid source format."""
        with pytest.raises(ValueError, match="Unknown source format"):
            plugin.apply_update("invalid_source", force=False)
    
    def test_apply_update_increments_counters(self, plugin, tmp_path):
        """Should increment update counters on success."""
        # Create a dummy zip file
        import zipfile
        zip_path = tmp_path / "update.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("dummy.txt", "test content")
        
        initial_count = plugin._update_count
        
        # Apply update
        with patch.object(plugin, "_apply_zip_update", return_value={"status": "ok", "message": "Done"}):
            plugin.apply_update(str(zip_path), force=False)
        
        assert plugin._update_count == initial_count + 1
        assert plugin._last_update is not None
    
    def test_upload_update_file(self, plugin):
        """Should save uploaded file."""
        content = b"ZIP content"
        filename = "update.zip"
        
        result = plugin.upload_update_file(content, filename)
        
        assert "path" in result
        assert result["filename"] == filename
    
    def test_upload_update_file_raises_when_disabled(self, plugin):
        """Should raise error when plugin is disabled."""
        plugin.configure({"enabled": False})
        
        with pytest.raises(RuntimeError, match="disabled"):
            plugin.upload_update_file(b"content", "test.zip")


# =============================================================================
# Bridge Core Plugins Integration Tests
# =============================================================================

class TestBridgeCorePluginsIntegration:
    """Tests for core plugins integration with Bridge."""
    
    def test_discover_includes_core_plugins(self):
        """Should discover core plugins."""
        from jupiter.core.bridge import Bridge
        
        # Reset to get clean state
        Bridge.reset_instance()
        bridge = Bridge()
        
        discovered = bridge.discover_core_plugins()
        
        assert "settings_update" in discovered
        assert "settings_update" in bridge._plugins
        
        # Cleanup
        Bridge.reset_instance()
    
    def test_discover_adds_core_plugins_first(self):
        """Should add core plugins in discover()."""
        from jupiter.core.bridge import Bridge
        from pathlib import Path
        
        Bridge.reset_instance()
        bridge = Bridge()
        
        # Point to a non-existent plugins dir to avoid scanning
        bridge._plugins_dir = Path("/nonexistent_plugins_dir_for_test")
        
        discovered = bridge.discover()
        
        assert "settings_update" in discovered
        
        Bridge.reset_instance()
    
    def test_initialize_core_plugin(self):
        """Should initialize core plugins correctly."""
        from jupiter.core.bridge import Bridge
        from jupiter.core.bridge.interfaces import PluginState
        
        Bridge.reset_instance()
        bridge = Bridge()
        
        # Discover core plugins
        bridge.discover_core_plugins()
        
        # Initialize
        results = bridge.initialize(["settings_update"])
        
        assert results["settings_update"] is True
        assert bridge._plugins["settings_update"].state == PluginState.READY
        
        Bridge.reset_instance()
    
    def test_core_plugin_api_contribution_registered(self):
        """Should register API contribution from core plugin."""
        from jupiter.core.bridge import Bridge
        
        Bridge.reset_instance()
        bridge = Bridge()
        
        bridge.discover_core_plugins()
        bridge.initialize(["settings_update"])
        
        # Check API contribution was registered
        api_keys = list(bridge._api_contributions.keys())
        assert any("settings_update" in key for key in api_keys)
        
        Bridge.reset_instance()
