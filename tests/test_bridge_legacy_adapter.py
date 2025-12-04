"""Tests for Legacy Adapter module.

Tests the LegacyAdapter functionality for detecting and wrapping
legacy plugins that use the old Plugin protocol.
"""

from __future__ import annotations

import logging
import pytest
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from jupiter.core.bridge.legacy_adapter import (
    LegacyAdapter,
    LegacyManifest,
    LegacyPluginWrapper,
    LegacyCapabilities,
    is_legacy_plugin,
    is_legacy_ui_plugin,
    get_legacy_adapter,
    init_legacy_adapter,
    shutdown_legacy_adapter,
    discover_legacy_plugins,
)
from jupiter.core.bridge.interfaces import PluginType


# =============================================================================
# FIXTURES
# =============================================================================

class MockLegacyPlugin:
    """Mock legacy plugin for testing."""
    
    name = "Mock Plugin"
    version = "1.0.0"
    description = "A mock legacy plugin for testing"
    
    def __init__(self):
        self.configured = False
        self.scan_called = False
        self.analyze_called = False
        self.last_config: Dict[str, Any] = {}
        self.last_report: Dict[str, Any] = {}
        self.last_summary: Dict[str, Any] = {}
    
    def on_scan(self, report: dict[str, Any]) -> None:
        self.scan_called = True
        self.last_report = report
    
    def on_analyze(self, summary: dict[str, Any]) -> None:
        self.analyze_called = True
        self.last_summary = summary
    
    def configure(self, config: dict[str, Any]) -> None:
        self.configured = True
        self.last_config = config


class MockLegacyUIPlugin:
    """Mock legacy UI plugin for testing."""
    
    name = "Mock UI Plugin"
    version = "2.0.0"
    description = "A mock legacy UI plugin"
    
    class MockUIConfig:
        ui_type = "sidebar"
        menu_icon = "🧪"
        menu_label_key = "mock_ui"
    
    ui_config = MockUIConfig()
    
    def __init__(self):
        self.configured = False
    
    def on_scan(self, report: dict[str, Any]) -> None:
        pass
    
    def on_analyze(self, summary: dict[str, Any]) -> None:
        pass
    
    def configure(self, config: dict[str, Any]) -> None:
        self.configured = True
    
    def get_ui_html(self) -> str:
        return "<div>Mock UI</div>"
    
    def get_ui_js(self) -> str:
        return "console.log('Mock UI');"


class NotAPlugin:
    """Class that is NOT a plugin."""
    
    name = "Not A Plugin"
    
    def some_method(self):
        pass


class IncompletePlugin:
    """Class missing some required methods."""
    
    name = "Incomplete"
    version = "1.0.0"
    description = "Missing methods"
    
    def on_scan(self, report: dict[str, Any]) -> None:
        pass
    
    # Missing on_analyze and configure


@pytest.fixture
def adapter():
    """Create a fresh LegacyAdapter for each test."""
    return LegacyAdapter()


@pytest.fixture
def mock_plugin():
    """Create a mock legacy plugin instance."""
    return MockLegacyPlugin()


