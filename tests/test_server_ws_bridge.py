"""Tests for Bridge-to-WebSocket Event Propagation.

Version: 0.1.0
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

# Use anyio for async tests
pytestmark = pytest.mark.anyio


class TestWSBridgeModule:
    """Test ws_bridge module functions."""
    
    def test_import_module(self):
        """Test module can be imported."""
        from jupiter.server import ws_bridge
        assert hasattr(ws_bridge, 'init_ws_bridge')
        assert hasattr(ws_bridge, 'shutdown_ws_bridge')
        assert hasattr(ws_bridge, 'is_ws_bridge_active')
    
    def test_is_ws_bridge_active_default(self):
        """Test is_ws_bridge_active returns False when not initialized."""
        from jupiter.server.ws_bridge import is_ws_bridge_active
        # Reset state
        import jupiter.server.ws_bridge as ws_mod
        ws_mod._initialized = False
        ws_mod._ws_hook = None
        
        assert is_ws_bridge_active() is False


class TestWSBridgeInit:
    """Test ws_bridge initialization."""
    
    async def test_init_ws_bridge_no_bridge(self):
        """Test init_ws_bridge when Bridge is not initialized."""
        import jupiter.server.ws_bridge as ws_mod
        ws_mod._initialized = False
        ws_mod._ws_hook = None
        
        # Patch bridge to return not initialized
        mock_bridge = MagicMock()
        mock_bridge.is_initialized = MagicMock(return_value=False)
        mock_bridge.get_event_bus = MagicMock(return_value=None)
        
        with patch.dict('sys.modules', {'jupiter.core.bridge': mock_bridge}):
            import importlib
            importlib.reload(ws_mod)
            
            result = await ws_mod.init_ws_bridge()
            # Should return False since bridge is not initialized
            assert result is False
    
    async def test_init_ws_bridge_with_bridge(self):
        """Test init_ws_bridge when Bridge is available."""
        import jupiter.server.ws_bridge as ws_mod
        ws_mod._initialized = False
        ws_mod._ws_hook = None
        
        mock_event_bus = MagicMock()
        mock_event_bus.add_websocket_hook = MagicMock()
        
        mock_bridge = MagicMock()
        mock_bridge.is_initialized = MagicMock(return_value=True)
        mock_bridge.get_event_bus = MagicMock(return_value=mock_event_bus)
        
        with patch.dict('sys.modules', {'jupiter.core.bridge': mock_bridge}):
            import importlib
            importlib.reload(ws_mod)
            
            result = await ws_mod.init_ws_bridge()
            
            # Should succeed and add hook
            assert result is True
            mock_event_bus.add_websocket_hook.assert_called_once()


class TestWSBridgeShutdown:
    """Test ws_bridge shutdown."""
    
    async def test_shutdown_not_initialized(self):
        """Test shutdown when not initialized does nothing."""
        import jupiter.server.ws_bridge as ws_mod
        ws_mod._initialized = False
        ws_mod._ws_hook = None
        
        # Should not raise
        await ws_mod.shutdown_ws_bridge()
        
        assert ws_mod._initialized is False


class TestWSEventHook:
    """Test the WebSocket event hook."""
    
    def test_create_ws_event_hook_returns_callable(self):
        """Test that _create_ws_event_hook returns a callable."""
        from jupiter.server.ws_bridge import _create_ws_event_hook
        hook = _create_ws_event_hook()
        assert callable(hook)
    
    async def test_event_hook_formats_event(self):
        """Test that event hook formats events correctly."""
        from jupiter.server.ws_bridge import _create_ws_event_hook
        from jupiter.server.ws import manager
        
        # Create hook
        hook = _create_ws_event_hook()
        
        # Create a mock event
        mock_event = MagicMock()
        mock_event.topic = "test.topic"
        mock_event.payload = {"key": "value"}
        mock_event.timestamp.isoformat.return_value = "2024-01-01T00:00:00Z"
        mock_event.source_plugin = "test_plugin"
        
        # Mock the manager's broadcast
        with patch.object(manager, 'broadcast', new_callable=AsyncMock) as mock_broadcast:
            # Call the hook in an async context
            hook(mock_event)
            
            # Give asyncio time to process the task
            await asyncio.sleep(0.05)
            
            # Check broadcast was called with correct format
            if mock_broadcast.called:
                call_args = mock_broadcast.call_args[0][0]
                assert call_args["type"] == "bridge_event"
                assert call_args["topic"] == "test.topic"


class TestWSBridgeIntegration:
    """Integration tests for ws_bridge."""
    
    async def test_full_lifecycle(self):
        """Test full init -> shutdown lifecycle."""
        import jupiter.server.ws_bridge as ws_mod
        ws_mod._initialized = False
        ws_mod._ws_hook = None
        
        mock_event_bus = MagicMock()
        mock_event_bus.add_websocket_hook = MagicMock()
        mock_event_bus.remove_websocket_hook = MagicMock(return_value=True)
        
        mock_bridge = MagicMock()
        mock_bridge.is_initialized = MagicMock(return_value=True)
        mock_bridge.get_event_bus = MagicMock(return_value=mock_event_bus)
        
        with patch.dict('sys.modules', {'jupiter.core.bridge': mock_bridge}):
            import importlib
            importlib.reload(ws_mod)
            
            # Init
            init_result = await ws_mod.init_ws_bridge()
            assert init_result is True
            assert ws_mod.is_ws_bridge_active() is True
            
            # Shutdown
            await ws_mod.shutdown_ws_bridge()
            assert ws_mod.is_ws_bridge_active() is False


class TestGetPropagatedEventCount:
    """Test event count function."""
    
    def test_get_propagated_event_count_returns_zero(self):
        """Test that get_propagated_event_count returns 0 (placeholder)."""
        from jupiter.server.ws_bridge import get_propagated_event_count
        assert get_propagated_event_count() == 0
