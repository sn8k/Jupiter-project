# Changelog: jupiter/core/bridge/notifications.py

## [0.1.0] - Initial Implementation

### Added
- `NotificationType` enum for notification types:
  - INFO, SUCCESS, WARNING, ERROR, ACTION_REQUIRED
- `NotificationPriority` enum for priority levels:
  - LOW, NORMAL, HIGH, URGENT
- `NotificationChannel` enum for delivery channels:
  - TOAST (temporary popup)
  - BADGE (icon badge counter)
  - ALERT (persistent alert bar)
  - SILENT (no UI, just logged)
- `NotificationAction` dataclass for action buttons:
  - action_id, label, callback_endpoint
  - callback_data, style, closes_notification
  - Serialization with to_dict/from_dict
- `Notification` dataclass for notifications:
  - notification_id, plugin_id, notification_type
  - title, message, priority, channel
  - icon, actions, metadata
  - duration_ms, dismissible
  - read, dismissed, actioned states
  - Serialization with to_dict/from_dict
- `PluginNotificationPreferences` dataclass:
  - Per-plugin notification settings
  - enabled, allowed_types, allowed_channels
  - min_priority, muted_until
- `NotificationConfig` dataclass for global config:
  - enabled, max_history, max_unread
  - default_duration_ms, global_muted
  - plugin_preferences dictionary
- `NotificationManager` class - main notification controller:
  - Configuration management with JSON persistence
  - Plugin preferences: get/set, disable/enable, mute/unmute
  - Global muting: mute_all(), unmute_all(), is_muted()
  - Notification emission: emit(), info(), success(), warning(), error(), action_required()
  - Filtering: by enabled, muted, type, priority
  - Management: get_notification(), get_notifications(), mark_as_read(), dismiss()
  - Actions: action_taken() with callback support
  - Badge counters: get_unread_count(), get_badge_counts()
  - Delivery callbacks: add_delivery_callback(), remove_delivery_callback()
  - Statistics: get_stats(), get_status()
- Global singleton pattern:
  - get_notification_manager(), init_notification_manager(), reset_notification_manager()
- Convenience functions:
  - notify(), notify_info(), notify_success(), notify_warning(), notify_error()
  - get_unread_count(), get_notifications(), get_notification_status()
- Thread-safe implementation with RLock (reentrant lock)
- Full JSON persistence support

### Features
- Multi-type notifications: info, success, warning, error, action_required
- Priority-based filtering (LOW to URGENT)
- Multiple delivery channels (toast, badge, alert, silent)
- Action buttons with callback endpoints
- Per-plugin notification preferences
- Global and per-plugin muting with expiration
- Badge counters for unread notifications
- Delivery callbacks for WebSocket integration
- Notification history with trimming

### Fixed
- Used RLock instead of Lock to prevent deadlocks in nested calls (get_stats/get_status calling get_unread_count)

### Tests
- 79 tests in test_bridge_notifications.py covering:
  - All enums and dataclasses
  - Notification emission and filtering
  - Plugin preferences
  - Global muting
  - Notification management (read, dismiss, action)
  - Badge counters
  - Delivery callbacks
  - Persistence
  - Statistics
  - Integration scenarios
