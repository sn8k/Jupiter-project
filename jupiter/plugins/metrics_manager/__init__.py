"""
Metrics Manager Plugin v2 - Jupiter Bridge Architecture

This plugin provides centralized metrics observation, visualization,
and management for Jupiter plugins and core components. It leverages
the MetricsCollector from jupiter.core.bridge.metrics to:
- Display real-time metrics dashboards
- Track plugin health and performance
- Export metrics in various formats (JSON, Prometheus)
- Configure alert thresholds

Conforme à plugins_architecture.md v0.6.0

@version 1.0.0
@module jupiter.plugins.metrics_manager
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime

__version__ = "1.0.0"

# =============================================================================
# BRIDGE REFERENCES (injected during init)
# =============================================================================

_bridge = None
_logger = None


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MetricAlert:
    """Represents a metric alert."""
    metric_name: str
    threshold: float
    current_value: float
    severity: str  # info, warning, critical
    message: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class PluginState:
    """Internal state of the Metrics Manager plugin."""
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    last_collection: Optional[float] = None
    collection_count: int = 0
    error_count: int = 0
    active_alerts: List[MetricAlert] = field(default_factory=list)
    # Track plugin-specific metrics
    api_calls: int = 0
    export_count: int = 0


# =============================================================================
# PLUGIN SINGLETON
# =============================================================================

_state: Optional[PluginState] = None


def _get_state() -> PluginState:
    """Get or create plugin state."""
    global _state
    if _state is None:
        _state = PluginState()
    return _state


# =============================================================================
# PLUGIN LIFECYCLE (Bridge v2 API)
# =============================================================================

def init(bridge) -> None:
    """
    Initialize the Metrics Manager plugin.
    
    Called by Bridge during plugin initialization phase.
    
    Args:
        bridge: Instance du Bridge fournissant les registres et services.
        
    Le Bridge expose un namespace `bridge.services` (§3.3.1) pour accéder
    aux services Jupiter sans importer directement `jupiter.core.*`.
    """
    global _bridge, _logger
    _bridge = bridge
    
    # Get dedicated logger via bridge.services (§3.3.1)
    _logger = bridge.services.get_logger("metrics_manager")
    
    _logger.info("Initializing Metrics Manager plugin v%s", __version__)
    
    # Load plugin config
    state = _get_state()
    try:
        config = bridge.services.get_config("metrics_manager")
        if config:
            state.config = config
            state.enabled = config.get("enabled", True)
    except Exception as e:
        _logger.warning("Failed to load config, using defaults: %s", e)
    
    # Register event handlers for metrics-related events
    try:
        event_bus = bridge.services.get_event_bus()
        if event_bus:
            event_bus.subscribe("plugin.loaded", _on_plugin_loaded)
            event_bus.subscribe("plugin.error", _on_plugin_error)
            event_bus.subscribe("metrics.recorded", _on_metric_recorded)
    except Exception as e:
        _logger.debug("Event bus not available: %s", e)
    
    _logger.info("Metrics Manager plugin initialized successfully")


def shutdown() -> None:
    """
    Shutdown the Metrics Manager plugin.
    
    Called by Bridge during plugin unload.
    """
    global _bridge, _logger
    
    if _logger:
        _logger.info("Shutting down Metrics Manager plugin")
    
    # Unsubscribe from events
    if _bridge:
        try:
            event_bus = _bridge.services.get_event_bus()
            if event_bus:
                event_bus.unsubscribe("plugin.loaded", _on_plugin_loaded)
                event_bus.unsubscribe("plugin.error", _on_plugin_error)
                event_bus.unsubscribe("metrics.recorded", _on_metric_recorded)
        except Exception:
            pass
    
    _bridge = None
    _logger = None


def health() -> Dict[str, Any]:
    """
    Return plugin health status.
    
    Required by Bridge v2 for health checks (§3.5).
    
    Returns:
        Dictionary with health status and details.
    """
    state = _get_state()
    
    # Check metrics collector availability
    collector_healthy = False
    try:
        from jupiter.core.bridge.metrics import get_metrics_collector
        collector = get_metrics_collector()
        if collector:
            collector_healthy = True
    except Exception:
        pass
    
    is_healthy = state.enabled and collector_healthy
    
    return {
        "status": "healthy" if is_healthy else "degraded",
        "enabled": state.enabled,
        "metrics_collector": "available" if collector_healthy else "unavailable",
        "last_collection": state.last_collection,
        "collection_count": state.collection_count,
        "active_alerts": len(state.active_alerts),
        "error_count": state.error_count,
        "version": __version__,
    }


def metrics() -> Dict[str, Any]:
    """
    Return plugin metrics for monitoring.
    
    Exposed via Bridge for `/plugins/<id>/metrics` endpoint (§10.2).
    
    Returns:
        Dictionary with plugin metrics.
    """
    state = _get_state()
    
    return {
        "plugin_id": "metrics_manager",
        "version": __version__,
        "counters": {
            "collections": state.collection_count,
            "api_calls": state.api_calls,
            "exports": state.export_count,
            "errors": state.error_count,
        },
        "gauges": {
            "active_alerts": len(state.active_alerts),
            "enabled": 1 if state.enabled else 0,
        },
        "timestamps": {
            "last_collection": state.last_collection,
        },
    }


def reset_settings() -> Dict[str, Any]:
    """
    Reset plugin settings to defaults.
    
    Returns:
        Result dictionary with success status.
    """
    global _state
    _state = PluginState()
    
    if _logger:
        _logger.info("Metrics Manager settings reset to defaults")
    
    return {
        "success": True,
        "message": "Settings reset to defaults",
    }


# =============================================================================
# EVENT HANDLERS
# =============================================================================

def _on_plugin_loaded(event: Dict[str, Any]) -> None:
    """Handle plugin loaded event."""
    if _logger:
        plugin_id = event.get("plugin_id", "unknown")
        _logger.debug("Plugin loaded event received: %s", plugin_id)


def _on_plugin_error(event: Dict[str, Any]) -> None:
    """Handle plugin error event."""
    state = _get_state()
    state.error_count += 1
    
    if _logger:
        plugin_id = event.get("plugin_id", "unknown")
        error = event.get("error", "unknown error")
        _logger.warning("Plugin error event: %s - %s", plugin_id, error)


def _on_metric_recorded(event: Dict[str, Any]) -> None:
    """Handle metric recorded event."""
    state = _get_state()
    state.collection_count += 1
    state.last_collection = time.time()
    
    # Check for alert thresholds
    _check_alert_thresholds(event)


# =============================================================================
# METRICS OPERATIONS
# =============================================================================

def collect_all_metrics() -> Dict[str, Any]:
    """
    Collect all metrics from the MetricsCollector.
    
    Returns:
        Dictionary with all collected metrics.
    """
    state = _get_state()
    state.collection_count += 1
    state.last_collection = time.time()
    
    try:
        from jupiter.core.bridge.metrics import get_metrics_collector
        collector = get_metrics_collector()
        
        # Collect plugin metrics as well
        collector.collect_plugin_metrics()
        
        return collector.get_all_metrics()
    except Exception as e:
        state.error_count += 1
        if _logger:
            _logger.error("Failed to collect metrics: %s", e)
        return {
            "error": str(e),
            "system": {},
            "metrics": {},
            "plugins": {},
        }


def get_metric_history(name: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get historical data points for a specific metric.
    
    Args:
        name: Metric name
        limit: Maximum points to return
        
    Returns:
        List of metric data points.
    """
    try:
        from jupiter.core.bridge.metrics import get_metrics_collector
        collector = get_metrics_collector()
        
        points = collector.get_metric_history(name, limit)
        return [p.to_dict() for p in points]
    except Exception as e:
        if _logger:
            _logger.error("Failed to get metric history: %s", e)
        return []


