"""Alerting System for Jupiter Plugin Bridge.

Version: 0.1.0

This module provides a threshold-based alerting system that monitors
plugin metrics and triggers notifications when thresholds are crossed.

Features:
- Configurable thresholds per metric/plugin
- Support for >, <, >=, <=, == comparisons
- Cooldown periods to prevent notification storms
- Integration with notification system
- Alert history and acknowledgment
- Support for recovery notifications

Usage:
    from jupiter.core.bridge.alerting import (
        get_alerting_manager,
        AlertThreshold,
        ComparisonOperator,
    )
    
    # Get alerting manager
    manager = get_alerting_manager()
    
    # Configure an alert threshold
    threshold = AlertThreshold(
        threshold_id="high_error_rate",
        plugin_id="my_plugin",
        metric_name="error_rate",
        operator=ComparisonOperator.GREATER_THAN,
        threshold_value=10.0,
        notification_type=NotificationType.WARNING,
        cooldown_seconds=300,
    )
    manager.add_threshold(threshold)
    
    # Check metrics against thresholds
    manager.check_all()
"""

from __future__ import annotations

import logging
import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class ComparisonOperator(str, Enum):
    """Comparison operators for threshold evaluation."""
    
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    EQUAL = "eq"
    NOT_EQUAL = "neq"


class AlertSeverity(str, Enum):
    """Severity levels for alerts."""
    
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertState(str, Enum):
    """State of an alert."""
    
    PENDING = "pending"      # Threshold crossed, waiting for confirmation
    FIRING = "firing"        # Alert is active
    RESOLVED = "resolved"    # Value returned to normal
    ACKNOWLEDGED = "acknowledged"  # User acknowledged the alert
    SILENCED = "silenced"    # Alert is silenced by user


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class AlertThreshold:
    """Configuration for a metric threshold that triggers alerts.
    
    Attributes:
        threshold_id: Unique identifier for this threshold
        plugin_id: Plugin this threshold applies to (or "*" for all)
        metric_name: Name of the metric to monitor
        operator: Comparison operator
        threshold_value: Value to compare against
        severity: Alert severity level
        cooldown_seconds: Minimum time between alerts for same threshold
        notify_on_recovery: Whether to send notification when value returns to normal
        description: Human-readable description
        enabled: Whether this threshold is active
    """
    
    threshold_id: str
    plugin_id: str
    metric_name: str
    operator: ComparisonOperator
    threshold_value: float
    severity: AlertSeverity = AlertSeverity.WARNING
    cooldown_seconds: int = 300  # 5 minutes
    notify_on_recovery: bool = True
    description: str = ""
    enabled: bool = True
    
    # Internal tracking
    _last_triggered: Optional[float] = field(default=None, repr=False)
    _last_value: Optional[float] = field(default=None, repr=False)
    _is_firing: bool = field(default=False, repr=False)
    
    def evaluate(self, value: float) -> bool:
        """Evaluate if the threshold is crossed.
        
        Args:
            value: Current metric value
            
        Returns:
            True if threshold is crossed
        """
        if self.operator == ComparisonOperator.GREATER_THAN:
            return value > self.threshold_value
        elif self.operator == ComparisonOperator.GREATER_THAN_OR_EQUAL:
            return value >= self.threshold_value
        elif self.operator == ComparisonOperator.LESS_THAN:
            return value < self.threshold_value
        elif self.operator == ComparisonOperator.LESS_THAN_OR_EQUAL:
            return value <= self.threshold_value
        elif self.operator == ComparisonOperator.EQUAL:
            return value == self.threshold_value
        elif self.operator == ComparisonOperator.NOT_EQUAL:
            return value != self.threshold_value
        return False
    
    def can_trigger(self) -> bool:
        """Check if cooldown has passed since last trigger.
        
        Returns:
            True if alert can be triggered
        """
        if not self.enabled:
            return False
        if self._last_triggered is None:
            return True
        return (time.time() - self._last_triggered) >= self.cooldown_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "threshold_id": self.threshold_id,
            "plugin_id": self.plugin_id,
            "metric_name": self.metric_name,
            "operator": self.operator.value,
            "threshold_value": self.threshold_value,
            "severity": self.severity.value,
            "cooldown_seconds": self.cooldown_seconds,
            "notify_on_recovery": self.notify_on_recovery,
            "description": self.description,
            "enabled": self.enabled,
            "is_firing": self._is_firing,
            "last_triggered": self._last_triggered,
            "last_value": self._last_value,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AlertThreshold":
        """Deserialize from dictionary."""
        threshold = cls(
            threshold_id=data.get("threshold_id", ""),
            plugin_id=data.get("plugin_id", "*"),
            metric_name=data.get("metric_name", ""),
            operator=ComparisonOperator(data.get("operator", "gt")),
            threshold_value=float(data.get("threshold_value", 0)),
            severity=AlertSeverity(data.get("severity", "warning")),
            cooldown_seconds=int(data.get("cooldown_seconds", 300)),
            notify_on_recovery=data.get("notify_on_recovery", True),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
        )
        threshold._last_triggered = data.get("last_triggered")
        threshold._last_value = data.get("last_value")
        threshold._is_firing = data.get("is_firing", False)
        return threshold


