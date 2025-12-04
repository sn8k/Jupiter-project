"""Plugin notification system for Jupiter Bridge.

Version: 0.1.0

This module provides a notification system for plugins to emit
notifications that can be displayed as toasts, badges, or alerts
in the WebUI.

Features:
- Multiple notification types (info, warning, error, action_required)
- Per-plugin notification channels
- User preferences for notification filtering
- Notification history and persistence
- Badge counters for unread notifications
- WebSocket integration for real-time delivery
"""

import logging
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class NotificationType(Enum):
    """Types of notifications."""
    
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    ACTION_REQUIRED = "action_required"


class NotificationPriority(Enum):
    """Priority levels for notifications."""
    
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationChannel(Enum):
    """Delivery channels for notifications."""
    
    TOAST = "toast"  # Temporary popup
    BADGE = "badge"  # Icon badge counter
    ALERT = "alert"  # Persistent alert bar
    SILENT = "silent"  # No UI, just logged


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class NotificationAction:
    """An action button that can be attached to a notification."""
    
    action_id: str
    label: str  # i18n key or text
    callback_endpoint: Optional[str] = None  # API endpoint to call
    callback_data: Dict[str, Any] = field(default_factory=dict)
    style: str = "default"  # default, primary, danger
    closes_notification: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "action_id": self.action_id,
            "label": self.label,
            "callback_endpoint": self.callback_endpoint,
            "callback_data": self.callback_data,
            "style": self.style,
            "closes_notification": self.closes_notification,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotificationAction":
        """Deserialize from dictionary."""
        return cls(
            action_id=data.get("action_id", ""),
            label=data.get("label", ""),
            callback_endpoint=data.get("callback_endpoint"),
            callback_data=data.get("callback_data", {}),
            style=data.get("style", "default"),
            closes_notification=data.get("closes_notification", True),
        )


@dataclass
class Notification:
    """A notification emitted by a plugin."""
    
    notification_id: str
    plugin_id: str
    notification_type: NotificationType
    title: str  # i18n key or text
    message: str  # i18n key or text
    priority: NotificationPriority = NotificationPriority.NORMAL
    channel: NotificationChannel = NotificationChannel.TOAST
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Optional fields
    icon: Optional[str] = None  # Icon name or URL
    actions: List[NotificationAction] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Display options
    duration_ms: int = 5000  # Auto-dismiss after (0 = persistent)
    dismissible: bool = True
    
    # State
    read: bool = False
    dismissed: bool = False
    actioned: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "notification_id": self.notification_id,
            "plugin_id": self.plugin_id,
            "type": self.notification_type.value,
            "title": self.title,
            "message": self.message,
            "priority": self.priority.value,
            "channel": self.channel.value,
            "timestamp": self.timestamp.isoformat(),
            "icon": self.icon,
            "actions": [a.to_dict() for a in self.actions],
            "metadata": self.metadata,
            "duration_ms": self.duration_ms,
            "dismissible": self.dismissible,
            "read": self.read,
            "dismissed": self.dismissed,
            "actioned": self.actioned,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Notification":
        """Deserialize from dictionary."""
        return cls(
            notification_id=data.get("notification_id", str(uuid4())),
            plugin_id=data.get("plugin_id", ""),
            notification_type=NotificationType(data.get("type", "info")),
            title=data.get("title", ""),
            message=data.get("message", ""),
            priority=NotificationPriority(data.get("priority", "normal")),
            channel=NotificationChannel(data.get("channel", "toast")),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            icon=data.get("icon"),
            actions=[NotificationAction.from_dict(a) for a in data.get("actions", [])],
            metadata=data.get("metadata", {}),
            duration_ms=data.get("duration_ms", 5000),
            dismissible=data.get("dismissible", True),
            read=data.get("read", False),
            dismissed=data.get("dismissed", False),
            actioned=data.get("actioned", False),
        )


