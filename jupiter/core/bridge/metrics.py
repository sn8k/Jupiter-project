"""Metrics Collection System for Jupiter Plugin Bridge.

Version: 0.1.0

This module provides a centralized metrics collection and aggregation system
for plugins and core components. Features include:
- Automatic collection from plugins implementing IPluginMetrics
- System-wide metrics aggregation
- Time-series data for recent metrics
- Export to various formats (dict, Prometheus, etc.)

Usage:
    from jupiter.core.bridge.metrics import MetricsCollector, get_metrics_collector
    
    # Get global collector
    collector = get_metrics_collector()
    
    # Record a custom metric
    collector.record("scan.duration_ms", 150, labels={"project": "myproject"})
    
    # Get all metrics
    all_metrics = collector.get_all_metrics()
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Type of metric for categorization."""
    
    COUNTER = "counter"      # Always increasing value
    GAUGE = "gauge"          # Current value that can go up or down
    HISTOGRAM = "histogram"  # Distribution of values
    SUMMARY = "summary"      # Similar to histogram but with percentiles


@dataclass
class MetricPoint:
    """A single metric data point."""
    
    name: str
    value: Union[int, float]
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "labels": self.labels,
            "type": self.metric_type.value,
        }


@dataclass
class MetricSummary:
    """Summary statistics for a metric over time."""
    
    name: str
    current: Union[int, float]
    min_value: Union[int, float]
    max_value: Union[int, float]
    avg_value: float
    count: int
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "current": self.current,
            "min": self.min_value,
            "max": self.max_value,
            "avg": self.avg_value,
            "count": self.count,
            "labels": self.labels,
        }