@dataclass
class Alert:
    """A triggered alert instance.
    
    Attributes:
        alert_id: Unique identifier for this alert instance
        threshold_id: ID of the threshold that triggered this alert
        plugin_id: Plugin that triggered the alert
        metric_name: Metric that crossed the threshold
        metric_value: Value that crossed the threshold
        threshold_value: The threshold value
        severity: Alert severity
        state: Current state of the alert
        created_at: When the alert was created
        resolved_at: When the alert was resolved (if applicable)
        acknowledged_at: When the alert was acknowledged (if applicable)
        acknowledged_by: Who acknowledged the alert (if applicable)
        message: Alert message
    """
    
    alert_id: str
    threshold_id: str
    plugin_id: str
    metric_name: str
    metric_value: float
    threshold_value: float
    severity: AlertSeverity
    state: AlertState = AlertState.FIRING
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    acknowledged_at: Optional[float] = None
    acknowledged_by: Optional[str] = None
    message: str = ""
    
    def acknowledge(self, user: str = "system") -> None:
        """Acknowledge this alert."""
        self.state = AlertState.ACKNOWLEDGED
        self.acknowledged_at = time.time()
        self.acknowledged_by = user
    
    def resolve(self) -> None:
        """Mark this alert as resolved."""
        self.state = AlertState.RESOLVED
        self.resolved_at = time.time()
    
    def silence(self) -> None:
        """Silence this alert."""
        self.state = AlertState.SILENCED
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "alert_id": self.alert_id,
            "threshold_id": self.threshold_id,
            "plugin_id": self.plugin_id,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "threshold_value": self.threshold_value,
            "severity": self.severity.value,
            "state": self.state.value,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "acknowledged_at": self.acknowledged_at,
            "acknowledged_by": self.acknowledged_by,
            "message": self.message,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Alert":
        """Deserialize from dictionary."""
        return cls(
            alert_id=data.get("alert_id", ""),
            threshold_id=data.get("threshold_id", ""),
            plugin_id=data.get("plugin_id", ""),
            metric_name=data.get("metric_name", ""),
            metric_value=float(data.get("metric_value", 0)),
            threshold_value=float(data.get("threshold_value", 0)),
            severity=AlertSeverity(data.get("severity", "warning")),
            state=AlertState(data.get("state", "firing")),
            created_at=data.get("created_at", time.time()),
            resolved_at=data.get("resolved_at"),
            acknowledged_at=data.get("acknowledged_at"),
            acknowledged_by=data.get("acknowledged_by"),
            message=data.get("message", ""),
        )


# =============================================================================
# Alerting Manager
# =============================================================================