@pytest.fixture
def mock_ui_plugin():
    """Create a mock legacy UI plugin instance."""
    return MockLegacyUIPlugin()


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton adapter after each test."""
    yield
    shutdown_legacy_adapter()


# =============================================================================
# TESTS: DETECTION FUNCTIONS
# =============================================================================

class TestDetectionFunctions:
    """Tests for legacy plugin detection functions."""
    
    def test_is_legacy_plugin_valid(self):
        """Test detection of valid legacy plugin."""
        assert is_legacy_plugin(MockLegacyPlugin) is True
    
    def test_is_legacy_plugin_ui(self):
        """Test that UI plugins are also detected as legacy plugins."""
        assert is_legacy_plugin(MockLegacyUIPlugin) is True
    
    def test_is_legacy_plugin_not_a_plugin(self):
        """Test that non-plugins are not detected."""
        assert is_legacy_plugin(NotAPlugin) is False
    
    def test_is_legacy_plugin_incomplete(self):
        """Test that incomplete plugins are not detected."""
        assert is_legacy_plugin(IncompletePlugin) is False
    
    def test_is_legacy_plugin_instance_not_class(self):
        """Test that instances are not detected (only classes)."""
        instance = MockLegacyPlugin()
        # Pass type to avoid type error, but it should still return False
        assert is_legacy_plugin(type(instance)) is True  # type(instance) IS the class
    
    def test_is_legacy_plugin_none(self):
        """Test handling of None."""
        assert is_legacy_plugin(None) is False  # type: ignore
    
    def test_is_legacy_ui_plugin_valid(self):
        """Test detection of valid legacy UI plugin."""
        assert is_legacy_ui_plugin(MockLegacyUIPlugin) is True
    
    def test_is_legacy_ui_plugin_no_ui(self):
        """Test that regular plugins without UI are not UI plugins."""
        assert is_legacy_ui_plugin(MockLegacyPlugin) is False
    
    def test_is_legacy_ui_plugin_not_a_plugin(self):
        """Test that non-plugins are not UI plugins."""
        assert is_legacy_ui_plugin(NotAPlugin) is False


# =============================================================================
# TESTS: LEGACY MANIFEST
# =============================================================================

class TestLegacyManifest:
    """Tests for LegacyManifest class."""
    
    def test_from_legacy_class_basic(self):
        """Test creating manifest from basic legacy class."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        
        assert manifest.id == "mock_plugin"
        assert manifest.name == "Mock Plugin"
        assert manifest.version == "1.0.0"
        assert manifest.description == "A mock legacy plugin for testing"
        assert manifest.legacy is True
        assert manifest.legacy_class == "jupiter.plugins.mock:MockLegacyPlugin"
    
    def test_from_legacy_class_ui(self):
        """Test creating manifest from UI legacy class."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyUIPlugin,
            "jupiter.plugins.mock_ui"
        )
        
        assert manifest.capabilities.ui is True
        assert manifest.capabilities.health is False
        assert manifest.capabilities.metrics is False
    
    def test_from_legacy_class_capabilities(self):
        """Test that capabilities are correctly detected."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        
        # Legacy plugins have limited capabilities
        assert manifest.capabilities.health is False
        assert manifest.capabilities.metrics is False
        assert manifest.capabilities.cli is False
        assert manifest.capabilities.api is False
        assert manifest.capabilities.ui is False
        assert manifest.capabilities.jobs is False
    
    def test_to_dict(self):
        """Test manifest serialization."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        
        data = manifest.to_dict()
        
        assert data["id"] == "mock_plugin"
        assert data["legacy"] is True
        assert data["legacy_class"] == "jupiter.plugins.mock:MockLegacyPlugin"
        assert "capabilities" in data
        assert "permissions" in data
    
    def test_default_permissions_empty(self):
        """Test that legacy plugins have no permissions by default."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        
        # Restrictive: no permissions by default
        assert manifest.permissions == []
    
    def test_plugin_type_default(self):
        """Test default plugin type."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        
        assert manifest.type == PluginType.TOOL


# =============================================================================
# TESTS: LEGACY PLUGIN WRAPPER
# =============================================================================

class TestLegacyPluginWrapper:
    """Tests for LegacyPluginWrapper class."""
    
    def test_wrapper_creation(self, mock_plugin):
        """Test wrapper creation."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        wrapper = LegacyPluginWrapper(manifest, mock_plugin)
        
        assert wrapper.manifest == manifest
        assert wrapper.legacy_instance == mock_plugin
    
    def test_wrapper_init(self, mock_plugin):
        """Test wrapper initialization."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        wrapper = LegacyPluginWrapper(manifest, mock_plugin)
        
        config = {"key": "value"}
        wrapper.init(config)
        
        assert mock_plugin.configured is True
        assert mock_plugin.last_config == config
    
    def test_wrapper_shutdown(self, mock_plugin):
        """Test wrapper shutdown (no-op for legacy)."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        wrapper = LegacyPluginWrapper(manifest, mock_plugin)
        wrapper.init({})
        
        # Should not raise
        wrapper.shutdown()
    
    def test_wrapper_health_initialized(self, mock_plugin):
        """Test health check when initialized."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        wrapper = LegacyPluginWrapper(manifest, mock_plugin)
        wrapper.init({})
        
        health = wrapper.health()
        
        assert health["status"] == "healthy"
        assert health["legacy"] is True
        assert health["initialized"] is True
    
    def test_wrapper_health_not_initialized(self, mock_plugin):
        """Test health check when not initialized."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        wrapper = LegacyPluginWrapper(manifest, mock_plugin)
        
        health = wrapper.health()
        
        assert health["status"] == "unhealthy"
        assert health["initialized"] is False
    
    def test_wrapper_metrics(self, mock_plugin):
        """Test metrics (not supported for legacy)."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        wrapper = LegacyPluginWrapper(manifest, mock_plugin)
        
        metrics = wrapper.metrics()
        
        assert metrics["legacy"] is True
        assert metrics["metrics_supported"] is False
    
    def test_wrapper_on_scan(self, mock_plugin):
        """Test on_scan delegation."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        wrapper = LegacyPluginWrapper(manifest, mock_plugin)
        wrapper.init({})
        
        report = {"files": [], "summary": {}}
        wrapper.on_scan(report)
        
        assert mock_plugin.scan_called is True
        assert mock_plugin.last_report == report
    
    def test_wrapper_on_scan_not_initialized(self, mock_plugin):
        """Test on_scan skipped when not initialized."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        wrapper = LegacyPluginWrapper(manifest, mock_plugin)
        
        report = {"files": []}
        wrapper.on_scan(report)
        
        # Should be skipped, not called
        assert mock_plugin.scan_called is False
    
    def test_wrapper_on_analyze(self, mock_plugin):
        """Test on_analyze delegation."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        wrapper = LegacyPluginWrapper(manifest, mock_plugin)
        wrapper.init({})
        
        summary = {"total_files": 10}
        wrapper.on_analyze(summary)
        
        assert mock_plugin.analyze_called is True
        assert mock_plugin.last_summary == summary
    
    def test_wrapper_on_analyze_not_initialized(self, mock_plugin):
        """Test on_analyze skipped when not initialized."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        wrapper = LegacyPluginWrapper(manifest, mock_plugin)
        
        summary = {"total_files": 10}
        wrapper.on_analyze(summary)
        
        assert mock_plugin.analyze_called is False
    
    def test_wrapper_get_ui_html_no_ui(self, mock_plugin):
        """Test get_ui_html for non-UI plugin."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        wrapper = LegacyPluginWrapper(manifest, mock_plugin)
        
        assert wrapper.get_ui_html() is None
    
    def test_wrapper_get_ui_html_with_ui(self, mock_ui_plugin):
        """Test get_ui_html for UI plugin."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyUIPlugin,
            "jupiter.plugins.mock_ui"
        )
        wrapper = LegacyPluginWrapper(manifest, mock_ui_plugin)
        
        html = wrapper.get_ui_html()
        
        assert html == "<div>Mock UI</div>"
    
    def test_wrapper_get_ui_js_no_ui(self, mock_plugin):
        """Test get_ui_js for non-UI plugin."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        wrapper = LegacyPluginWrapper(manifest, mock_plugin)
        
        assert wrapper.get_ui_js() is None
    
    def test_wrapper_get_ui_js_with_ui(self, mock_ui_plugin):
        """Test get_ui_js for UI plugin."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyUIPlugin,
            "jupiter.plugins.mock_ui"
        )
        wrapper = LegacyPluginWrapper(manifest, mock_ui_plugin)
        
        js = wrapper.get_ui_js()
        
        assert js == "console.log('Mock UI');"
    
    def test_wrapper_init_error_handling(self, mock_plugin):
        """Test error handling during init."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        
        # Make configure raise an error
        mock_plugin.configure = MagicMock(side_effect=ValueError("Config error"))
        
        wrapper = LegacyPluginWrapper(manifest, mock_plugin)
        
        with pytest.raises(Exception):
            wrapper.init({})
        
        health = wrapper.health()
        assert health["status"] == "unhealthy"
        assert "Config error" in health["error"]


