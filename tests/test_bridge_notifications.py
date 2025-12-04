"""
Tests for jupiter.core.bridge.notifications module.

Version: 0.1.0

Tests for plugin notification system including emission,
filtering, preferences, and delivery.
"""

import pytest
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

from jupiter.core.bridge.notifications import (
    NotificationType,
    NotificationPriority,
    NotificationChannel,
    NotificationAction,
    Notification,
    PluginNotificationPreferences,
    NotificationConfig,
    NotificationManager,
    get_notification_manager,
    init_notification_manager,
    reset_notification_manager,
    notify,
    notify_info,
    notify_success,
    notify_warning,
    notify_error,
    get_unread_count,
    get_notifications,
    get_notification_status,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def manager():
    """Create a fresh notification manager."""
    return NotificationManager()


@pytest.fixture(autouse=True)
def reset_global():
    """Reset global notification manager before and after each test."""
    reset_notification_manager()
    yield
    reset_notification_manager()


# =============================================================================
# NotificationType Tests
# =============================================================================

class TestNotificationType:
    """Tests for NotificationType enum."""

    def test_values(self):
        """Test enum values."""
        assert NotificationType.INFO.value == "info"
        assert NotificationType.SUCCESS.value == "success"
        assert NotificationType.WARNING.value == "warning"
        assert NotificationType.ERROR.value == "error"
        assert NotificationType.ACTION_REQUIRED.value == "action_required"


# =============================================================================
# NotificationPriority Tests
# =============================================================================

class TestNotificationPriority:
    """Tests for NotificationPriority enum."""

    def test_values(self):
        """Test enum values."""
        assert NotificationPriority.LOW.value == "low"
        assert NotificationPriority.NORMAL.value == "normal"
        assert NotificationPriority.HIGH.value == "high"
        assert NotificationPriority.URGENT.value == "urgent"


# =============================================================================
# NotificationChannel Tests
# =============================================================================

class TestNotificationChannel:
    """Tests for NotificationChannel enum."""

    def test_values(self):
        """Test enum values."""
        assert NotificationChannel.TOAST.value == "toast"
        assert NotificationChannel.BADGE.value == "badge"
        assert NotificationChannel.ALERT.value == "alert"
        assert NotificationChannel.SILENT.value == "silent"


# =============================================================================
# NotificationAction Tests
# =============================================================================

class TestNotificationAction:
    """Tests for NotificationAction dataclass."""

    def test_defaults(self):
        """Test default values."""
        action = NotificationAction(action_id="test", label="Test")
        
        assert action.action_id == "test"
        assert action.label == "Test"
        assert action.callback_endpoint is None
        assert action.callback_data == {}
        assert action.style == "default"
        assert action.closes_notification is True

    def test_to_dict(self):
        """Test serialization."""
        action = NotificationAction(
            action_id="confirm",
            label="Confirm",
            callback_endpoint="/api/confirm",
            style="primary",
        )
        data = action.to_dict()
        
        assert data["action_id"] == "confirm"
        assert data["label"] == "Confirm"
        assert data["callback_endpoint"] == "/api/confirm"
        assert data["style"] == "primary"

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "action_id": "cancel",
            "label": "Cancel",
            "style": "danger",
        }
        action = NotificationAction.from_dict(data)
        
        assert action.action_id == "cancel"
        assert action.label == "Cancel"
        assert action.style == "danger"


# =============================================================================
# Notification Tests
# =============================================================================