@dataclass
class PluginNotificationPreferences:
    """User preferences for a specific plugin's notifications."""
    
    plugin_id: str
    enabled: bool = True
    allowed_types: Set[NotificationType] = field(
        default_factory=lambda: set(NotificationType)
    )
    allowed_channels: Set[NotificationChannel] = field(
        default_factory=lambda: set(NotificationChannel)
    )
    min_priority: NotificationPriority = NotificationPriority.LOW
    muted_until: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "plugin_id": self.plugin_id,
            "enabled": self.enabled,
            "allowed_types": [t.value for t in self.allowed_types],
            "allowed_channels": [c.value for c in self.allowed_channels],
            "min_priority": self.min_priority.value,
            "muted_until": self.muted_until.isoformat() if self.muted_until else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginNotificationPreferences":
        """Deserialize from dictionary."""
        return cls(
            plugin_id=data.get("plugin_id", ""),
            enabled=data.get("enabled", True),
            allowed_types={NotificationType(t) for t in data.get("allowed_types", [t.value for t in NotificationType])},
            allowed_channels={NotificationChannel(c) for c in data.get("allowed_channels", [c.value for c in NotificationChannel])},
            min_priority=NotificationPriority(data.get("min_priority", "low")),
            muted_until=datetime.fromisoformat(data["muted_until"]) if data.get("muted_until") else None,
        )


@dataclass
class NotificationConfig:
    """Global notification configuration."""
    
    enabled: bool = True
    max_history: int = 100
    max_unread: int = 50
    default_duration_ms: int = 5000
    global_muted: bool = False
    global_muted_until: Optional[datetime] = None
    plugin_preferences: Dict[str, PluginNotificationPreferences] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "enabled": self.enabled,
            "max_history": self.max_history,
            "max_unread": self.max_unread,
            "default_duration_ms": self.default_duration_ms,
            "global_muted": self.global_muted,
            "global_muted_until": self.global_muted_until.isoformat() if self.global_muted_until else None,
            "plugin_preferences": {k: v.to_dict() for k, v in self.plugin_preferences.items()},
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotificationConfig":
        """Deserialize from dictionary."""
        return cls(
            enabled=data.get("enabled", True),
            max_history=data.get("max_history", 100),
            max_unread=data.get("max_unread", 50),
            default_duration_ms=data.get("default_duration_ms", 5000),
            global_muted=data.get("global_muted", False),
            global_muted_until=datetime.fromisoformat(data["global_muted_until"]) if data.get("global_muted_until") else None,
            plugin_preferences={
                k: PluginNotificationPreferences.from_dict(v)
                for k, v in data.get("plugin_preferences", {}).items()
            },
        )


# =============================================================================
# Notification Manager
# =============================================================================