# =============================================================================
# TESTS: LEGACY ADAPTER
# =============================================================================

class TestLegacyAdapter:
    """Tests for LegacyAdapter class."""
    
    def test_adapter_creation(self, adapter):
        """Test adapter creation."""
        assert adapter.discovered_plugins == {}
        assert adapter.discovery_errors == {}
    
    def test_adapter_get_stats_empty(self, adapter):
        """Test stats when no plugins discovered."""
        stats = adapter.get_stats()
        
        assert stats["discovered_count"] == 0
        assert stats["error_count"] == 0
        assert stats["scan_count"] == 0
        assert stats["plugins"] == []
    
    def test_adapter_get_plugin_not_found(self, adapter):
        """Test getting a non-existent plugin."""
        assert adapter.get_plugin("nonexistent") is None
    
    def test_adapter_clear(self, adapter):
        """Test clearing the adapter."""
        # Add some mock data
        adapter._discovered["test"] = MagicMock()
        adapter._errors["error.py"] = "Some error"
        
        adapter.clear()
        
        assert adapter.discovered_plugins == {}
        assert adapter.discovery_errors == {}
    
    def test_adapter_discover_nonexistent_dir(self, adapter, tmp_path):
        """Test discovery with non-existent directory."""
        nonexistent = tmp_path / "nonexistent"
        
        result = adapter.discover(nonexistent)
        
        assert result == []
    
    def test_adapter_discover_empty_dir(self, adapter, tmp_path):
        """Test discovery with empty directory."""
        result = adapter.discover(tmp_path)
        
        assert result == []
    
    def test_adapter_discover_skips_underscore_files(self, adapter, tmp_path):
        """Test that files starting with _ are skipped."""
        # Create a file starting with _
        (tmp_path / "_private.py").write_text("# Private module")
        
        result = adapter.discover(tmp_path)
        
        assert result == []
    
    def test_adapter_stats_after_scan(self, adapter, tmp_path):
        """Test stats after scanning."""
        adapter.discover(tmp_path)
        
        stats = adapter.get_stats()
        
        assert stats["scan_count"] == 1


