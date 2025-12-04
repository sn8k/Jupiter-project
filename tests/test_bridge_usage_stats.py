"""
Tests for the Plugin Usage Statistics module.

Tests cover:
- ExecutionRecord creation and serialization
- MethodStats tracking and calculations
- PluginStats aggregation
- UsageStatsManager functionality
- TimeFrame aggregations
- ExecutionTimer context manager
- Persistence (save/load)
- Global functions
"""

import pytest
import time
import json
import tempfile
import threading
from pathlib import Path
from unittest.mock import Mock, patch

from jupiter.core.bridge.usage_stats import (
    # Enums
    TimeFrame,
    ExecutionStatus,
    # Dataclasses
    ExecutionRecord,
    MethodStats,
    PluginStats,
    TimeframeStats,
    UsageStatsConfig,
    # Classes
    ExecutionTimer,
    UsageStatsManager,
    # Global functions
    get_usage_stats_manager,
    init_usage_stats_manager,
    reset_usage_stats_manager,
    record_execution,
    time_execution,
    get_plugin_stats,
    get_stats_summary,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def manager():
    """Create a fresh manager for each test."""
    return UsageStatsManager()


@pytest.fixture
def config():
    """Create a test configuration."""
    return UsageStatsConfig(
        enabled=True,
        persist_to_disk=False,
        max_records_in_memory=100,
        max_history_per_method=50
    )


@pytest.fixture
def manager_with_config(config):
    """Create a manager with custom config."""
    return UsageStatsManager(config)


@pytest.fixture(autouse=True)
def reset_global_manager():
    """Reset global manager before each test."""
    reset_usage_stats_manager()
    yield
    reset_usage_stats_manager()


# ============================================================================
# ExecutionStatus Tests
# ============================================================================

class TestExecutionStatus:
    """Tests for ExecutionStatus enum."""
    
    def test_status_values(self):
        """Test all status values exist."""
        assert ExecutionStatus.SUCCESS.value == "success"
        assert ExecutionStatus.FAILURE.value == "failure"
        assert ExecutionStatus.TIMEOUT.value == "timeout"
        assert ExecutionStatus.CANCELLED.value == "cancelled"
    
    def test_status_from_string(self):
        """Test creating status from string."""
        assert ExecutionStatus("success") == ExecutionStatus.SUCCESS
        assert ExecutionStatus("failure") == ExecutionStatus.FAILURE


# ============================================================================
# TimeFrame Tests
# ============================================================================

class TestTimeFrame:
    """Tests for TimeFrame enum."""
    
    def test_timeframe_values(self):
        """Test all timeframe values exist."""
        assert TimeFrame.HOUR.value == "hour"
        assert TimeFrame.DAY.value == "day"
        assert TimeFrame.WEEK.value == "week"
        assert TimeFrame.MONTH.value == "month"
        assert TimeFrame.ALL_TIME.value == "all_time"


# ============================================================================
# ExecutionRecord Tests
# ============================================================================

class TestExecutionRecord:
    """Tests for ExecutionRecord dataclass."""
    
    def test_create_record(self):
        """Test basic record creation."""
        record = ExecutionRecord(
            plugin_id="test-plugin",
            method="process",
            started_at=time.time(),
            duration_ms=100.5,
            status=ExecutionStatus.SUCCESS
        )
        assert record.plugin_id == "test-plugin"
        assert record.method == "process"
        assert record.duration_ms == 100.5
        assert record.status == ExecutionStatus.SUCCESS
        assert record.error_type is None
    
    def test_record_with_error(self):
        """Test record with error information."""
        record = ExecutionRecord(
            plugin_id="test-plugin",
            method="process",
            started_at=time.time(),
            duration_ms=50.0,
            status=ExecutionStatus.FAILURE,
            error_type="ValueError"
        )
        assert record.status == ExecutionStatus.FAILURE
        assert record.error_type == "ValueError"
    
    def test_record_to_dict(self):
        """Test converting record to dictionary."""
        started = time.time()
        record = ExecutionRecord(
            plugin_id="test-plugin",
            method="process",
            started_at=started,
            duration_ms=100.0,
            status=ExecutionStatus.SUCCESS,
            metadata={"key": "value"}
        )
        data = record.to_dict()
        assert data["plugin_id"] == "test-plugin"
        assert data["method"] == "process"
        assert data["started_at"] == started
        assert data["duration_ms"] == 100.0
        assert data["status"] == "success"
        assert data["metadata"] == {"key": "value"}
    
    def test_record_from_dict(self):
        """Test creating record from dictionary."""
        data = {
            "plugin_id": "test-plugin",
            "method": "process",
            "started_at": 1234567890.0,
            "duration_ms": 75.0,
            "status": "failure",
            "error_type": "RuntimeError",
            "metadata": {"context": "test"}
        }
        record = ExecutionRecord.from_dict(data)
        assert record.plugin_id == "test-plugin"
        assert record.status == ExecutionStatus.FAILURE
        assert record.error_type == "RuntimeError"
    
    def test_record_with_memory_delta(self):
        """Test record with memory tracking."""
        record = ExecutionRecord(
            plugin_id="test-plugin",
            method="process",
            started_at=time.time(),
            duration_ms=100.0,
            status=ExecutionStatus.SUCCESS,
            memory_delta_kb=512.5
        )
        assert record.memory_delta_kb == 512.5


# ============================================================================
# MethodStats Tests
# ============================================================================

class TestMethodStats:
    """Tests for MethodStats dataclass."""
    
    def test_create_method_stats(self):
        """Test basic method stats creation."""
        stats = MethodStats(method="process")
        assert stats.method == "process"
        assert stats.execution_count == 0
        assert stats.success_count == 0
        assert stats.average_duration_ms == 0.0
    
    def test_record_execution(self):
        """Test recording an execution."""
        stats = MethodStats(method="process")
        stats.record_execution(100.0, ExecutionStatus.SUCCESS)
        
        assert stats.execution_count == 1
        assert stats.success_count == 1
        assert stats.total_duration_ms == 100.0
        assert stats.average_duration_ms == 100.0
        assert stats.min_duration_ms == 100.0
        assert stats.max_duration_ms == 100.0
    
    def test_record_multiple_executions(self):
        """Test recording multiple executions."""
        stats = MethodStats(method="process")
        stats.record_execution(100.0, ExecutionStatus.SUCCESS)
        stats.record_execution(200.0, ExecutionStatus.SUCCESS)
        stats.record_execution(150.0, ExecutionStatus.FAILURE, "TestError")
        
        assert stats.execution_count == 3
        assert stats.success_count == 2
        assert stats.failure_count == 1
        assert stats.average_duration_ms == 150.0
        assert stats.min_duration_ms == 100.0
        assert stats.max_duration_ms == 200.0
    
    def test_success_rate(self):
        """Test success rate calculation."""
        stats = MethodStats(method="process")
        stats.record_execution(100.0, ExecutionStatus.SUCCESS)
        stats.record_execution(100.0, ExecutionStatus.SUCCESS)
        stats.record_execution(100.0, ExecutionStatus.FAILURE)
        stats.record_execution(100.0, ExecutionStatus.SUCCESS)
        
        assert stats.success_rate == 75.0
    
    def test_error_types_tracking(self):
        """Test tracking of error types."""
        stats = MethodStats(method="process")
        stats.record_execution(100.0, ExecutionStatus.FAILURE, "ValueError")
        stats.record_execution(100.0, ExecutionStatus.FAILURE, "TypeError")
        stats.record_execution(100.0, ExecutionStatus.FAILURE, "ValueError")
        
        assert stats.error_types["ValueError"] == 2
        assert stats.error_types["TypeError"] == 1
    
    def test_timeout_and_cancelled_tracking(self):
        """Test tracking timeouts and cancellations."""
        stats = MethodStats(method="process")
        stats.record_execution(100.0, ExecutionStatus.TIMEOUT)
        stats.record_execution(100.0, ExecutionStatus.CANCELLED)
        stats.record_execution(100.0, ExecutionStatus.TIMEOUT)
        
        assert stats.timeout_count == 2
        assert stats.cancelled_count == 1
    
    def test_percentile_calculation(self):
        """Test percentile calculations."""
        stats = MethodStats(method="process")
        for i in range(100):
            stats.record_execution(float(i + 1), ExecutionStatus.SUCCESS)
        
        assert stats.median_duration_ms is not None
        assert stats.p95_duration_ms is not None
        assert stats.p95_duration_ms > stats.median_duration_ms
    
    def test_history_size_limit(self):
        """Test that history is limited."""
        stats = MethodStats(method="process")
        for i in range(200):
            stats.record_execution(float(i), ExecutionStatus.SUCCESS, max_history_size=50)
        
        assert len(stats.durations_history) == 50
    
    def test_method_stats_to_dict(self):
        """Test conversion to dictionary."""
        stats = MethodStats(method="process")
        stats.record_execution(100.0, ExecutionStatus.SUCCESS)
        
        data = stats.to_dict()
        assert data["method"] == "process"
        assert data["execution_count"] == 1
        assert data["average_duration_ms"] == 100.0
    
    def test_method_stats_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "method": "process",
            "execution_count": 5,
            "success_count": 4,
            "failure_count": 1,
            "timeout_count": 0,
            "cancelled_count": 0,
            "total_duration_ms": 500.0,
            "min_duration_ms": 50.0,
            "max_duration_ms": 150.0,
            "error_types": {"TestError": 1}
        }
        stats = MethodStats.from_dict(data)
        assert stats.execution_count == 5
        assert stats.average_duration_ms == 100.0