class TestNotification:
    """Tests for Notification dataclass."""

    def test_creation(self):
        """Test creating a notification."""
        notification = Notification(
            notification_id="test-123",
            plugin_id="my_plugin",
            notification_type=NotificationType.INFO,
            title="Test Title",
            message="Test message",
        )
        
        assert notification.notification_id == "test-123"
        assert notification.plugin_id == "my_plugin"
        assert notification.notification_type == NotificationType.INFO
        assert notification.title == "Test Title"
        assert notification.message == "Test message"
        assert notification.read is False
        assert notification.dismissed is False

    def test_defaults(self):
        """Test default values."""
        notification = Notification(
            notification_id="test",
            plugin_id="plugin",
            notification_type=NotificationType.INFO,
            title="Title",
            message="Message",
        )
        
        assert notification.priority == NotificationPriority.NORMAL
        assert notification.channel == NotificationChannel.TOAST
        assert notification.duration_ms == 5000
        assert notification.dismissible is True

    def test_to_dict(self):
        """Test serialization."""
        notification = Notification(
            notification_id="test",
            plugin_id="plugin",
            notification_type=NotificationType.WARNING,
            title="Warning",
            message="Be careful",
        )
        data = notification.to_dict()
        
        assert data["notification_id"] == "test"
        assert data["type"] == "warning"
        assert data["title"] == "Warning"

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "notification_id": "test",
            "plugin_id": "plugin",
            "type": "error",
            "title": "Error",
            "message": "Something went wrong",
            "priority": "high",
        }
        notification = Notification.from_dict(data)
        
        assert notification.notification_type == NotificationType.ERROR
        assert notification.priority == NotificationPriority.HIGH


# =============================================================================
# PluginNotificationPreferences Tests
# =============================================================================

class TestPluginNotificationPreferences:
    """Tests for PluginNotificationPreferences dataclass."""

    def test_defaults(self):
        """Test default values."""
        prefs = PluginNotificationPreferences(plugin_id="test")
        
        assert prefs.plugin_id == "test"
        assert prefs.enabled is True
        assert len(prefs.allowed_types) == len(NotificationType)
        assert prefs.min_priority == NotificationPriority.LOW

    def test_to_dict(self):
        """Test serialization."""
        prefs = PluginNotificationPreferences(
            plugin_id="test",
            enabled=False,
        )
        data = prefs.to_dict()
        
        assert data["plugin_id"] == "test"
        assert data["enabled"] is False

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "plugin_id": "test",
            "enabled": False,
            "min_priority": "high",
        }
        prefs = PluginNotificationPreferences.from_dict(data)
        
        assert prefs.enabled is False
        assert prefs.min_priority == NotificationPriority.HIGH


# =============================================================================
# NotificationConfig Tests
# =============================================================================

class TestNotificationConfig:
    """Tests for NotificationConfig dataclass."""

    def test_defaults(self):
        """Test default values."""
        config = NotificationConfig()
        
        assert config.enabled is True
        assert config.max_history == 100
        assert config.default_duration_ms == 5000
        assert config.global_muted is False

    def test_to_dict(self):
        """Test serialization."""
        config = NotificationConfig(max_history=50)
        data = config.to_dict()
        
        assert data["max_history"] == 50

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "enabled": False,
            "max_history": 200,
        }
        config = NotificationConfig.from_dict(data)
        
        assert config.enabled is False
        assert config.max_history == 200


# =============================================================================
# NotificationManager Basic Tests
# =============================================================================

class TestNotificationManagerBasic:
    """Basic tests for NotificationManager."""

    def test_initialization(self, manager):
        """Test manager initialization."""
        assert manager.config is not None
        assert manager.config.enabled is True

    def test_update_config(self, manager):
        """Test updating configuration."""
        new_config = NotificationConfig(max_history=50)
        manager.update_config(new_config)
        
        assert manager.config.max_history == 50


# =============================================================================
# Notification Emission Tests
# =============================================================================