# =============================================================================
# TESTS: MODULE-LEVEL FUNCTIONS
# =============================================================================

class TestModuleFunctions:
    """Tests for module-level convenience functions."""
    
    def test_get_legacy_adapter_singleton(self):
        """Test that get_legacy_adapter returns singleton."""
        adapter1 = get_legacy_adapter()
        adapter2 = get_legacy_adapter()
        
        assert adapter1 is adapter2
    
    def test_init_legacy_adapter(self):
        """Test initializing the adapter."""
        adapter = init_legacy_adapter()
        
        assert adapter is not None
        assert get_legacy_adapter() is adapter
    
    def test_shutdown_legacy_adapter(self):
        """Test shutting down the adapter."""
        init_legacy_adapter()
        shutdown_legacy_adapter()
        
        # After shutdown, getting adapter should create new one
        new_adapter = get_legacy_adapter()
        assert new_adapter is not None
    
    def test_shutdown_legacy_adapter_not_initialized(self):
        """Test shutdown when not initialized (should not raise)."""
        # Ensure no adapter exists
        shutdown_legacy_adapter()
        
        # Should not raise
        shutdown_legacy_adapter()
    
    def test_discover_legacy_plugins_uses_singleton(self, tmp_path):
        """Test that discover_legacy_plugins uses the singleton."""
        result = discover_legacy_plugins(tmp_path)
        
        assert result == []
        
        # Check that singleton was used
        adapter = get_legacy_adapter()
        stats = adapter.get_stats()
        assert stats["scan_count"] >= 1