# ============================================================================
# PluginStats Tests
# ============================================================================

class TestPluginStats:
    """Tests for PluginStats dataclass."""
    
    def test_create_plugin_stats(self):
        """Test basic plugin stats creation."""
        stats = PluginStats(plugin_id="test-plugin")
        assert stats.plugin_id == "test-plugin"
        assert stats.total_executions == 0
        assert len(stats.methods) == 0
    
    def test_record_execution(self):
        """Test recording an execution."""
        stats = PluginStats(plugin_id="test-plugin")
        stats.record_execution("process", 100.0, ExecutionStatus.SUCCESS)
        
        assert stats.total_executions == 1
        assert "process" in stats.methods
        assert stats.first_execution is not None
    
    def test_multiple_methods(self):
        """Test tracking multiple methods."""
        stats = PluginStats(plugin_id="test-plugin")
        stats.record_execution("process", 100.0, ExecutionStatus.SUCCESS)
        stats.record_execution("validate", 50.0, ExecutionStatus.SUCCESS)
        stats.record_execution("process", 110.0, ExecutionStatus.SUCCESS)
        
        assert stats.total_executions == 3
        assert len(stats.methods) == 2
        assert stats.methods["process"].execution_count == 2
        assert stats.methods["validate"].execution_count == 1
    
    def test_overall_success_rate(self):
        """Test overall success rate."""
        stats = PluginStats(plugin_id="test-plugin")
        stats.record_execution("m1", 100.0, ExecutionStatus.SUCCESS)
        stats.record_execution("m1", 100.0, ExecutionStatus.FAILURE)
        stats.record_execution("m2", 100.0, ExecutionStatus.SUCCESS)
        stats.record_execution("m2", 100.0, ExecutionStatus.SUCCESS)
        
        assert stats.overall_success_rate == 75.0
    
    def test_most_used_method(self):
        """Test finding most used method."""
        stats = PluginStats(plugin_id="test-plugin")
        stats.record_execution("rarely_used", 100.0, ExecutionStatus.SUCCESS)
        stats.record_execution("often_used", 100.0, ExecutionStatus.SUCCESS)
        stats.record_execution("often_used", 100.0, ExecutionStatus.SUCCESS)
        stats.record_execution("often_used", 100.0, ExecutionStatus.SUCCESS)
        
        assert stats.most_used_method == "often_used"
    
    def test_slowest_method(self):
        """Test finding slowest method."""
        stats = PluginStats(plugin_id="test-plugin")
        stats.record_execution("fast", 10.0, ExecutionStatus.SUCCESS)
        stats.record_execution("slow", 1000.0, ExecutionStatus.SUCCESS)
        stats.record_execution("medium", 100.0, ExecutionStatus.SUCCESS)
        
        assert stats.slowest_method == "slow"
    
    def test_load_unload_tracking(self):
        """Test tracking plugin load/unload."""
        stats = PluginStats(plugin_id="test-plugin")
        stats.record_load()
        
        assert stats.load_count == 1
        assert stats.is_currently_enabled is True
        
        time.sleep(0.01)
        stats.record_unload()
        
        assert stats.unload_count == 1
        assert stats.is_currently_enabled is False
        assert stats.enabled_time_total_seconds > 0
    
    def test_tags(self):
        """Test plugin tagging."""
        stats = PluginStats(plugin_id="test-plugin")
        stats.tags.add("analytics")
        stats.tags.add("experimental")
        
        assert "analytics" in stats.tags
        assert "experimental" in stats.tags
    
    def test_plugin_stats_to_dict(self):
        """Test conversion to dictionary."""
        stats = PluginStats(plugin_id="test-plugin")
        stats.record_execution("process", 100.0, ExecutionStatus.SUCCESS)
        stats.tags.add("test")
        
        data = stats.to_dict()
        assert data["plugin_id"] == "test-plugin"
        assert data["total_executions"] == 1
        assert "test" in data["tags"]
    
    def test_plugin_stats_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "plugin_id": "test-plugin",
            "first_execution": 1234567890.0,
            "methods": {},
            "enabled_time_total_seconds": 3600.0,
            "load_count": 5,
            "unload_count": 4,
            "error_count_total": 2,
            "tags": ["analytics"]
        }
        stats = PluginStats.from_dict(data)
        assert stats.plugin_id == "test-plugin"
        assert stats.load_count == 5
        assert "analytics" in stats.tags