class TestNotificationEmission:
    """Tests for notification emission."""

    def test_emit_basic(self, manager):
        """Test basic notification emission."""
        notification = manager.emit(
            plugin_id="test_plugin",
            notification_type=NotificationType.INFO,
            title="Test",
            message="Test message",
        )
        
        assert notification is not None
        assert notification.plugin_id == "test_plugin"
        assert notification.notification_type == NotificationType.INFO

    def test_emit_with_all_options(self, manager):
        """Test emission with all options."""
        action = NotificationAction(action_id="ok", label="OK")
        notification = manager.emit(
            plugin_id="plugin",
            notification_type=NotificationType.WARNING,
            title="Warning",
            message="Caution",
            priority=NotificationPriority.HIGH,
            channel=NotificationChannel.ALERT,
            icon="warning-icon",
            actions=[action],
            metadata={"key": "value"},
            duration_ms=10000,
            dismissible=False,
        )
        
        assert notification is not None
        assert notification.priority == NotificationPriority.HIGH
        assert notification.channel == NotificationChannel.ALERT
        assert notification.icon == "warning-icon"
        assert len(notification.actions) == 1
        assert notification.duration_ms == 10000
        assert notification.dismissible is False

    def test_emit_info(self, manager):
        """Test info convenience method."""
        notification = manager.info("plugin", "Info", "Information")
        
        assert notification is not None
        assert notification.notification_type == NotificationType.INFO

    def test_emit_success(self, manager):
        """Test success convenience method."""
        notification = manager.success("plugin", "Success", "Done")
        
        assert notification is not None
        assert notification.notification_type == NotificationType.SUCCESS

    def test_emit_warning(self, manager):
        """Test warning convenience method."""
        notification = manager.warning("plugin", "Warning", "Be careful")
        
        assert notification is not None
        assert notification.notification_type == NotificationType.WARNING
        assert notification.priority == NotificationPriority.HIGH

    def test_emit_error(self, manager):
        """Test error convenience method."""
        notification = manager.error("plugin", "Error", "Failed")
        
        assert notification is not None
        assert notification.notification_type == NotificationType.ERROR
        assert notification.duration_ms == 0  # Persistent

    def test_emit_action_required(self, manager):
        """Test action_required convenience method."""
        actions = [NotificationAction(action_id="confirm", label="Confirm")]
        notification = manager.action_required(
            "plugin",
            "Action Required",
            "Please confirm",
            actions=actions,
        )
        
        assert notification is not None
        assert notification.notification_type == NotificationType.ACTION_REQUIRED
        assert notification.priority == NotificationPriority.URGENT
        assert notification.dismissible is False
        assert len(notification.actions) == 1


# =============================================================================
# Notification Filtering Tests
# =============================================================================

class TestNotificationFiltering:
    """Tests for notification filtering."""

    def test_filter_when_disabled(self, manager):
        """Test filtering when notifications are disabled."""
        manager.update_config(NotificationConfig(enabled=False))
        
        notification = manager.emit("plugin", NotificationType.INFO, "Test", "Test")
        
        assert notification is None

    def test_filter_when_globally_muted(self, manager):
        """Test filtering when globally muted."""
        manager.mute_all()
        
        notification = manager.emit("plugin", NotificationType.INFO, "Test", "Test")
        
        assert notification is None

    def test_filter_plugin_disabled(self, manager):
        """Test filtering when plugin notifications are disabled."""
        manager.disable_plugin_notifications("plugin")
        
        notification = manager.emit("plugin", NotificationType.INFO, "Test", "Test")
        
        assert notification is None

    def test_filter_plugin_muted(self, manager):
        """Test filtering when plugin is muted."""
        manager.mute_plugin("plugin", until=datetime.now() + timedelta(hours=1))
        
        notification = manager.emit("plugin", NotificationType.INFO, "Test", "Test")
        
        assert notification is None

    def test_filter_by_type(self, manager):
        """Test filtering by notification type."""
        prefs = PluginNotificationPreferences(
            plugin_id="plugin",
            allowed_types={NotificationType.ERROR},
        )
        manager.set_plugin_preferences("plugin", prefs)
        
        # Info should be filtered
        info = manager.emit("plugin", NotificationType.INFO, "Test", "Test")
        assert info is None
        
        # Error should pass
        error = manager.emit("plugin", NotificationType.ERROR, "Test", "Test")
        assert error is not None

    def test_filter_by_priority(self, manager):
        """Test filtering by priority."""
        prefs = PluginNotificationPreferences(
            plugin_id="plugin",
            min_priority=NotificationPriority.HIGH,
        )
        manager.set_plugin_preferences("plugin", prefs)
        
        # Low priority should be filtered
        low = manager.emit(
            "plugin", NotificationType.INFO, "Test", "Test",
            priority=NotificationPriority.LOW,
        )
        assert low is None
        
        # High priority should pass
        high = manager.emit(
            "plugin", NotificationType.INFO, "Test", "Test",
            priority=NotificationPriority.HIGH,
        )
        assert high is not None


# =============================================================================
# Plugin Preferences Tests
# =============================================================================

