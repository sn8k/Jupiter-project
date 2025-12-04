"""
Plugin Usage Statistics Module for Jupiter Bridge.

Provides comprehensive tracking of plugin usage including:
- Execution counts (total, by method, by timeframe)
- Timing statistics (last execution, average duration, min/max)
- Success/failure rates
- Resource usage estimates
- Historical trends

Version: 0.1.0
"""

__version__ = "0.1.0"

import threading
import time
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable, Set
from pathlib import Path
from enum import Enum
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class TimeFrame(Enum):
    """Time frames for statistics aggregation."""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    ALL_TIME = "all_time"


class ExecutionStatus(Enum):
    """Status of a plugin execution."""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ExecutionRecord:
    """Record of a single plugin execution."""
    plugin_id: str
    method: str
    started_at: float  # timestamp
    duration_ms: float
    status: ExecutionStatus
    error_type: Optional[str] = None
    memory_delta_kb: Optional[float] = None  # Memory change during execution
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "plugin_id": self.plugin_id,
            "method": self.method,
            "started_at": self.started_at,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "error_type": self.error_type,
            "memory_delta_kb": self.memory_delta_kb,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionRecord":
        """Create from dictionary."""
        return cls(
            plugin_id=data["plugin_id"],
            method=data["method"],
            started_at=data["started_at"],
            duration_ms=data["duration_ms"],
            status=ExecutionStatus(data["status"]),
            error_type=data.get("error_type"),
            memory_delta_kb=data.get("memory_delta_kb"),
            metadata=data.get("metadata", {})
        )


@dataclass
class MethodStats:
    """Statistics for a specific method of a plugin."""
    method: str
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    timeout_count: int = 0
    cancelled_count: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: Optional[float] = None
    max_duration_ms: Optional[float] = None
    last_execution: Optional[float] = None
    last_status: Optional[ExecutionStatus] = None
    error_types: Dict[str, int] = field(default_factory=dict)
    durations_history: List[float] = field(default_factory=list)  # Recent durations for percentile calc
    
    @property
    def average_duration_ms(self) -> float:
        """Calculate average duration."""
        if self.execution_count == 0:
            return 0.0
        return self.total_duration_ms / self.execution_count
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.execution_count == 0:
            return 0.0
        return (self.success_count / self.execution_count) * 100
    
    @property
    def p95_duration_ms(self) -> Optional[float]:
        """Calculate 95th percentile duration."""
        if len(self.durations_history) < 2:
            return None
        sorted_durations = sorted(self.durations_history)
        idx = int(len(sorted_durations) * 0.95)
        return sorted_durations[min(idx, len(sorted_durations) - 1)]
    
    @property
    def median_duration_ms(self) -> Optional[float]:
        """Calculate median duration."""
        if not self.durations_history:
            return None
        return statistics.median(self.durations_history)
    
    def record_execution(
        self,
        duration_ms: float,
        status: ExecutionStatus,
        error_type: Optional[str] = None,
        max_history_size: int = 100
    ) -> None:
        """Record a new execution."""
        self.execution_count += 1
        self.total_duration_ms += duration_ms
        self.last_execution = time.time()
        self.last_status = status
        
        # Update min/max
        if self.min_duration_ms is None or duration_ms < self.min_duration_ms:
            self.min_duration_ms = duration_ms
        if self.max_duration_ms is None or duration_ms > self.max_duration_ms:
            self.max_duration_ms = duration_ms
        
        # Update status counts
        if status == ExecutionStatus.SUCCESS:
            self.success_count += 1
        elif status == ExecutionStatus.FAILURE:
            self.failure_count += 1
            if error_type:
                self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
        elif status == ExecutionStatus.TIMEOUT:
            self.timeout_count += 1
        elif status == ExecutionStatus.CANCELLED:
            self.cancelled_count += 1
        
        # Update history (with size limit)
        self.durations_history.append(duration_ms)
        if len(self.durations_history) > max_history_size:
            self.durations_history = self.durations_history[-max_history_size:]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "method": self.method,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "timeout_count": self.timeout_count,
            "cancelled_count": self.cancelled_count,
            "total_duration_ms": self.total_duration_ms,
            "average_duration_ms": self.average_duration_ms,
            "min_duration_ms": self.min_duration_ms,
            "max_duration_ms": self.max_duration_ms,
            "median_duration_ms": self.median_duration_ms,
            "p95_duration_ms": self.p95_duration_ms,
            "success_rate": self.success_rate,
            "last_execution": self.last_execution,
            "last_status": self.last_status.value if self.last_status else None,
            "error_types": self.error_types
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MethodStats":
        """Create from dictionary."""
        stats = cls(method=data["method"])
        stats.execution_count = data.get("execution_count", 0)
        stats.success_count = data.get("success_count", 0)
        stats.failure_count = data.get("failure_count", 0)
        stats.timeout_count = data.get("timeout_count", 0)
        stats.cancelled_count = data.get("cancelled_count", 0)
        stats.total_duration_ms = data.get("total_duration_ms", 0.0)
        stats.min_duration_ms = data.get("min_duration_ms")
        stats.max_duration_ms = data.get("max_duration_ms")
        stats.last_execution = data.get("last_execution")
        last_status = data.get("last_status")
        if last_status:
            stats.last_status = ExecutionStatus(last_status)
        stats.error_types = data.get("error_types", {})
        stats.durations_history = data.get("durations_history", [])
        return stats


