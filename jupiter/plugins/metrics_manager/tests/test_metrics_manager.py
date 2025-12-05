"""
Metrics Manager Plugin - Tests Module

@version 1.0.0
@module jupiter.plugins.metrics_manager.tests
"""

import pytest
from unittest.mock import MagicMock, patch


class TestMetricsManagerPlugin:
    """Tests for the Metrics Manager plugin."""
    
    def test_init_creates_state(self):
        """Test that init creates plugin state."""
        from jupiter.plugins import metrics_manager
        
        # Create mock bridge
        mock_bridge = MagicMock()
        mock_bridge.services.get_logger.return_value = MagicMock()
        mock_bridge.services.get_config.return_value = {"enabled": True}
        mock_bridge.services.get_event_bus.return_value = MagicMock()
        
        # Reset state
        metrics_manager._state = None
        metrics_manager._bridge = None
        
        # Initialize
        metrics_manager.init(mock_bridge)
        
        assert metrics_manager._bridge is not None
        assert metrics_manager._get_state().enabled is True
    
    def test_health_returns_status(self):
        """Test that health returns proper status."""
        from jupiter.plugins import metrics_manager
        
        # Setup state
        metrics_manager._state = None
        
        with patch('jupiter.plugins.metrics_manager.get_metrics_collector') as mock_collector:
            mock_collector.return_value = MagicMock()
            
            result = metrics_manager.health()
            
            assert "status" in result
            assert "enabled" in result
            assert "version" in result
    
    def test_metrics_returns_counters(self):
        """Test that metrics returns counter values."""
        from jupiter.plugins import metrics_manager
        
        # Setup state
        metrics_manager._state = None
        state = metrics_manager._get_state()
        state.collection_count = 5
        state.api_calls = 10
        
        result = metrics_manager.metrics()
        
        assert result["counters"]["collections"] == 5
        assert result["counters"]["api_calls"] == 10
    
    def test_reset_settings(self):
        """Test that reset_settings clears state."""
        from jupiter.plugins import metrics_manager
        
        # Setup state with some values
        state = metrics_manager._get_state()
        state.collection_count = 100
        state.error_count = 5
        
        result = metrics_manager.reset_settings()
        
        assert result["success"] is True
        # State should be reset
        new_state = metrics_manager._get_state()
        assert new_state.collection_count == 0
    
    def test_collect_all_metrics(self):
        """Test collect_all_metrics function."""
        from jupiter.plugins import metrics_manager
        
        with patch('jupiter.plugins.metrics_manager.get_metrics_collector') as mock_get:
            mock_collector = MagicMock()
            mock_collector.get_all_metrics.return_value = {
                "system": {"uptime_seconds": 100},
                "metrics": {},
                "counters": {},
                "plugins": {}
            }
            mock_get.return_value = mock_collector
            
            result = metrics_manager.collect_all_metrics()
            
            assert "system" in result
            assert result["system"]["uptime_seconds"] == 100
    
    def test_export_metrics_json(self):
        """Test export_metrics with JSON format."""
        from jupiter.plugins import metrics_manager
        
        with patch('jupiter.plugins.metrics_manager.get_metrics_collector') as mock_get:
            mock_collector = MagicMock()
            mock_collector.get_all_metrics.return_value = {"test": "data"}
            mock_get.return_value = mock_collector
            
            result = metrics_manager.export_metrics("json")
            
            assert "test" in result
            assert "data" in result
    
    def test_export_metrics_prometheus(self):
        """Test export_metrics with Prometheus format."""
        from jupiter.plugins import metrics_manager
        
        with patch('jupiter.plugins.metrics_manager.get_metrics_collector') as mock_get:
            mock_collector = MagicMock()
            mock_collector.to_prometheus.return_value = "# HELP test\ntest_metric 42"
            mock_get.return_value = mock_collector
            
            result = metrics_manager.export_metrics("prometheus")
            
            assert "HELP" in result or "test_metric" in result
    
    def test_record_custom_metric(self):
        """Test recording a custom metric."""
        from jupiter.plugins import metrics_manager
        
        with patch('jupiter.plugins.metrics_manager.get_metrics_collector') as mock_get:
            mock_collector = MagicMock()
            mock_get.return_value = mock_collector
            
            result = metrics_manager.record_custom_metric(
                "test.metric",
                42.5,
                {"label": "value"}
            )
            
            assert result["success"] is True
            mock_collector.record.assert_called_once()
    
    def test_clear_alerts(self):
        """Test clearing alerts."""
        from jupiter.plugins import metrics_manager
        
        # Add some alerts
        state = metrics_manager._get_state()
        state.active_alerts = [
            metrics_manager.MetricAlert(
                metric_name="test",
                threshold=1.0,
                current_value=2.0,
                severity="warning",
                message="Test alert"
            )
        ]
        
        result = metrics_manager.clear_alerts()
        
        assert result["success"] is True
        assert result["cleared_count"] == 1
        assert len(state.active_alerts) == 0


class TestMetricsManagerAPI:
    """Tests for the Metrics Manager API routes."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from jupiter.plugins.metrics_manager.server.api import router
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router, prefix="/test")
        return TestClient(app)
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns plugin info."""
        response = client.get("/test/")
        assert response.status_code == 200
        data = response.json()
        assert data["plugin"] == "metrics_manager"
    
    def test_health_endpoint(self, client):
        """Test health endpoint."""
        response = client.get("/test/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        response = client.get("/test/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "counters" in data