class AlertingManager:
    """Manager for threshold-based alerting.
    
    This class handles:
    - Registration and management of alert thresholds
    - Evaluation of metrics against thresholds
    - Triggering notifications when thresholds are crossed
    - Alert history and acknowledgment
    - Persistence of configuration and state
    """
    
    def __init__(
        self,
        persist_path: Optional[Path] = None,
        notification_callback: Optional[Callable[[Alert], None]] = None,
    ):
        """Initialize the alerting manager.
        
        Args:
            persist_path: Path to persist thresholds and alerts
            notification_callback: Callback to send notifications
        """
        self._thresholds: Dict[str, AlertThreshold] = {}
        self._alerts: Dict[str, Alert] = {}  # alert_id -> Alert
        self._alert_history: List[Alert] = []  # Historical alerts
        self._lock = threading.Lock()
        self._persist_path = persist_path
        self._notification_callback = notification_callback
        self._max_history = 1000
        
        # Statistics
        self._stats = {
            "alerts_triggered": 0,
            "alerts_resolved": 0,
            "alerts_acknowledged": 0,
            "checks_performed": 0,
        }
        
        # Load persisted state
        if persist_path:
            self._load_state()
        
        logger.debug("AlertingManager initialized")
    
    # -------------------------------------------------------------------------
    # Threshold Management
    # -------------------------------------------------------------------------
    
    def add_threshold(self, threshold: AlertThreshold) -> None:
        """Add or update an alert threshold.
        
        Args:
            threshold: The threshold to add
        """
        with self._lock:
            self._thresholds[threshold.threshold_id] = threshold
            logger.info(
                "Added threshold %s: %s %s %s for %s",
                threshold.threshold_id,
                threshold.metric_name,
                threshold.operator.value,
                threshold.threshold_value,
                threshold.plugin_id,
            )
            self._persist_state()
    
    def remove_threshold(self, threshold_id: str) -> bool:
        """Remove an alert threshold.
        
        Args:
            threshold_id: ID of threshold to remove
            
        Returns:
            True if threshold was removed
        """
        with self._lock:
            if threshold_id in self._thresholds:
                del self._thresholds[threshold_id]
                logger.info("Removed threshold %s", threshold_id)
                self._persist_state()
                return True
            return False
    
    def get_threshold(self, threshold_id: str) -> Optional[AlertThreshold]:
        """Get a specific threshold.
        
        Args:
            threshold_id: ID of threshold
            
        Returns:
            The threshold or None
        """
        return self._thresholds.get(threshold_id)
    
    def list_thresholds(
        self,
        plugin_id: Optional[str] = None,
        enabled_only: bool = False,
    ) -> List[AlertThreshold]:
        """List all thresholds, optionally filtered.
        
        Args:
            plugin_id: Filter by plugin ID
            enabled_only: Only return enabled thresholds
            
        Returns:
            List of thresholds
        """
        thresholds = list(self._thresholds.values())
        
        if plugin_id:
            thresholds = [
                t for t in thresholds
                if t.plugin_id == plugin_id or t.plugin_id == "*"
            ]
        
        if enabled_only:
            thresholds = [t for t in thresholds if t.enabled]
        
        return thresholds
    
    def enable_threshold(self, threshold_id: str) -> bool:
        """Enable a threshold.
        
        Args:
            threshold_id: ID of threshold
            
        Returns:
            True if threshold was enabled
        """
        with self._lock:
            if threshold_id in self._thresholds:
                self._thresholds[threshold_id].enabled = True
                self._persist_state()
                return True
            return False
    
    def disable_threshold(self, threshold_id: str) -> bool:
        """Disable a threshold.
        
        Args:
            threshold_id: ID of threshold
            
        Returns:
            True if threshold was disabled
        """
        with self._lock:
            if threshold_id in self._thresholds:
                self._thresholds[threshold_id].enabled = False
                self._persist_state()
                return True
            return False
    
    # -------------------------------------------------------------------------
    # Metric Evaluation
    # -------------------------------------------------------------------------
    
    def check_metric(
        self,
        plugin_id: str,
        metric_name: str,
        value: float,
    ) -> List[Alert]:
        """Check a metric value against all applicable thresholds.
        
        Args:
            plugin_id: Plugin that owns the metric
            metric_name: Name of the metric
            value: Current metric value
            
        Returns:
            List of triggered alerts
        """
        triggered_alerts = []
        
        with self._lock:
            self._stats["checks_performed"] += 1
            
            # Find applicable thresholds
            applicable = [
                t for t in self._thresholds.values()
                if t.enabled
                and t.metric_name == metric_name
                and (t.plugin_id == plugin_id or t.plugin_id == "*")
            ]
            
            for threshold in applicable:
                crossed = threshold.evaluate(value)
                
                if crossed and not threshold._is_firing:
                    # Threshold newly crossed
                    if threshold.can_trigger():
                        alert = self._trigger_alert(threshold, plugin_id, value)
                        triggered_alerts.append(alert)
                        threshold._is_firing = True
                        threshold._last_triggered = time.time()
                
                elif not crossed and threshold._is_firing:
                    # Value returned to normal - resolve
                    if threshold.notify_on_recovery:
                        self._resolve_alerts_for_threshold(
                            threshold.threshold_id,
                            plugin_id,
                        )
                    threshold._is_firing = False
                
                threshold._last_value = value
        
        return triggered_alerts
    
    def check_all_from_metrics_collector(self) -> List[Alert]:
        """Check all metrics from the global metrics collector.
        
        Returns:
            List of triggered alerts
        """
        try:
            from jupiter.core.bridge.metrics import get_metrics_collector
            
            collector = get_metrics_collector()
            all_metrics = collector.get_all_metrics()
            
            triggered = []
            
            # Check plugin metrics
            plugin_metrics = all_metrics.get("plugins", {})
            for plugin_id, metrics in plugin_metrics.items():
                for metric_name, value in metrics.items():
                    if isinstance(value, (int, float)):
                        alerts = self.check_metric(plugin_id, metric_name, value)
                        triggered.extend(alerts)
            
            # Check system metrics
            system_metrics = all_metrics.get("system", {})
            for metric_name, value in system_metrics.items():
                if isinstance(value, (int, float)):
                    alerts = self.check_metric("system", metric_name, value)
                    triggered.extend(alerts)
            
            return triggered
            
        except ImportError:
            logger.debug("Metrics collector not available")
            return []
    
    def _trigger_alert(
        self,
        threshold: AlertThreshold,
        plugin_id: str,
        value: float,
    ) -> Alert:
        """Create and trigger an alert.
        
        Args:
            threshold: The threshold that was crossed
            plugin_id: Plugin ID
            value: The value that crossed the threshold
            
        Returns:
            The created alert
        """
        from uuid import uuid4
        
        alert = Alert(
            alert_id=str(uuid4()),
            threshold_id=threshold.threshold_id,
            plugin_id=plugin_id,
            metric_name=threshold.metric_name,
            metric_value=value,
            threshold_value=threshold.threshold_value,
            severity=threshold.severity,
            message=self._format_alert_message(threshold, plugin_id, value),
        )
        
        self._alerts[alert.alert_id] = alert
        self._stats["alerts_triggered"] += 1
        
        logger.warning(
            "Alert triggered: %s - %s %s %s (actual: %s)",
            alert.alert_id,
            threshold.metric_name,
            threshold.operator.value,
            threshold.threshold_value,
            value,
        )
        
        # Send notification
        if self._notification_callback:
            try:
                self._notification_callback(alert)
            except Exception as e:
                logger.error("Failed to send alert notification: %s", e)
        
        self._persist_state()
        return alert
    
    def _format_alert_message(
        self,
        threshold: AlertThreshold,
        plugin_id: str,
        value: float,
    ) -> str:
        """Format an alert message.
        
        Args:
            threshold: The threshold
            plugin_id: Plugin ID
            value: Current value
            
        Returns:
            Formatted message
        """
        op_symbols = {
            ComparisonOperator.GREATER_THAN: ">",
            ComparisonOperator.GREATER_THAN_OR_EQUAL: ">=",
            ComparisonOperator.LESS_THAN: "<",
            ComparisonOperator.LESS_THAN_OR_EQUAL: "<=",
            ComparisonOperator.EQUAL: "==",
            ComparisonOperator.NOT_EQUAL: "!=",
        }
        op = op_symbols.get(threshold.operator, "?")
        
        if threshold.description:
            return f"{threshold.description} (Plugin: {plugin_id}, Value: {value} {op} {threshold.threshold_value})"
        
        return f"Alert: {threshold.metric_name} = {value} {op} {threshold.threshold_value} for plugin {plugin_id}"
    
    def _resolve_alerts_for_threshold(
        self,
        threshold_id: str,
        plugin_id: str,
    ) -> List[Alert]:
        """Resolve all firing alerts for a threshold.
        
        Args:
            threshold_id: Threshold ID
            plugin_id: Plugin ID
            
        Returns:
            List of resolved alerts
        """
        resolved = []
        
        for alert in list(self._alerts.values()):
            if (
                alert.threshold_id == threshold_id
                and alert.plugin_id == plugin_id
                and alert.state == AlertState.FIRING
            ):
                alert.resolve()
                resolved.append(alert)
                self._stats["alerts_resolved"] += 1
                
                # Move to history
                self._alert_history.append(alert)
                del self._alerts[alert.alert_id]
                
                logger.info("Alert resolved: %s", alert.alert_id)
                
                # Send recovery notification
                if self._notification_callback:
                    try:
                        self._notification_callback(alert)
                    except Exception as e:
                        logger.error("Failed to send recovery notification: %s", e)
        
        # Trim history
        if len(self._alert_history) > self._max_history:
            self._alert_history = self._alert_history[-self._max_history:]
        
        self._persist_state()
        return resolved
    
    # -------------------------------------------------------------------------
    # Alert Management
    # -------------------------------------------------------------------------
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get a specific alert.
        
        Args:
            alert_id: Alert ID
            
        Returns:
            The alert or None
        """
        return self._alerts.get(alert_id)
    
    def list_alerts(
        self,
        plugin_id: Optional[str] = None,
        severity: Optional[AlertSeverity] = None,
        state: Optional[AlertState] = None,
    ) -> List[Alert]:
        """List active alerts with optional filters.
        
        Args:
            plugin_id: Filter by plugin
            severity: Filter by severity
            state: Filter by state
            
        Returns:
            List of alerts
        """
        alerts = list(self._alerts.values())
        
        if plugin_id:
            alerts = [a for a in alerts if a.plugin_id == plugin_id]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if state:
            alerts = [a for a in alerts if a.state == state]
        
        return sorted(alerts, key=lambda a: a.created_at, reverse=True)
    
    def acknowledge_alert(self, alert_id: str, user: str = "system") -> bool:
        """Acknowledge an alert.
        
        Args:
            alert_id: Alert ID
            user: User who acknowledged
            
        Returns:
            True if alert was acknowledged
        """
        with self._lock:
            if alert_id in self._alerts:
                self._alerts[alert_id].acknowledge(user)
                self._stats["alerts_acknowledged"] += 1
                self._persist_state()
                return True
            return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Manually resolve an alert.
        
        Args:
            alert_id: Alert ID
            
        Returns:
            True if alert was resolved
        """
        with self._lock:
            if alert_id in self._alerts:
                alert = self._alerts[alert_id]
                alert.resolve()
                self._stats["alerts_resolved"] += 1
                
                # Move to history
                self._alert_history.append(alert)
                del self._alerts[alert_id]
                
                self._persist_state()
                return True
            return False
    
    def silence_alert(self, alert_id: str) -> bool:
        """Silence an alert.
        
        Args:
            alert_id: Alert ID
            
        Returns:
            True if alert was silenced
        """
        with self._lock:
            if alert_id in self._alerts:
                self._alerts[alert_id].silence()
                self._persist_state()
                return True
            return False
    
    def get_alert_history(
        self,
        limit: int = 100,
        plugin_id: Optional[str] = None,
    ) -> List[Alert]:
        """Get alert history.
        
        Args:
            limit: Maximum number of alerts to return
            plugin_id: Filter by plugin
            
        Returns:
            List of historical alerts
        """
        history = self._alert_history
        
        if plugin_id:
            history = [a for a in history if a.plugin_id == plugin_id]
        
        return sorted(history, key=lambda a: a.created_at, reverse=True)[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get alerting statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            **self._stats,
            "active_alerts": len(self._alerts),
            "thresholds_count": len(self._thresholds),
            "history_count": len(self._alert_history),
            "firing_thresholds": sum(
                1 for t in self._thresholds.values() if t._is_firing
            ),
        }
    
    # -------------------------------------------------------------------------
    # Default Thresholds
    # -------------------------------------------------------------------------
    
    def add_default_thresholds(self) -> None:
        """Add sensible default thresholds for common metrics."""
        defaults = [
            AlertThreshold(
                threshold_id="high_error_rate",
                plugin_id="*",
                metric_name="error_count",
                operator=ComparisonOperator.GREATER_THAN,
                threshold_value=10,
                severity=AlertSeverity.WARNING,
                cooldown_seconds=600,
                description="High error count detected",
            ),
            AlertThreshold(
                threshold_id="critical_error_rate",
                plugin_id="*",
                metric_name="error_count",
                operator=ComparisonOperator.GREATER_THAN,
                threshold_value=50,
                severity=AlertSeverity.CRITICAL,
                cooldown_seconds=300,
                description="Critical error count exceeded",
            ),
            AlertThreshold(
                threshold_id="low_request_count",
                plugin_id="*",
                metric_name="request_count",
                operator=ComparisonOperator.LESS_THAN,
                threshold_value=1,
                severity=AlertSeverity.INFO,
                cooldown_seconds=3600,
                description="Plugin has no recent activity",
                enabled=False,  # Disabled by default
            ),
        ]
        
        for threshold in defaults:
            if threshold.threshold_id not in self._thresholds:
                self.add_threshold(threshold)
    
    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------
    
    def _persist_state(self) -> None:
        """Persist thresholds and alerts to disk."""
        if not self._persist_path:
            return
        
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            
            state = {
                "thresholds": [t.to_dict() for t in self._thresholds.values()],
                "alerts": [a.to_dict() for a in self._alerts.values()],
                "history": [a.to_dict() for a in self._alert_history[-100:]],  # Last 100
                "stats": self._stats,
            }
            
            with open(self._persist_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            
        except Exception as e:
            logger.error("Failed to persist alerting state: %s", e)
    
    def _load_state(self) -> None:
        """Load thresholds and alerts from disk."""
        if not self._persist_path or not self._persist_path.exists():
            return
        
        try:
            with open(self._persist_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            
            # Load thresholds
            for data in state.get("thresholds", []):
                try:
                    threshold = AlertThreshold.from_dict(data)
                    self._thresholds[threshold.threshold_id] = threshold
                except Exception as e:
                    logger.warning("Failed to load threshold: %s", e)
            
            # Load active alerts
            for data in state.get("alerts", []):
                try:
                    alert = Alert.from_dict(data)
                    self._alerts[alert.alert_id] = alert
                except Exception as e:
                    logger.warning("Failed to load alert: %s", e)
            
            # Load history
            for data in state.get("history", []):
                try:
                    alert = Alert.from_dict(data)
                    self._alert_history.append(alert)
                except Exception as e:
                    logger.warning("Failed to load historical alert: %s", e)
            
            # Load stats
            self._stats.update(state.get("stats", {}))
            
            logger.info(
                "Loaded alerting state: %d thresholds, %d active alerts",
                len(self._thresholds),
                len(self._alerts),
            )
            
        except Exception as e:
            logger.error("Failed to load alerting state: %s", e)


# =============================================================================
# Global Instance
# =============================================================================

_alerting_manager: Optional[AlertingManager] = None
_alerting_lock = threading.Lock()


def get_alerting_manager() -> AlertingManager:
    """Get or create the global alerting manager.
    
    Returns:
        The global AlertingManager instance
    """
    global _alerting_manager
    
    with _alerting_lock:
        if _alerting_manager is None:
            # Default persist path
            persist_path = Path.home() / ".jupiter" / "alerting.json"
            _alerting_manager = AlertingManager(persist_path=persist_path)
            _alerting_manager.add_default_thresholds()
        
        return _alerting_manager


def init_alerting_manager(
    persist_path: Optional[Path] = None,
    notification_callback: Optional[Callable[[Alert], None]] = None,
) -> AlertingManager:
    """Initialize the global alerting manager with custom settings.
    
    Args:
        persist_path: Path to persist state
        notification_callback: Callback for sending notifications
        
    Returns:
        The initialized AlertingManager
    """
    global _alerting_manager
    
    with _alerting_lock:
        _alerting_manager = AlertingManager(
            persist_path=persist_path,
            notification_callback=notification_callback,
        )
        _alerting_manager.add_default_thresholds()
        return _alerting_manager


def reset_alerting_manager() -> None:
    """Reset the global alerting manager (for testing)."""
    global _alerting_manager
    
    with _alerting_lock:
        _alerting_manager = None


# =============================================================================
# Convenience Functions
# =============================================================================

def add_threshold(threshold: AlertThreshold) -> None:
    """Add a threshold to the global manager."""
    get_alerting_manager().add_threshold(threshold)


def remove_threshold(threshold_id: str) -> bool:
    """Remove a threshold from the global manager."""
    return get_alerting_manager().remove_threshold(threshold_id)


def check_metric(plugin_id: str, metric_name: str, value: float) -> List[Alert]:
    """Check a metric against all applicable thresholds."""
    return get_alerting_manager().check_metric(plugin_id, metric_name, value)


def check_all() -> List[Alert]:
    """Check all metrics from the collector against thresholds."""
    return get_alerting_manager().check_all_from_metrics_collector()


def list_alerts(
    plugin_id: Optional[str] = None,
    severity: Optional[AlertSeverity] = None,
) -> List[Alert]:
    """List active alerts."""
    return get_alerting_manager().list_alerts(plugin_id=plugin_id, severity=severity)


def acknowledge_alert(alert_id: str, user: str = "system") -> bool:
    """Acknowledge an alert."""
    return get_alerting_manager().acknowledge_alert(alert_id, user)