@dataclass
class PluginStats:
    """Comprehensive statistics for a single plugin."""
    plugin_id: str
    first_execution: Optional[float] = None
    methods: Dict[str, MethodStats] = field(default_factory=dict)
    enabled_time_total_seconds: float = 0.0  # Total time plugin was enabled
    last_enabled_at: Optional[float] = None
    is_currently_enabled: bool = False
    load_count: int = 0  # Number of times plugin was loaded
    unload_count: int = 0  # Number of times plugin was unloaded
    error_count_total: int = 0  # Total errors across all methods
    tags: Set[str] = field(default_factory=set)  # Custom tags for filtering
    
    @property
    def total_executions(self) -> int:
        """Total executions across all methods."""
        return sum(m.execution_count for m in self.methods.values())
    
    @property
    def total_success(self) -> int:
        """Total successful executions."""
        return sum(m.success_count for m in self.methods.values())
    
    @property
    def total_failures(self) -> int:
        """Total failed executions."""
        return sum(m.failure_count for m in self.methods.values())
    
    @property
    def overall_success_rate(self) -> float:
        """Overall success rate across all methods."""
        total = self.total_executions
        if total == 0:
            return 0.0
        return (self.total_success / total) * 100
    
    @property
    def total_duration_ms(self) -> float:
        """Total execution time across all methods."""
        return sum(m.total_duration_ms for m in self.methods.values())
    
    @property
    def average_duration_ms(self) -> float:
        """Average execution time across all methods."""
        total = self.total_executions
        if total == 0:
            return 0.0
        return self.total_duration_ms / total
    
    @property
    def last_execution(self) -> Optional[float]:
        """Most recent execution timestamp."""
        last_times = [m.last_execution for m in self.methods.values() if m.last_execution]
        return max(last_times) if last_times else None
    
    @property
    def most_used_method(self) -> Optional[str]:
        """Method with most executions."""
        if not self.methods:
            return None
        return max(self.methods.values(), key=lambda m: m.execution_count).method
    
    @property
    def slowest_method(self) -> Optional[str]:
        """Method with highest average duration."""
        if not self.methods:
            return None
        methods_with_executions = [m for m in self.methods.values() if m.execution_count > 0]
        if not methods_with_executions:
            return None
        return max(methods_with_executions, key=lambda m: m.average_duration_ms).method
    
    def get_method_stats(self, method: str) -> MethodStats:
        """Get or create method stats."""
        if method not in self.methods:
            self.methods[method] = MethodStats(method=method)
        return self.methods[method]
    
    def record_execution(
        self,
        method: str,
        duration_ms: float,
        status: ExecutionStatus,
        error_type: Optional[str] = None
    ) -> None:
        """Record a method execution."""
        if self.first_execution is None:
            self.first_execution = time.time()
        
        method_stats = self.get_method_stats(method)
        method_stats.record_execution(duration_ms, status, error_type)
        
        if status in (ExecutionStatus.FAILURE, ExecutionStatus.TIMEOUT):
            self.error_count_total += 1
    
    def record_load(self) -> None:
        """Record plugin load event."""
        self.load_count += 1
        self.is_currently_enabled = True
        self.last_enabled_at = time.time()
    
    def record_unload(self) -> None:
        """Record plugin unload event."""
        self.unload_count += 1
        if self.is_currently_enabled and self.last_enabled_at:
            self.enabled_time_total_seconds += time.time() - self.last_enabled_at
        self.is_currently_enabled = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "plugin_id": self.plugin_id,
            "first_execution": self.first_execution,
            "methods": {k: v.to_dict() for k, v in self.methods.items()},
            "enabled_time_total_seconds": self.enabled_time_total_seconds,
            "last_enabled_at": self.last_enabled_at,
            "is_currently_enabled": self.is_currently_enabled,
            "load_count": self.load_count,
            "unload_count": self.unload_count,
            "error_count_total": self.error_count_total,
            "tags": list(self.tags),
            "total_executions": self.total_executions,
            "total_success": self.total_success,
            "total_failures": self.total_failures,
            "overall_success_rate": self.overall_success_rate,
            "total_duration_ms": self.total_duration_ms,
            "average_duration_ms": self.average_duration_ms,
            "last_execution": self.last_execution,
            "most_used_method": self.most_used_method,
            "slowest_method": self.slowest_method
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginStats":
        """Create from dictionary."""
        stats = cls(plugin_id=data["plugin_id"])
        stats.first_execution = data.get("first_execution")
        stats.methods = {
            k: MethodStats.from_dict(v) 
            for k, v in data.get("methods", {}).items()
        }
        stats.enabled_time_total_seconds = data.get("enabled_time_total_seconds", 0.0)
        stats.last_enabled_at = data.get("last_enabled_at")
        stats.is_currently_enabled = data.get("is_currently_enabled", False)
        stats.load_count = data.get("load_count", 0)
        stats.unload_count = data.get("unload_count", 0)
        stats.error_count_total = data.get("error_count_total", 0)
        stats.tags = set(data.get("tags", []))
        return stats