class MetricsCollector:
    """Centralized metrics collection and aggregation.
    
    This collector gathers metrics from multiple sources:
    - Core Jupiter components
    - Plugins implementing IPluginMetrics
    - Manual metric recording
    
    Thread-safe for concurrent metric recording.
    """
    
    def __init__(self, history_size: int = 1000):
        """Initialize the metrics collector.
        
        Args:
            history_size: Maximum number of data points to retain per metric
        """
        self._history_size = history_size
        self._metrics: Dict[str, deque] = {}  # name -> deque of MetricPoint
        self._counters: Dict[str, float] = {}  # name -> cumulative value
        self._lock = Lock()
        self._plugin_metrics_cache: Dict[str, Dict[str, Any]] = {}
        self._last_collection_time: Optional[float] = None
        
        # Built-in metrics
        self._start_time = time.time()
        
        logger.debug("MetricsCollector initialized (history_size=%d)", history_size)
    
    def record(
        self,
        name: str,
        value: Union[int, float],
        labels: Optional[Dict[str, str]] = None,
        metric_type: MetricType = MetricType.GAUGE,
    ) -> None:
        """Record a metric value.
        
        Args:
            name: Metric name (e.g., "scan.duration_ms", "plugins.loaded")
            value: Metric value
            labels: Optional key-value labels for the metric
            metric_type: Type of metric (default: GAUGE)
        """
        point = MetricPoint(
            name=name,
            value=value,
            labels=labels or {},
            metric_type=metric_type,
        )
        
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = deque(maxlen=self._history_size)
            
            self._metrics[name].append(point)
            
            # For counters, track cumulative value
            if metric_type == MetricType.COUNTER:
                self._counters[name] = self._counters.get(name, 0) + value
        
        logger.debug("Recorded metric: %s = %s", name, value)
    
    def increment(
        self,
        name: str,
        amount: Union[int, float] = 1,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Increment a counter metric.
        
        Args:
            name: Counter name
            amount: Amount to increment by
            labels: Optional labels
        """
        self.record(name, amount, labels, MetricType.COUNTER)
    
    def gauge(
        self,
        name: str,
        value: Union[int, float],
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a gauge metric.
        
        Args:
            name: Gauge name
            value: Current value
            labels: Optional labels
        """
        self.record(name, value, labels, MetricType.GAUGE)
    
    def timing(
        self,
        name: str,
        duration_ms: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a timing/duration metric.
        
        Args:
            name: Metric name
            duration_ms: Duration in milliseconds
            labels: Optional labels
        """
        self.record(name, duration_ms, labels, MetricType.HISTOGRAM)
    
    def get_metric(self, name: str) -> Optional[MetricSummary]:
        """Get summary for a specific metric.
        
        Args:
            name: Metric name
            
        Returns:
            MetricSummary or None if metric doesn't exist
        """
        with self._lock:
            if name not in self._metrics or not self._metrics[name]:
                return None
            
            points = list(self._metrics[name])
            values = [p.value for p in points]
            
            return MetricSummary(
                name=name,
                current=values[-1] if values else 0,
                min_value=min(values) if values else 0,
                max_value=max(values) if values else 0,
                avg_value=sum(values) / len(values) if values else 0,
                count=len(values),
                labels=points[-1].labels if points else {},
            )
    
    def get_metric_history(
        self,
        name: str,
        limit: int = 100,
    ) -> List[MetricPoint]:
        """Get historical data points for a metric.
        
        Args:
            name: Metric name
            limit: Maximum points to return
            
        Returns:
            List of MetricPoint (most recent last)
        """
        with self._lock:
            if name not in self._metrics:
                return []
            
            points = list(self._metrics[name])
            return points[-limit:]
    
    def get_counter(self, name: str) -> float:
        """Get cumulative value of a counter.
        
        Args:
            name: Counter name
            
        Returns:
            Cumulative counter value
        """
        with self._lock:
            return self._counters.get(name, 0)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics as a dictionary.
        
        Returns:
            Dictionary with metric summaries
        """
        result: Dict[str, Any] = {
            "system": self._get_system_metrics(),
            "metrics": {},
            "counters": {},
            "plugins": {},
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }
        
        with self._lock:
            # Add metric summaries (inline to avoid recursive lock)
            for name, points in self._metrics.items():
                if not points:
                    continue
                point_list = list(points)
                values = [p.value for p in point_list]
                summary = MetricSummary(
                    name=name,
                    current=values[-1] if values else 0,
                    min_value=min(values) if values else 0,
                    max_value=max(values) if values else 0,
                    avg_value=sum(values) / len(values) if values else 0,
                    count=len(values),
                    labels=point_list[-1].labels if point_list else {},
                )
                result["metrics"][name] = summary.to_dict()
            
            # Add counter values
            result["counters"] = dict(self._counters)
            
            # Add cached plugin metrics
            result["plugins"] = dict(self._plugin_metrics_cache)
        
        return result
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system-level metrics.
        
        Returns:
            Dictionary with system metrics
        """
        uptime = time.time() - self._start_time
        
        return {
            "uptime_seconds": uptime,
            "metrics_collected": sum(len(q) for q in self._metrics.values()),
            "unique_metrics": len(self._metrics),
            "counters_tracked": len(self._counters),
        }
    
    def collect_plugin_metrics(self) -> Dict[str, Any]:
        """Collect metrics from all plugins implementing IPluginMetrics.
        
        Returns:
            Dictionary mapping plugin_id to their metrics
        """
        plugin_metrics = {}
        
        try:
            from jupiter.core.bridge import get_bridge
            
            bridge = get_bridge()
            if bridge is None:
                return plugin_metrics
            
            # Iterate through loaded plugins
            for plugin_id, info in bridge._plugins.items():
                if info.instance is None:
                    continue
                
                # Check if plugin implements metrics()
                metrics_method = getattr(info.instance, 'metrics', None)
                if metrics_method and callable(metrics_method):
                    try:
                        metrics = metrics_method()
                        to_dict_method = getattr(metrics, 'to_dict', None)
                        if to_dict_method and callable(to_dict_method):
                            plugin_metrics[plugin_id] = to_dict_method()
                        elif isinstance(metrics, dict):
                            plugin_metrics[plugin_id] = metrics
                        else:
                            plugin_metrics[plugin_id] = {"raw": str(metrics)}
                    except Exception as e:
                        logger.warning(
                            "Failed to collect metrics from plugin %s: %s",
                            plugin_id, e
                        )
                        plugin_metrics[plugin_id] = {"error": str(e)}
            
            # Cache the results
            with self._lock:
                self._plugin_metrics_cache = plugin_metrics
                self._last_collection_time = time.time()
                
        except ImportError:
            logger.debug("Bridge not available for plugin metrics collection")
        except Exception as e:
            logger.error("Error collecting plugin metrics: %s", e)
        
        return plugin_metrics
    
    def to_prometheus(self) -> str:
        """Export metrics in Prometheus text format.
        
        Returns:
            Prometheus-formatted metrics string
        """
        lines = []
        
        with self._lock:
            # Export gauges and histograms
            for name, points in self._metrics.items():
                if not points:
                    continue
                
                # Use last point
                point = points[-1]
                metric_name = name.replace(".", "_").replace("-", "_")
                
                # Add HELP and TYPE comments
                lines.append(f"# HELP {metric_name} Jupiter metric")
                lines.append(f"# TYPE {metric_name} {point.metric_type.value}")
                
                # Format labels
                label_str = ""
                if point.labels:
                    label_parts = [f'{k}="{v}"' for k, v in point.labels.items()]
                    label_str = "{" + ",".join(label_parts) + "}"
                
                lines.append(f"{metric_name}{label_str} {point.value}")
            
            # Export counters
            for name, value in self._counters.items():
                metric_name = name.replace(".", "_").replace("-", "_") + "_total"
                lines.append(f"# HELP {metric_name} Jupiter counter")
                lines.append(f"# TYPE {metric_name} counter")
                lines.append(f"{metric_name} {value}")
        
        return "\n".join(lines)
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()
            self._plugin_metrics_cache.clear()
            self._last_collection_time = None
        
        logger.info("Metrics collector reset")


# Global collector instance
_collector: Optional[MetricsCollector] = None
_collector_lock = Lock()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance.
    
    Returns:
        The global MetricsCollector instance
    """
    global _collector
    
    with _collector_lock:
        if _collector is None:
            _collector = MetricsCollector()
    
    return _collector


def init_metrics_collector(history_size: int = 1000) -> MetricsCollector:
    """Initialize or reinitialize the global metrics collector.
    
    Args:
        history_size: Maximum history size per metric
        
    Returns:
        The initialized MetricsCollector
    """
    global _collector
    
    with _collector_lock:
        _collector = MetricsCollector(history_size=history_size)
    
    logger.info("Global metrics collector initialized")
    return _collector


def record_metric(
    name: str,
    value: Union[int, float],
    labels: Optional[Dict[str, str]] = None,
    metric_type: MetricType = MetricType.GAUGE,
) -> None:
    """Convenience function to record a metric.
    
    Args:
        name: Metric name
        value: Metric value
        labels: Optional labels
        metric_type: Type of metric
    """
    get_metrics_collector().record(name, value, labels, metric_type)


def increment_counter(
    name: str,
    amount: Union[int, float] = 1,
    labels: Optional[Dict[str, str]] = None,
) -> None:
    """Convenience function to increment a counter.
    
    Args:
        name: Counter name
        amount: Amount to increment
        labels: Optional labels
    """
    get_metrics_collector().increment(name, amount, labels)


def record_timing(
    name: str,
    duration_ms: float,
    labels: Optional[Dict[str, str]] = None,
) -> None:
    """Convenience function to record a timing metric.
    
    Args:
        name: Metric name
        duration_ms: Duration in milliseconds
        labels: Optional labels
    """
    get_metrics_collector().timing(name, duration_ms, labels)


# Context manager for timing operations
class TimingContext:
    """Context manager for automatically timing operations.
    
    Usage:
        with TimingContext("operation.duration_ms"):
            # Do something
            pass
    """
    
    def __init__(
        self,
        metric_name: str,
        labels: Optional[Dict[str, str]] = None,
    ):
        """Initialize timing context.
        
        Args:
            metric_name: Name of the timing metric
            labels: Optional labels
        """
        self.metric_name = metric_name
        self.labels = labels
        self._start_time: Optional[float] = None
    
    def __enter__(self) -> "TimingContext":
        self._start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._start_time is not None:
            duration_ms = (time.time() - self._start_time) * 1000
            record_timing(self.metric_name, duration_ms, self.labels)


def timed(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """Decorator to automatically time function execution.
    
    Args:
        metric_name: Name of the timing metric
        labels: Optional labels
        
    Usage:
        @timed("my_function.duration_ms")
        def my_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            with TimingContext(metric_name, labels):
                return func(*args, **kwargs)
        return wrapper
    return decorator
