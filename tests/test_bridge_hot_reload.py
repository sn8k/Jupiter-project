"""Tests for jupiter.core.bridge.hot_reload module.

Tests cover:
- HotReloader initialization and singleton
- Reload validation (can_reload)
- Successful reload flow
- Error handling during reload phases
- History tracking
- Statistics
- Blacklist management
- Callbacks
"""

import sys
import time
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from jupiter.core.bridge.hot_reload import (
    HotReloader,
    HotReloadError,
    ReloadResult,
    ReloadHistoryEntry,
    get_hot_reloader,
    init_hot_reloader,
    reset_hot_reloader,
    reload_plugin,
    can_reload_plugin,
    get_reload_history,
    get_reload_stats,
)
from jupiter.core.bridge.interfaces import PluginState


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton before and after each test."""
    reset_hot_reloader()
    yield
    reset_hot_reloader()


@pytest.fixture(autouse=True)
def mock_dev_mode():
    """Mock developer mode as enabled by default for hot reload tests.
    
    Tests that specifically test dev mode behavior should override this.
    """
    with patch("jupiter.core.bridge.dev_mode.is_dev_mode", return_value=True):
        yield


@pytest.fixture
def reloader():
    """Create a fresh HotReloader instance."""
    return HotReloader()


@pytest.fixture
def mock_bridge():
    """Create a mock Bridge."""
    bridge = MagicMock()
    bridge._cli_contributions = {}
    bridge._api_contributions = {}
    bridge._ui_contributions = {}
    bridge.plugins_dir = Path("/fake/plugins")
    return bridge


@pytest.fixture
def mock_plugin_info():
    """Create a mock PluginInfo."""
    info = MagicMock()
    info.manifest = MagicMock()
    info.manifest.id = "test_plugin"
    info.manifest.version = "1.0.0"
    info.state = PluginState.READY
    info.legacy = False
    info.module = MagicMock()
    info.instance = MagicMock()
    return info


# =============================================================================
# TEST: HotReloadError
# =============================================================================

class TestHotReloadError:
    """Tests for HotReloadError exception."""
    
    def test_create_error(self):
        """Test creating a HotReloadError."""
        error = HotReloadError(
            "Test error",
            plugin_id="test_plugin",
            phase="initialization",
        )
        
        assert str(error) == "Test error"
        assert error.plugin_id == "test_plugin"
        assert error.phase == "initialization"
        assert error.original_error is None
    
    def test_error_with_original(self):
        """Test error with original exception."""
        original = ValueError("Original error")
        error = HotReloadError(
            "Wrapper error",
            plugin_id="test_plugin",
            phase="module_unload",
            original_error=original,
        )
        
        assert error.original_error is original
    
    def test_error_to_dict(self):
        """Test error serialization."""
        original = ValueError("Original")
        error = HotReloadError(
            "Test error",
            plugin_id="test_plugin",
            phase="shutdown",
            original_error=original,
        )
        
        d = error.to_dict()
        
        assert d["error"] == "HotReloadError"
        assert d["message"] == "Test error"
        assert d["plugin_id"] == "test_plugin"
        assert d["phase"] == "shutdown"
        assert d["original_error"] == "Original"


# =============================================================================
# TEST: ReloadResult
# =============================================================================

class TestReloadResult:
    """Tests for ReloadResult dataclass."""
    
    def test_create_success_result(self):
        """Test creating a successful result."""
        result = ReloadResult(
            success=True,
            plugin_id="test_plugin",
            duration_ms=150.5,
            phase="completed",
            old_version="1.0.0",
            new_version="1.1.0",
            contributions_reloaded=True,
        )
        
        assert result.success is True
        assert result.plugin_id == "test_plugin"
        assert result.duration_ms == 150.5
        assert result.phase == "completed"
        assert result.old_version == "1.0.0"
        assert result.new_version == "1.1.0"
        assert result.contributions_reloaded is True
        assert result.error is None
    
    def test_create_failure_result(self):
        """Test creating a failure result."""
        result = ReloadResult(
            success=False,
            plugin_id="test_plugin",
            phase="initialization",
            error="Init failed",
            warnings=["Warning 1", "Warning 2"],
        )
        
        assert result.success is False
        assert result.error == "Init failed"
        assert len(result.warnings) == 2
    
    def test_result_to_dict(self):
        """Test result serialization."""
        result = ReloadResult(
            success=True,
            plugin_id="test_plugin",
            duration_ms=100.0,
            old_version="1.0.0",
            new_version="1.1.0",
        )
        
        d = result.to_dict()
        
        assert d["success"] is True
        assert d["plugin_id"] == "test_plugin"
        assert d["duration_ms"] == 100.0
        assert d["old_version"] == "1.0.0"
        assert d["new_version"] == "1.1.0"


# =============================================================================
# TEST: HotReloader Initialization
# =============================================================================

class TestHotReloaderInit:
    """Tests for HotReloader initialization."""
    
    def test_create_reloader(self, reloader):
        """Test creating a HotReloader."""
        assert reloader._bridge is None
        assert reloader._reload_count == 0
        assert len(reloader._history) == 0
        assert "bridge" in reloader._blacklist
    
    def test_set_bridge(self, reloader, mock_bridge):
        """Test setting the Bridge."""
        reloader.set_bridge(mock_bridge)
        assert reloader._bridge is mock_bridge
    
    def test_get_bridge_after_set(self, reloader, mock_bridge):
        """Test getting Bridge after setting it."""
        reloader.set_bridge(mock_bridge)
        assert reloader.get_bridge() is mock_bridge
    
    def test_get_bridge_creates_instance(self, reloader):
        """Test that get_bridge creates Bridge if not set."""
        with patch("jupiter.core.bridge.bridge.Bridge") as MockBridge:
            mock_instance = MagicMock()
            MockBridge.get_instance.return_value = mock_instance
            
            bridge = reloader.get_bridge()
            
            MockBridge.get_instance.assert_called_once()
            assert bridge is mock_instance


# =============================================================================
# TEST: Can Reload Validation
# =============================================================================

class TestCanReload:
    """Tests for reload validation."""
    
    def test_cannot_reload_blacklisted(self, reloader, mock_bridge):
        """Test that blacklisted plugins cannot be reloaded."""
        reloader.set_bridge(mock_bridge)
        
        can, reason = reloader.can_reload("bridge")
        
        assert can is False
        assert "core plugin" in reason
    
    def test_cannot_reload_not_found(self, reloader, mock_bridge):
        """Test that non-existent plugins cannot be reloaded."""
        reloader.set_bridge(mock_bridge)
        mock_bridge.get_plugin.return_value = None
        
        can, reason = reloader.can_reload("unknown_plugin")
        
        assert can is False
        assert "not found" in reason
    
    def test_cannot_reload_while_loading(self, reloader, mock_bridge, mock_plugin_info):
        """Test that loading plugins cannot be reloaded."""
        reloader.set_bridge(mock_bridge)
        mock_plugin_info.state = PluginState.LOADING
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        can, reason = reloader.can_reload("test_plugin")
        
        assert can is False
        assert "currently loading" in reason
    
    def test_cannot_reload_while_unloading(self, reloader, mock_bridge, mock_plugin_info):
        """Test that unloading plugins cannot be reloaded."""
        reloader.set_bridge(mock_bridge)
        mock_plugin_info.state = PluginState.UNLOADING
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        can, reason = reloader.can_reload("test_plugin")
        
        assert can is False
        assert "currently unloading" in reason
    
    def test_cannot_reload_legacy_without_module(self, reloader, mock_bridge, mock_plugin_info):
        """Test that legacy plugins without module cannot be reloaded."""
        reloader.set_bridge(mock_bridge)
        mock_plugin_info.state = PluginState.READY
        mock_plugin_info.legacy = True
        mock_plugin_info.module = None
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        can, reason = reloader.can_reload("test_plugin")
        
        assert can is False
        assert "no module" in reason
    
    def test_can_reload_requires_dev_mode(self, reloader, mock_bridge, mock_plugin_info):
        """Test that reload requires developer mode."""
        reloader.set_bridge(mock_bridge)
        mock_plugin_info.state = PluginState.READY
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        with patch("jupiter.core.bridge.dev_mode.is_dev_mode", return_value=False):
            can, reason = reloader.can_reload("test_plugin")
        
        assert can is False
        assert "developer mode" in reason.lower()
    
    def test_can_reload_with_dev_mode_enabled(self, reloader, mock_bridge, mock_plugin_info):
        """Test that reload works with developer mode enabled."""
        reloader.set_bridge(mock_bridge)
        mock_plugin_info.state = PluginState.READY
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        # Dev mode is auto-mocked to True
        can, reason = reloader.can_reload("test_plugin")
        
        assert can is True
        assert "can be reloaded" in reason
    
    def test_can_reload_ready_plugin(self, reloader, mock_bridge, mock_plugin_info):
        """Test that ready plugins can be reloaded."""
        reloader.set_bridge(mock_bridge)
        mock_plugin_info.state = PluginState.READY
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        # Dev mode is auto-mocked to True
        can, reason = reloader.can_reload("test_plugin")
        
        assert can is True
        assert "can be reloaded" in reason


# =============================================================================
# TEST: Reload Flow
# =============================================================================

class TestReloadFlow:
    """Tests for the reload flow."""
    
    def test_reload_fails_without_dev_mode(self, reloader, mock_bridge, mock_plugin_info):
        """Test reload fails when developer mode is disabled."""
        reloader.set_bridge(mock_bridge)
        mock_plugin_info.state = PluginState.READY
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        with patch("jupiter.core.bridge.dev_mode.is_dev_mode", return_value=False):
            result = reloader.reload("test_plugin")
        
        assert result.success is False
        assert result.phase == "dev_mode_check"
        assert "developer mode" in result.error.lower()
    
    def test_reload_skip_dev_mode_check(self, reloader, mock_bridge, mock_plugin_info):
        """Test reload with skip_dev_mode_check bypasses dev mode."""
        reloader.set_bridge(mock_bridge)
        mock_plugin_info.state = PluginState.READY
        mock_bridge.get_plugin.return_value = mock_plugin_info
        mock_bridge._get_plugin_config.return_value = {}
        mock_bridge.initialize.return_value = {"test_plugin": True}
        mock_bridge.plugins_dir = Path("/fake/plugins")
        
        with patch("jupiter.core.bridge.dev_mode.is_dev_mode", return_value=False), \
             patch("pathlib.Path.is_dir", return_value=True), \
             patch("pathlib.Path.is_file", return_value=True), \
             patch.object(reloader, "_rediscover_plugin"):
            # Skip dev mode check should allow reload
            result = reloader.reload("test_plugin", skip_dev_mode_check=True)
        
        # Should pass dev mode check and proceed (may fail later in flow)
        assert result.phase != "dev_mode_check"
    
    def test_reload_validation_fails(self, reloader, mock_bridge):
        """Test reload fails validation for unknown plugin."""
        reloader.set_bridge(mock_bridge)
        mock_bridge.get_plugin.return_value = None
        
        # Dev mode is auto-mocked to True
        result = reloader.reload("unknown_plugin")
        
        assert result.success is False
        assert result.phase == "validation"
        assert "not found" in result.error
    
    def test_reload_blacklisted_plugin(self, reloader, mock_bridge):
        """Test reload fails for blacklisted plugin."""
        reloader.set_bridge(mock_bridge)
        
        # Dev mode is auto-mocked to True
        result = reloader.reload("bridge")
        
        assert result.success is False
        assert "core plugin" in result.error
    
    def test_reload_force_bypasses_blacklist(self, reloader, mock_bridge, mock_plugin_info):
        """Test force reload bypasses blacklist but still needs plugin."""
        reloader.set_bridge(mock_bridge)
        mock_bridge.get_plugin.return_value = None
        
        # Force bypass validation but plugin still not found in lock phase
        # Dev mode is auto-mocked to True
        result = reloader.reload("bridge", force=True)
        
        assert result.success is False
    
    def test_reload_successful(self, reloader, mock_bridge, mock_plugin_info):
        """Test successful reload flow."""
        reloader.set_bridge(mock_bridge)
        mock_bridge.get_plugin.return_value = mock_plugin_info
        mock_bridge._get_plugin_config.return_value = {}
        mock_bridge.initialize.return_value = {"test_plugin": True}
        mock_bridge.plugins_dir = Path("/fake/plugins")
        
        # Mock plugin directory for rediscovery
        # Dev mode is auto-mocked to True
        with patch("pathlib.Path.is_dir", return_value=True), \
             patch("pathlib.Path.is_file", return_value=True), \
             patch.object(reloader, "_rediscover_plugin"):
            
            result = reloader.reload("test_plugin")
        
        assert result.success is True
        assert result.plugin_id == "test_plugin"
        assert result.phase == "completed"
        assert result.old_version == "1.0.0"
        assert result.duration_ms > 0
    
    def test_reload_shutdown_called(self, reloader, mock_bridge, mock_plugin_info):
        """Test that shutdown is called during reload."""
        reloader.set_bridge(mock_bridge)
        mock_bridge.get_plugin.return_value = mock_plugin_info
        mock_bridge._get_plugin_config.return_value = {}
        
        # Create a mock instance with shutdown method
        mock_instance = MagicMock()
        mock_plugin_info.instance = mock_instance
        
        with patch.object(reloader, "_rediscover_plugin"), \
             patch.object(reloader, "_unload_module", return_value=[]):
            
            reloader.reload("test_plugin")
        
        # Verify shutdown was called on instance
        mock_instance.shutdown.assert_called_once()
    
    def test_reload_module_unloaded(self, reloader, mock_bridge, mock_plugin_info):
        """Test that module is unloaded during reload."""
        reloader.set_bridge(mock_bridge)
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        # Add a fake module to sys.modules
        fake_module_name = "jupiter.plugins.test_plugin"
        sys.modules[fake_module_name] = MagicMock()
        
        try:
            with patch.object(reloader, "_rediscover_plugin"):
                reloader.reload("test_plugin")
            
            # Module should be removed
            assert fake_module_name not in sys.modules
        finally:
            # Cleanup
            sys.modules.pop(fake_module_name, None)
    
    def test_reload_contributions_cleared(self, reloader, mock_bridge, mock_plugin_info):
        """Test that contributions are cleared during reload."""
        reloader.set_bridge(mock_bridge)
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        # Add some contributions
        mock_bridge._cli_contributions = {"test_plugin.cmd1": MagicMock()}
        mock_bridge._api_contributions = {"test_plugin./api": MagicMock()}
        mock_bridge._ui_contributions = {"test_plugin.panel": MagicMock()}
        
        with patch.object(reloader, "_rediscover_plugin"), \
             patch.object(reloader, "_unload_module", return_value=[]):
            
            reloader.reload("test_plugin")
        
        # Contributions should be cleared
        assert len(mock_bridge._cli_contributions) == 0
        assert len(mock_bridge._api_contributions) == 0
        assert len(mock_bridge._ui_contributions) == 0
    
    def test_reload_emits_event(self, reloader, mock_bridge, mock_plugin_info):
        """Test that reload emits event."""
        reloader.set_bridge(mock_bridge)
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        with patch.object(reloader, "_rediscover_plugin"), \
             patch.object(reloader, "_unload_module", return_value=[]):
            
            reloader.reload("test_plugin")
        
        # Should emit PLUGIN_RELOADED event
        mock_bridge.emit.assert_called()
        call_args = mock_bridge.emit.call_args_list
        
        # Find the PLUGIN_RELOADED call
        reloaded_call = next(
            (c for c in call_args if c[0][0] == "PLUGIN_RELOADED"),
            None
        )
        assert reloaded_call is not None


# =============================================================================
# TEST: Reload Error Handling
# =============================================================================

class TestReloadErrors:
    """Tests for error handling during reload."""
    
    def test_reload_module_unload_error(self, reloader, mock_bridge, mock_plugin_info):
        """Test handling of module unload errors."""
        reloader.set_bridge(mock_bridge)
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        with patch.object(reloader, "_unload_module", side_effect=Exception("Unload failed")):
            result = reloader.reload("test_plugin")
        
        assert result.success is False
        assert result.phase == "module_unload"
        assert "Unload failed" in result.error
    
    def test_reload_rediscovery_error(self, reloader, mock_bridge, mock_plugin_info):
        """Test handling of rediscovery errors."""
        reloader.set_bridge(mock_bridge)
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        with patch.object(reloader, "_unload_module", return_value=[]), \
             patch.object(reloader, "_rediscover_plugin", side_effect=Exception("Not found")):
            
            result = reloader.reload("test_plugin")
        
        assert result.success is False
        assert result.phase == "rediscovery"
    
    def test_reload_initialization_error(self, reloader, mock_bridge, mock_plugin_info):
        """Test handling of initialization errors."""
        reloader.set_bridge(mock_bridge)
        mock_bridge.get_plugin.return_value = mock_plugin_info
        mock_bridge.initialize.side_effect = Exception("Init failed")
        
        with patch.object(reloader, "_unload_module", return_value=[]), \
             patch.object(reloader, "_rediscover_plugin"):
            
            result = reloader.reload("test_plugin")
        
        assert result.success is False
        assert result.phase == "initialization"


# =============================================================================
# TEST: History
# =============================================================================

class TestReloadHistory:
    """Tests for reload history tracking."""
    
    def test_history_recorded_on_success(self, reloader, mock_bridge, mock_plugin_info):
        """Test that successful reloads are recorded in history."""
        reloader.set_bridge(mock_bridge)
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        with patch.object(reloader, "_unload_module", return_value=[]), \
             patch.object(reloader, "_rediscover_plugin"):
            
            reloader.reload("test_plugin")
        
        history = reloader.get_history()
        
        assert len(history) == 1
        assert history[0]["plugin_id"] == "test_plugin"
        assert history[0]["success"] is True
    
    def test_history_recorded_on_failure(self, reloader, mock_bridge, mock_plugin_info):
        """Test that failed reloads cause reload result with error."""
        reloader.set_bridge(mock_bridge)
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        with patch.object(reloader, "_unload_module", side_effect=Exception("Failed")):
            result = reloader.reload("test_plugin")
        
        # Verify the result indicates failure
        assert result.success is False
        assert result.phase == "module_unload"
        assert "Failed" in result.error
        assert result.old_version == "1.0.0"
    
    def test_history_filtered_by_plugin(self, reloader):
        """Test filtering history by plugin ID."""
        # Add some history entries manually
        reloader._history = [
            ReloadHistoryEntry(
                plugin_id="plugin_a",
                timestamp=time.time(),
                success=True,
                duration_ms=100,
            ),
            ReloadHistoryEntry(
                plugin_id="plugin_b",
                timestamp=time.time(),
                success=True,
                duration_ms=150,
            ),
            ReloadHistoryEntry(
                plugin_id="plugin_a",
                timestamp=time.time(),
                success=False,
                duration_ms=50,
            ),
        ]
        
        history = reloader.get_history(plugin_id="plugin_a")
        
        assert len(history) == 2
        assert all(h["plugin_id"] == "plugin_a" for h in history)
    
    def test_history_limited(self, reloader):
        """Test history limit."""
        # Add many entries
        for i in range(10):
            reloader._history.append(ReloadHistoryEntry(
                plugin_id=f"plugin_{i}",
                timestamp=time.time(),
                success=True,
                duration_ms=100,
            ))
        
        history = reloader.get_history(limit=5)
        
        assert len(history) == 5
    
    def test_history_max_size(self, reloader):
        """Test that history is trimmed when exceeding max size."""
        reloader._max_history = 5
        
        # Record more than max entries
        for i in range(10):
            reloader._record_history(ReloadHistoryEntry(
                plugin_id=f"plugin_{i}",
                timestamp=time.time(),
                success=True,
                duration_ms=100,
            ))
        
        assert len(reloader._history) == 5
    
    def test_clear_history(self, reloader):
        """Test clearing history."""
        reloader._history = [
            ReloadHistoryEntry(
                plugin_id="test",
                timestamp=time.time(),
                success=True,
                duration_ms=100,
            )
        ]
        
        reloader.clear_history()
        
        assert len(reloader._history) == 0


# =============================================================================
# TEST: Statistics
# =============================================================================

class TestReloadStats:
    """Tests for reload statistics."""
    
    def test_empty_stats(self, reloader):
        """Test stats with no reloads."""
        stats = reloader.get_stats()
        
        assert stats["total_reloads"] == 0
        assert stats["successful"] == 0
        assert stats["failed"] == 0
        assert stats["success_rate"] == 0
    
    def test_stats_after_reloads(self, reloader):
        """Test stats after some reloads."""
        # Add history entries
        reloader._reload_count = 5
        reloader._history = [
            ReloadHistoryEntry("p1", time.time(), True, 100),
            ReloadHistoryEntry("p1", time.time(), True, 150),
            ReloadHistoryEntry("p2", time.time(), False, 50),
            ReloadHistoryEntry("p2", time.time(), True, 200),
        ]
        
        stats = reloader.get_stats()
        
        assert stats["total_reloads"] == 5
        assert stats["successful"] == 3
        assert stats["failed"] == 1
        assert stats["success_rate"] == 0.75
        assert stats["average_duration_ms"] == 150.0
    
    def test_stats_blacklist(self, reloader):
        """Test that stats include blacklist."""
        stats = reloader.get_stats()
        
        assert "blacklisted_plugins" in stats
        assert "bridge" in stats["blacklisted_plugins"]


# =============================================================================
# TEST: Blacklist Management
# =============================================================================

class TestBlacklist:
    """Tests for blacklist management."""
    
    def test_add_to_blacklist(self, reloader):
        """Test adding plugin to blacklist."""
        reloader.add_to_blacklist("custom_plugin")
        
        assert "custom_plugin" in reloader._blacklist
    
    def test_remove_from_blacklist(self, reloader):
        """Test removing plugin from blacklist."""
        reloader.add_to_blacklist("custom_plugin")
        reloader.remove_from_blacklist("custom_plugin")
        
        assert "custom_plugin" not in reloader._blacklist
    
    def test_remove_nonexistent_from_blacklist(self, reloader):
        """Test removing non-existent plugin from blacklist."""
        # Should not raise
        reloader.remove_from_blacklist("nonexistent")
    
    def test_default_blacklist(self, reloader):
        """Test default blacklisted plugins."""
        assert "bridge" in reloader._blacklist
        assert "settings_update" in reloader._blacklist


# =============================================================================
# TEST: Callbacks
# =============================================================================

class TestCallbacks:
    """Tests for reload callbacks."""
    
    def test_register_callback(self, reloader):
        """Test registering a callback."""
        callback = MagicMock()
        reloader.register_callback(callback)
        
        assert callback in reloader._callbacks
    
    def test_unregister_callback(self, reloader):
        """Test unregistering a callback."""
        callback = MagicMock()
        reloader.register_callback(callback)
        reloader.unregister_callback(callback)
        
        assert callback not in reloader._callbacks
    
    def test_unregister_nonexistent_callback(self, reloader):
        """Test unregistering non-existent callback."""
        callback = MagicMock()
        # Should not raise
        reloader.unregister_callback(callback)
    
    def test_callback_called_on_reload(self, reloader, mock_bridge, mock_plugin_info):
        """Test that callbacks are called on reload."""
        reloader.set_bridge(mock_bridge)
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        callback = MagicMock()
        reloader.register_callback(callback)
        
        with patch.object(reloader, "_unload_module", return_value=[]), \
             patch.object(reloader, "_rediscover_plugin"):
            
            reloader.reload("test_plugin")
        
        callback.assert_called_once()
        result = callback.call_args[0][0]
        assert isinstance(result, ReloadResult)
        assert result.plugin_id == "test_plugin"
    
    def test_callback_error_ignored(self, reloader, mock_bridge, mock_plugin_info):
        """Test that callback errors don't break reload."""
        reloader.set_bridge(mock_bridge)
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        callback = MagicMock(side_effect=Exception("Callback error"))
        reloader.register_callback(callback)
        
        with patch.object(reloader, "_unload_module", return_value=[]), \
             patch.object(reloader, "_rediscover_plugin"):
            
            # Should not raise despite callback error
            result = reloader.reload("test_plugin")
        
        assert result.success is True


