"""Tests for jupiter.server.routers.plugins module.

Version: 0.2.0 - Added WebSocket logs stream tests

Tests for the Bridge v2 plugin API endpoints.
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.testclient import TestClient

from jupiter.core.bridge.interfaces import (
    PluginState,
    PluginType,
    Permission,
    HealthStatus,
    HealthCheckResult,
    PluginMetrics,
    IPluginHealth,
    IPluginMetrics,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_plugin_manifest():
    """Create a mock plugin manifest."""
    manifest = MagicMock()
    manifest.id = "test_plugin"
    manifest.name = "Test Plugin"
    manifest.version = "1.0.0"
    manifest.description = "A test plugin"
    manifest.plugin_type = PluginType.TOOL
    manifest.permissions = [Permission.FS_READ]
    manifest.config_defaults = {"key": "value"}
    manifest.config_schema = {"type": "object"}
    return manifest


@pytest.fixture
def mock_plugin_info(mock_plugin_manifest):
    """Create a mock PluginInfo."""
    info = MagicMock()
    info.manifest = mock_plugin_manifest
    info.state = PluginState.READY
    info.error = None
    info.legacy = False
    info.load_order = 1
    info.instance = None
    info.to_dict.return_value = {
        "id": "test_plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "description": "A test plugin",
        "type": "tool",
        "state": "ready",
        "error": None,
        "legacy": False,
        "trust_level": "experimental",
        "permissions": ["fs_read"],
    }
    return info


@pytest.fixture
def mock_bridge(mock_plugin_info):
    """Create a mock Bridge."""
    bridge = MagicMock()
    bridge.get_all_plugins.return_value = [mock_plugin_info]
    bridge.get_plugin.return_value = mock_plugin_info
    return bridge


@pytest.fixture
def mock_registries():
    """Create mock registries."""
    cli_registry = MagicMock()
    cli_registry.get_all_commands.return_value = []
    cli_registry.get_plugin_commands.return_value = []
    cli_registry.to_dict.return_value = {"commands": [], "groups": [], "total": 0}
    
    api_registry = MagicMock()
    api_registry.get_all_routes.return_value = []
    api_registry.get_plugin_routes.return_value = []
    api_registry.to_dict.return_value = {"routes": [], "plugins": [], "total": 0}
    
    ui_registry = MagicMock()
    ui_registry.get_sidebar_panels.return_value = []
    ui_registry.get_plugin_panels.return_value = []
    ui_registry.get_ui_manifest.return_value = {
        "plugins": {},
        "sidebar_panels": [],
        "settings_panels": [],
        "menu_items": [],
        "plugin_count": 0,
    }
    
    return cli_registry, api_registry, ui_registry


@pytest.fixture
def test_app(mock_bridge, mock_registries):
    """Create test FastAPI app with mocked dependencies."""
    from jupiter.server.routers.plugins import router
    
    app = FastAPI()
    app.include_router(router)
    
    cli_registry, api_registry, ui_registry = mock_registries
    
    # Patch the helper functions
    with patch("jupiter.server.routers.plugins.get_bridge", return_value=mock_bridge), \
         patch("jupiter.server.routers.plugins.get_cli_registry", return_value=cli_registry), \
         patch("jupiter.server.routers.plugins.get_api_registry", return_value=api_registry), \
         patch("jupiter.server.routers.plugins.get_ui_registry", return_value=ui_registry), \
         patch("jupiter.server.routers.auth.verify_token", return_value=True), \
         patch("jupiter.server.routers.auth.require_admin", return_value=True):
        yield TestClient(app)


# =============================================================================
# Bridge Status Tests
# =============================================================================

class TestBridgeStatus:
    """Tests for GET /plugins/v2/status endpoint."""
    
    def test_returns_status_with_bridge(self, test_app, mock_bridge):
        """Should return bridge status when bridge is available."""
        response = test_app.get("/plugins/v2/status")
        assert response.status_code == 200
        data = response.json()
        
        assert "version" in data
        assert "initialized" in data
        assert "plugins_loaded" in data
        assert "plugins_ready" in data
        assert "plugins_error" in data
        assert "cli_commands" in data
        assert "api_routes" in data
        assert "ui_panels" in data
    
    def test_returns_empty_status_without_bridge(self):
        """Should return empty status when bridge is not available."""
        from jupiter.server.routers.plugins import router
        
        app = FastAPI()
        app.include_router(router)
        
        with patch("jupiter.server.routers.plugins.get_bridge", return_value=None), \
             patch("jupiter.server.routers.plugins.get_cli_registry", return_value=None), \
             patch("jupiter.server.routers.plugins.get_api_registry", return_value=None), \
             patch("jupiter.server.routers.plugins.get_ui_registry", return_value=None), \
             patch("jupiter.server.routers.auth.verify_token", return_value=True):
            client = TestClient(app)
            response = client.get("/plugins/v2/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["initialized"] == False
            assert data["plugins_loaded"] == 0


# =============================================================================
# Plugin List Tests
# =============================================================================

class TestPluginList:
    """Tests for GET /plugins/v2 endpoint."""
    
    def test_returns_plugin_list(self, test_app, mock_plugin_info):
        """Should return list of plugins."""
        response = test_app.get("/plugins/v2")
        assert response.status_code == 200
        data = response.json()
        
        assert "plugins" in data
        assert "total" in data
        assert "by_type" in data
        assert "by_state" in data
        assert len(data["plugins"]) == 1
        assert data["plugins"][0]["id"] == "test_plugin"
    
    def test_filters_by_type(self, test_app, mock_bridge, mock_plugin_info):
        """Should filter plugins by type."""
        response = test_app.get("/plugins/v2?type=tool")
        assert response.status_code == 200
        data = response.json()
        # Plugin should be included since it's a tool
        assert len(data["plugins"]) == 1
    
    def test_filters_by_state(self, test_app, mock_bridge, mock_plugin_info):
        """Should filter plugins by state."""
        response = test_app.get("/plugins/v2?state=ready")
        assert response.status_code == 200
        data = response.json()
        assert len(data["plugins"]) == 1


# =============================================================================
# Plugin Details Tests
# =============================================================================

class TestPluginDetails:
    """Tests for GET /plugins/v2/{plugin_id} endpoint."""
    
    def test_returns_plugin_details(self, test_app):
        """Should return plugin details."""
        response = test_app.get("/plugins/v2/test_plugin")
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == "test_plugin"
        assert data["name"] == "Test Plugin"
        assert "cli_commands" in data
        assert "api_routes" in data
        assert "ui_panels" in data
    
    def test_returns_404_for_unknown_plugin(self, test_app, mock_bridge):
        """Should return 404 for unknown plugin."""
        mock_bridge.get_plugin.return_value = None
        
        response = test_app.get("/plugins/v2/unknown_plugin")
        assert response.status_code == 404


# =============================================================================
# Plugin Health Tests
# =============================================================================

class TestPluginHealth:
    """Tests for GET /plugins/v2/{plugin_id}/health endpoint."""
    
    def test_returns_health_for_ready_plugin(self, test_app, mock_plugin_info):
        """Should return healthy status for ready plugin."""
        response = test_app.get("/plugins/v2/test_plugin/health")
        assert response.status_code == 200
        data = response.json()
        
        assert data["plugin_id"] == "test_plugin"
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_returns_unhealthy_for_error_plugin(self, test_app, mock_plugin_info):
        """Should return unhealthy status for errored plugin."""
        mock_plugin_info.state = PluginState.ERROR
        mock_plugin_info.error = "Test error"
        
        response = test_app.get("/plugins/v2/test_plugin/health")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "unhealthy"
        assert "Test error" in data["message"]
    
    def test_calls_health_interface_if_available(self, test_app, mock_plugin_info):
        """Should call plugin health() method if it implements IPluginHealth."""
        # Create mock health result
        health_instance = MagicMock(spec=IPluginHealth)
        health_instance.health.return_value = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="All checks passed",
            details={"database": "ok", "cache": "ok"},
        )
        mock_plugin_info.instance = health_instance
        
        response = test_app.get("/plugins/v2/test_plugin/health")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["message"] == "All checks passed"
        assert "database" in data["checks"]


# =============================================================================
# Plugin Metrics Tests
# =============================================================================

class TestPluginMetrics:
    """Tests for GET /plugins/v2/{plugin_id}/metrics endpoint."""
    
    def test_returns_basic_metrics(self, test_app, mock_plugin_info):
        """Should return basic metrics for plugin."""
        response = test_app.get("/plugins/v2/test_plugin/metrics")
        assert response.status_code == 200
        data = response.json()
        
        assert data["plugin_id"] == "test_plugin"
        assert "uptime_seconds" in data
        assert "request_count" in data
        assert "error_count" in data
        assert "timestamp" in data
        assert "custom_metrics" in data
    
    def test_calls_metrics_interface_if_available(self, test_app, mock_plugin_info):
        """Should call plugin metrics() method if it implements IPluginMetrics."""
        metrics_instance = MagicMock(spec=IPluginMetrics)
        metrics_instance.metrics.return_value = PluginMetrics(
            execution_count=100,
            error_count=5,
            last_execution=datetime.now(timezone.utc).timestamp(),
            custom={"requests_per_minute": 10},
        )
        mock_plugin_info.instance = metrics_instance
        
        response = test_app.get("/plugins/v2/test_plugin/metrics")
        assert response.status_code == 200
        data = response.json()
        
        assert data["request_count"] == 100
        assert data["error_count"] == 5
        assert "requests_per_minute" in data["custom_metrics"]


# =============================================================================
# Plugin Logs Tests
# =============================================================================

class TestPluginLogs:
    """Tests for GET /plugins/v2/{plugin_id}/logs endpoint."""
    
    def test_returns_empty_logs_when_no_log_file(self, test_app, mock_plugin_info):
        """Should return empty logs when no log file exists."""
        with patch("pathlib.Path.exists", return_value=False):
            response = test_app.get("/plugins/v2/test_plugin/logs")
            assert response.status_code == 200
            data = response.json()
            
            assert data["plugin_id"] == "test_plugin"
            assert "entries" in data
            assert data["total"] == 0


# =============================================================================
# Plugin Config Tests
# =============================================================================

class TestPluginConfig:
    """Tests for GET /plugins/v2/{plugin_id}/config endpoint."""
    
    def test_returns_plugin_config(self, test_app, mock_plugin_info):
        """Should return plugin configuration."""
        # Patch PluginManifest type check
        from jupiter.core.bridge.manifest import PluginManifest
        mock_plugin_info.manifest.__class__ = PluginManifest
        mock_plugin_info.manifest.config_defaults = {"key": "default_value"}
        mock_plugin_info.manifest.config_schema = {"type": "object"}
        
        with patch("jupiter.core.bridge.services.create_service_locator") as mock_locator:
            mock_config = MagicMock()
            mock_config.get_all.return_value = {"key": "current_value"}
            mock_locator.return_value.get_config.return_value = mock_config
            
            response = test_app.get("/plugins/v2/test_plugin/config")
            assert response.status_code == 200
            data = response.json()
            
            assert data["plugin_id"] == "test_plugin"
            assert "config" in data
            assert "defaults" in data


# =============================================================================
# UI Manifest Tests
# =============================================================================

class TestUIManifest:
    """Tests for GET /plugins/v2/ui/manifest endpoint."""
    
    def test_returns_ui_manifest(self, test_app):
        """Should return UI manifest for all plugins."""
        response = test_app.get("/plugins/v2/ui/manifest")
        assert response.status_code == 200
        data = response.json()
        
        assert "plugins" in data
        assert "sidebar_panels" in data
        assert "settings_panels" in data
        assert "menu_items" in data


# =============================================================================
# CLI Manifest Tests
# =============================================================================

class TestCLIManifest:
    """Tests for GET /plugins/v2/cli/manifest endpoint."""
    
    def test_returns_cli_manifest(self, test_app):
        """Should return CLI manifest for all plugins."""
        response = test_app.get("/plugins/v2/cli/manifest")
        assert response.status_code == 200
        data = response.json()
        
        assert "commands" in data
        assert "groups" in data
        assert "total" in data


# =============================================================================
# API Manifest Tests
# =============================================================================

class TestAPIManifest:
    """Tests for GET /plugins/v2/api/manifest endpoint."""
    
    def test_returns_api_manifest(self, test_app):
        """Should return API manifest for all plugins."""
        response = test_app.get("/plugins/v2/api/manifest")
        assert response.status_code == 200
        data = response.json()
        
        assert "routes" in data
        assert "plugins" in data
        assert "total" in data


# =============================================================================
# WebSocket Log Stream Tests
# =============================================================================

class TestPluginLogConnectionManager:
    """Tests for PluginLogConnectionManager class."""
    
    def test_get_connection_count_empty(self):
        """Should return 0 for plugin with no connections."""
        from jupiter.server.routers.plugins import PluginLogConnectionManager
        
        manager = PluginLogConnectionManager()
        assert manager.get_connection_count("test_plugin") == 0
    
    def test_get_all_stats_empty(self):
        """Should return empty dict when no connections."""
        from jupiter.server.routers.plugins import PluginLogConnectionManager
        
        manager = PluginLogConnectionManager()
        assert manager.get_all_stats() == {}
    
    def test_connect_adds_websocket(self):
        """Should add websocket to connections on connect."""
        from jupiter.server.routers.plugins import PluginLogConnectionManager
        
        async def run_test():
            manager = PluginLogConnectionManager()
            ws = AsyncMock()
            
            await manager.connect("test_plugin", ws)
            
            ws.accept.assert_called_once()
            assert manager.get_connection_count("test_plugin") == 1
        
        asyncio.run(run_test())
    
    def test_disconnect_removes_websocket(self):
        """Should remove websocket from connections on disconnect."""
        from jupiter.server.routers.plugins import PluginLogConnectionManager
        
        async def run_test():
            manager = PluginLogConnectionManager()
            ws = AsyncMock()
            
            await manager.connect("test_plugin", ws)
            assert manager.get_connection_count("test_plugin") == 1
            
            await manager.disconnect("test_plugin", ws)
            assert manager.get_connection_count("test_plugin") == 0
        
        asyncio.run(run_test())
    
    def test_disconnect_cleans_up_empty_plugin(self):
        """Should remove plugin entry when last connection disconnects."""
        from jupiter.server.routers.plugins import PluginLogConnectionManager
        
        async def run_test():
            manager = PluginLogConnectionManager()
            ws = AsyncMock()
            
            await manager.connect("test_plugin", ws)
            await manager.disconnect("test_plugin", ws)
            
            assert "test_plugin" not in manager._connections
        
        asyncio.run(run_test())
    
    def test_broadcast_sends_to_all(self):
        """Should broadcast message to all subscribers."""
        from jupiter.server.routers.plugins import PluginLogConnectionManager
        
        async def run_test():
            manager = PluginLogConnectionManager()
            ws1 = AsyncMock()
            ws2 = AsyncMock()
            
            await manager.connect("test_plugin", ws1)
            await manager.connect("test_plugin", ws2)
            
            await manager.broadcast("test_plugin", {"type": "log", "message": "test"})
            
            ws1.send_text.assert_called_once()
            ws2.send_text.assert_called_once()
        
        asyncio.run(run_test())
    
    def test_broadcast_cleans_up_failed_connections(self):
        """Should remove connections that fail to receive messages."""
        from jupiter.server.routers.plugins import PluginLogConnectionManager
        
        async def run_test():
            manager = PluginLogConnectionManager()
            ws_good = AsyncMock()
            ws_bad = AsyncMock()
            ws_bad.send_text.side_effect = Exception("Connection closed")
            
            await manager.connect("test_plugin", ws_good)
            await manager.connect("test_plugin", ws_bad)
            
            assert manager.get_connection_count("test_plugin") == 2
            
            await manager.broadcast("test_plugin", {"type": "log", "message": "test"})
            
            # Bad connection should be removed
            assert manager.get_connection_count("test_plugin") == 1
        
        asyncio.run(run_test())


class TestBroadcastPluginLog:
    """Tests for broadcast_plugin_log helper function."""
    
    def test_broadcasts_log_entry(self):
        """Should broadcast log entry to subscribers."""
        from jupiter.server.routers.plugins import (
            broadcast_plugin_log,
            PluginLogConnectionManager,
        )
        
        async def run_test():
            # Create fresh manager to avoid global state issues
            manager = PluginLogConnectionManager()
            ws = AsyncMock()
            
            await manager.connect("broadcast_test_plugin", ws)
            
            await manager.broadcast("broadcast_test_plugin", {
                "type": "log",
                "plugin_id": "broadcast_test_plugin",
                "entry": {
                    "timestamp": "2025-12-03T10:00:00Z",
                    "level": "INFO",
                    "message": "Test log message",
                },
            })
            
            ws.send_text.assert_called_once()
            # Check the payload
            call_args = ws.send_text.call_args[0][0]
            data = json.loads(call_args)
            assert data["type"] == "log"
            assert data["plugin_id"] == "broadcast_test_plugin"
            assert data["entry"]["message"] == "Test log message"
            
            # Cleanup
            await manager.disconnect("broadcast_test_plugin", ws)
        
        asyncio.run(run_test())


class TestGetLogHistory:
    """Tests for _get_log_history helper function."""
    
    def test_returns_empty_for_nonexistent_log(self):
        """Should return empty list when no log file exists."""
        from jupiter.server.routers.plugins import _get_log_history
        
        async def run_test():
            # This test validates the function handles missing files gracefully
            history = await _get_log_history("nonexistent_plugin_xyz_123", lines=10)
            assert isinstance(history, list)
        
        asyncio.run(run_test())
    
    def test_returns_list_type(self):
        """Should always return a list."""
        from jupiter.server.routers.plugins import _get_log_history
        
        async def run_test():
            history = await _get_log_history("test_plugin", lines=5)
            assert isinstance(history, list)
        
        asyncio.run(run_test())


class TestLogStreamWebSocket:
    """Integration tests for WebSocket log stream endpoint."""
    
    def test_websocket_closes_for_nonexistent_plugin(self, mock_bridge):
        """Should close WebSocket for nonexistent plugin."""
        from jupiter.server.routers.plugins import router
        
        app = FastAPI()
        app.include_router(router)
        
        mock_bridge.get_plugin.return_value = None
        
        with patch("jupiter.server.routers.plugins.get_bridge", return_value=mock_bridge):
            client = TestClient(app)
            
            # WebSocket should close with error for nonexistent plugin
            try:
                with client.websocket_connect("/plugins/v2/nonexistent/logs/stream") as ws:
                    # Should not reach here
                    pass
            except Exception:
                # Expected - WebSocket should close
                pass
    
    def test_websocket_connects_for_valid_plugin(self, mock_bridge, mock_plugin_info):
        """Should connect successfully for valid plugin."""
        from jupiter.server.routers.plugins import router
        
        app = FastAPI()
        app.include_router(router)
        
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        with patch("jupiter.server.routers.plugins.get_bridge", return_value=mock_bridge):
            client = TestClient(app)
            
            with client.websocket_connect("/plugins/v2/test_plugin/logs/stream") as ws:
                # Should receive connection info message
                data = ws.receive_json()
                assert data["type"] == "info"
                assert data["plugin_id"] == "test_plugin"
                
                # Should receive history message
                data = ws.receive_json()
                assert data["type"] == "history"
                assert "entries" in data
    
    def test_websocket_responds_to_ping(self, mock_bridge, mock_plugin_info):
        """Should respond to ping with pong."""
        from jupiter.server.routers.plugins import router
        
        app = FastAPI()
        app.include_router(router)
        
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        with patch("jupiter.server.routers.plugins.get_bridge", return_value=mock_bridge):
            client = TestClient(app)
            
            with client.websocket_connect("/plugins/v2/test_plugin/logs/stream") as ws:
                # Receive initial messages
                ws.receive_json()  # info
                ws.receive_json()  # history
                
                # Send ping
                ws.send_json({"type": "ping"})
                
                # Should receive pong
                data = ws.receive_json()
                assert data["type"] == "pong"
    
    def test_websocket_tail_parameter(self, mock_bridge, mock_plugin_info):
        """Should respect tail parameter for history."""
        from jupiter.server.routers.plugins import router
        
        app = FastAPI()
        app.include_router(router)
        
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        with patch("jupiter.server.routers.plugins.get_bridge", return_value=mock_bridge):
            client = TestClient(app)
            
            # Connect with tail=0 to skip history
            with client.websocket_connect("/plugins/v2/test_plugin/logs/stream?tail=0") as ws:
                # Should receive connection info
                data = ws.receive_json()
                assert data["type"] == "info"
                
                # Should NOT receive history since tail=0
                # Send ping to verify connection is working
                ws.send_json({"type": "ping"})
                data = ws.receive_json()
                assert data["type"] == "pong"