class TestPluginPreferences:
    """Tests for plugin notification preferences."""

    def test_get_default_preferences(self, manager):
        """Test getting default preferences."""
        prefs = manager.get_plugin_preferences("new_plugin")
        
        assert prefs.plugin_id == "new_plugin"
        assert prefs.enabled is True

    def test_set_preferences(self, manager):
        """Test setting preferences."""
        prefs = PluginNotificationPreferences(
            plugin_id="plugin",
            enabled=False,
        )
        manager.set_plugin_preferences("plugin", prefs)
        
        retrieved = manager.get_plugin_preferences("plugin")
        assert retrieved.enabled is False

    def test_disable_plugin(self, manager):
        """Test disabling plugin notifications."""
        manager.disable_plugin_notifications("plugin")
        
        prefs = manager.get_plugin_preferences("plugin")
        assert prefs.enabled is False

    def test_enable_plugin(self, manager):
        """Test enabling plugin notifications."""
        manager.disable_plugin_notifications("plugin")
        manager.enable_plugin_notifications("plugin")
        
        prefs = manager.get_plugin_preferences("plugin")
        assert prefs.enabled is True

    def test_mute_plugin(self, manager):
        """Test muting a plugin."""
        until = datetime.now() + timedelta(hours=1)
        manager.mute_plugin("plugin", until=until)
        
        prefs = manager.get_plugin_preferences("plugin")
        assert prefs.muted_until is not None

    def test_unmute_plugin(self, manager):
        """Test unmuting a plugin."""
        manager.mute_plugin("plugin", until=datetime.now() + timedelta(hours=1))
        manager.unmute_plugin("plugin")
        
        prefs = manager.get_plugin_preferences("plugin")
        assert prefs.muted_until is None


# =============================================================================
# Global Muting Tests
# =============================================================================

class TestGlobalMuting:
    """Tests for global muting."""

    def test_mute_all(self, manager):
        """Test muting all notifications."""
        manager.mute_all()
        
        assert manager.is_muted() is True

    def test_unmute_all(self, manager):
        """Test unmuting all notifications."""
        manager.mute_all()
        manager.unmute_all()
        
        assert manager.is_muted() is False

    def test_mute_with_expiry(self, manager):
        """Test muting with expiry."""
        manager.mute_all(until=datetime.now() + timedelta(hours=1))
        
        assert manager.is_muted() is True

    def test_expired_mute(self, manager):
        """Test expired mute is automatically lifted."""
        manager.mute_all(until=datetime.now() - timedelta(seconds=1))
        
        assert manager.is_muted() is False


# =============================================================================
# Notification Management Tests
# =============================================================================