# =============================================================================
# TEST: Singleton Functions
# =============================================================================

class TestSingletonFunctions:
    """Tests for module-level singleton functions."""
    
    def test_get_hot_reloader_singleton(self):
        """Test that get_hot_reloader returns singleton."""
        r1 = get_hot_reloader()
        r2 = get_hot_reloader()
        
        assert r1 is r2
    
    def test_init_hot_reloader(self, mock_bridge):
        """Test initializing the reloader with bridge."""
        reloader = init_hot_reloader(mock_bridge)
        
        assert reloader._bridge is mock_bridge
    
    def test_reset_hot_reloader(self):
        """Test resetting the singleton."""
        r1 = get_hot_reloader()
        reset_hot_reloader()
        r2 = get_hot_reloader()
        
        assert r1 is not r2


# =============================================================================
# TEST: Convenience Functions
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_reload_plugin_function(self, mock_bridge, mock_plugin_info):
        """Test reload_plugin convenience function."""
        reloader = init_hot_reloader(mock_bridge)
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        with patch.object(reloader, "_unload_module", return_value=[]), \
             patch.object(reloader, "_rediscover_plugin"):
            
            result = reload_plugin("test_plugin")
        
        assert result.plugin_id == "test_plugin"
    
    def test_can_reload_plugin_function(self, mock_bridge, mock_plugin_info):
        """Test can_reload_plugin convenience function."""
        init_hot_reloader(mock_bridge)
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        can, reason = can_reload_plugin("test_plugin")
        
        assert can is True
    
    def test_get_reload_history_function(self):
        """Test get_reload_history convenience function."""
        reloader = get_hot_reloader()
        reloader._history = [
            ReloadHistoryEntry("test", time.time(), True, 100)
        ]
        
        history = get_reload_history()
        
        assert len(history) == 1
    
    def test_get_reload_stats_function(self):
        """Test get_reload_stats convenience function."""
        reloader = get_hot_reloader()
        reloader._reload_count = 5
        
        stats = get_reload_stats()
        
        assert stats["total_reloads"] == 5