def export_metrics(format: str = "json") -> str:
    """
    Export metrics in specified format.
    
    Args:
        format: Export format ('json' or 'prometheus')
        
    Returns:
        Formatted metrics string.
    """
    state = _get_state()
    state.export_count += 1
    
    try:
        from jupiter.core.bridge.metrics import get_metrics_collector
        import json
        
        collector = get_metrics_collector()
        
        if format == "prometheus":
            return collector.to_prometheus()
        else:
            return json.dumps(collector.get_all_metrics(), indent=2, default=str)
    except Exception as e:
        if _logger:
            _logger.error("Failed to export metrics: %s", e)
        return f"Error exporting metrics: {e}"


def get_active_alerts() -> List[Dict[str, Any]]:
    """
    Get list of active metric alerts.
    
    Returns:
        List of alert dictionaries.
    """
    state = _get_state()
    return [asdict(alert) for alert in state.active_alerts]


def clear_alerts() -> Dict[str, Any]:
    """
    Clear all active alerts.
    
    Returns:
        Result dictionary.
    """
    state = _get_state()
    count = len(state.active_alerts)
    state.active_alerts.clear()
    
    if _logger:
        _logger.info("Cleared %d alerts", count)
    
    return {
        "success": True,
        "cleared_count": count,
    }