# ============================================================================
# TimeframeStats Tests
# ============================================================================

class TestTimeframeStats:
    """Tests for TimeframeStats dataclass."""
    
    def test_create_timeframe_stats(self):
        """Test basic timeframe stats creation."""
        stats = TimeframeStats(
            timeframe=TimeFrame.HOUR,
            start_time=time.time() - 3600,
            end_time=time.time()
        )
        assert stats.timeframe == TimeFrame.HOUR
        assert stats.total_executions == 0
    
    def test_timeframe_success_rate(self):
        """Test success rate calculation."""
        stats = TimeframeStats(
            timeframe=TimeFrame.DAY,
            start_time=time.time() - 86400,
            end_time=time.time()
        )
        stats.total_executions = 100
        stats.total_success = 90
        
        assert stats.success_rate == 90.0
    
    def test_timeframe_to_dict(self):
        """Test conversion to dictionary."""
        stats = TimeframeStats(
            timeframe=TimeFrame.WEEK,
            start_time=100.0,
            end_time=200.0
        )
        stats.total_executions = 50
        stats.unique_plugins.add("plugin1")
        
        data = stats.to_dict()
        assert data["timeframe"] == "week"
        assert data["unique_plugins_count"] == 1


# ============================================================================
# UsageStatsConfig Tests
# ============================================================================