class NotificationManager:
    """Central manager for plugin notifications.
    
    Handles notification emission, filtering, storage, and delivery.
    """
    
    def __init__(
        self,
        config: Optional[NotificationConfig] = None,
        config_path: Optional[Path] = None,
    ):
        """Initialize the notification manager.
        
        Args:
            config: Optional configuration
            config_path: Path to persist configuration
        """
        self._config = config or NotificationConfig()
        self._config_path = config_path
        self._lock = threading.RLock()  # Reentrant lock for nested calls
        
        # Notification storage
        self._notifications: List[Notification] = []
        self._unread_count: Dict[str, int] = {}  # plugin_id -> count
        
        # Callbacks for delivery
        self._delivery_callbacks: List[Callable[[Notification], None]] = []
        
        # Statistics
        self._stats = {
            "total_emitted": 0,
            "total_filtered": 0,
            "total_delivered": 0,
            "by_type": {t.value: 0 for t in NotificationType},
            "by_plugin": {},
        }
        
        # Load config if path provided
        if config_path and config_path.exists():
            self._load_config()
    
    # -------------------------------------------------------------------------
    # Configuration
    # -------------------------------------------------------------------------
    
    @property
    def config(self) -> NotificationConfig:
        """Get current configuration."""
        return self._config
    
    def update_config(self, config: NotificationConfig) -> None:
        """Update configuration."""
        with self._lock:
            self._config = config
            self._save_config()
    
    def _load_config(self) -> None:
        """Load configuration from file."""
        if not self._config_path:
            return
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._config = NotificationConfig.from_dict(data.get("config", {}))
            # Load notifications history
            for n_data in data.get("notifications", []):
                self._notifications.append(Notification.from_dict(n_data))
            logger.debug(f"Loaded notification config from {self._config_path}")
        except Exception as e:
            logger.warning(f"Failed to load notification config: {e}")
    
    def _save_config(self) -> None:
        """Save configuration to file."""
        if not self._config_path:
            return
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "config": self._config.to_dict(),
                "notifications": [n.to_dict() for n in self._notifications[-self._config.max_history:]],
            }
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save notification config: {e}")
    
    # -------------------------------------------------------------------------
    # Plugin Preferences
    # -------------------------------------------------------------------------
    
    def get_plugin_preferences(self, plugin_id: str) -> PluginNotificationPreferences:
        """Get notification preferences for a plugin."""
        with self._lock:
            if plugin_id not in self._config.plugin_preferences:
                self._config.plugin_preferences[plugin_id] = PluginNotificationPreferences(
                    plugin_id=plugin_id
                )
            return self._config.plugin_preferences[plugin_id]
    
    def set_plugin_preferences(
        self,
        plugin_id: str,
        preferences: PluginNotificationPreferences,
    ) -> None:
        """Set notification preferences for a plugin."""
        with self._lock:
            self._config.plugin_preferences[plugin_id] = preferences
            self._save_config()
    
    def disable_plugin_notifications(self, plugin_id: str) -> None:
        """Disable all notifications from a plugin."""
        prefs = self.get_plugin_preferences(plugin_id)
        prefs.enabled = False
        self.set_plugin_preferences(plugin_id, prefs)
    
    def enable_plugin_notifications(self, plugin_id: str) -> None:
        """Enable notifications from a plugin."""
        prefs = self.get_plugin_preferences(plugin_id)
        prefs.enabled = True
        self.set_plugin_preferences(plugin_id, prefs)
    
    def mute_plugin(self, plugin_id: str, until: Optional[datetime] = None) -> None:
        """Temporarily mute a plugin's notifications."""
        prefs = self.get_plugin_preferences(plugin_id)
        prefs.muted_until = until
        self.set_plugin_preferences(plugin_id, prefs)
    
    def unmute_plugin(self, plugin_id: str) -> None:
        """Unmute a plugin's notifications."""
        prefs = self.get_plugin_preferences(plugin_id)
        prefs.muted_until = None
        self.set_plugin_preferences(plugin_id, prefs)
    
    # -------------------------------------------------------------------------
    # Global Muting
    # -------------------------------------------------------------------------
    
    def mute_all(self, until: Optional[datetime] = None) -> None:
        """Mute all notifications globally."""
        with self._lock:
            self._config.global_muted = True
            self._config.global_muted_until = until
            self._save_config()
    
    def unmute_all(self) -> None:
        """Unmute all notifications globally."""
        with self._lock:
            self._config.global_muted = False
            self._config.global_muted_until = None
            self._save_config()
    
    def is_muted(self) -> bool:
        """Check if notifications are globally muted."""
        if not self._config.global_muted:
            return False
        if self._config.global_muted_until:
            if datetime.now() > self._config.global_muted_until:
                self.unmute_all()
                return False
        return True
    
    # -------------------------------------------------------------------------
    # Notification Emission
    # -------------------------------------------------------------------------
    
    def emit(
        self,
        plugin_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channel: NotificationChannel = NotificationChannel.TOAST,
        icon: Optional[str] = None,
        actions: Optional[List[NotificationAction]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        dismissible: bool = True,
    ) -> Optional[Notification]:
        """Emit a notification from a plugin.
        
        Args:
            plugin_id: ID of the emitting plugin
            notification_type: Type of notification
            title: Title (i18n key or text)
            message: Message (i18n key or text)
            priority: Priority level
            channel: Delivery channel
            icon: Optional icon
            actions: Optional action buttons
            metadata: Optional metadata
            duration_ms: Auto-dismiss duration (None for default)
            dismissible: Whether user can dismiss
            
        Returns:
            The created notification if delivered, None if filtered
        """
        with self._lock:
            self._stats["total_emitted"] += 1
            self._stats["by_type"][notification_type.value] += 1
            
            if plugin_id not in self._stats["by_plugin"]:
                self._stats["by_plugin"][plugin_id] = 0
            self._stats["by_plugin"][plugin_id] += 1
            
            # Check if should be filtered
            if not self._should_deliver(plugin_id, notification_type, priority):
                self._stats["total_filtered"] += 1
                logger.debug(f"Notification filtered: {plugin_id}/{notification_type.value}")
                return None
            
            # Create notification
            notification = Notification(
                notification_id=str(uuid4()),
                plugin_id=plugin_id,
                notification_type=notification_type,
                title=title,
                message=message,
                priority=priority,
                channel=channel,
                icon=icon,
                actions=actions or [],
                metadata=metadata or {},
                duration_ms=duration_ms if duration_ms is not None else self._config.default_duration_ms,
                dismissible=dismissible,
            )
            
            # Store notification
            self._notifications.append(notification)
            self._trim_history()
            
            # Update unread count
            if plugin_id not in self._unread_count:
                self._unread_count[plugin_id] = 0
            self._unread_count[plugin_id] += 1
            
            # Deliver to callbacks
            self._deliver(notification)
            self._stats["total_delivered"] += 1
            
            self._save_config()
            
            logger.debug(f"Notification emitted: {notification.notification_id}")
            return notification
    
    def _should_deliver(
        self,
        plugin_id: str,
        notification_type: NotificationType,
        priority: NotificationPriority,
    ) -> bool:
        """Check if a notification should be delivered."""
        # Global checks
        if not self._config.enabled:
            return False
        
        if self.is_muted():
            return False
        
        # Plugin-specific checks
        prefs = self._config.plugin_preferences.get(plugin_id)
        if prefs:
            if not prefs.enabled:
                return False
            
            # Check muted status
            if prefs.muted_until:
                if datetime.now() < prefs.muted_until:
                    return False
            
            # Check type filter
            if notification_type not in prefs.allowed_types:
                return False
            
            # Check priority filter
            priority_order = list(NotificationPriority)
            if priority_order.index(priority) < priority_order.index(prefs.min_priority):
                return False
        
        return True
    
    def _deliver(self, notification: Notification) -> None:
        """Deliver notification to registered callbacks."""
        for callback in self._delivery_callbacks:
            try:
                callback(notification)
            except Exception as e:
                logger.error(f"Notification delivery callback error: {e}")
    
    def _trim_history(self) -> None:
        """Trim notification history to max size."""
        if len(self._notifications) > self._config.max_history:
            excess = len(self._notifications) - self._config.max_history
            self._notifications = self._notifications[excess:]
    
    # -------------------------------------------------------------------------
    # Convenience Emission Methods
    # -------------------------------------------------------------------------
    
    def info(
        self,
        plugin_id: str,
        title: str,
        message: str,
        **kwargs: Any,
    ) -> Optional[Notification]:
        """Emit an info notification."""
        return self.emit(plugin_id, NotificationType.INFO, title, message, **kwargs)
    
    def success(
        self,
        plugin_id: str,
        title: str,
        message: str,
        **kwargs: Any,
    ) -> Optional[Notification]:
        """Emit a success notification."""
        return self.emit(plugin_id, NotificationType.SUCCESS, title, message, **kwargs)
    
    def warning(
        self,
        plugin_id: str,
        title: str,
        message: str,
        **kwargs: Any,
    ) -> Optional[Notification]:
        """Emit a warning notification."""
        return self.emit(
            plugin_id,
            NotificationType.WARNING,
            title,
            message,
            priority=NotificationPriority.HIGH,
            **kwargs,
        )
    
    def error(
        self,
        plugin_id: str,
        title: str,
        message: str,
        **kwargs: Any,
    ) -> Optional[Notification]:
        """Emit an error notification."""
        return self.emit(
            plugin_id,
            NotificationType.ERROR,
            title,
            message,
            priority=NotificationPriority.HIGH,
            duration_ms=0,  # Persistent
            **kwargs,
        )
    
    def action_required(
        self,
        plugin_id: str,
        title: str,
        message: str,
        actions: List[NotificationAction],
        **kwargs: Any,
    ) -> Optional[Notification]:
        """Emit an action-required notification."""
        return self.emit(
            plugin_id,
            NotificationType.ACTION_REQUIRED,
            title,
            message,
            priority=NotificationPriority.URGENT,
            channel=NotificationChannel.ALERT,
            duration_ms=0,  # Persistent
            dismissible=False,
            actions=actions,
            **kwargs,
        )
    
    # -------------------------------------------------------------------------
    # Notification Management
    # -------------------------------------------------------------------------
    
    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get a notification by ID."""
        with self._lock:
            for n in self._notifications:
                if n.notification_id == notification_id:
                    return n
            return None
    
    def get_notifications(
        self,
        plugin_id: Optional[str] = None,
        notification_type: Optional[NotificationType] = None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[Notification]:
        """Get notifications with optional filtering."""
        with self._lock:
            result = []
            for n in reversed(self._notifications):  # Most recent first
                if plugin_id and n.plugin_id != plugin_id:
                    continue
                if notification_type and n.notification_type != notification_type:
                    continue
                if unread_only and n.read:
                    continue
                result.append(n)
                if len(result) >= limit:
                    break
            return result
    
    def mark_as_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        with self._lock:
            for n in self._notifications:
                if n.notification_id == notification_id:
                    if not n.read:
                        n.read = True
                        if n.plugin_id in self._unread_count:
                            self._unread_count[n.plugin_id] = max(
                                0, self._unread_count[n.plugin_id] - 1
                            )
                        self._save_config()
                    return True
            return False
    
    def mark_all_as_read(self, plugin_id: Optional[str] = None) -> int:
        """Mark all notifications as read."""
        with self._lock:
            count = 0
            for n in self._notifications:
                if plugin_id and n.plugin_id != plugin_id:
                    continue
                if not n.read:
                    n.read = True
                    count += 1
            
            if plugin_id:
                self._unread_count[plugin_id] = 0
            else:
                self._unread_count.clear()
            
            self._save_config()
            return count
    
    def dismiss(self, notification_id: str) -> bool:
        """Dismiss a notification."""
        with self._lock:
            for n in self._notifications:
                if n.notification_id == notification_id:
                    if n.dismissible:
                        n.dismissed = True
                        if not n.read:
                            n.read = True
                            if n.plugin_id in self._unread_count:
                                self._unread_count[n.plugin_id] = max(
                                    0, self._unread_count[n.plugin_id] - 1
                                )
                        self._save_config()
                        return True
                    return False
            return False
    
    def action_taken(self, notification_id: str, action_id: str) -> Optional[NotificationAction]:
        """Record that an action was taken on a notification."""
        with self._lock:
            for n in self._notifications:
                if n.notification_id == notification_id:
                    for action in n.actions:
                        if action.action_id == action_id:
                            n.actioned = True
                            if action.closes_notification:
                                n.dismissed = True
                            if not n.read:
                                n.read = True
                                if n.plugin_id in self._unread_count:
                                    self._unread_count[n.plugin_id] = max(
                                        0, self._unread_count[n.plugin_id] - 1
                                    )
                            self._save_config()
                            return action
            return None
    
    def clear_notifications(self, plugin_id: Optional[str] = None) -> int:
        """Clear notifications."""
        with self._lock:
            if plugin_id:
                original_count = len(self._notifications)
                self._notifications = [
                    n for n in self._notifications if n.plugin_id != plugin_id
                ]
                self._unread_count.pop(plugin_id, None)
                cleared = original_count - len(self._notifications)
            else:
                cleared = len(self._notifications)
                self._notifications.clear()
                self._unread_count.clear()
            
            self._save_config()
            return cleared
    
    # -------------------------------------------------------------------------
    # Badge Counters
    # -------------------------------------------------------------------------
    
    def get_unread_count(self, plugin_id: Optional[str] = None) -> int:
        """Get unread notification count."""
        with self._lock:
            if plugin_id:
                return self._unread_count.get(plugin_id, 0)
            return sum(self._unread_count.values())
    
    def get_badge_counts(self) -> Dict[str, int]:
        """Get badge counts per plugin."""
        with self._lock:
            return dict(self._unread_count)
    
    # -------------------------------------------------------------------------
    # Delivery Callbacks
    # -------------------------------------------------------------------------
    
    def add_delivery_callback(
        self,
        callback: Callable[[Notification], None],
    ) -> None:
        """Add a callback for notification delivery."""
        with self._lock:
            if callback not in self._delivery_callbacks:
                self._delivery_callbacks.append(callback)
    
    def remove_delivery_callback(
        self,
        callback: Callable[[Notification], None],
    ) -> bool:
        """Remove a delivery callback."""
        with self._lock:
            if callback in self._delivery_callbacks:
                self._delivery_callbacks.remove(callback)
                return True
            return False
    
    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification statistics."""
        with self._lock:
            return {
                "total_emitted": self._stats["total_emitted"],
                "total_filtered": self._stats["total_filtered"],
                "total_delivered": self._stats["total_delivered"],
                "total_in_history": len(self._notifications),
                "total_unread": self.get_unread_count(),
                "by_type": dict(self._stats["by_type"]),
                "by_plugin": dict(self._stats["by_plugin"]),
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get notification system status."""
        with self._lock:
            return {
                "enabled": self._config.enabled,
                "global_muted": self._config.global_muted,
                "global_muted_until": self._config.global_muted_until.isoformat() if self._config.global_muted_until else None,
                "total_notifications": len(self._notifications),
                "unread_count": self.get_unread_count(),
                "badge_counts": self.get_badge_counts(),
                "delivery_callbacks_count": len(self._delivery_callbacks),
            }


# =============================================================================
# Global Instance
# =============================================================================

_notification_manager: Optional[NotificationManager] = None
_lock = threading.Lock()


def get_notification_manager() -> NotificationManager:
    """Get the global notification manager instance."""
    global _notification_manager
    with _lock:
        if _notification_manager is None:
            _notification_manager = NotificationManager()
        return _notification_manager


def init_notification_manager(
    config: Optional[NotificationConfig] = None,
    config_path: Optional[Path] = None,
) -> NotificationManager:
    """Initialize the global notification manager."""
    global _notification_manager
    with _lock:
        _notification_manager = NotificationManager(
            config=config,
            config_path=config_path,
        )
        return _notification_manager


def reset_notification_manager() -> None:
    """Reset the global notification manager."""
    global _notification_manager
    with _lock:
        _notification_manager = None


# =============================================================================
# Convenience Functions
# =============================================================================

def notify(
    plugin_id: str,
    notification_type: NotificationType,
    title: str,
    message: str,
    **kwargs: Any,
) -> Optional[Notification]:
    """Emit a notification (convenience function)."""
    return get_notification_manager().emit(
        plugin_id, notification_type, title, message, **kwargs
    )


def notify_info(plugin_id: str, title: str, message: str, **kwargs: Any) -> Optional[Notification]:
    """Emit an info notification."""
    return get_notification_manager().info(plugin_id, title, message, **kwargs)


def notify_success(plugin_id: str, title: str, message: str, **kwargs: Any) -> Optional[Notification]:
    """Emit a success notification."""
    return get_notification_manager().success(plugin_id, title, message, **kwargs)


def notify_warning(plugin_id: str, title: str, message: str, **kwargs: Any) -> Optional[Notification]:
    """Emit a warning notification."""
    return get_notification_manager().warning(plugin_id, title, message, **kwargs)


def notify_error(plugin_id: str, title: str, message: str, **kwargs: Any) -> Optional[Notification]:
    """Emit an error notification."""
    return get_notification_manager().error(plugin_id, title, message, **kwargs)


def get_unread_count(plugin_id: Optional[str] = None) -> int:
    """Get unread notification count."""
    return get_notification_manager().get_unread_count(plugin_id)


def get_notifications(
    plugin_id: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 50,
) -> List[Notification]:
    """Get notifications."""
    return get_notification_manager().get_notifications(
        plugin_id=plugin_id,
        unread_only=unread_only,
        limit=limit,
    )


def get_notification_status() -> Dict[str, Any]:
    """Get notification system status."""
    return get_notification_manager().get_status()