def _check_alert_thresholds(event: Dict[str, Any]) -> None:
    """Check if metric values exceed configured thresholds."""
    state = _get_state()
    config = state.config
    
    thresholds = config.get("alert_thresholds", {})
    if not thresholds:
        return
    
    metric_name = event.get("name", "")
    value = event.get("value", 0)
    
    # Check error rate
    if "error" in metric_name.lower():
        warn = thresholds.get("error_rate_warn", 0.05)
        crit = thresholds.get("error_rate_critical", 0.15)
        
        if value >= crit:
            _add_alert(metric_name, crit, value, "critical", f"Error rate critical: {value:.2%}")
        elif value >= warn:
            _add_alert(metric_name, warn, value, "warning", f"Error rate warning: {value:.2%}")
    
    # Check response time
    if "duration" in metric_name.lower() or "time" in metric_name.lower():
        warn = thresholds.get("response_time_warn", 1000)
        crit = thresholds.get("response_time_critical", 5000)
        
        if value >= crit:
            _add_alert(metric_name, crit, value, "critical", f"Response time critical: {value}ms")
        elif value >= warn:
            _add_alert(metric_name, warn, value, "warning", f"Response time warning: {value}ms")


def _add_alert(metric_name: str, threshold: float, value: float, severity: str, message: str) -> None:
    """Add a new alert if not already present."""
    state = _get_state()
    
    # Check if alert already exists for this metric
    for alert in state.active_alerts:
        if alert.metric_name == metric_name and alert.severity == severity:
            # Update existing alert
            alert.current_value = value
            alert.timestamp = time.time()
            return
    
    # Add new alert
    alert = MetricAlert(
        metric_name=metric_name,
        threshold=threshold,
        current_value=value,
        severity=severity,
        message=message,
    )
    state.active_alerts.append(alert)
    
    # Keep only last 50 alerts
    if len(state.active_alerts) > 50:
        state.active_alerts = state.active_alerts[-50:]
    
    if _logger:
        _logger.warning("Alert triggered: %s", message)


def record_custom_metric(name: str, value: float, labels: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Record a custom metric.
    
    Args:
        name: Metric name
        value: Metric value
        labels: Optional labels
        
    Returns:
        Result dictionary.
    """
    try:
        from jupiter.core.bridge.metrics import get_metrics_collector
        collector = get_metrics_collector()
        
        collector.record(name, value, labels)
        
        return {
            "success": True,
            "metric": name,
            "value": value,
        }
    except Exception as e:
        if _logger:
            _logger.error("Failed to record metric: %s", e)
        return {
            "success": False,
            "error": str(e),
        }


def reset_metrics() -> Dict[str, Any]:
    """
    Reset all metrics in the collector.
    
    Returns:
        Result dictionary.
    """
    try:
        from jupiter.core.bridge.metrics import get_metrics_collector
        collector = get_metrics_collector()
        
        collector.reset()
        
        state = _get_state()
        state.collection_count = 0
        state.api_calls = 0
        state.export_count = 0
        state.active_alerts.clear()
        
        if _logger:
            _logger.info("All metrics reset")
        
        return {
            "success": True,
            "message": "All metrics have been reset",
        }
    except Exception as e:
        if _logger:
            _logger.error("Failed to reset metrics: %s", e)
        return {
            "success": False,
            "error": str(e),
        }
