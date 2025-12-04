"""Tests for Bridge Metrics Collection System.

Version: 0.1.0
"""

import pytest
import time
from unittest.mock import MagicMock, patch

from jupiter.core.bridge.metrics import (
    MetricsCollector,
    MetricType,
    MetricPoint,
    MetricSummary,
    TimingContext,
    get_metrics_collector,
    init_metrics_collector,
    record_metric,
    increment_counter,
    record_timing,
    timed,
)


class TestMetricPoint:
    """Test MetricPoint dataclass."""
    
    def test_create_metric_point(self):
        """Test creating a MetricPoint."""
        point = MetricPoint(
            name="test.metric",
            value=42,
            labels={"env": "test"},
        )
        
        assert point.name == "test.metric"
        assert point.value == 42
        assert point.labels == {"env": "test"}
        assert point.metric_type == MetricType.GAUGE
    
    def test_to_dict(self):
        """Test serializing MetricPoint to dict."""
        point = MetricPoint(
            name="test.metric",
            value=100,
            metric_type=MetricType.COUNTER,
        )
        
        d = point.to_dict()
        
        assert d["name"] == "test.metric"
        assert d["value"] == 100
        assert d["type"] == "counter"
        assert "timestamp" in d


class TestMetricSummary:
    """Test MetricSummary dataclass."""
    
    def test_create_summary(self):
        """Test creating a MetricSummary."""
        summary = MetricSummary(
            name="test.metric",
            current=10,
            min_value=5,
            max_value=15,
            avg_value=10.0,
            count=3,
        )
        
        assert summary.current == 10
        assert summary.min_value == 5
        assert summary.max_value == 15
        assert summary.avg_value == 10.0
        assert summary.count == 3
    
    def test_to_dict(self):
        """Test serializing MetricSummary to dict."""
        summary = MetricSummary(
            name="test.metric",
            current=10,
            min_value=5,
            max_value=15,
            avg_value=10.0,
            count=3,
            labels={"key": "value"},
        )
        
        d = summary.to_dict()
        
        assert d["name"] == "test.metric"
        assert d["current"] == 10
        assert d["min"] == 5
        assert d["max"] == 15
        assert d["avg"] == 10.0
        assert d["count"] == 3
        assert d["labels"] == {"key": "value"}