# =============================================================================
# TESTS: INTEGRATION
# =============================================================================

class TestIntegration:
    """Integration tests for legacy adapter."""
    
    def test_full_workflow(self, mock_plugin):
        """Test full workflow: detect, wrap, initialize, call hooks."""
        # Create manifest
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        
        # Create wrapper
        wrapper = LegacyPluginWrapper(manifest, mock_plugin)
        
        # Initialize
        wrapper.init({"setting": "value"})
        assert mock_plugin.configured is True
        
        # Call hooks
        wrapper.on_scan({"files": []})
        assert mock_plugin.scan_called is True
        
        wrapper.on_analyze({"summary": {}})
        assert mock_plugin.analyze_called is True
        
        # Check health
        health = wrapper.health()
        assert health["status"] == "healthy"
        
        # Shutdown
        wrapper.shutdown()
    
    def test_adapter_with_exclusions(self, adapter, tmp_path):
        """Test adapter respects exclusions."""
        # Even if plugins were found, exclusions would filter them
        result = adapter.discover(tmp_path, exclude={"some_plugin"})
        
        assert result == []
    
    def test_manifest_serialization_roundtrip(self):
        """Test manifest can be serialized and contains all fields."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        
        data = manifest.to_dict()
        
        # Check all expected fields are present
        expected_fields = [
            "id", "name", "version", "description", "author",
            "type", "capabilities", "permissions", "legacy",
            "legacy_class", "dependencies", "entrypoints"
        ]
        
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"


# =============================================================================
# TESTS: ERROR HANDLING
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in legacy adapter."""
    
    def test_wrapper_handles_on_scan_error(self, mock_plugin):
        """Test wrapper handles errors in on_scan."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        
        # Make on_scan raise an error
        mock_plugin.on_scan = MagicMock(side_effect=RuntimeError("Scan error"))
        
        wrapper = LegacyPluginWrapper(manifest, mock_plugin)
        wrapper.init({})
        
        # Should not raise, error should be logged
        wrapper.on_scan({})
        
        # Error should be captured
        health = wrapper.health()
        assert "Scan error" in (health.get("error") or "")
    
    def test_wrapper_handles_on_analyze_error(self, mock_plugin):
        """Test wrapper handles errors in on_analyze."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyPlugin,
            "jupiter.plugins.mock"
        )
        
        # Make on_analyze raise an error
        mock_plugin.on_analyze = MagicMock(side_effect=RuntimeError("Analyze error"))
        
        wrapper = LegacyPluginWrapper(manifest, mock_plugin)
        wrapper.init({})
        
        # Should not raise
        wrapper.on_analyze({})
        
        health = wrapper.health()
        assert "Analyze error" in (health.get("error") or "")
    
    def test_wrapper_handles_ui_html_error(self, mock_ui_plugin):
        """Test wrapper handles errors in get_ui_html."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyUIPlugin,
            "jupiter.plugins.mock_ui"
        )
        
        # Make get_ui_html raise an error
        mock_ui_plugin.get_ui_html = MagicMock(side_effect=RuntimeError("UI error"))
        
        wrapper = LegacyPluginWrapper(manifest, mock_ui_plugin)
        
        # Should not raise, should return None
        result = wrapper.get_ui_html()
        assert result is None
    
    def test_wrapper_handles_ui_js_error(self, mock_ui_plugin):
        """Test wrapper handles errors in get_ui_js."""
        manifest = LegacyManifest.from_legacy_class(
            MockLegacyUIPlugin,
            "jupiter.plugins.mock_ui"
        )
        
        # Make get_ui_js raise an error
        mock_ui_plugin.get_ui_js = MagicMock(side_effect=RuntimeError("JS error"))
        
        wrapper = LegacyPluginWrapper(manifest, mock_ui_plugin)
        
        # Should not raise, should return None
        result = wrapper.get_ui_js()
        assert result is None
