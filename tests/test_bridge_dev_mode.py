"""
Tests for jupiter.core.bridge.dev_mode module.

Version: 0.1.0

Tests for developer mode features including configuration,
hot reload, and security bypass controls.
"""

import pytest
import logging
from pathlib import Path
from threading import Lock
from unittest.mock import Mock, patch, MagicMock

pytestmark = pytest.mark.anyio

from jupiter.core.bridge.dev_mode import (
    DevModeConfig,
    DeveloperMode,
    PluginFileHandler,
    get_dev_mode,
    init_dev_mode,
    reset_dev_mode,
    is_dev_mode,
    enable_dev_mode,
    disable_dev_mode,
    get_dev_mode_status,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def dev_config():
    """Create a test dev mode configuration."""
    return DevModeConfig(
        enabled=False,
        allow_unsigned_plugins=True,
        skip_signature_verification=True,
        verbose_logging=True,
        disable_rate_limiting=True,
    )


@pytest.fixture
def enabled_config():
    """Create an enabled dev mode configuration."""
    return DevModeConfig(
        enabled=True,
        allow_unsigned_plugins=True,
        skip_signature_verification=True,
        verbose_logging=True,
        disable_rate_limiting=True,
    )


@pytest.fixture
def dev_mode(dev_config):
    """Create a fresh DeveloperMode instance."""
    return DeveloperMode(config=dev_config)


@pytest.fixture
def enabled_dev_mode(enabled_config):
    """Create a DeveloperMode instance that is already enabled."""
    return DeveloperMode(config=enabled_config)


@pytest.fixture(autouse=True)
def reset_global_mode():
    """Reset global developer mode before and after each test."""
    reset_dev_mode()
    yield
    reset_dev_mode()


# =============================================================================
# DevModeConfig Tests
# =============================================================================

class TestDevModeConfig:
    """Tests for DevModeConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = DevModeConfig()
        
        assert config.enabled is False
        assert config.allow_unsigned_plugins is True
        assert config.skip_signature_verification is True
        assert config.allow_all_permissions is False
        assert config.verbose_logging is True
        assert config.log_level == "DEBUG"
        assert config.disable_rate_limiting is True
        assert config.enable_hot_reload is True
        assert config.auto_reload_on_change is True
        assert config.enable_test_console is True
        assert config.enable_debug_endpoints is True
        assert config.enable_profiling is False
        assert config.profile_plugin_loads is False

    def test_custom_values(self):
        """Test custom configuration values."""
        config = DevModeConfig(
            enabled=True,
            allow_unsigned_plugins=False,
            skip_signature_verification=False,
            allow_all_permissions=True,
            verbose_logging=False,
            log_level="INFO",
            disable_rate_limiting=False,
            enable_hot_reload=False,
            auto_reload_on_change=False,
            enable_test_console=False,
            enable_debug_endpoints=False,
            enable_profiling=True,
            profile_plugin_loads=True,
        )
        
        assert config.enabled is True
        assert config.allow_unsigned_plugins is False
        assert config.skip_signature_verification is False
        assert config.allow_all_permissions is True
        assert config.verbose_logging is False
        assert config.log_level == "INFO"
        assert config.disable_rate_limiting is False
        assert config.enable_hot_reload is False
        assert config.auto_reload_on_change is False
        assert config.enable_test_console is False
        assert config.enable_debug_endpoints is False
        assert config.enable_profiling is True
        assert config.profile_plugin_loads is True

    def test_to_dict(self):
        """Test serialization to dictionary."""
        config = DevModeConfig(enabled=True, log_level="WARNING")
        
        result = config.to_dict()
        
        assert result["enabled"] is True
        assert result["log_level"] == "WARNING"
        assert isinstance(result["watch_dirs"], list)

    def test_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "enabled": True,
            "log_level": "INFO",
            "enable_profiling": True,
        }
        
        config = DevModeConfig.from_dict(data)
        
        assert config.enabled is True
        assert config.log_level == "INFO"
        assert config.enable_profiling is True

    def test_from_dict_missing_keys(self):
        """Test creating config from dictionary with missing keys."""
        data = {"enabled": True}
        
        config = DevModeConfig.from_dict(data)
        
        assert config.enabled is True
        assert config.verbose_logging is True  # Default value


# =============================================================================
# DeveloperMode Basic Tests
# =============================================================================

class TestDeveloperModeBasic:
    """Basic tests for DeveloperMode."""

    def test_initialization_disabled(self, dev_mode):
        """Test initialization in disabled state."""
        assert dev_mode.enabled is False

    def test_initialization_enabled(self, enabled_dev_mode):
        """Test initialization in enabled state."""
        assert enabled_dev_mode.enabled is True

    def test_config_property(self, dev_mode, dev_config):
        """Test config property access."""
        config = dev_mode.config
        
        assert config.enabled == dev_config.enabled
        assert config.verbose_logging == dev_config.verbose_logging

    def test_enable_changes_state(self, dev_mode):
        """Test that enable changes state."""
        assert dev_mode.enabled is False
        
        dev_mode.enable()
        
        assert dev_mode.enabled is True

    def test_disable_changes_state(self, enabled_dev_mode):
        """Test that disable changes state."""
        assert enabled_dev_mode.enabled is True
        
        enabled_dev_mode.disable()
        
        assert enabled_dev_mode.enabled is False

    def test_enable_with_new_config(self, dev_mode):
        """Test enable with a new configuration."""
        new_config = DevModeConfig(
            enabled=False,
            verbose_logging=False,
            log_level="WARNING",
        )
        
        dev_mode.enable(new_config)
        
        assert dev_mode.enabled is True
        assert dev_mode.config.verbose_logging is False
        assert dev_mode.config.log_level == "WARNING"


# =============================================================================
# Security Bypass Tests
# =============================================================================

class TestSecurityBypass:
    """Tests for security bypass controls."""

    def test_should_allow_unsigned_disabled(self, dev_mode):
        """Test unsigned check when dev mode is disabled."""
        assert dev_mode.should_allow_unsigned() is False

    def test_should_allow_unsigned_enabled(self, enabled_dev_mode):
        """Test unsigned check when dev mode is enabled."""
        assert enabled_dev_mode.should_allow_unsigned() is True

    def test_should_skip_signature_disabled(self, dev_mode):
        """Test signature skip when dev mode is disabled."""
        assert dev_mode.should_skip_signature_verification() is False

    def test_should_skip_signature_enabled(self, enabled_dev_mode):
        """Test signature skip when dev mode is enabled."""
        assert enabled_dev_mode.should_skip_signature_verification() is True

    def test_should_allow_all_permissions_disabled(self, dev_mode):
        """Test permissions when dev mode is disabled."""
        # Config has allow_all_permissions=False by default
        assert dev_mode.should_allow_all_permissions() is False

    def test_should_allow_all_permissions_enabled(self):
        """Test permissions when explicitly enabled."""
        config = DevModeConfig(
            enabled=True,
            allow_all_permissions=True,
        )
        mode = DeveloperMode(config=config)
        
        assert mode.should_allow_all_permissions() is True

    def test_should_disable_rate_limiting_disabled(self, dev_mode):
        """Test rate limiting when dev mode is disabled."""
        assert dev_mode.should_disable_rate_limiting() is False

    def test_should_disable_rate_limiting_enabled(self, enabled_dev_mode):
        """Test rate limiting when dev mode is enabled."""
        assert enabled_dev_mode.should_disable_rate_limiting() is True

    def test_bypass_requires_dev_mode_enabled(self):
        """Test that bypasses require dev mode to be enabled."""
        config = DevModeConfig(
            enabled=False,
            allow_unsigned_plugins=True,
            skip_signature_verification=True,
            disable_rate_limiting=True,
        )
        mode = DeveloperMode(config=config)
        
        # All should return False because enabled=False
        assert mode.should_allow_unsigned() is False
        assert mode.should_skip_signature_verification() is False
        assert mode.should_disable_rate_limiting() is False


# =============================================================================
# Debug Features Tests
# =============================================================================

class TestDebugFeatures:
    """Tests for debug features."""

    def test_is_test_console_enabled_disabled(self, dev_mode):
        """Test test console check when disabled."""
        assert dev_mode.is_test_console_enabled() is False

    def test_is_test_console_enabled_enabled(self, enabled_dev_mode):
        """Test test console check when enabled."""
        assert enabled_dev_mode.is_test_console_enabled() is True

    def test_is_debug_endpoints_enabled_disabled(self, dev_mode):
        """Test debug endpoints check when disabled."""
        assert dev_mode.is_debug_endpoints_enabled() is False

    def test_is_debug_endpoints_enabled_enabled(self, enabled_dev_mode):
        """Test debug endpoints check when enabled."""
        assert enabled_dev_mode.is_debug_endpoints_enabled() is True

    def test_is_profiling_enabled_disabled(self, dev_mode):
        """Test profiling check when disabled."""
        assert dev_mode.is_profiling_enabled() is False

    def test_is_profiling_enabled_with_config(self):
        """Test profiling check when enabled in config."""
        config = DevModeConfig(
            enabled=True,
            enable_profiling=True,
        )
        mode = DeveloperMode(config=config)
        
        assert mode.is_profiling_enabled() is True


# =============================================================================
# Plugin Watching Tests
# =============================================================================

class TestPluginWatching:
    """Tests for plugin file watching functionality."""

    def test_watch_plugin(self, enabled_dev_mode):
        """Test watching a plugin's files."""
        paths = [Path("/some/path")]
        
        enabled_dev_mode.watch_plugin("test_plugin", paths)
        
        assert "test_plugin" in enabled_dev_mode._watched_plugins

    def test_unwatch_plugin(self, enabled_dev_mode):
        """Test unwatching a plugin."""
        paths = [Path("/some/path")]
        enabled_dev_mode.watch_plugin("test_plugin", paths)
        
        enabled_dev_mode.unwatch_plugin("test_plugin")
        
        assert "test_plugin" not in enabled_dev_mode._watched_plugins

    def test_unwatch_nonexistent_plugin(self, enabled_dev_mode):
        """Test unwatching a plugin that wasn't being watched."""
        # Should not raise
        enabled_dev_mode.unwatch_plugin("nonexistent")


# =============================================================================
# Auto-Reload Tests
# =============================================================================

class TestAutoReload:
    """Tests for auto-reload functionality."""

    def test_schedule_reload(self, enabled_dev_mode):
        """Test scheduling a plugin reload."""
        enabled_dev_mode.schedule_reload("test_plugin")
        
        pending = enabled_dev_mode.get_pending_reloads()
        assert "test_plugin" in pending

    def test_schedule_reload_disabled(self, dev_mode):
        """Test that reload is not scheduled when disabled."""
        dev_mode.schedule_reload("test_plugin")
        
        pending = dev_mode.get_pending_reloads()
        assert "test_plugin" not in pending

    def test_clear_pending_reload(self, enabled_dev_mode):
        """Test clearing a pending reload."""
        enabled_dev_mode.schedule_reload("test_plugin")
        
        enabled_dev_mode.clear_pending_reload("test_plugin")
        
        pending = enabled_dev_mode.get_pending_reloads()
        assert "test_plugin" not in pending

    def test_add_reload_callback(self, enabled_dev_mode):
        """Test adding a reload callback."""
        callback = Mock()
        
        enabled_dev_mode.add_reload_callback(callback)
        enabled_dev_mode.schedule_reload("test_plugin")
        
        callback.assert_called_once_with("test_plugin")

    def test_remove_reload_callback(self, enabled_dev_mode):
        """Test removing a reload callback."""
        callback = Mock()
        enabled_dev_mode.add_reload_callback(callback)
        
        result = enabled_dev_mode.remove_reload_callback(callback)
        
        assert result is True
        
        # Callback should not be called after removal
        enabled_dev_mode.schedule_reload("test_plugin")
        callback.assert_not_called()

    def test_remove_nonexistent_callback(self, enabled_dev_mode):
        """Test removing a callback that wasn't registered."""
        callback = Mock()
        
        result = enabled_dev_mode.remove_reload_callback(callback)
        
        assert result is False


# =============================================================================
# Status and Stats Tests
# =============================================================================

class TestStatusStats:
    """Tests for status and statistics methods."""

    def test_get_stats_disabled(self, dev_mode):
        """Test getting stats when disabled."""
        stats = dev_mode.get_stats()
        
        assert stats["enabled"] is False
        assert stats["auto_reloads"] == 0
        assert stats["files_watched"] == 0
        assert "watched_plugins" in stats
        assert "pending_reloads" in stats
        assert "config" in stats

    def test_get_stats_enabled(self, enabled_dev_mode):
        """Test getting stats when enabled."""
        stats = enabled_dev_mode.get_stats()
        
        assert stats["enabled"] is True

    def test_get_status_disabled(self, dev_mode):
        """Test getting status when disabled."""
        status = dev_mode.get_status()
        
        assert status["enabled"] is False
        assert "features" in status
        assert status["features"]["unsigned_plugins"] is False
        assert status["features"]["skip_verification"] is False

    def test_get_status_enabled(self, enabled_dev_mode):
        """Test getting status when enabled."""
        status = enabled_dev_mode.get_status()
        
        assert status["enabled"] is True
        assert status["features"]["unsigned_plugins"] is True
        assert status["features"]["skip_verification"] is True
        assert status["features"]["no_rate_limit"] is True

    def test_get_stats_tracks_reloads(self, enabled_dev_mode):
        """Test that stats track auto-reloads."""
        enabled_dev_mode.schedule_reload("plugin1")
        enabled_dev_mode.schedule_reload("plugin2")
        
        stats = enabled_dev_mode.get_stats()
        
        assert stats["auto_reloads"] == 2


# =============================================================================
# PluginFileHandler Tests
# =============================================================================

class TestPluginFileHandler:
    """Tests for PluginFileHandler."""

    def test_initialization(self, enabled_dev_mode):
        """Test handler initialization."""
        handler = PluginFileHandler(enabled_dev_mode)
        
        assert handler._dev_mode is enabled_dev_mode
        assert handler._debounce_seconds == 1.0

    def test_custom_debounce(self, enabled_dev_mode):
        """Test handler with custom debounce."""
        handler = PluginFileHandler(enabled_dev_mode, debounce_seconds=2.5)
        
        assert handler._debounce_seconds == 2.5

    def test_on_modified_ignores_directories(self, enabled_dev_mode):
        """Test that directory modifications are ignored."""
        handler = PluginFileHandler(enabled_dev_mode)
        
        event = MagicMock()
        event.is_directory = True
        event.src_path = "/some/dir"
        
        # Should not raise or call schedule_reload
        handler.on_modified(event)

    def test_on_modified_ignores_non_python(self, enabled_dev_mode):
        """Test that non-Python files are ignored."""
        handler = PluginFileHandler(enabled_dev_mode)
        
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/some/file.txt"
        
        # Should not call schedule_reload
        handler.on_modified(event)


# =============================================================================
# Global Functions Tests
# =============================================================================

class TestGlobalFunctions:
    """Tests for global convenience functions."""

    def test_get_dev_mode_creates_instance(self):
        """Test that get_dev_mode creates an instance."""
        mode = get_dev_mode()
        
        assert mode is not None
        assert isinstance(mode, DeveloperMode)

    def test_get_dev_mode_singleton(self):
        """Test that get_dev_mode returns same instance."""
        mode1 = get_dev_mode()
        mode2 = get_dev_mode()
        
        assert mode1 is mode2

    def test_init_dev_mode_custom_config(self):
        """Test initializing with custom config."""
        config = DevModeConfig(
            enabled=True,
            log_level="WARNING",
        )
        
        mode = init_dev_mode(config=config)
        
        assert mode.enabled is True
        assert mode.config.log_level == "WARNING"

    def test_reset_dev_mode(self):
        """Test resetting the global dev mode."""
        mode1 = get_dev_mode()
        mode1.enable()
        
        reset_dev_mode()
        
        mode2 = get_dev_mode()
        assert mode1 is not mode2
        assert mode2.enabled is False

    def test_is_dev_mode_function(self):
        """Test the is_dev_mode convenience function."""
        assert is_dev_mode() is False
        
        enable_dev_mode()
        assert is_dev_mode() is True
        
        disable_dev_mode()
        assert is_dev_mode() is False

    def test_enable_dev_mode_function(self):
        """Test the enable_dev_mode convenience function."""
        enable_dev_mode()
        
        assert is_dev_mode() is True

    def test_enable_dev_mode_with_config(self):
        """Test enable_dev_mode with custom config."""
        config = DevModeConfig(
            verbose_logging=False,
            log_level="ERROR",
        )
        
        enable_dev_mode(config)
        
        mode = get_dev_mode()
        assert mode.enabled is True
        assert mode.config.verbose_logging is False
        assert mode.config.log_level == "ERROR"

    def test_disable_dev_mode_function(self):
        """Test the disable_dev_mode convenience function."""
        enable_dev_mode()
        
        disable_dev_mode()
        
        assert is_dev_mode() is False

    def test_get_dev_mode_status_function(self):
        """Test the get_dev_mode_status convenience function."""
        status = get_dev_mode_status()
        
        assert "enabled" in status
        assert "features" in status


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_rapid_enable_disable(self, dev_mode):
        """Test rapid enable/disable cycles."""
        for _ in range(10):
            dev_mode.enable()
            dev_mode.disable()
        
        assert dev_mode.enabled is False

    def test_callback_exception_handling(self, enabled_dev_mode):
        """Test that callback exceptions don't break reload scheduling."""
        bad_callback = Mock(side_effect=RuntimeError("Test error"))
        good_callback = Mock()
        
        enabled_dev_mode.add_reload_callback(bad_callback)
        enabled_dev_mode.add_reload_callback(good_callback)
        
        # Should not raise
        enabled_dev_mode.schedule_reload("test_plugin")
        
        # Good callback should still be called
        good_callback.assert_called_once_with("test_plugin")

    def test_multiple_plugins_watched(self, enabled_dev_mode):
        """Test watching multiple plugins."""
        enabled_dev_mode.watch_plugin("plugin1", [Path("/path1")])
        enabled_dev_mode.watch_plugin("plugin2", [Path("/path2")])
        enabled_dev_mode.watch_plugin("plugin3", [Path("/path3")])
        
        stats = enabled_dev_mode.get_stats()
        
        assert len(stats["watched_plugins"]) == 3

    def test_multiple_pending_reloads(self, enabled_dev_mode):
        """Test multiple pending reloads."""
        enabled_dev_mode.schedule_reload("plugin1")
        enabled_dev_mode.schedule_reload("plugin2")
        enabled_dev_mode.schedule_reload("plugin1")  # Duplicate
        
        pending = enabled_dev_mode.get_pending_reloads()
        
        # Should only have 2 (set behavior)
        assert len(pending) == 2
        assert "plugin1" in pending
        assert "plugin2" in pending


# =============================================================================
# Integration-like Tests
# =============================================================================

class TestIntegration:
    """Integration-like tests for dev mode scenarios."""

    def test_full_dev_workflow(self):
        """Test a typical development workflow."""
        config = DevModeConfig(
            enabled=True,
            allow_unsigned_plugins=True,
            skip_signature_verification=True,
            disable_rate_limiting=True,
            enable_hot_reload=True,
            auto_reload_on_change=True,
            enable_test_console=True,
        )
        mode = DeveloperMode(config=config)
        
        # Verify all features
        assert mode.should_allow_unsigned() is True
        assert mode.should_skip_signature_verification() is True
        assert mode.should_disable_rate_limiting() is True
        assert mode.is_test_console_enabled() is True
        
        # Watch a plugin
        mode.watch_plugin("my_plugin", [Path("/dev/plugins/my_plugin")])
        
        # Add reload callback
        reload_callback = Mock()
        mode.add_reload_callback(reload_callback)
        
        # Trigger reload
        mode.schedule_reload("my_plugin")
        
        reload_callback.assert_called_once_with("my_plugin")
        
        # Check stats
        stats = mode.get_stats()
        assert stats["auto_reloads"] == 1
        assert "my_plugin" in stats["watched_plugins"]

    def test_production_safe_defaults(self):
        """Test that production defaults are safe."""
        mode = DeveloperMode()  # Default config
        
        # By default, dev mode is disabled
        assert mode.enabled is False
        
        # All security bypasses should return False
        assert mode.should_allow_unsigned() is False
        assert mode.should_skip_signature_verification() is False
        assert mode.should_disable_rate_limiting() is False
        assert mode.should_allow_all_permissions() is False
        
        # Debug features should be disabled
        assert mode.is_test_console_enabled() is False
        assert mode.is_debug_endpoints_enabled() is False
        assert mode.is_profiling_enabled() is False

    def test_enable_disable_cycle(self):
        """Test complete enable/disable cycle."""
        mode = DeveloperMode()
        
        # Start disabled
        assert mode.enabled is False
        
        # Enable
        mode.enable()
        assert mode.enabled is True
        assert mode.should_allow_unsigned() is True
        
        # Watch a plugin while enabled
        mode.watch_plugin("test", [Path("/test")])
        
        # Disable
        mode.disable()
        assert mode.enabled is False
        assert mode.should_allow_unsigned() is False

    def test_global_api_workflow(self):
        """Test using the global API."""
        # Start with clean state (from autouse fixture)
        assert is_dev_mode() is False
        
        # Enable
        enable_dev_mode()
        assert is_dev_mode() is True
        
        # Get status
        status = get_dev_mode_status()
        assert status["enabled"] is True
        
        # Disable
        disable_dev_mode()
        assert is_dev_mode() is False