class TestNotificationManagement:
    """Tests for notification management."""

    def test_get_notification(self, manager):
        """Test getting a notification by ID."""
        notification = manager.emit("plugin", NotificationType.INFO, "Test", "Test")
        assert notification is not None
        
        retrieved = manager.get_notification(notification.notification_id)
        assert retrieved is not None
        assert retrieved.notification_id == notification.notification_id

    def test_get_nonexistent_notification(self, manager):
        """Test getting non-existent notification."""
        result = manager.get_notification("nonexistent")
        
        assert result is None

    def test_get_notifications_list(self, manager):
        """Test getting list of notifications."""
        manager.emit("plugin1", NotificationType.INFO, "Test1", "Test")
        manager.emit("plugin2", NotificationType.INFO, "Test2", "Test")
        
        notifications = manager.get_notifications()
        
        assert len(notifications) == 2

    def test_get_notifications_filtered_by_plugin(self, manager):
        """Test getting notifications filtered by plugin."""
        manager.emit("plugin1", NotificationType.INFO, "Test1", "Test")
        manager.emit("plugin2", NotificationType.INFO, "Test2", "Test")
        
        notifications = manager.get_notifications(plugin_id="plugin1")
        
        assert len(notifications) == 1
        assert notifications[0].plugin_id == "plugin1"

    def test_get_notifications_unread_only(self, manager):
        """Test getting unread notifications only."""
        n1 = manager.emit("plugin", NotificationType.INFO, "Test1", "Test")
        manager.emit("plugin", NotificationType.INFO, "Test2", "Test")
        
        assert n1 is not None
        manager.mark_as_read(n1.notification_id)
        
        notifications = manager.get_notifications(unread_only=True)
        
        assert len(notifications) == 1

    def test_mark_as_read(self, manager):
        """Test marking notification as read."""
        notification = manager.emit("plugin", NotificationType.INFO, "Test", "Test")
        assert notification is not None
        
        result = manager.mark_as_read(notification.notification_id)
        
        assert result is True
        assert manager.get_notification(notification.notification_id).read is True  # type: ignore

    def test_mark_all_as_read(self, manager):
        """Test marking all notifications as read."""
        manager.emit("plugin", NotificationType.INFO, "Test1", "Test")
        manager.emit("plugin", NotificationType.INFO, "Test2", "Test")
        
        count = manager.mark_all_as_read()
        
        assert count == 2
        assert manager.get_unread_count() == 0

    def test_dismiss_notification(self, manager):
        """Test dismissing a notification."""
        notification = manager.emit("plugin", NotificationType.INFO, "Test", "Test")
        assert notification is not None
        
        result = manager.dismiss(notification.notification_id)
        
        assert result is True
        assert manager.get_notification(notification.notification_id).dismissed is True  # type: ignore

    def test_dismiss_non_dismissible(self, manager):
        """Test cannot dismiss non-dismissible notification."""
        notification = manager.emit(
            "plugin", NotificationType.INFO, "Test", "Test",
            dismissible=False,
        )
        assert notification is not None
        
        result = manager.dismiss(notification.notification_id)
        
        assert result is False

    def test_action_taken(self, manager):
        """Test recording action taken."""
        action = NotificationAction(action_id="confirm", label="Confirm")
        notification = manager.emit(
            "plugin", NotificationType.INFO, "Test", "Test",
            actions=[action],
        )
        assert notification is not None
        
        result = manager.action_taken(notification.notification_id, "confirm")
        
        assert result is not None
        assert result.action_id == "confirm"
        assert manager.get_notification(notification.notification_id).actioned is True  # type: ignore

    def test_clear_notifications(self, manager):
        """Test clearing notifications."""
        manager.emit("plugin", NotificationType.INFO, "Test1", "Test")
        manager.emit("plugin", NotificationType.INFO, "Test2", "Test")
        
        count = manager.clear_notifications()
        
        assert count == 2
        assert len(manager.get_notifications()) == 0

    def test_clear_notifications_by_plugin(self, manager):
        """Test clearing notifications for specific plugin."""
        manager.emit("plugin1", NotificationType.INFO, "Test1", "Test")
        manager.emit("plugin2", NotificationType.INFO, "Test2", "Test")
        
        count = manager.clear_notifications("plugin1")
        
        assert count == 1
        assert len(manager.get_notifications()) == 1


# =============================================================================
# Badge Counter Tests
# =============================================================================

class TestBadgeCounters:
    """Tests for badge counters."""

    def test_unread_count_increments(self, manager):
        """Test unread count increments on emission."""
        manager.emit("plugin", NotificationType.INFO, "Test", "Test")
        
        assert manager.get_unread_count() == 1

    def test_unread_count_by_plugin(self, manager):
        """Test unread count by plugin."""
        manager.emit("plugin1", NotificationType.INFO, "Test1", "Test")
        manager.emit("plugin1", NotificationType.INFO, "Test2", "Test")
        manager.emit("plugin2", NotificationType.INFO, "Test3", "Test")
        
        assert manager.get_unread_count("plugin1") == 2
        assert manager.get_unread_count("plugin2") == 1
        assert manager.get_unread_count() == 3

    def test_badge_counts(self, manager):
        """Test getting badge counts per plugin."""
        manager.emit("plugin1", NotificationType.INFO, "Test1", "Test")
        manager.emit("plugin2", NotificationType.INFO, "Test2", "Test")
        
        counts = manager.get_badge_counts()
        
        assert counts["plugin1"] == 1
        assert counts["plugin2"] == 1

    def test_count_decrements_on_read(self, manager):
        """Test unread count decrements when marked as read."""
        notification = manager.emit("plugin", NotificationType.INFO, "Test", "Test")
        assert notification is not None
        
        manager.mark_as_read(notification.notification_id)
        
        assert manager.get_unread_count() == 0