class TestMetricsCollector:
    """Test MetricsCollector class."""
    
    def test_init(self):
        """Test collector initialization."""
        collector = MetricsCollector(history_size=100)
        
        assert collector._history_size == 100
        assert len(collector._metrics) == 0
        assert len(collector._counters) == 0
    
    def test_record_gauge(self):
        """Test recording a gauge metric."""
        collector = MetricsCollector()
        
        collector.record("test.gauge", 42)
        
        summary = collector.get_metric("test.gauge")
        assert summary is not None
        assert summary.current == 42
        assert summary.count == 1
    
    def test_record_multiple_values(self):
        """Test recording multiple values for the same metric."""
        collector = MetricsCollector()
        
        collector.record("test.metric", 10)
        collector.record("test.metric", 20)
        collector.record("test.metric", 30)
        
        summary = collector.get_metric("test.metric")
        assert summary is not None
        assert summary.current == 30
        assert summary.min_value == 10
        assert summary.max_value == 30
        assert summary.avg_value == 20.0
        assert summary.count == 3
    
    def test_record_with_labels(self):
        """Test recording metrics with labels."""
        collector = MetricsCollector()
        
        collector.record(
            "test.metric",
            100,
            labels={"project": "jupiter", "env": "test"}
        )
        
        summary = collector.get_metric("test.metric")
        assert summary is not None
        assert summary.labels == {"project": "jupiter", "env": "test"}
    
    def test_increment_counter(self):
        """Test incrementing a counter."""
        collector = MetricsCollector()
        
        collector.increment("test.counter")
        collector.increment("test.counter", 5)
        collector.increment("test.counter", 2)
        
        total = collector.get_counter("test.counter")
        assert total == 8
    
    def test_gauge_method(self):
        """Test gauge convenience method."""
        collector = MetricsCollector()
        
        collector.gauge("cpu.usage", 75.5)
        
        summary = collector.get_metric("cpu.usage")
        assert summary is not None
        assert summary.current == 75.5
    
    def test_timing_method(self):
        """Test timing convenience method."""
        collector = MetricsCollector()
        
        collector.timing("request.duration_ms", 150.5)
        
        summary = collector.get_metric("request.duration_ms")
        assert summary is not None
        assert summary.current == 150.5
    
    def test_get_metric_not_found(self):
        """Test getting a non-existent metric."""
        collector = MetricsCollector()
        
        summary = collector.get_metric("nonexistent")
        assert summary is None
    
    def test_get_metric_history(self):
        """Test getting metric history."""
        collector = MetricsCollector()
        
        for i in range(5):
            collector.record("test.metric", i * 10)
        
        history = collector.get_metric_history("test.metric")
        
        assert len(history) == 5
        assert history[0].value == 0
        assert history[-1].value == 40
    
    def test_get_metric_history_with_limit(self):
        """Test getting limited metric history."""
        collector = MetricsCollector()
        
        for i in range(10):
            collector.record("test.metric", i)
        
        history = collector.get_metric_history("test.metric", limit=3)
        
        assert len(history) == 3
        assert history[-1].value == 9
    
    def test_get_all_metrics(self):
        """Test getting all metrics."""
        collector = MetricsCollector()
        
        collector.record("metric.a", 10)
        collector.record("metric.b", 20)
        collector.increment("counter.a", 5)
        
        all_metrics = collector.get_all_metrics()
        
        assert "system" in all_metrics
        assert "metrics" in all_metrics
        assert "counters" in all_metrics
        assert "collected_at" in all_metrics
        
        assert "metric.a" in all_metrics["metrics"]
        assert "metric.b" in all_metrics["metrics"]
        assert "counter.a" in all_metrics["counters"]
    
    def test_system_metrics(self):
        """Test system metrics."""
        collector = MetricsCollector()
        
        # Wait a tiny bit for uptime
        time.sleep(0.01)
        
        metrics = collector.get_all_metrics()
        system = metrics["system"]
        
        assert "uptime_seconds" in system
        assert system["uptime_seconds"] > 0
        assert "metrics_collected" in system
        assert "unique_metrics" in system
    
    def test_history_size_limit(self):
        """Test that history size is respected."""
        collector = MetricsCollector(history_size=5)
        
        for i in range(10):
            collector.record("test.metric", i)
        
        history = collector.get_metric_history("test.metric")
        
        assert len(history) == 5
        # Should have the last 5 values
        assert history[0].value == 5
        assert history[-1].value == 9
    
    def test_to_prometheus(self):
        """Test Prometheus format export."""
        collector = MetricsCollector()
        
        collector.gauge("test_gauge", 100)
        collector.increment("test_counter", 10)
        
        prometheus = collector.to_prometheus()
        
        assert "test_gauge" in prometheus
        assert "test_counter_total" in prometheus
        assert "# TYPE" in prometheus
    
    def test_to_prometheus_with_labels(self):
        """Test Prometheus format with labels."""
        collector = MetricsCollector()
        
        collector.gauge("cpu_usage", 75, labels={"host": "server1"})
        
        prometheus = collector.to_prometheus()
        
        assert 'cpu_usage{host="server1"}' in prometheus
    
    def test_reset(self):
        """Test resetting the collector."""
        collector = MetricsCollector()
        
        collector.record("test.metric", 100)
        collector.increment("test.counter", 5)
        
        collector.reset()
        
        assert len(collector._metrics) == 0
        assert len(collector._counters) == 0
        assert collector.get_metric("test.metric") is None