class TestUsageStatsConfig:
    """Tests for UsageStatsConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = UsageStatsConfig()
        assert config.enabled is True
        assert config.persist_to_disk is True
        assert config.max_records_in_memory == 10000
        assert config.retention_days == 30
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = UsageStatsConfig(
            enabled=False,
            max_records_in_memory=500,
            retention_days=7
        )
        assert config.enabled is False
        assert config.max_records_in_memory == 500
        assert config.retention_days == 7
    
    def test_config_to_dict(self):
        """Test conversion to dictionary."""
        config = UsageStatsConfig(enabled=True, retention_days=14)
        data = config.to_dict()
        assert data["enabled"] is True
        assert data["retention_days"] == 14
    
    def test_config_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "enabled": False,
            "persist_to_disk": True,
            "max_records_in_memory": 5000,
            "retention_days": 60
        }
        config = UsageStatsConfig.from_dict(data)
        assert config.enabled is False
        assert config.max_records_in_memory == 5000


# ============================================================================
# ExecutionTimer Tests
# ============================================================================

class TestExecutionTimer:
    """Tests for ExecutionTimer context manager."""
    
    def test_basic_timing(self, manager):
        """Test basic execution timing."""
        with manager.time_execution("test-plugin", "process"):
            time.sleep(0.01)
        
        stats = manager.get_plugin_stats("test-plugin")
        assert stats is not None
        assert stats.total_executions == 1
        assert stats.methods["process"].average_duration_ms >= 10
    
    def test_timing_with_exception(self, manager):
        """Test timing when exception occurs."""
        with pytest.raises(ValueError):
            with manager.time_execution("test-plugin", "process"):
                raise ValueError("Test error")
        
        stats = manager.get_plugin_stats("test-plugin")
        assert stats is not None
        assert stats.total_failures == 1
        method_stats = stats.methods["process"]
        assert method_stats.failure_count == 1
        assert "ValueError" in method_stats.error_types
    
    def test_mark_timeout(self, manager):
        """Test marking execution as timeout."""
        with manager.time_execution("test-plugin", "process") as timer:
            timer.mark_timeout()
        
        stats = manager.get_plugin_stats("test-plugin")
        method_stats = stats.methods["process"]
        assert method_stats.timeout_count == 1
    
    def test_mark_cancelled(self, manager):
        """Test marking execution as cancelled."""
        with manager.time_execution("test-plugin", "process") as timer:
            timer.mark_cancelled()
        
        stats = manager.get_plugin_stats("test-plugin")
        method_stats = stats.methods["process"]
        assert method_stats.cancelled_count == 1
    
    def test_mark_failure(self, manager):
        """Test marking execution as failed."""
        with manager.time_execution("test-plugin", "process") as timer:
            timer.mark_failure("CustomError")
        
        stats = manager.get_plugin_stats("test-plugin")
        method_stats = stats.methods["process"]
        assert method_stats.failure_count == 1
    
    def test_timing_with_metadata(self, manager):
        """Test timing with metadata."""
        with manager.time_execution("test-plugin", "process", {"context": "test"}):
            pass
        
        records = manager.get_recent_records(count=1)
        assert len(records) == 1
        assert records[0].metadata["context"] == "test"


# ============================================================================
# UsageStatsManager Tests
# ============================================================================

class TestUsageStatsManager:
    """Tests for UsageStatsManager."""
    
    def test_create_manager(self):
        """Test manager creation."""
        manager = UsageStatsManager()
        assert manager is not None
        assert manager.config.enabled is True
    
    def test_create_with_config(self, config):
        """Test manager creation with config."""
        manager = UsageStatsManager(config)
        assert manager.config.enabled is True
        assert manager.config.max_records_in_memory == 100
    
    def test_record_execution(self, manager):
        """Test recording an execution."""
        record = manager.record_execution(
            plugin_id="test-plugin",
            method="process",
            duration_ms=100.0,
            status=ExecutionStatus.SUCCESS
        )
        
        assert record is not None
        assert record.plugin_id == "test-plugin"
        
        stats = manager.get_plugin_stats("test-plugin")
        assert stats.total_executions == 1
    
    def test_record_disabled(self, config):
        """Test recording when disabled."""
        config.enabled = False
        manager = UsageStatsManager(config)
        
        record = manager.record_execution(
            plugin_id="test-plugin",
            method="process",
            duration_ms=100.0
        )
        
        assert record is not None
        # Stats should not be updated
        stats = manager.get_plugin_stats("test-plugin")
        assert stats is None
    
    def test_get_all_plugin_stats(self, manager):
        """Test getting all plugin stats."""
        manager.record_execution("plugin1", "m1", 100.0)
        manager.record_execution("plugin2", "m1", 100.0)
        
        all_stats = manager.get_all_plugin_stats()
        assert len(all_stats) == 2
        assert "plugin1" in all_stats
        assert "plugin2" in all_stats
    
    def test_get_method_stats(self, manager):
        """Test getting method stats."""
        manager.record_execution("test-plugin", "process", 100.0)
        
        method_stats = manager.get_method_stats("test-plugin", "process")
        assert method_stats is not None
        assert method_stats.execution_count == 1
    
    def test_record_plugin_load_unload(self, manager):
        """Test recording plugin load/unload."""
        manager.record_plugin_load("test-plugin")
        stats = manager.get_plugin_stats("test-plugin")
        assert stats.load_count == 1
        assert stats.is_currently_enabled is True
        
        manager.record_plugin_unload("test-plugin")
        assert stats.unload_count == 1
        assert stats.is_currently_enabled is False
    
    def test_plugin_tags(self, manager):
        """Test plugin tagging."""
        manager.add_plugin_tag("test-plugin", "analytics")
        manager.add_plugin_tag("test-plugin", "experimental")
        manager.add_plugin_tag("other-plugin", "analytics")
        
        analytics_plugins = manager.get_plugins_by_tag("analytics")
        assert "test-plugin" in analytics_plugins
        assert "other-plugin" in analytics_plugins
        
        manager.remove_plugin_tag("test-plugin", "analytics")
        analytics_plugins = manager.get_plugins_by_tag("analytics")
        assert "test-plugin" not in analytics_plugins
    
    def test_timeframe_stats(self, manager):
        """Test getting timeframe statistics."""
        manager.record_execution("plugin1", "m1", 100.0)
        manager.record_execution("plugin2", "m2", 200.0)
        
        hour_stats = manager.get_timeframe_stats(TimeFrame.HOUR)
        assert hour_stats.total_executions == 2
        assert len(hour_stats.unique_plugins) == 2
    
    def test_recent_records(self, manager):
        """Test getting recent records."""
        for i in range(10):
            manager.record_execution("plugin1", "process", float(i * 10))
        
        records = manager.get_recent_records(count=5)
        assert len(records) == 5
    
    def test_recent_records_filtered(self, manager):
        """Test filtering recent records."""
        manager.record_execution("plugin1", "process", 100.0)
        manager.record_execution("plugin2", "process", 100.0)
        manager.record_execution("plugin1", "validate", 100.0)
        
        records = manager.get_recent_records(plugin_id="plugin1")
        assert len(records) == 2
        
        records = manager.get_recent_records(method="validate")
        assert len(records) == 1
    
    def test_top_plugins_by_executions(self, manager):
        """Test getting top plugins by executions."""
        for i in range(10):
            manager.record_execution("busy-plugin", "m1", 100.0)
        for i in range(5):
            manager.record_execution("moderate-plugin", "m1", 100.0)
        manager.record_execution("quiet-plugin", "m1", 100.0)
        
        top = manager.get_top_plugins(metric="executions", limit=2)
        assert len(top) == 2
        assert top[0]["plugin_id"] == "busy-plugin"
        assert top[1]["plugin_id"] == "moderate-plugin"
    
    def test_top_plugins_by_errors(self, manager):
        """Test getting top plugins by errors."""
        manager.record_execution("error-plugin", "m1", 100.0, ExecutionStatus.FAILURE)
        manager.record_execution("error-plugin", "m1", 100.0, ExecutionStatus.FAILURE)
        manager.record_execution("ok-plugin", "m1", 100.0, ExecutionStatus.SUCCESS)
        
        top = manager.get_top_plugins(metric="errors", limit=2)
        assert top[0]["plugin_id"] == "error-plugin"
    
    def test_slowest_methods(self, manager):
        """Test getting slowest methods."""
        manager.record_execution("plugin1", "fast", 10.0)
        manager.record_execution("plugin1", "slow", 1000.0)
        manager.record_execution("plugin2", "very_slow", 5000.0)
        
        slowest = manager.get_slowest_methods(limit=2)
        assert len(slowest) == 2
        assert slowest[0]["method"] == "very_slow"
        assert slowest[1]["method"] == "slow"
    
    def test_error_summary(self, manager):
        """Test error summary."""
        manager.record_execution("p1", "m1", 100.0, ExecutionStatus.FAILURE, "ValueError")
        manager.record_execution("p1", "m1", 100.0, ExecutionStatus.FAILURE, "ValueError")
        manager.record_execution("p2", "m1", 100.0, ExecutionStatus.FAILURE, "TypeError")
        manager.record_execution("p2", "m1", 100.0, ExecutionStatus.SUCCESS)
        
        summary = manager.get_error_summary()
        assert summary["total_errors"] == 3
        assert summary["unique_error_types"] == 2
        assert summary["plugins_with_errors"] == 2
        assert summary["most_common_error"] == "ValueError"
    
    def test_summary(self, manager):
        """Test overall summary."""
        manager.record_execution("plugin1", "m1", 100.0)
        manager.record_execution("plugin2", "m1", 200.0)
        
        summary = manager.get_summary()
        assert summary["total_plugins_tracked"] == 2
        assert summary["total_executions"] == 2
        assert summary["records_in_memory"] == 2
    
    def test_callbacks(self, manager):
        """Test execution callbacks."""
        callback_data = []
        
        def callback(record):
            callback_data.append(record)
        
        manager.register_callback(callback)
        manager.record_execution("plugin1", "m1", 100.0)
        
        assert len(callback_data) == 1
        assert callback_data[0].plugin_id == "plugin1"
        
        manager.unregister_callback(callback)
        manager.record_execution("plugin1", "m1", 100.0)
        
        assert len(callback_data) == 1  # No new callback
    
    def test_clear_all_stats(self, manager):
        """Test clearing all stats."""
        manager.record_execution("plugin1", "m1", 100.0)
        manager.record_execution("plugin2", "m1", 100.0)
        
        manager.clear_all_stats()
        
        assert len(manager.get_all_plugin_stats()) == 0
        assert len(manager.get_recent_records()) == 0
    
    def test_clear_plugin_stats(self, manager):
        """Test clearing specific plugin stats."""
        manager.record_execution("plugin1", "m1", 100.0)
        manager.record_execution("plugin2", "m1", 100.0)
        
        result = manager.clear_plugin_stats("plugin1")
        assert result is True
        
        assert manager.get_plugin_stats("plugin1") is None
        assert manager.get_plugin_stats("plugin2") is not None
    
    def test_cleanup_old_records(self, manager):
        """Test cleaning up old records."""
        # Add records with old timestamps
        old_record = ExecutionRecord(
            plugin_id="old-plugin",
            method="m1",
            started_at=time.time() - (31 * 86400),  # 31 days ago
            duration_ms=100.0,
            status=ExecutionStatus.SUCCESS
        )
        manager._execution_records.append(old_record)
        
        manager.record_execution("new-plugin", "m1", 100.0)
        
        removed = manager.cleanup_old_records(retention_days=30)
        assert removed == 1
    
    def test_max_records_limit(self, config):
        """Test max records limit."""
        config.max_records_in_memory = 10
        manager = UsageStatsManager(config)
        
        for i in range(20):
            manager.record_execution("plugin1", "m1", float(i))
        
        records = manager.get_recent_records(count=100)
        assert len(records) == 10
    
    def test_export_to_json(self, manager):
        """Test exporting to JSON."""
        manager.record_execution("plugin1", "m1", 100.0)
        
        json_str = manager.export_to_json()
        data = json.loads(json_str)
        
        assert "summary" in data
        assert "plugins" in data
        assert "plugin1" in data["plugins"]
    
    def test_get_status(self, manager):
        """Test getting manager status."""
        manager.record_execution("plugin1", "m1", 100.0)
        
        status = manager.get_status()
        assert status["enabled"] is True
        assert status["plugins_tracked"] == 1
        assert status["records_in_memory"] == 1
    
    def test_needs_save(self, manager):
        """Test needs_save flag."""
        assert manager.needs_save() is False
        
        manager.record_execution("plugin1", "m1", 100.0)
        assert manager.needs_save() is True


# ============================================================================
# Persistence Tests
# ============================================================================

class TestPersistence:
    """Tests for save/load functionality."""
    
    def test_save_to_disk(self):
        """Test saving stats to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "stats.json"
            config = UsageStatsConfig(
                persist_to_disk=True,
                persistence_path=path
            )
            manager = UsageStatsManager(config)
            
            manager.record_execution("plugin1", "m1", 100.0)
            manager.record_execution("plugin1", "m2", 200.0)
            
            result = manager.save_to_disk()
            assert result is True
            assert path.exists()
    
    def test_load_from_disk(self):
        """Test loading stats from disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "stats.json"
            
            # Create and save first manager
            config1 = UsageStatsConfig(
                persist_to_disk=True,
                persistence_path=path
            )
            manager1 = UsageStatsManager(config1)
            manager1.record_execution("plugin1", "m1", 100.0)
            manager1.save_to_disk()
            
            # Create new manager that loads from disk
            config2 = UsageStatsConfig(
                persist_to_disk=True,
                persistence_path=path
            )
            manager2 = UsageStatsManager(config2)
            
            stats = manager2.get_plugin_stats("plugin1")
            assert stats is not None
            assert stats.total_executions == 1
    
    def test_save_without_path(self):
        """Test saving without path configured."""
        manager = UsageStatsManager()
        result = manager.save_to_disk()
        assert result is False


# ============================================================================
# Thread Safety Tests
# ============================================================================

class TestThreadSafety:
    """Tests for thread safety."""
    
    def test_concurrent_recording(self, manager):
        """Test concurrent execution recording."""
        results = []
        
        def record_many(plugin_id):
            for i in range(100):
                manager.record_execution(plugin_id, "process", float(i))
            results.append(plugin_id)
        
        threads = [
            threading.Thread(target=record_many, args=(f"plugin{i}",))
            for i in range(5)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(results) == 5
        summary = manager.get_summary()
        assert summary["total_executions"] == 500
    
    def test_concurrent_read_write(self, manager):
        """Test concurrent reads and writes."""
        stop_event = threading.Event()
        errors = []
        
        def writer():
            while not stop_event.is_set():
                try:
                    manager.record_execution("plugin1", "m1", 100.0)
                except Exception as e:
                    errors.append(e)
        
        def reader():
            while not stop_event.is_set():
                try:
                    manager.get_summary()
                    manager.get_plugin_stats("plugin1")
                except Exception as e:
                    errors.append(e)
        
        writer_thread = threading.Thread(target=writer)
        reader_thread = threading.Thread(target=reader)
        
        writer_thread.start()
        reader_thread.start()
        
        time.sleep(0.1)
        stop_event.set()
        
        writer_thread.join()
        reader_thread.join()
        
        assert len(errors) == 0


# ============================================================================
# Global Functions Tests
# ============================================================================

class TestGlobalFunctions:
    """Tests for global convenience functions."""
    
    def test_get_usage_stats_manager(self):
        """Test getting global manager."""
        manager = get_usage_stats_manager()
        assert manager is not None
        
        # Same instance
        manager2 = get_usage_stats_manager()
        assert manager is manager2
    
    def test_init_usage_stats_manager(self):
        """Test initializing global manager."""
        config = UsageStatsConfig(enabled=True, max_records_in_memory=50)
        manager = init_usage_stats_manager(config)
        
        assert manager.config.max_records_in_memory == 50
        
        # Should be the global instance
        assert get_usage_stats_manager() is manager
    
    def test_reset_usage_stats_manager(self):
        """Test resetting global manager."""
        manager1 = get_usage_stats_manager()
        reset_usage_stats_manager()
        manager2 = get_usage_stats_manager()
        
        assert manager1 is not manager2
    
    def test_record_execution_global(self):
        """Test global record_execution."""
        record = record_execution("test-plugin", "process", 100.0)
        assert record.plugin_id == "test-plugin"
        
        stats = get_plugin_stats("test-plugin")
        assert stats is not None
        assert stats.total_executions == 1
    
    def test_time_execution_global(self):
        """Test global time_execution."""
        with time_execution("test-plugin", "process"):
            time.sleep(0.01)
        
        stats = get_plugin_stats("test-plugin")
        assert stats is not None
        assert stats.total_executions == 1
    
    def test_get_stats_summary_global(self):
        """Test global get_stats_summary."""
        record_execution("test-plugin", "process", 100.0)
        
        summary = get_stats_summary()
        assert summary["total_executions"] == 1


# ============================================================================
# Error Anonymization Tests
# ============================================================================

class TestErrorAnonymization:
    """Tests for error anonymization."""
    
    def test_anonymize_error_type(self):
        """Test error type anonymization."""
        config = UsageStatsConfig(anonymize_errors=True)
        manager = UsageStatsManager(config)
        
        manager.record_execution(
            "plugin1", "m1", 100.0,
            status=ExecutionStatus.FAILURE,
            error_type="ValueError: Invalid input data"
        )
        
        stats = manager.get_plugin_stats("plugin1")
        assert stats is not None
        method_stats = stats.methods["m1"]
        
        # Should be anonymized to just the class name
        assert "Invalid input data" not in str(method_stats.error_types)
    
    def test_no_anonymization(self):
        """Test with anonymization disabled."""
        config = UsageStatsConfig(anonymize_errors=False)
        manager = UsageStatsManager(config)
        
        manager.record_execution(
            "plugin1", "m1", 100.0,
            status=ExecutionStatus.FAILURE,
            error_type="ValueError: Invalid input data"
        )
        
        records = manager.get_recent_records()
        assert records[0].error_type == "ValueError: Invalid input data"


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_empty_plugin_id(self, manager):
        """Test with empty plugin ID."""
        manager.record_execution("", "process", 100.0)
        stats = manager.get_plugin_stats("")
        assert stats is not None
    
    def test_empty_method(self, manager):
        """Test with empty method name."""
        manager.record_execution("plugin1", "", 100.0)
        stats = manager.get_plugin_stats("plugin1")
        assert "" in stats.methods
    
    def test_zero_duration(self, manager):
        """Test with zero duration."""
        manager.record_execution("plugin1", "m1", 0.0)
        stats = manager.get_plugin_stats("plugin1")
        assert stats.average_duration_ms == 0.0
    
    def test_negative_duration(self, manager):
        """Test with negative duration (should still record)."""
        manager.record_execution("plugin1", "m1", -100.0)
        stats = manager.get_plugin_stats("plugin1")
        assert stats.total_duration_ms == -100.0
    
    def test_very_large_duration(self, manager):
        """Test with very large duration."""
        manager.record_execution("plugin1", "m1", 1e12)
        stats = manager.get_plugin_stats("plugin1")
        assert stats.total_duration_ms == 1e12
    
    def test_unicode_plugin_id(self, manager):
        """Test with unicode plugin ID."""
        manager.record_execution("플러그인-日本語", "process", 100.0)
        stats = manager.get_plugin_stats("플러그인-日本語")
        assert stats is not None
    
    def test_special_characters_method(self, manager):
        """Test with special characters in method."""
        manager.record_execution("plugin1", "process/data@v2", 100.0)
        stats = manager.get_method_stats("plugin1", "process/data@v2")
        assert stats is not None
    
    def test_get_nonexistent_plugin(self, manager):
        """Test getting stats for nonexistent plugin."""
        stats = manager.get_plugin_stats("nonexistent")
        assert stats is None
    
    def test_get_nonexistent_method(self, manager):
        """Test getting stats for nonexistent method."""
        manager.record_execution("plugin1", "m1", 100.0)
        stats = manager.get_method_stats("plugin1", "nonexistent")
        assert stats is None
    
    def test_clear_nonexistent_plugin(self, manager):
        """Test clearing nonexistent plugin."""
        result = manager.clear_plugin_stats("nonexistent")
        assert result is False
    
    def test_top_plugins_empty(self, manager):
        """Test top plugins when empty."""
        top = manager.get_top_plugins()
        assert top == []
    
    def test_slowest_methods_empty(self, manager):
        """Test slowest methods when empty."""
        slowest = manager.get_slowest_methods()
        assert slowest == []
    
    def test_error_summary_empty(self, manager):
        """Test error summary when no errors."""
        manager.record_execution("plugin1", "m1", 100.0, ExecutionStatus.SUCCESS)
        
        summary = manager.get_error_summary()
        assert summary["total_errors"] == 0
        assert summary["most_common_error"] is None