# =============================================================================
# Delivery Callback Tests
# =============================================================================

class TestDeliveryCallbacks:
    """Tests for delivery callbacks."""

    def test_add_callback(self, manager):
        """Test adding a delivery callback."""
        callback = Mock()
        manager.add_delivery_callback(callback)
        
        manager.emit("plugin", NotificationType.INFO, "Test", "Test")
        
        callback.assert_called_once()

    def test_remove_callback(self, manager):
        """Test removing a delivery callback."""
        callback = Mock()
        manager.add_delivery_callback(callback)
        
        result = manager.remove_delivery_callback(callback)
        
        assert result is True
        
        manager.emit("plugin", NotificationType.INFO, "Test", "Test")
        callback.assert_not_called()

    def test_callback_receives_notification(self, manager):
        """Test that callback receives the notification."""
        received = []
        
        def callback(notification):
            received.append(notification)
        
        manager.add_delivery_callback(callback)
        manager.emit("plugin", NotificationType.INFO, "Test", "Test")
        
        assert len(received) == 1
        assert isinstance(received[0], Notification)


# =============================================================================
# Persistence Tests
# =============================================================================

class TestPersistence:
    """Tests for configuration persistence."""

    def test_save_and_load_config(self):
        """Test saving and loading configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "notifications.json"
            
            # Create and emit
            manager1 = NotificationManager(config_path=config_path)
            manager1.emit("plugin", NotificationType.INFO, "Test", "Test")
            manager1.disable_plugin_notifications("disabled_plugin")
            
            # Load in new manager
            manager2 = NotificationManager(config_path=config_path)
            
            prefs = manager2.get_plugin_preferences("disabled_plugin")
            assert prefs.enabled is False


# =============================================================================
# Statistics Tests
# =============================================================================

class TestStatistics:
    """Tests for statistics."""

    def test_get_stats(self, manager):
        """Test getting statistics."""
        manager.emit("plugin1", NotificationType.INFO, "Test", "Test")
        manager.emit("plugin2", NotificationType.WARNING, "Test", "Test")
        
        stats = manager.get_stats()
        
        assert stats["total_emitted"] == 2
        assert stats["total_delivered"] == 2
        assert stats["by_type"]["info"] == 1
        assert stats["by_type"]["warning"] == 1
        assert stats["by_plugin"]["plugin1"] == 1

    def test_stats_track_filtered(self, manager):
        """Test that stats track filtered notifications."""
        manager.disable_plugin_notifications("plugin")
        manager.emit("plugin", NotificationType.INFO, "Test", "Test")
        
        stats = manager.get_stats()
        
        assert stats["total_filtered"] == 1

    def test_get_status(self, manager):
        """Test getting status."""
        manager.emit("plugin", NotificationType.INFO, "Test", "Test")
        
        status = manager.get_status()
        
        assert status["enabled"] is True
        assert status["total_notifications"] == 1
        assert status["unread_count"] == 1


# =============================================================================
# Global Functions Tests
# =============================================================================

class TestGlobalFunctions:
    """Tests for global convenience functions."""

    def test_get_notification_manager_singleton(self):
        """Test that get_notification_manager returns singleton."""
        m1 = get_notification_manager()
        m2 = get_notification_manager()
        
        assert m1 is m2

    def test_init_notification_manager(self):
        """Test initializing notification manager."""
        config = NotificationConfig(max_history=50)
        
        manager = init_notification_manager(config=config)
        
        assert manager.config.max_history == 50

    def test_reset_notification_manager(self):
        """Test resetting notification manager."""
        m1 = get_notification_manager()
        m1.emit("plugin", NotificationType.INFO, "Test", "Test")
        
        reset_notification_manager()
        
        m2 = get_notification_manager()
        assert m1 is not m2
        assert len(m2.get_notifications()) == 0

    def test_notify_function(self):
        """Test notify convenience function."""
        notification = notify("plugin", NotificationType.INFO, "Test", "Test")
        
        assert notification is not None
        assert notification.plugin_id == "plugin"

    def test_notify_info_function(self):
        """Test notify_info function."""
        notification = notify_info("plugin", "Info", "Message")
        
        assert notification is not None
        assert notification.notification_type == NotificationType.INFO

    def test_notify_success_function(self):
        """Test notify_success function."""
        notification = notify_success("plugin", "Success", "Done")
        
        assert notification is not None
        assert notification.notification_type == NotificationType.SUCCESS

    def test_notify_warning_function(self):
        """Test notify_warning function."""
        notification = notify_warning("plugin", "Warning", "Careful")
        
        assert notification is not None
        assert notification.notification_type == NotificationType.WARNING

    def test_notify_error_function(self):
        """Test notify_error function."""
        notification = notify_error("plugin", "Error", "Failed")
        
        assert notification is not None
        assert notification.notification_type == NotificationType.ERROR

    def test_get_unread_count_function(self):
        """Test get_unread_count function."""
        notify_info("plugin", "Test", "Test")
        
        count = get_unread_count()
        
        assert count == 1

    def test_get_notifications_function(self):
        """Test get_notifications function."""
        notify_info("plugin", "Test", "Test")
        
        notifications = get_notifications()
        
        assert len(notifications) == 1

    def test_get_notification_status_function(self):
        """Test get_notification_status function."""
        status = get_notification_status()
        
        assert "enabled" in status
        assert "unread_count" in status


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for notification scenarios."""

    def test_full_notification_workflow(self):
        """Test complete notification workflow."""
        manager = NotificationManager()
        
        # Emit various notifications
        info = manager.info("plugin", "Info", "Information message")
        warning = manager.warning("plugin", "Warning", "Warning message")
        error = manager.error("plugin", "Error", "Error message")
        
        assert info is not None
        assert warning is not None
        assert error is not None
        
        # Check counts
        assert manager.get_unread_count() == 3
        
        # Mark one as read
        manager.mark_as_read(info.notification_id)
        assert manager.get_unread_count() == 2
        
        # Dismiss one
        manager.dismiss(warning.notification_id)
        assert manager.get_unread_count() == 1

    def test_action_required_workflow(self):
        """Test action-required notification workflow."""
        manager = NotificationManager()
        
        # Create action-required notification
        actions = [
            NotificationAction(
                action_id="approve",
                label="Approve",
                callback_endpoint="/api/approve",
                style="primary",
            ),
            NotificationAction(
                action_id="reject",
                label="Reject",
                callback_endpoint="/api/reject",
                style="danger",
            ),
        ]
        
        notification = manager.action_required(
            "plugin",
            "Approval Required",
            "Please review and approve",
            actions=actions,
        )
        
        assert notification is not None
        assert notification.dismissible is False
        assert len(notification.actions) == 2
        
        # Take action
        action = manager.action_taken(notification.notification_id, "approve")
        assert action is not None
        assert action.action_id == "approve"
        
        # Notification should be marked as actioned
        updated = manager.get_notification(notification.notification_id)
        assert updated is not None
        assert updated.actioned is True

    def test_per_plugin_preferences(self):
        """Test per-plugin notification preferences."""
        manager = NotificationManager()
        
        # Disable warnings for plugin1
        prefs = PluginNotificationPreferences(
            plugin_id="plugin1",
            allowed_types={NotificationType.INFO, NotificationType.ERROR},
        )
        manager.set_plugin_preferences("plugin1", prefs)
        
        # Warning should be filtered
        warning = manager.warning("plugin1", "Warning", "Test")
        assert warning is None
        
        # Info should pass
        info = manager.info("plugin1", "Info", "Test")
        assert info is not None
        
        # Plugin2 should still receive warnings
        warning2 = manager.warning("plugin2", "Warning", "Test")
        assert warning2 is not None

    def test_delivery_with_websocket_hook(self):
        """Test delivery with WebSocket hook simulation."""
        manager = NotificationManager()
        
        ws_messages = []
        
        def ws_hook(notification: Notification):
            ws_messages.append({
                "type": "NOTIFICATION",
                "payload": notification.to_dict(),
            })
        
        manager.add_delivery_callback(ws_hook)
        
        manager.info("plugin", "Test", "Message")
        manager.warning("plugin", "Alert", "Warning message")
        
        assert len(ws_messages) == 2
        assert ws_messages[0]["type"] == "NOTIFICATION"
        assert ws_messages[0]["payload"]["type"] == "info"