class TestTimingContext:
    """Test TimingContext context manager."""
    
    def test_timing_context(self):
        """Test timing context manager."""
        collector = MetricsCollector()
        
        # Use a fresh collector for the global functions
        import jupiter.core.bridge.metrics as metrics_mod
        old_collector = metrics_mod._collector
        metrics_mod._collector = collector
        
        try:
            with TimingContext("operation.duration_ms"):
                time.sleep(0.01)  # 10ms
            
            summary = collector.get_metric("operation.duration_ms")
            assert summary is not None
            assert summary.current >= 10  # At least 10ms
        finally:
            metrics_mod._collector = old_collector
    
    def test_timing_context_with_labels(self):
        """Test timing context with labels."""
        collector = MetricsCollector()
        
        import jupiter.core.bridge.metrics as metrics_mod
        old_collector = metrics_mod._collector
        metrics_mod._collector = collector
        
        try:
            with TimingContext("test.timing", labels={"type": "test"}):
                pass
            
            summary = collector.get_metric("test.timing")
            assert summary is not None
        finally:
            metrics_mod._collector = old_collector


class TestTimedDecorator:
    """Test timed decorator."""
    
    def test_timed_decorator(self):
        """Test timed function decorator."""
        collector = MetricsCollector()
        
        import jupiter.core.bridge.metrics as metrics_mod
        old_collector = metrics_mod._collector
        metrics_mod._collector = collector
        
        try:
            @timed("my_function.duration_ms")
            def my_function():
                time.sleep(0.01)
                return 42
            
            result = my_function()
            
            assert result == 42
            summary = collector.get_metric("my_function.duration_ms")
            assert summary is not None
            assert summary.current >= 10
        finally:
            metrics_mod._collector = old_collector


class TestGlobalFunctions:
    """Test global convenience functions."""
    
    def test_get_metrics_collector(self):
        """Test get_metrics_collector returns singleton."""
        c1 = get_metrics_collector()
        c2 = get_metrics_collector()
        
        assert c1 is c2
    
    def test_init_metrics_collector(self):
        """Test initializing new collector."""
        # Reset
        import jupiter.core.bridge.metrics as metrics_mod
        metrics_mod._collector = None
        
        collector = init_metrics_collector(history_size=50)
        
        assert collector._history_size == 50
        assert get_metrics_collector() is collector
    
    def test_record_metric(self):
        """Test record_metric function."""
        collector = init_metrics_collector()
        collector.reset()
        
        record_metric("test.metric", 123)
        
        summary = collector.get_metric("test.metric")
        assert summary is not None
        assert summary.current == 123
    
    def test_increment_counter(self):
        """Test increment_counter function."""
        collector = init_metrics_collector()
        collector.reset()
        
        increment_counter("test.counter")
        increment_counter("test.counter", 4)
        
        assert collector.get_counter("test.counter") == 5
    
    def test_record_timing(self):
        """Test record_timing function."""
        collector = init_metrics_collector()
        collector.reset()
        
        record_timing("test.timing", 150.5)
        
        summary = collector.get_metric("test.timing")
        assert summary is not None
        assert summary.current == 150.5


class TestCollectPluginMetrics:
    """Test plugin metrics collection."""
    
    def test_collect_without_bridge(self):
        """Test collection when Bridge is not available."""
        collector = MetricsCollector()
        
        # Mock bridge not initialized
        with patch('jupiter.core.bridge.get_bridge', return_value=None):
            result = collector.collect_plugin_metrics()
            assert result == {}
    
    def test_collect_with_bridge(self):
        """Test collection with Bridge and plugins."""
        collector = MetricsCollector()
        
        # Create mock plugin with metrics
        mock_metrics = MagicMock()
        mock_metrics.to_dict.return_value = {"count": 10}
        
        mock_instance = MagicMock()
        mock_instance.metrics.return_value = mock_metrics
        
        mock_info = MagicMock()
        mock_info.instance = mock_instance
        
        mock_bridge = MagicMock()
        mock_bridge._plugins = {"test_plugin": mock_info}
        
        with patch('jupiter.core.bridge.get_bridge', return_value=mock_bridge):
            result = collector.collect_plugin_metrics()
            
            assert "test_plugin" in result
            assert result["test_plugin"]["count"] == 10