@dataclass
class TimeframeStats:
    """Aggregated statistics for a time frame."""
    timeframe: TimeFrame
    start_time: float
    end_time: float
    total_executions: int = 0
    total_success: int = 0
    total_failures: int = 0
    total_duration_ms: float = 0.0
    unique_plugins: Set[str] = field(default_factory=set)
    unique_methods: Set[str] = field(default_factory=set)
    
    @property
    def success_rate(self) -> float:
        """Success rate for the timeframe."""
        if self.total_executions == 0:
            return 0.0
        return (self.total_success / self.total_executions) * 100
    
    @property
    def average_duration_ms(self) -> float:
        """Average duration for the timeframe."""
        if self.total_executions == 0:
            return 0.0
        return self.total_duration_ms / self.total_executions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timeframe": self.timeframe.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_executions": self.total_executions,
            "total_success": self.total_success,
            "total_failures": self.total_failures,
            "total_duration_ms": self.total_duration_ms,
            "success_rate": self.success_rate,
            "average_duration_ms": self.average_duration_ms,
            "unique_plugins_count": len(self.unique_plugins),
            "unique_methods_count": len(self.unique_methods)
        }


@dataclass
class UsageStatsConfig:
    """Configuration for usage statistics tracking."""
    enabled: bool = True
    persist_to_disk: bool = True
    persistence_path: Optional[Path] = None
    max_records_in_memory: int = 10000  # Max execution records to keep
    max_history_per_method: int = 100  # Max duration history per method
    auto_save_interval_seconds: int = 300  # Auto-save every 5 minutes
    retention_days: int = 30  # Keep records for 30 days
    track_memory_usage: bool = False  # Memory tracking (expensive)
    anonymize_errors: bool = True  # Anonymize error details
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enabled": self.enabled,
            "persist_to_disk": self.persist_to_disk,
            "persistence_path": str(self.persistence_path) if self.persistence_path else None,
            "max_records_in_memory": self.max_records_in_memory,
            "max_history_per_method": self.max_history_per_method,
            "auto_save_interval_seconds": self.auto_save_interval_seconds,
            "retention_days": self.retention_days,
            "track_memory_usage": self.track_memory_usage,
            "anonymize_errors": self.anonymize_errors
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UsageStatsConfig":
        """Create from dictionary."""
        config = cls()
        config.enabled = data.get("enabled", True)
        config.persist_to_disk = data.get("persist_to_disk", True)
        if data.get("persistence_path"):
            config.persistence_path = Path(data["persistence_path"])
        config.max_records_in_memory = data.get("max_records_in_memory", 10000)
        config.max_history_per_method = data.get("max_history_per_method", 100)
        config.auto_save_interval_seconds = data.get("auto_save_interval_seconds", 300)
        config.retention_days = data.get("retention_days", 30)
        config.track_memory_usage = data.get("track_memory_usage", False)
        config.anonymize_errors = data.get("anonymize_errors", True)
        return config


