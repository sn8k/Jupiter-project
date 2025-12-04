"""Tests for jupiter.core.bridge.bootstrap module.

Version: 0.1.0

Tests for the plugin system bootstrap functionality.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

from jupiter.core.bridge.bootstrap import (
    init_plugin_system,
    shutdown_plugin_system,
    is_initialized,
    get_bridge,
    get_plugin_stats,
)


@pytest.fixture(autouse=True)
def reset_module_state():
    """Reset module-level state before and after each test."""
    import jupiter.core.bridge.bootstrap as bootstrap
    bootstrap._initialized = False
    bootstrap._bridge = None
    yield
    bootstrap._initialized = False
    bootstrap._bridge = None


@pytest.fixture
def mock_app():
    """Create a mock FastAPI app."""
    app = MagicMock()
    app.state = MagicMock()
    return app


@pytest.fixture
def mock_bridge():
    """Create a mock Bridge."""
    bridge = MagicMock()
    bridge.get_all_plugins.return_value = {}
    return bridge


class TestIsInitialized:
    """Tests for is_initialized function."""
    
    def test_returns_false_initially(self):
        """Should return False when not initialized."""
        assert is_initialized() is False
    
    def test_returns_true_after_init(self):
        """Should return True after initialization."""
        import jupiter.core.bridge.bootstrap as bootstrap
        bootstrap._initialized = True
        assert is_initialized() is True


class TestGetBridge:
    """Tests for get_bridge function."""
    
    def test_returns_none_when_not_initialized(self):
        """Should return None when not initialized."""
        assert get_bridge() is None
    
    def test_returns_bridge_when_initialized(self, mock_bridge):
        """Should return Bridge when initialized."""
        import jupiter.core.bridge.bootstrap as bootstrap
        bootstrap._bridge = mock_bridge
        assert get_bridge() is mock_bridge


class TestGetPluginStats:
    """Tests for get_plugin_stats function."""
    
    def test_returns_uninitialized_stats(self):
        """Should return uninitialized stats."""
        stats = get_plugin_stats()
        
        assert stats["initialized"] is False
        assert stats["plugins_loaded"] == 0
    
    def test_returns_stats_when_initialized(self, mock_bridge):
        """Should return stats when initialized."""
        import jupiter.core.bridge.bootstrap as bootstrap
        bootstrap._initialized = True
        bootstrap._bridge = mock_bridge
        
        # Mock plugin with ready state
        plugin_info = MagicMock()
        plugin_info.state = MagicMock()
        plugin_info.state.value = "ready"
        mock_bridge.get_all_plugins.return_value = [plugin_info]  # Returns list not dict
        
        # Mock registries via jupiter.core.bridge module
        with patch('jupiter.core.bridge.get_cli_registry') as mock_cli, \
             patch('jupiter.core.bridge.get_api_registry') as mock_api, \
             patch('jupiter.core.bridge.get_ui_registry') as mock_ui:
            
            mock_cli.return_value.get_all_commands.return_value = []
            mock_api.return_value.get_all_routes.return_value = []
            mock_ui.return_value.get_sidebar_panels.return_value = []
            mock_ui.return_value.get_settings_panels.return_value = []
            
            stats = get_plugin_stats()
        
        assert stats["initialized"] is True
        assert stats["plugins_loaded"] == 1
        assert stats["plugins_ready"] == 1


class TestInitPluginSystemSync:
    """Synchronous wrapper tests for init_plugin_system."""
    
    def test_skips_if_already_initialized(self, mock_app, mock_bridge):
        """Should skip if already initialized."""
        import asyncio
        import jupiter.core.bridge.bootstrap as bootstrap
        bootstrap._initialized = True
        bootstrap._bridge = mock_bridge
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(init_plugin_system(mock_app))
        finally:
            loop.close()
        
        assert result is mock_bridge
    
    def test_initialization_sets_initialized_flag(self, mock_app):
        """Should set initialized flag after successful init."""
        import asyncio
        import jupiter.core.bridge.bootstrap as bootstrap
        
        # Save original state
        was_initialized = is_initialized()
        
        # Use a real plugins_dir that exists but is empty (or won't find plugins)
        from pathlib import Path
        fake_plugins = Path(__file__).parent / "fake_plugins_dir_that_doesnt_exist"
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # This will init but won't find any plugins
            result = loop.run_until_complete(
                init_plugin_system(mock_app, plugins_dir=fake_plugins)
            )
            
            assert is_initialized() is True
            assert result is not None
        finally:
            loop.close()
            # Reset state
            bootstrap._initialized = False
            bootstrap._bridge = None


class TestShutdownPluginSystemSync:
    """Synchronous wrapper tests for shutdown_plugin_system."""
    
    def test_does_nothing_when_not_initialized(self):
        """Should do nothing when not initialized."""
        import asyncio
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(shutdown_plugin_system())
        finally:
            loop.close()
        
        assert is_initialized() is False
    
    def test_resets_state(self, mock_bridge):
        """Should reset module state."""
        import asyncio
        import jupiter.core.bridge.bootstrap as bootstrap
        bootstrap._initialized = True
        bootstrap._bridge = mock_bridge
        
        mock_bridge.get_all_plugins.return_value = {}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(shutdown_plugin_system())
        finally:
            loop.close()
        
        assert is_initialized() is False
        assert get_bridge() is None
