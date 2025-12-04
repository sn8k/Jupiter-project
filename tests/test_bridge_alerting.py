"""Tests for Jupiter Bridge Alerting System.

Version: 0.1.0
"""

import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from jupiter.core.bridge.alerting import (
    ComparisonOperator,
    AlertSeverity,
    AlertState,
    AlertThreshold,
    Alert,
    AlertingManager,
    get_alerting_manager,
    init_alerting_manager,
    reset_alerting_manager,
    add_threshold,
    remove_threshold,
    check_metric,
    check_all,
    list_alerts,
    acknowledge_alert,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def reset_alerting():
    """Reset alerting manager before each test."""
    reset_alerting_manager()
    yield
    reset_alerting_manager()


@pytest.fixture
def manager():
    """Create a fresh alerting manager."""
    return AlertingManager()


@pytest.fixture
def threshold():
    """Create a sample threshold."""
    return AlertThreshold(
        threshold_id="test_threshold",
        plugin_id="test_plugin",
        metric_name="error_count",
        operator=ComparisonOperator.GREATER_THAN,
        threshold_value=10.0,
        severity=AlertSeverity.WARNING,
        cooldown_seconds=0,  # No cooldown for testing
    )


# =============================================================================
# ComparisonOperator Tests
# =============================================================================

class TestComparisonOperator:
    """Tests for ComparisonOperator enum."""
    
    def test_all_operators_have_values(self):
        """All operators should have string values."""
        assert ComparisonOperator.GREATER_THAN.value == "gt"
        assert ComparisonOperator.GREATER_THAN_OR_EQUAL.value == "gte"
        assert ComparisonOperator.LESS_THAN.value == "lt"
        assert ComparisonOperator.LESS_THAN_OR_EQUAL.value == "lte"
        assert ComparisonOperator.EQUAL.value == "eq"
        assert ComparisonOperator.NOT_EQUAL.value == "neq"


# =============================================================================
# AlertSeverity Tests
# =============================================================================

class TestAlertSeverity:
    """Tests for AlertSeverity enum."""
    
    def test_all_severities_have_values(self):
        """All severities should have string values."""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"


# =============================================================================
# AlertState Tests
# =============================================================================

class TestAlertState:
    """Tests for AlertState enum."""
    
    def test_all_states_have_values(self):
        """All states should have string values."""
        assert AlertState.PENDING.value == "pending"
        assert AlertState.FIRING.value == "firing"
        assert AlertState.RESOLVED.value == "resolved"
        assert AlertState.ACKNOWLEDGED.value == "acknowledged"
        assert AlertState.SILENCED.value == "silenced"


# =============================================================================
# AlertThreshold Tests
# =============================================================================

class TestAlertThreshold:
    """Tests for AlertThreshold dataclass."""
    
    def test_create_threshold(self):
        """Should create a threshold with defaults."""
        threshold = AlertThreshold(
            threshold_id="test",
            plugin_id="plugin",
            metric_name="metric",
            operator=ComparisonOperator.GREATER_THAN,
            threshold_value=10.0,
        )
        
        assert threshold.threshold_id == "test"
        assert threshold.plugin_id == "plugin"
        assert threshold.metric_name == "metric"
        assert threshold.severity == AlertSeverity.WARNING  # default
        assert threshold.cooldown_seconds == 300  # default
        assert threshold.enabled is True  # default
    
    def test_evaluate_greater_than(self):
        """Should evaluate greater than correctly."""
        threshold = AlertThreshold(
            threshold_id="test",
            plugin_id="*",
            metric_name="value",
            operator=ComparisonOperator.GREATER_THAN,
            threshold_value=10.0,
        )
        
        assert threshold.evaluate(15.0) is True
        assert threshold.evaluate(10.0) is False
        assert threshold.evaluate(5.0) is False
    
    def test_evaluate_greater_than_or_equal(self):
        """Should evaluate >= correctly."""
        threshold = AlertThreshold(
            threshold_id="test",
            plugin_id="*",
            metric_name="value",
            operator=ComparisonOperator.GREATER_THAN_OR_EQUAL,
            threshold_value=10.0,
        )
        
        assert threshold.evaluate(15.0) is True
        assert threshold.evaluate(10.0) is True
        assert threshold.evaluate(5.0) is False
    
    def test_evaluate_less_than(self):
        """Should evaluate less than correctly."""
        threshold = AlertThreshold(
            threshold_id="test",
            plugin_id="*",
            metric_name="value",
            operator=ComparisonOperator.LESS_THAN,
            threshold_value=10.0,
        )
        
        assert threshold.evaluate(5.0) is True
        assert threshold.evaluate(10.0) is False
        assert threshold.evaluate(15.0) is False
    
    def test_evaluate_less_than_or_equal(self):
        """Should evaluate <= correctly."""
        threshold = AlertThreshold(
            threshold_id="test",
            plugin_id="*",
            metric_name="value",
            operator=ComparisonOperator.LESS_THAN_OR_EQUAL,
            threshold_value=10.0,
        )
        
        assert threshold.evaluate(5.0) is True
        assert threshold.evaluate(10.0) is True
        assert threshold.evaluate(15.0) is False
    
    def test_evaluate_equal(self):
        """Should evaluate equal correctly."""
        threshold = AlertThreshold(
            threshold_id="test",
            plugin_id="*",
            metric_name="value",
            operator=ComparisonOperator.EQUAL,
            threshold_value=10.0,
        )
        
        assert threshold.evaluate(10.0) is True
        assert threshold.evaluate(5.0) is False
        assert threshold.evaluate(15.0) is False
    
    def test_evaluate_not_equal(self):
        """Should evaluate not equal correctly."""
        threshold = AlertThreshold(
            threshold_id="test",
            plugin_id="*",
            metric_name="value",
            operator=ComparisonOperator.NOT_EQUAL,
            threshold_value=10.0,
        )
        
        assert threshold.evaluate(10.0) is False
        assert threshold.evaluate(5.0) is True
        assert threshold.evaluate(15.0) is True
    
    def test_can_trigger_no_previous(self):
        """Should allow trigger if never triggered."""
        threshold = AlertThreshold(
            threshold_id="test",
            plugin_id="*",
            metric_name="value",
            operator=ComparisonOperator.GREATER_THAN,
            threshold_value=10.0,
        )
        
        assert threshold.can_trigger() is True
    
    def test_can_trigger_cooldown_not_passed(self):
        """Should not allow trigger during cooldown."""
        threshold = AlertThreshold(
            threshold_id="test",
            plugin_id="*",
            metric_name="value",
            operator=ComparisonOperator.GREATER_THAN,
            threshold_value=10.0,
            cooldown_seconds=300,
        )
        threshold._last_triggered = time.time()
        
        assert threshold.can_trigger() is False
    
    def test_can_trigger_cooldown_passed(self):
        """Should allow trigger after cooldown."""
        threshold = AlertThreshold(
            threshold_id="test",
            plugin_id="*",
            metric_name="value",
            operator=ComparisonOperator.GREATER_THAN,
            threshold_value=10.0,
            cooldown_seconds=0,
        )
        threshold._last_triggered = time.time() - 10
        
        assert threshold.can_trigger() is True
    
    def test_can_trigger_disabled(self):
        """Should not allow trigger if disabled."""
        threshold = AlertThreshold(
            threshold_id="test",
            plugin_id="*",
            metric_name="value",
            operator=ComparisonOperator.GREATER_THAN,
            threshold_value=10.0,
            enabled=False,
        )
        
        assert threshold.can_trigger() is False
    
    def test_to_dict(self, threshold):
        """Should serialize to dict."""
        data = threshold.to_dict()
        
        assert data["threshold_id"] == "test_threshold"
        assert data["plugin_id"] == "test_plugin"
        assert data["metric_name"] == "error_count"
        assert data["operator"] == "gt"
        assert data["threshold_value"] == 10.0
    
    def test_from_dict(self):
        """Should deserialize from dict."""
        data = {
            "threshold_id": "test",
            "plugin_id": "plugin",
            "metric_name": "metric",
            "operator": "gt",
            "threshold_value": 10.0,
            "severity": "error",
            "enabled": False,
        }
        
        threshold = AlertThreshold.from_dict(data)
        
        assert threshold.threshold_id == "test"
        assert threshold.severity == AlertSeverity.ERROR
        assert threshold.enabled is False


# =============================================================================
# Alert Tests
# =============================================================================

class TestAlert:
    """Tests for Alert dataclass."""
    
    def test_create_alert(self):
        """Should create an alert with defaults."""
        alert = Alert(
            alert_id="alert1",
            threshold_id="threshold1",
            plugin_id="plugin1",
            metric_name="metric",
            metric_value=15.0,
            threshold_value=10.0,
            severity=AlertSeverity.WARNING,
        )
        
        assert alert.alert_id == "alert1"
        assert alert.state == AlertState.FIRING
        assert alert.resolved_at is None
    
    def test_acknowledge(self):
        """Should acknowledge alert."""
        alert = Alert(
            alert_id="alert1",
            threshold_id="threshold1",
            plugin_id="plugin1",
            metric_name="metric",
            metric_value=15.0,
            threshold_value=10.0,
            severity=AlertSeverity.WARNING,
        )
        
        alert.acknowledge("admin")
        
        assert alert.state == AlertState.ACKNOWLEDGED
        assert alert.acknowledged_by == "admin"
        assert alert.acknowledged_at is not None
    
    def test_resolve(self):
        """Should resolve alert."""
        alert = Alert(
            alert_id="alert1",
            threshold_id="threshold1",
            plugin_id="plugin1",
            metric_name="metric",
            metric_value=15.0,
            threshold_value=10.0,
            severity=AlertSeverity.WARNING,
        )
        
        alert.resolve()
        
        assert alert.state == AlertState.RESOLVED
        assert alert.resolved_at is not None
    
    def test_silence(self):
        """Should silence alert."""
        alert = Alert(
            alert_id="alert1",
            threshold_id="threshold1",
            plugin_id="plugin1",
            metric_name="metric",
            metric_value=15.0,
            threshold_value=10.0,
            severity=AlertSeverity.WARNING,
        )
        
        alert.silence()
        
        assert alert.state == AlertState.SILENCED
    
    def test_to_dict(self):
        """Should serialize to dict."""
        alert = Alert(
            alert_id="alert1",
            threshold_id="threshold1",
            plugin_id="plugin1",
            metric_name="metric",
            metric_value=15.0,
            threshold_value=10.0,
            severity=AlertSeverity.WARNING,
            message="Test message",
        )
        
        data = alert.to_dict()
        
        assert data["alert_id"] == "alert1"
        assert data["message"] == "Test message"
        assert data["severity"] == "warning"
    
    def test_from_dict(self):
        """Should deserialize from dict."""
        data = {
            "alert_id": "alert1",
            "threshold_id": "threshold1",
            "plugin_id": "plugin1",
            "metric_name": "metric",
            "metric_value": 15.0,
            "threshold_value": 10.0,
            "severity": "error",
            "state": "acknowledged",
        }
        
        alert = Alert.from_dict(data)
        
        assert alert.alert_id == "alert1"
        assert alert.severity == AlertSeverity.ERROR
        assert alert.state == AlertState.ACKNOWLEDGED


# =============================================================================
# AlertingManager Tests
# =============================================================================

class TestAlertingManager:
    """Tests for AlertingManager class."""
    
    def test_add_threshold(self, manager, threshold):
        """Should add a threshold."""
        manager.add_threshold(threshold)
        
        assert threshold.threshold_id in manager._thresholds
    
    def test_remove_threshold(self, manager, threshold):
        """Should remove a threshold."""
        manager.add_threshold(threshold)
        
        result = manager.remove_threshold(threshold.threshold_id)
        
        assert result is True
        assert threshold.threshold_id not in manager._thresholds
    
    def test_remove_nonexistent_threshold(self, manager):
        """Should return False for nonexistent threshold."""
        result = manager.remove_threshold("nonexistent")
        
        assert result is False
    
    def test_get_threshold(self, manager, threshold):
        """Should get a threshold by ID."""
        manager.add_threshold(threshold)
        
        result = manager.get_threshold(threshold.threshold_id)
        
        assert result is threshold
    
    def test_get_nonexistent_threshold(self, manager):
        """Should return None for nonexistent threshold."""
        result = manager.get_threshold("nonexistent")
        
        assert result is None
    
    def test_list_thresholds_all(self, manager, threshold):
        """Should list all thresholds."""
        manager.add_threshold(threshold)
        
        result = manager.list_thresholds()
        
        assert len(result) == 1
        assert result[0] is threshold
    
    def test_list_thresholds_by_plugin(self, manager):
        """Should filter thresholds by plugin."""
        threshold1 = AlertThreshold(
            threshold_id="t1",
            plugin_id="plugin1",
            metric_name="metric",
            operator=ComparisonOperator.GREATER_THAN,
            threshold_value=10.0,
        )
        threshold2 = AlertThreshold(
            threshold_id="t2",
            plugin_id="plugin2",
            metric_name="metric",
            operator=ComparisonOperator.GREATER_THAN,
            threshold_value=10.0,
        )
        manager.add_threshold(threshold1)
        manager.add_threshold(threshold2)
        
        result = manager.list_thresholds(plugin_id="plugin1")
        
        assert len(result) == 1
        assert result[0].plugin_id == "plugin1"
    
    def test_list_thresholds_enabled_only(self, manager):
        """Should filter enabled thresholds only."""
        threshold1 = AlertThreshold(
            threshold_id="t1",
            plugin_id="plugin1",
            metric_name="metric",
            operator=ComparisonOperator.GREATER_THAN,
            threshold_value=10.0,
            enabled=True,
        )
        threshold2 = AlertThreshold(
            threshold_id="t2",
            plugin_id="plugin2",
            metric_name="metric",
            operator=ComparisonOperator.GREATER_THAN,
            threshold_value=10.0,
            enabled=False,
        )
        manager.add_threshold(threshold1)
        manager.add_threshold(threshold2)
        
        result = manager.list_thresholds(enabled_only=True)
        
        assert len(result) == 1
        assert result[0].enabled is True
    
    def test_enable_threshold(self, manager, threshold):
        """Should enable a threshold."""
        threshold.enabled = False
        manager.add_threshold(threshold)
        
        result = manager.enable_threshold(threshold.threshold_id)
        
        assert result is True
        assert manager._thresholds[threshold.threshold_id].enabled is True
    
    def test_disable_threshold(self, manager, threshold):
        """Should disable a threshold."""
        manager.add_threshold(threshold)
        
        result = manager.disable_threshold(threshold.threshold_id)
        
        assert result is True
        assert manager._thresholds[threshold.threshold_id].enabled is False
    
    def test_check_metric_triggers_alert(self, manager, threshold):
        """Should trigger alert when threshold crossed."""
        manager.add_threshold(threshold)
        
        alerts = manager.check_metric("test_plugin", "error_count", 15.0)
        
        assert len(alerts) == 1
        assert alerts[0].metric_value == 15.0
        assert alerts[0].state == AlertState.FIRING
    
    def test_check_metric_no_alert_below_threshold(self, manager, threshold):
        """Should not trigger alert when below threshold."""
        manager.add_threshold(threshold)
        
        alerts = manager.check_metric("test_plugin", "error_count", 5.0)
        
        assert len(alerts) == 0
    
    def test_check_metric_wildcard_plugin(self, manager):
        """Should match wildcard plugin ID."""
        threshold = AlertThreshold(
            threshold_id="test",
            plugin_id="*",  # Matches all plugins
            metric_name="error_count",
            operator=ComparisonOperator.GREATER_THAN,
            threshold_value=10.0,
            cooldown_seconds=0,
        )
        manager.add_threshold(threshold)
        
        alerts = manager.check_metric("any_plugin", "error_count", 15.0)
        
        assert len(alerts) == 1
    
    def test_check_metric_resolves_when_value_returns_normal(self, manager, threshold):
        """Should resolve alert when value returns below threshold."""
        threshold.notify_on_recovery = True
        manager.add_threshold(threshold)
        
        # First, trigger the alert
        manager.check_metric("test_plugin", "error_count", 15.0)
        assert len(manager._alerts) == 1
        
        # Now, value returns to normal
        manager.check_metric("test_plugin", "error_count", 5.0)
        
        # Alert should be resolved and moved to history
        assert len(manager._alerts) == 0
        assert len(manager._alert_history) == 1
        assert manager._alert_history[0].state == AlertState.RESOLVED
    
    def test_notification_callback_called(self, manager, threshold):
        """Should call notification callback when alert triggered."""
        callback = Mock()
        manager._notification_callback = callback
        manager.add_threshold(threshold)
        
        manager.check_metric("test_plugin", "error_count", 15.0)
        
        callback.assert_called_once()
        alert = callback.call_args[0][0]
        assert alert.metric_value == 15.0
    
    def test_acknowledge_alert(self, manager, threshold):
        """Should acknowledge an alert."""
        manager.add_threshold(threshold)
        manager.check_metric("test_plugin", "error_count", 15.0)
        alert_id = list(manager._alerts.keys())[0]
        
        result = manager.acknowledge_alert(alert_id, "admin")
        
        assert result is True
        assert manager._alerts[alert_id].state == AlertState.ACKNOWLEDGED
    
    def test_resolve_alert(self, manager, threshold):
        """Should manually resolve an alert."""
        manager.add_threshold(threshold)
        manager.check_metric("test_plugin", "error_count", 15.0)
        alert_id = list(manager._alerts.keys())[0]
        
        result = manager.resolve_alert(alert_id)
        
        assert result is True
        assert len(manager._alerts) == 0
        assert len(manager._alert_history) == 1
    
    def test_silence_alert(self, manager, threshold):
        """Should silence an alert."""
        manager.add_threshold(threshold)
        manager.check_metric("test_plugin", "error_count", 15.0)
        alert_id = list(manager._alerts.keys())[0]
        
        result = manager.silence_alert(alert_id)
        
        assert result is True
        assert manager._alerts[alert_id].state == AlertState.SILENCED
    
    def test_list_alerts_empty(self, manager):
        """Should return empty list when no alerts."""
        result = manager.list_alerts()
        
        assert result == []
    
    def test_list_alerts_with_filters(self, manager):
        """Should filter alerts by criteria."""
        threshold1 = AlertThreshold(
            threshold_id="t1",
            plugin_id="plugin1",
            metric_name="error_count",
            operator=ComparisonOperator.GREATER_THAN,
            threshold_value=10.0,
            severity=AlertSeverity.WARNING,
            cooldown_seconds=0,
        )
        threshold2 = AlertThreshold(
            threshold_id="t2",
            plugin_id="plugin2",
            metric_name="error_count",
            operator=ComparisonOperator.GREATER_THAN,
            threshold_value=10.0,
            severity=AlertSeverity.ERROR,
            cooldown_seconds=0,
        )
        manager.add_threshold(threshold1)
        manager.add_threshold(threshold2)
        
        manager.check_metric("plugin1", "error_count", 15.0)
        manager.check_metric("plugin2", "error_count", 15.0)
        
        # Filter by plugin
        result = manager.list_alerts(plugin_id="plugin1")
        assert len(result) == 1
        assert result[0].plugin_id == "plugin1"
        
        # Filter by severity
        result = manager.list_alerts(severity=AlertSeverity.ERROR)
        assert len(result) == 1
        assert result[0].severity == AlertSeverity.ERROR
    
    def test_get_stats(self, manager, threshold):
        """Should return statistics."""
        manager.add_threshold(threshold)
        manager.check_metric("test_plugin", "error_count", 15.0)
        
        stats = manager.get_stats()
        
        assert stats["alerts_triggered"] == 1
        assert stats["active_alerts"] == 1
        assert stats["thresholds_count"] == 1
    
    def test_add_default_thresholds(self, manager):
        """Should add default thresholds."""
        manager.add_default_thresholds()
        
        assert len(manager._thresholds) >= 2
        assert "high_error_rate" in manager._thresholds
        assert "critical_error_rate" in manager._thresholds


# =============================================================================
# Global Functions Tests
# =============================================================================

class TestGlobalFunctions:
    """Tests for global alerting functions."""
    
    def test_get_alerting_manager(self):
        """Should return global alerting manager."""
        manager = get_alerting_manager()
        
        assert manager is not None
        assert isinstance(manager, AlertingManager)
    
    def test_get_alerting_manager_singleton(self):
        """Should return same instance."""
        manager1 = get_alerting_manager()
        manager2 = get_alerting_manager()
        
        assert manager1 is manager2
    
    def test_init_alerting_manager(self, tmp_path):
        """Should initialize with custom settings."""
        persist_path = tmp_path / "alerting.json"
        callback = Mock()
        
        manager = init_alerting_manager(
            persist_path=persist_path,
            notification_callback=callback,
        )
        
        assert manager._persist_path == persist_path
        assert manager._notification_callback is callback
    
    def test_add_threshold_global(self):
        """Should add threshold via global function."""
        threshold = AlertThreshold(
            threshold_id="global_test",
            plugin_id="*",
            metric_name="test",
            operator=ComparisonOperator.GREATER_THAN,
            threshold_value=10.0,
        )
        
        add_threshold(threshold)
        
        manager = get_alerting_manager()
        assert "global_test" in manager._thresholds
    
    def test_remove_threshold_global(self):
        """Should remove threshold via global function."""
        threshold = AlertThreshold(
            threshold_id="to_remove",
            plugin_id="*",
            metric_name="test",
            operator=ComparisonOperator.GREATER_THAN,
            threshold_value=10.0,
        )
        add_threshold(threshold)
        
        result = remove_threshold("to_remove")
        
        assert result is True
    
    def test_check_metric_global(self):
        """Should check metric via global function."""
        # Use a unique metric name to avoid default threshold matches
        threshold = AlertThreshold(
            threshold_id="check_test",
            plugin_id="*",
            metric_name="unique_test_metric_xyz",
            operator=ComparisonOperator.GREATER_THAN,
            threshold_value=5.0,
            cooldown_seconds=0,
        )
        add_threshold(threshold)
        
        alerts = check_metric("plugin", "unique_test_metric_xyz", 10.0)
        
        assert len(alerts) == 1
    
    def test_list_alerts_global(self):
        """Should list alerts via global function."""
        # Use a unique metric name to avoid default threshold matches
        threshold = AlertThreshold(
            threshold_id="list_test",
            plugin_id="*",
            metric_name="unique_list_metric_xyz",
            operator=ComparisonOperator.GREATER_THAN,
            threshold_value=5.0,
            cooldown_seconds=0,
        )
        add_threshold(threshold)
        check_metric("plugin", "unique_list_metric_xyz", 10.0)
        
        alerts = list_alerts()
        
        assert len(alerts) >= 1


# =============================================================================
# Persistence Tests
# =============================================================================

class TestPersistence:
    """Tests for alerting state persistence."""
    
    def test_persist_and_load_thresholds(self, tmp_path):
        """Should persist and load thresholds."""
        persist_path = tmp_path / "alerting.json"
        
        # Create and save
        manager1 = AlertingManager(persist_path=persist_path)
        threshold = AlertThreshold(
            threshold_id="persist_test",
            plugin_id="plugin",
            metric_name="metric",
            operator=ComparisonOperator.GREATER_THAN,
            threshold_value=10.0,
        )
        manager1.add_threshold(threshold)
        
        # Load in new manager
        manager2 = AlertingManager(persist_path=persist_path)
        
        assert "persist_test" in manager2._thresholds
    
    def test_persist_and_load_alerts(self, tmp_path):
        """Should persist and load active alerts."""
        persist_path = tmp_path / "alerting.json"
        
        # Create and trigger alert
        manager1 = AlertingManager(persist_path=persist_path)
        threshold = AlertThreshold(
            threshold_id="alert_persist",
            plugin_id="*",
            metric_name="metric",
            operator=ComparisonOperator.GREATER_THAN,
            threshold_value=5.0,
            cooldown_seconds=0,
        )
        manager1.add_threshold(threshold)
        manager1.check_metric("plugin", "metric", 10.0)
        
        # Load in new manager
        manager2 = AlertingManager(persist_path=persist_path)
        
        assert len(manager2._alerts) == 1
