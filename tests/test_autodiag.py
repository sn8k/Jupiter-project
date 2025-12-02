"""
Tests for the autodiag dual-port architecture (Phase 3).

Version: 1.0.0
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from jupiter.server.routers import autodiag
from jupiter.config.config import AutodiagConfig, JupiterConfig


class TestAutodiagConfig:
    """Tests for AutodiagConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = AutodiagConfig()
        assert config.enabled is False
        assert config.port == 8081
        assert config.introspect_api is True
        assert config.validate_handlers is True
        assert config.collect_runtime_stats is False
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = AutodiagConfig(
            enabled=True,
            port=9000,
            introspect_api=False,
            validate_handlers=False,
            collect_runtime_stats=True,
        )
        assert config.enabled is True
        assert config.port == 9000
        assert config.introspect_api is False
        assert config.validate_handlers is False
        assert config.collect_runtime_stats is True


class TestAutodiagConfigParsing:
    """Tests for parsing autodiag config from YAML."""
    
    def test_from_dict_with_autodiag(self):
        """Test parsing config with autodiag section."""
        data = {
            "autodiag": {
                "enabled": True,
                "port": 8082,
            }
        }
        config = JupiterConfig.from_dict(data)
        assert config.autodiag.enabled is True
        assert config.autodiag.port == 8082
    
    def test_from_dict_without_autodiag(self):
        """Test parsing config without autodiag section."""
        data = {}
        config = JupiterConfig.from_dict(data)
        assert config.autodiag.enabled is False
        assert config.autodiag.port == 8081  # default


class TestAutodiagRouter:
    """Tests for autodiag router endpoints."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app with autodiag router."""
        test_app = FastAPI()
        test_app.include_router(autodiag.router)
        
        # Mock main app
        mock_main_app = MagicMock()
        mock_main_app.routes = []
        mock_main_app.state = MagicMock()
        mock_main_app.state.plugin_manager = None
        mock_main_app.state.root_path = Path.cwd()
        
        test_app.state.main_app = mock_main_app
        test_app.state.start_time = 0
        
        return test_app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Test /diag/health endpoint."""
        response = client.get("/diag/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "autodiag"
    
    def test_introspect_empty_routes(self, client):
        """Test /diag/introspect with no routes."""
        response = client.get("/diag/introspect")
        assert response.status_code == 200
        data = response.json()
        assert data["endpoints"] == []
        assert data["total"] == 0
    
    def test_handlers_endpoint(self, client):
        """Test /diag/handlers endpoint."""
        response = client.get("/diag/handlers")
        assert response.status_code == 200
        data = response.json()
        assert "api_handlers" in data
        assert "cli_handlers" in data
        assert "plugin_handlers" in data
        assert "total" in data
    
    def test_validate_unused_known_pattern(self, client):
        """Test /diag/validate-unused with known pattern."""
        response = client.post(
            "/diag/validate-unused",
            json=["some_module::__init__"],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["validated"] == 1
        result = data["results"]["some_module::__init__"]
        assert result["is_unused"] is False
        assert result["reason"] == "known_pattern"
    
    def test_validate_unused_unknown_function(self, client):
        """Test /diag/validate-unused with unknown function."""
        response = client.post(
            "/diag/validate-unused",
            json=["some_module::completely_unknown_function_xyz"],
        )
        assert response.status_code == 200
        data = response.json()
        result = data["results"]["some_module::completely_unknown_function_xyz"]
        assert result["is_unused"] is True
        assert result["reason"] == "no_usage_found"
    
    def test_stats_endpoint(self, client):
        """Test /diag/stats endpoint."""
        response = client.get("/diag/stats")
        assert response.status_code == 200
        data = response.json()
        assert "pid" in data
        assert "route_count" in data


class TestAutodiagRouterWithRoutes:
    """Tests for autodiag router with mock routes."""
    
    @pytest.fixture
    def app_with_routes(self):
        """Create test FastAPI app with mock routes."""
        test_app = FastAPI()
        test_app.include_router(autodiag.router)
        
        # Create mock main app with routes
        mock_main_app = FastAPI()
        
        @mock_main_app.get("/api/health")
        async def health():
            return {"status": "ok"}
        
        @mock_main_app.post("/api/scan")
        async def scan():
            return {"files": []}
        
        mock_main_app.state = MagicMock()
        mock_main_app.state.plugin_manager = None
        mock_main_app.state.root_path = Path.cwd()
        
        test_app.state.main_app = mock_main_app
        test_app.state.start_time = 0
        
        return test_app
    
    @pytest.fixture
    def client(self, app_with_routes):
        """Create test client."""
        return TestClient(app_with_routes)
    
    def test_introspect_with_routes(self, client):
        """Test /diag/introspect with actual routes."""
        response = client.get("/diag/introspect")
        assert response.status_code == 200
        data = response.json()
        
        # Should find at least the health and scan endpoints
        assert data["total"] >= 2
        
        paths = [ep["path"] for ep in data["endpoints"]]
        assert "/api/health" in paths
        assert "/api/scan" in paths
    
    def test_handlers_with_routes(self, client):
        """Test /diag/handlers includes API handlers."""
        response = client.get("/diag/handlers")
        assert response.status_code == 200
        data = response.json()
        
        # Should have API handlers
        assert len(data["api_handlers"]) >= 2
        
        # Check handler info
        handler_names = [h["function_name"] for h in data["api_handlers"]]
        assert "health" in handler_names
        assert "scan" in handler_names


class TestCLIHandlersIntegration:
    """Tests for CLI handlers integration in autodiag."""
    
    def test_get_cli_handlers_available(self):
        """Test that CLI handlers can be retrieved."""
        try:
            from jupiter.cli.main import get_cli_handlers, CLI_HANDLERS
            handlers = get_cli_handlers()
            
            assert len(handlers) > 0
            assert len(handlers) == len(CLI_HANDLERS)
            
            # Check handler structure
            for h in handlers:
                assert "command" in h
                assert "function_name" in h
                assert "module" in h
        except ImportError:
            pytest.skip("CLI handlers not available")
    
    def test_cli_handlers_in_autodiag(self):
        """Test that CLI handlers appear in autodiag response."""
        test_app = FastAPI()
        test_app.include_router(autodiag.router)
        
        mock_main_app = MagicMock()
        mock_main_app.routes = []
        mock_main_app.state = MagicMock()
        mock_main_app.state.plugin_manager = None
        
        test_app.state.main_app = mock_main_app
        
        client = TestClient(test_app)
        response = client.get("/diag/handlers")
        data = response.json()
        
        # Should have CLI handlers
        assert len(data["cli_handlers"]) > 0
        
        # Check for expected commands
        commands = [h["command"] for h in data["cli_handlers"]]
        assert "scan" in commands
        assert "analyze" in commands
        assert "server" in commands