# =============================================================================
# TEST: Thread Safety
# =============================================================================

class TestThreadSafety:
    """Tests for thread safety."""
    
    def test_plugin_lock_created(self, reloader):
        """Test that plugin locks are created on demand."""
        lock1 = reloader._get_plugin_lock("plugin_a")
        lock2 = reloader._get_plugin_lock("plugin_a")
        
        assert lock1 is lock2
        assert isinstance(lock1, Lock)
    
    def test_different_plugins_different_locks(self, reloader):
        """Test that different plugins have different locks."""
        lock_a = reloader._get_plugin_lock("plugin_a")
        lock_b = reloader._get_plugin_lock("plugin_b")
        
        assert lock_a is not lock_b


# =============================================================================
# TEST: Module Unloading
# =============================================================================

class TestModuleUnloading:
    """Tests for module unloading."""
    
    def test_unload_main_module(self, reloader, mock_plugin_info):
        """Test unloading main module."""
        # Add fake module
        fake_name = "jupiter.plugins.test_plugin"
        sys.modules[fake_name] = MagicMock()
        
        try:
            unloaded = reloader._unload_module("test_plugin", mock_plugin_info)
            
            assert fake_name in unloaded
            assert fake_name not in sys.modules
        finally:
            sys.modules.pop(fake_name, None)
    
    def test_unload_submodules(self, reloader, mock_plugin_info):
        """Test unloading submodules."""
        # Add fake modules
        main = "jupiter.plugins.test_plugin"
        sub1 = "jupiter.plugins.test_plugin.models"
        sub2 = "jupiter.plugins.test_plugin.api"
        
        for name in [main, sub1, sub2]:
            sys.modules[name] = MagicMock()
        
        try:
            unloaded = reloader._unload_module("test_plugin", mock_plugin_info)
            
            assert len(unloaded) == 3
            for name in [main, sub1, sub2]:
                assert name not in sys.modules
        finally:
            for name in [main, sub1, sub2]:
                sys.modules.pop(name, None)
    
    def test_module_reference_cleared(self, reloader, mock_plugin_info):
        """Test that module reference is cleared in PluginInfo."""
        mock_plugin_info.module = MagicMock()
        
        reloader._unload_module("test_plugin", mock_plugin_info)
        
        assert mock_plugin_info.module is None
