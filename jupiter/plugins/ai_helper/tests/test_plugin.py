"""
tests/test_plugin.py – Unit tests for AI Helper plugin.
Version: 1.1.0

Tests cover plugin lifecycle, business logic, and API endpoints.
Conforme à plugins_architecture.md v0.4.0

@module jupiter.plugins.ai_helper.tests.test_plugin
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import asdict


class MockBridge:
    """Mock Bridge for testing."""
    
    def __init__(self):
        self.services = MockServices()
        self.config = MockConfig()
        self.jobs = MockJobs()
        self.plugins = MockPlugins()


class MockServices:
    """Mock services namespace."""
    
    def get_logger(self, plugin_id):
        logger = MagicMock()
        logger.isEnabledFor = MagicMock(return_value=True)
        return logger
    
    def get_config(self, plugin_id):
        return {
            "enabled": True,
            "provider": "mock",
            "api_key": "",
            "suggestion_types": ["refactoring", "doc", "testing"],
            "severity_threshold": "info",
            "large_file_threshold_kb": 50,
            "max_functions_threshold": 20
        }
    
    def get_log_dir(self):
        return "/tmp/jupiter/logs"


class MockConfig:
    """Mock config namespace."""
    
    def __init__(self):
        self._data = {}
    
    def set(self, plugin_id, config):
        self._data[plugin_id] = config
    
    def get(self, plugin_id):
        return self._data.get(plugin_id, {})


class MockJobs:
    """Mock jobs namespace."""
    
    async def submit(self, plugin_id, handler, params):
        return "test-job-123"
    
    async def list(self, plugin_id):
        return []
    
    async def get(self, job_id):
        return {"id": job_id, "status": "completed"}
    
    async def cancel(self, job_id):
        return True


class MockPlugins:
    """Mock plugins namespace."""
    
    def has(self, plugin_id):
        return plugin_id == "ai_helper"


# =============================================================================
# LIFECYCLE TESTS
# =============================================================================

class TestPluginLifecycle:
    """Tests for plugin initialization and lifecycle."""
    
    def test_init_with_bridge(self):
        """Test plugin initialization with bridge."""
        from jupiter.plugins import ai_helper
        
        bridge = MockBridge()
        ai_helper.init(bridge)
        
        assert ai_helper._bridge is not None
        assert ai_helper._logger is not None
    
    def test_health_when_enabled(self):
        """Test health check returns healthy when enabled."""
        from jupiter.plugins import ai_helper
        
        bridge = MockBridge()
        ai_helper.init(bridge)
        
        health = ai_helper.health()
        
        assert health["status"] == "healthy"
        assert "details" in health
    
    def test_health_when_disabled(self):
        """Test health check returns degraded when disabled."""
        from jupiter.plugins import ai_helper
        
        bridge = MockBridge()
        ai_helper.init(bridge)
        
        # Disable the plugin
        state = ai_helper._get_state()
        state.enabled = False
        
        health = ai_helper.health()
        
        assert health["status"] == "degraded"
    
    def test_metrics_returns_dict(self):
        """Test metrics returns a dictionary."""
        from jupiter.plugins import ai_helper
        
        bridge = MockBridge()
        ai_helper.init(bridge)
        
        metrics = ai_helper.metrics()
        
        assert isinstance(metrics, dict)
        assert "ai_helper_executions_total" in metrics
        assert "ai_helper_errors_total" in metrics
        assert "ai_helper_suggestions_total" in metrics
    
    def test_reset_settings(self):
        """Test settings reset."""
        from jupiter.plugins import ai_helper
        
        bridge = MockBridge()
        ai_helper.init(bridge)
        
        # Modify settings
        state = ai_helper._get_state()
        state.provider = "openai"
        state.enabled = False
        
        # Reset
        result = ai_helper.reset_settings()
        
        assert result["success"] is True
        assert state.enabled is True
        assert state.provider == "mock"


# =============================================================================
# BUSINESS LOGIC TESTS
# =============================================================================

class TestSuggestionGeneration:
    """Tests for suggestion generation logic."""
    
    def test_generate_suggestions_empty_summary(self):
        """Test with empty summary returns no suggestions."""
        from jupiter.plugins.ai_helper.core.logic import generate_suggestions
        
        config = {"provider": "mock", "suggestion_types": ["refactoring"]}
        suggestions = generate_suggestions({}, config)
        
        assert isinstance(suggestions, list)
    
    def test_generate_doc_suggestion(self):
        """Test documentation suggestion generation."""
        from jupiter.plugins.ai_helper.core.logic import generate_suggestions
        
        config = {
            "provider": "mock",
            "suggestion_types": ["doc"],
            "large_file_threshold_kb": 50,
            "max_functions_threshold": 20
        }
        summary = {
            "python_summary": {
                "avg_functions_per_file": 5  # > 3 triggers suggestion
            }
        }
        
        suggestions = generate_suggestions(summary, config)
        
        doc_suggestions = [s for s in suggestions if s.type == "doc"]
        assert len(doc_suggestions) > 0
    
    def test_generate_cleanup_suggestion(self):
        """Test cleanup suggestion for unused functions."""
        from jupiter.plugins.ai_helper.core.logic import generate_suggestions
        
        config = {
            "provider": "mock",
            "suggestion_types": ["cleanup"],
            "large_file_threshold_kb": 50,
            "max_functions_threshold": 20
        }
        summary = {
            "python_summary": {
                "total_potentially_unused_functions": 15  # > 10 triggers suggestion
            }
        }
        
        suggestions = generate_suggestions(summary, config)
        
        cleanup_suggestions = [s for s in suggestions if s.type == "cleanup"]
        assert len(cleanup_suggestions) > 0
    
    def test_suggestion_dataclass(self):
        """Test AISuggestion dataclass."""
        from jupiter.plugins.ai_helper.core.logic import AISuggestion
        
        suggestion = AISuggestion(
            path="test.py",
            type="refactoring",
            details="Test suggestion",
            severity="medium"
        )
        
        assert suggestion.path == "test.py"
        assert suggestion.type == "refactoring"
        
        as_dict = asdict(suggestion)
        assert as_dict["path"] == "test.py"


# =============================================================================
# HOOK TESTS
# =============================================================================

class TestHooks:
    """Tests for analysis hooks."""
    
    def test_on_scan_captures_files(self):
        """Test on_scan captures file list."""
        from jupiter.plugins import ai_helper
        
        bridge = MockBridge()
        ai_helper.init(bridge)
        
        report = {
            "files": [
                {"path": "test1.py", "file_type": "py"},
                {"path": "test2.py", "file_type": "py"}
            ]
        }
        
        ai_helper.on_scan(report)
        
        state = ai_helper._get_state()
        assert len(state.scanned_files) == 2
    
    def test_on_analyze_enriches_summary(self):
        """Test on_analyze adds refactoring suggestions."""
        from jupiter.plugins import ai_helper
        
        bridge = MockBridge()
        ai_helper.init(bridge)
        
        summary = {
            "python_summary": {
                "avg_functions_per_file": 5
            }
        }
        
        ai_helper.on_analyze(summary)
        
        assert "refactoring" in summary
        assert isinstance(summary["refactoring"], list)
    
    def test_on_analyze_skips_when_disabled(self):
        """Test on_analyze does nothing when disabled."""
        from jupiter.plugins import ai_helper
        
        bridge = MockBridge()
        ai_helper.init(bridge)
        
        state = ai_helper._get_state()
        state.enabled = False
        initial_count = state.execution_count
        
        summary = {}
        ai_helper.on_analyze(summary)
        
        # Should not increment execution count
        assert state.execution_count == initial_count


# =============================================================================
# API HELPER TESTS
# =============================================================================

class TestAPIHelpers:
    """Tests for API helper functions."""
    
    def test_get_suggestions_returns_list(self):
        """Test get_suggestions returns list of dicts."""
        from jupiter.plugins import ai_helper
        
        bridge = MockBridge()
        ai_helper.init(bridge)
        
        # Generate some suggestions first
        summary = {"python_summary": {"avg_functions_per_file": 5}}
        ai_helper.on_analyze(summary)
        
        suggestions = ai_helper.get_suggestions()
        
        assert isinstance(suggestions, list)
        for s in suggestions:
            assert isinstance(s, dict)
    
    def test_get_config_returns_dict(self):
        """Test get_config returns configuration dict."""
        from jupiter.plugins import ai_helper
        
        bridge = MockBridge()
        ai_helper.init(bridge)
        
        config = ai_helper.get_config()
        
        assert isinstance(config, dict)
        assert "enabled" in config or config.get("enabled") is not None


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