class ExecutionTimer:
    """Context manager for timing plugin executions."""
    
    def __init__(
        self,
        manager: "UsageStatsManager",
        plugin_id: str,
        method: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.manager = manager
        self.plugin_id = plugin_id
        self.method = method
        self.metadata = metadata or {}
        self.start_time: Optional[float] = None
        self.status = ExecutionStatus.SUCCESS
        self.error_type: Optional[str] = None
    
    def __enter__(self) -> "ExecutionTimer":
        """Start timing."""
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Stop timing and record execution."""
        if self.start_time is None:
            return False
        
        duration_ms = (time.perf_counter() - self.start_time) * 1000
        
        if exc_type is not None:
            self.status = ExecutionStatus.FAILURE
            self.error_type = exc_type.__name__
        
        self.manager.record_execution(
            plugin_id=self.plugin_id,
            method=self.method,
            duration_ms=duration_ms,
            status=self.status,
            error_type=self.error_type,
            metadata=self.metadata
        )
        
        return False  # Don't suppress exceptions
    
    def mark_timeout(self) -> None:
        """Mark execution as timed out."""
        self.status = ExecutionStatus.TIMEOUT
    
    def mark_cancelled(self) -> None:
        """Mark execution as cancelled."""
        self.status = ExecutionStatus.CANCELLED
    
    def mark_failure(self, error_type: Optional[str] = None) -> None:
        """Mark execution as failed."""
        self.status = ExecutionStatus.FAILURE
        self.error_type = error_type


class UsageStatsManager:
    """
    Manager for plugin usage statistics.
    
    Provides comprehensive tracking of plugin executions including:
    - Per-plugin and per-method statistics
    - Time-based aggregations
    - Persistence to disk
    - Reporting and export
    
    Thread-safe implementation using RLock for reentrant access.
    """
    
    def __init__(self, config: Optional[UsageStatsConfig] = None):
        """Initialize the usage stats manager."""
        self.config = config or UsageStatsConfig()
        self._lock = threading.RLock()  # RLock for reentrant calls
        self._plugin_stats: Dict[str, PluginStats] = {}
        self._execution_records: List[ExecutionRecord] = []
        self._callbacks: List[Callable[[ExecutionRecord], None]] = []
        self._started_at = time.time()
        self._last_save_time: Optional[float] = None
        self._dirty = False  # Track if changes need saving
        
        # Load existing data if configured
        if self.config.persist_to_disk and self.config.persistence_path:
            self._load_from_disk()
    
    def record_execution(
        self,
        plugin_id: str,
        method: str,
        duration_ms: float,
        status: ExecutionStatus = ExecutionStatus.SUCCESS,
        error_type: Optional[str] = None,
        memory_delta_kb: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExecutionRecord:
        """
        Record a plugin execution.
        
        Args:
            plugin_id: The plugin identifier
            method: The method that was executed
            duration_ms: Execution duration in milliseconds
            status: Execution status (success, failure, timeout, cancelled)
            error_type: Type of error if failed
            memory_delta_kb: Memory change during execution
            metadata: Additional metadata
            
        Returns:
            The created ExecutionRecord
        """
        if not self.config.enabled:
            # Return dummy record if disabled
            return ExecutionRecord(
                plugin_id=plugin_id,
                method=method,
                started_at=time.time(),
                duration_ms=duration_ms,
                status=status
            )
        
        # Anonymize error type if configured
        if self.config.anonymize_errors and error_type:
            # Keep only the class name, not the full message
            error_type = error_type.split(":")[0].strip() if ":" in error_type else error_type
        
        record = ExecutionRecord(
            plugin_id=plugin_id,
            method=method,
            started_at=time.time(),
            duration_ms=duration_ms,
            status=status,
            error_type=error_type,
            memory_delta_kb=memory_delta_kb,
            metadata=metadata or {}
        )
        
        with self._lock:
            # Update plugin stats
            if plugin_id not in self._plugin_stats:
                self._plugin_stats[plugin_id] = PluginStats(plugin_id=plugin_id)
            
            self._plugin_stats[plugin_id].record_execution(
                method=method,
                duration_ms=duration_ms,
                status=status,
                error_type=error_type
            )
            
            # Store record
            self._execution_records.append(record)
            
            # Trim records if needed
            if len(self._execution_records) > self.config.max_records_in_memory:
                # Remove oldest records
                excess = len(self._execution_records) - self.config.max_records_in_memory
                self._execution_records = self._execution_records[excess:]
            
            self._dirty = True
        
        # Notify callbacks (outside lock)
        for callback in self._callbacks:
            try:
                callback(record)
            except Exception as e:
                logger.warning(f"Stats callback error: {e}")
        
        return record
    
    def time_execution(
        self,
        plugin_id: str,
        method: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExecutionTimer:
        """
        Create a context manager for timing an execution.
        
        Usage:
            with manager.time_execution("my-plugin", "process") as timer:
                # do work
                if error_occurred:
                    timer.mark_failure("SomeError")
        
        Args:
            plugin_id: The plugin identifier
            method: The method being executed
            metadata: Additional metadata
            
        Returns:
            ExecutionTimer context manager
        """
        return ExecutionTimer(self, plugin_id, method, metadata)
    
    def get_plugin_stats(self, plugin_id: str) -> Optional[PluginStats]:
        """Get statistics for a specific plugin."""
        with self._lock:
            return self._plugin_stats.get(plugin_id)
    
    def get_all_plugin_stats(self) -> Dict[str, PluginStats]:
        """Get statistics for all plugins."""
        with self._lock:
            return dict(self._plugin_stats)
    
    def get_method_stats(self, plugin_id: str, method: str) -> Optional[MethodStats]:
        """Get statistics for a specific method of a plugin."""
        with self._lock:
            plugin_stats = self._plugin_stats.get(plugin_id)
            if plugin_stats:
                return plugin_stats.methods.get(method)
            return None
    
    def record_plugin_load(self, plugin_id: str) -> None:
        """Record that a plugin was loaded."""
        with self._lock:
            if plugin_id not in self._plugin_stats:
                self._plugin_stats[plugin_id] = PluginStats(plugin_id=plugin_id)
            self._plugin_stats[plugin_id].record_load()
            self._dirty = True
    
    def record_plugin_unload(self, plugin_id: str) -> None:
        """Record that a plugin was unloaded."""
        with self._lock:
            if plugin_id in self._plugin_stats:
                self._plugin_stats[plugin_id].record_unload()
                self._dirty = True
    
    def add_plugin_tag(self, plugin_id: str, tag: str) -> None:
        """Add a tag to a plugin for filtering/grouping."""
        with self._lock:
            if plugin_id not in self._plugin_stats:
                self._plugin_stats[plugin_id] = PluginStats(plugin_id=plugin_id)
            self._plugin_stats[plugin_id].tags.add(tag)
            self._dirty = True
    
    def remove_plugin_tag(self, plugin_id: str, tag: str) -> None:
        """Remove a tag from a plugin."""
        with self._lock:
            if plugin_id in self._plugin_stats:
                self._plugin_stats[plugin_id].tags.discard(tag)
                self._dirty = True
    
    def get_plugins_by_tag(self, tag: str) -> List[str]:
        """Get all plugin IDs that have a specific tag."""
        with self._lock:
            return [
                plugin_id for plugin_id, stats in self._plugin_stats.items()
                if tag in stats.tags
            ]
    
    def get_timeframe_stats(self, timeframe: TimeFrame) -> TimeframeStats:
        """Get aggregated statistics for a time frame."""
        now = time.time()
        
        if timeframe == TimeFrame.HOUR:
            start_time = now - 3600
        elif timeframe == TimeFrame.DAY:
            start_time = now - 86400
        elif timeframe == TimeFrame.WEEK:
            start_time = now - 604800
        elif timeframe == TimeFrame.MONTH:
            start_time = now - 2592000
        else:  # ALL_TIME
            start_time = 0
        
        stats = TimeframeStats(
            timeframe=timeframe,
            start_time=start_time,
            end_time=now
        )
        
        with self._lock:
            for record in self._execution_records:
                if record.started_at >= start_time:
                    stats.total_executions += 1
                    stats.total_duration_ms += record.duration_ms
                    stats.unique_plugins.add(record.plugin_id)
                    stats.unique_methods.add(f"{record.plugin_id}.{record.method}")
                    
                    if record.status == ExecutionStatus.SUCCESS:
                        stats.total_success += 1
                    elif record.status in (ExecutionStatus.FAILURE, ExecutionStatus.TIMEOUT):
                        stats.total_failures += 1
        
        return stats
    
    def get_recent_records(
        self,
        count: int = 100,
        plugin_id: Optional[str] = None,
        method: Optional[str] = None,
        status: Optional[ExecutionStatus] = None
    ) -> List[ExecutionRecord]:
        """Get recent execution records with optional filtering."""
        with self._lock:
            records = self._execution_records.copy()
        
        # Apply filters
        if plugin_id:
            records = [r for r in records if r.plugin_id == plugin_id]
        if method:
            records = [r for r in records if r.method == method]
        if status:
            records = [r for r in records if r.status == status]
        
        # Return most recent
        return records[-count:]
    
    def get_top_plugins(
        self,
        metric: str = "executions",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top plugins by a specific metric.
        
        Args:
            metric: One of "executions", "duration", "errors", "success_rate"
            limit: Maximum number of plugins to return
            
        Returns:
            List of plugin stats sorted by the metric
        """
        with self._lock:
            plugins = list(self._plugin_stats.values())
        
        if not plugins:
            return []
        
        if metric == "executions":
            plugins.sort(key=lambda p: p.total_executions, reverse=True)
        elif metric == "duration":
            plugins.sort(key=lambda p: p.total_duration_ms, reverse=True)
        elif metric == "errors":
            plugins.sort(key=lambda p: p.error_count_total, reverse=True)
        elif metric == "success_rate":
            plugins.sort(key=lambda p: p.overall_success_rate, reverse=True)
        else:
            plugins.sort(key=lambda p: p.total_executions, reverse=True)
        
        return [p.to_dict() for p in plugins[:limit]]
    
    def get_slowest_methods(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the slowest methods across all plugins."""
        methods: List[tuple] = []
        
        with self._lock:
            for plugin_id, plugin_stats in self._plugin_stats.items():
                for method_name, method_stats in plugin_stats.methods.items():
                    if method_stats.execution_count > 0:
                        methods.append((
                            plugin_id,
                            method_name,
                            method_stats.average_duration_ms,
                            method_stats
                        ))
        
        methods.sort(key=lambda x: x[2], reverse=True)
        
        return [
            {
                "plugin_id": plugin_id,
                "method": method_name,
                "average_duration_ms": avg_duration,
                **method_stats.to_dict()
            }
            for plugin_id, method_name, avg_duration, method_stats in methods[:limit]
        ]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get a summary of errors across all plugins."""
        error_counts: Dict[str, int] = defaultdict(int)
        plugins_with_errors: Set[str] = set()
        total_errors = 0
        
        with self._lock:
            for plugin_id, plugin_stats in self._plugin_stats.items():
                if plugin_stats.error_count_total > 0:
                    plugins_with_errors.add(plugin_id)
                    total_errors += plugin_stats.error_count_total
                    
                    for method_stats in plugin_stats.methods.values():
                        for error_type, count in method_stats.error_types.items():
                            error_counts[error_type] += count
        
        return {
            "total_errors": total_errors,
            "unique_error_types": len(error_counts),
            "plugins_with_errors": len(plugins_with_errors),
            "error_types": dict(error_counts),
            "most_common_error": max(error_counts.items(), key=lambda x: x[1])[0] if error_counts else None
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get an overall summary of usage statistics."""
        with self._lock:
            total_executions = sum(p.total_executions for p in self._plugin_stats.values())
            total_success = sum(p.total_success for p in self._plugin_stats.values())
            total_duration = sum(p.total_duration_ms for p in self._plugin_stats.values())
            
            return {
                "tracking_started": self._started_at,
                "tracking_duration_seconds": time.time() - self._started_at,
                "total_plugins_tracked": len(self._plugin_stats),
                "total_executions": total_executions,
                "total_success": total_success,
                "total_failures": total_executions - total_success,
                "overall_success_rate": (total_success / total_executions * 100) if total_executions > 0 else 0,
                "total_duration_ms": total_duration,
                "average_duration_ms": total_duration / total_executions if total_executions > 0 else 0,
                "records_in_memory": len(self._execution_records),
                "config": self.config.to_dict()
            }
    
    def register_callback(self, callback: Callable[[ExecutionRecord], None]) -> None:
        """Register a callback to be notified of new executions."""
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[ExecutionRecord], None]) -> None:
        """Unregister a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def clear_all_stats(self) -> None:
        """Clear all statistics (use with caution)."""
        with self._lock:
            self._plugin_stats.clear()
            self._execution_records.clear()
            self._dirty = True
    
    def clear_plugin_stats(self, plugin_id: str) -> bool:
        """Clear statistics for a specific plugin."""
        with self._lock:
            if plugin_id in self._plugin_stats:
                del self._plugin_stats[plugin_id]
                self._execution_records = [
                    r for r in self._execution_records
                    if r.plugin_id != plugin_id
                ]
                self._dirty = True
                return True
            return False
    
    def cleanup_old_records(self, retention_days: Optional[int] = None) -> int:
        """Remove records older than retention period."""
        days = retention_days or self.config.retention_days
        cutoff = time.time() - (days * 86400)
        
        with self._lock:
            original_count = len(self._execution_records)
            self._execution_records = [
                r for r in self._execution_records
                if r.started_at >= cutoff
            ]
            removed = original_count - len(self._execution_records)
            if removed > 0:
                self._dirty = True
            return removed
    
    def export_to_json(self) -> str:
        """Export all statistics to JSON string."""
        with self._lock:
            data = {
                "exported_at": time.time(),
                "summary": self.get_summary(),
                "plugins": {k: v.to_dict() for k, v in self._plugin_stats.items()},
                "recent_records": [r.to_dict() for r in self._execution_records[-1000:]]
            }
            return json.dumps(data, indent=2)
    
    def save_to_disk(self, path: Optional[Path] = None) -> bool:
        """Save statistics to disk."""
        save_path = path or self.config.persistence_path
        if not save_path:
            logger.warning("No persistence path configured for stats")
            return False
        
        try:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with self._lock:
                data = {
                    "version": __version__,
                    "saved_at": time.time(),
                    "started_at": self._started_at,
                    "config": self.config.to_dict(),
                    "plugins": {k: v.to_dict() for k, v in self._plugin_stats.items()},
                    "records": [r.to_dict() for r in self._execution_records]
                }
                self._dirty = False
                self._last_save_time = time.time()
            
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Stats saved to {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save stats: {e}")
            return False
    
    def _load_from_disk(self) -> bool:
        """Load statistics from disk."""
        if not self.config.persistence_path:
            return False
        
        path = Path(self.config.persistence_path)
        if not path.exists():
            return False
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            with self._lock:
                self._started_at = data.get("started_at", time.time())
                
                # Load plugin stats
                for plugin_id, plugin_data in data.get("plugins", {}).items():
                    self._plugin_stats[plugin_id] = PluginStats.from_dict(plugin_data)
                
                # Load recent records
                for record_data in data.get("records", []):
                    self._execution_records.append(ExecutionRecord.from_dict(record_data))
            
            logger.debug(f"Stats loaded from {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load stats: {e}")
            return False
    
    def needs_save(self) -> bool:
        """Check if stats need to be saved."""
        with self._lock:
            return self._dirty
    
    def get_status(self) -> Dict[str, Any]:
        """Get manager status."""
        with self._lock:
            return {
                "enabled": self.config.enabled,
                "tracking_since": self._started_at,
                "plugins_tracked": len(self._plugin_stats),
                "records_in_memory": len(self._execution_records),
                "callbacks_registered": len(self._callbacks),
                "needs_save": self._dirty,
                "last_save": self._last_save_time,
                "persistence_path": str(self.config.persistence_path) if self.config.persistence_path else None
            }


# Global manager instance
_manager: Optional[UsageStatsManager] = None
_manager_lock = threading.Lock()


def get_usage_stats_manager() -> UsageStatsManager:
    """Get the global usage stats manager instance."""
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = UsageStatsManager()
        return _manager


def init_usage_stats_manager(config: Optional[UsageStatsConfig] = None) -> UsageStatsManager:
    """Initialize the global usage stats manager with optional config."""
    global _manager
    with _manager_lock:
        _manager = UsageStatsManager(config)
        return _manager


def reset_usage_stats_manager() -> None:
    """Reset the global manager (for testing)."""
    global _manager
    with _manager_lock:
        _manager = None


# Convenience functions
def record_execution(
    plugin_id: str,
    method: str,
    duration_ms: float,
    status: ExecutionStatus = ExecutionStatus.SUCCESS,
    error_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> ExecutionRecord:
    """Record a plugin execution using the global manager."""
    return get_usage_stats_manager().record_execution(
        plugin_id=plugin_id,
        method=method,
        duration_ms=duration_ms,
        status=status,
        error_type=error_type,
        metadata=metadata
    )


def time_execution(
    plugin_id: str,
    method: str,
    metadata: Optional[Dict[str, Any]] = None
) -> ExecutionTimer:
    """Create a timing context manager using the global manager."""
    return get_usage_stats_manager().time_execution(plugin_id, method, metadata)


def get_plugin_stats(plugin_id: str) -> Optional[PluginStats]:
    """Get stats for a plugin using the global manager."""
    return get_usage_stats_manager().get_plugin_stats(plugin_id)


def get_stats_summary() -> Dict[str, Any]:
    """Get summary using the global manager."""
    return get_usage_stats_manager().get_summary()
