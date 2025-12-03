"""Tests for jupiter.core.bridge.events module.

Version: 0.1.0

Tests for the EventBus and related event functionality.
"""

import pytest
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from jupiter.core.bridge.events import (
    EventBus,
    EventTopic,
    Event,
    Subscription,
    get_event_bus,
    reset_event_bus,
    emit_plugin_loaded,
    emit_plugin_error,
    emit_scan_started,
    emit_scan_progress,
    emit_scan_finished,
    emit_scan_error,
    emit_config_changed,
    emit_job_started,
    emit_job_progress,
    emit_job_completed,
    emit_job_failed,
)


@pytest.fixture(autouse=True)
def reset_bus():
    """Reset the global event bus before and after each test."""
    reset_event_bus()
    yield
    reset_event_bus()


# =============================================================================
# EventTopic Tests
# =============================================================================

class TestEventTopic:
    """Tests for EventTopic enum."""
    
    def test_plugin_topics_defined(self):
        """Plugin lifecycle topics should be defined."""
        assert EventTopic.PLUGIN_LOADED.value == "plugin.loaded"
        assert EventTopic.PLUGIN_ERROR.value == "plugin.error"
        assert EventTopic.PLUGIN_DISABLED.value == "plugin.disabled"
        assert EventTopic.PLUGIN_RELOADED.value == "plugin.reloaded"
    
    def test_scan_topics_defined(self):
        """Scan topics should be defined."""
        assert EventTopic.SCAN_STARTED.value == "scan.started"
        assert EventTopic.SCAN_PROGRESS.value == "scan.progress"
        assert EventTopic.SCAN_FINISHED.value == "scan.finished"
        assert EventTopic.SCAN_ERROR.value == "scan.error"
    
    def test_job_topics_defined(self):
        """Job topics should be defined."""
        assert EventTopic.JOB_STARTED.value == "job.started"
        assert EventTopic.JOB_PROGRESS.value == "job.progress"
        assert EventTopic.JOB_COMPLETED.value == "job.completed"
        assert EventTopic.JOB_FAILED.value == "job.failed"
        assert EventTopic.JOB_CANCELLED.value == "job.cancelled"
    
    def test_config_topics_defined(self):
        """Config topics should be defined."""
        assert EventTopic.CONFIG_CHANGED.value == "config.changed"
        assert EventTopic.CONFIG_RESET.value == "config.reset"


# =============================================================================
# Event Tests
# =============================================================================

class TestEvent:
    """Tests for Event dataclass."""
    
    def test_creates_with_defaults(self):
        """Event should have timestamp and optional source."""
        event = Event(topic="test.topic", payload={"key": "value"})
        
        assert event.topic == "test.topic"
        assert event.payload == {"key": "value"}
        assert event.timestamp is not None
        assert event.source_plugin is None
    
    def test_creates_with_source(self):
        """Event can include source plugin."""
        event = Event(
            topic="test",
            payload={},
            source_plugin="my_plugin"
        )
        
        assert event.source_plugin == "my_plugin"
    
    def test_to_dict_serializes(self):
        """to_dict should serialize all fields."""
        event = Event(
            topic="test.topic",
            payload={"data": 123},
            source_plugin="plugin"
        )
        
        data = event.to_dict()
        
        assert data["topic"] == "test.topic"
        assert data["payload"] == {"data": 123}
        assert data["source_plugin"] == "plugin"
        assert "timestamp" in data


# =============================================================================
# Subscription Tests
# =============================================================================

class TestSubscription:
    """Tests for Subscription dataclass."""
    
    def test_creates_subscription(self):
        """Should create a subscription."""
        callback = MagicMock()
        sub = Subscription(topic="test", callback=callback)
        
        assert sub.topic == "test"
        assert sub.callback is callback
        assert sub.plugin_id is None
    
    def test_subscription_with_plugin_id(self):
        """Subscription can include plugin ID."""
        callback = MagicMock()
        sub = Subscription(topic="test", callback=callback, plugin_id="my_plugin")
        
        assert sub.plugin_id == "my_plugin"
    
    def test_subscriptions_hashable(self):
        """Subscriptions should be hashable for set operations."""
        callback = MagicMock()
        sub1 = Subscription(topic="test", callback=callback)
        sub2 = Subscription(topic="test", callback=callback)
        
        # Same callback should hash the same
        assert hash(sub1) == hash(sub2)
    
    def test_subscriptions_equality(self):
        """Subscriptions with same topic and callback are equal."""
        callback = MagicMock()
        sub1 = Subscription(topic="test", callback=callback)
        sub2 = Subscription(topic="test", callback=callback)
        
        assert sub1 == sub2


# =============================================================================
# EventBus Tests
# =============================================================================

class TestEventBusSubscribe:
    """Tests for EventBus subscription methods."""
    
    def test_subscribe_returns_subscription(self):
        """subscribe should return a Subscription object."""
        bus = EventBus()
        callback = MagicMock()
        
        sub = bus.subscribe("test.topic", callback)
        
        assert isinstance(sub, Subscription)
        assert sub.topic == "test.topic"
    
    def test_subscribe_with_plugin_id(self):
        """subscribe should track plugin ID."""
        bus = EventBus()
        callback = MagicMock()
        
        sub = bus.subscribe("test", callback, plugin_id="my_plugin")
        
        assert sub.plugin_id == "my_plugin"
    
    def test_subscribe_wildcard(self):
        """Wildcard subscription should receive all events."""
        bus = EventBus()
        callback = MagicMock()
        
        bus.subscribe("*", callback)
        bus.emit("any.topic", {"data": 1})
        bus.emit("another.topic", {"data": 2})
        
        assert callback.call_count == 2
    
    def test_multiple_subscriptions_same_topic(self):
        """Multiple callbacks can subscribe to same topic."""
        bus = EventBus()
        callback1 = MagicMock()
        callback2 = MagicMock()
        
        bus.subscribe("test", callback1)
        bus.subscribe("test", callback2)
        bus.emit("test", {})
        
        callback1.assert_called_once()
        callback2.assert_called_once()


class TestEventBusUnsubscribe:
    """Tests for EventBus unsubscribe methods."""
    
    def test_unsubscribe_removes_callback(self):
        """unsubscribe should remove the callback."""
        bus = EventBus()
        callback = MagicMock()
        
        bus.subscribe("test", callback)
        result = bus.unsubscribe("test", callback)
        bus.emit("test", {})
        
        assert result is True
        callback.assert_not_called()
    
    def test_unsubscribe_returns_false_if_not_found(self):
        """unsubscribe returns False if callback not found."""
        bus = EventBus()
        callback = MagicMock()
        
        result = bus.unsubscribe("test", callback)
        
        assert result is False
    
    def test_unsubscribe_wildcard(self):
        """Can unsubscribe from wildcard."""
        bus = EventBus()
        callback = MagicMock()
        
        bus.subscribe("*", callback)
        result = bus.unsubscribe("*", callback)
        bus.emit("test", {})
        
        assert result is True
        callback.assert_not_called()
    
    def test_unsubscribe_plugin_removes_all(self):
        """unsubscribe_plugin removes all subscriptions for plugin."""
        bus = EventBus()
        callback1 = MagicMock()
        callback2 = MagicMock()
        callback3 = MagicMock()
        
        bus.subscribe("topic1", callback1, plugin_id="plugin_a")
        bus.subscribe("topic2", callback2, plugin_id="plugin_a")
        bus.subscribe("topic1", callback3, plugin_id="plugin_b")
        
        count = bus.unsubscribe_plugin("plugin_a")
        
        assert count == 2
        
        bus.emit("topic1", {})
        bus.emit("topic2", {})
        
        callback1.assert_not_called()
        callback2.assert_not_called()
        callback3.assert_called_once()


class TestEventBusEmit:
    """Tests for EventBus emit method."""
    
    def test_emit_calls_subscriber(self):
        """emit should call the subscribed callback."""
        bus = EventBus()
        callback = MagicMock()
        
        bus.subscribe("test.topic", callback)
        bus.emit("test.topic", {"key": "value"})
        
        callback.assert_called_once_with("test.topic", {"key": "value"})
    
    def test_emit_only_calls_matching_topic(self):
        """emit should only call subscribers of matching topic."""
        bus = EventBus()
        callback1 = MagicMock()
        callback2 = MagicMock()
        
        bus.subscribe("topic1", callback1)
        bus.subscribe("topic2", callback2)
        
        bus.emit("topic1", {})
        
        callback1.assert_called_once()
        callback2.assert_not_called()
    
    def test_emit_with_source_plugin(self):
        """emit can include source plugin."""
        bus = EventBus()
        callback = MagicMock()
        
        bus.subscribe("test", callback)
        bus.emit("test", {"data": 1}, source_plugin="my_plugin")
        
        callback.assert_called_once()
    
    def test_emit_handles_callback_error(self):
        """emit should continue if a callback raises."""
        bus = EventBus()
        bad_callback = MagicMock(side_effect=Exception("test error"))
        good_callback = MagicMock()
        
        bus.subscribe("test", bad_callback)
        bus.subscribe("test", good_callback)
        
        bus.emit("test", {})  # Should not raise
        
        good_callback.assert_called_once()
    
    def test_emit_adds_to_history(self):
        """emit should add event to history."""
        bus = EventBus()
        
        bus.emit("test", {"data": 1})
        bus.emit("test", {"data": 2})
        
        history = bus.get_history()
        assert len(history) == 2
        assert history[0].payload == {"data": 1}
        assert history[1].payload == {"data": 2}


class TestEventBusPauseResume:
    """Tests for pause/resume functionality."""
    
    def test_pause_queues_events(self):
        """Paused bus should queue events."""
        bus = EventBus()
        callback = MagicMock()
        
        bus.subscribe("test", callback)
        bus.pause()
        bus.emit("test", {"data": 1})
        bus.emit("test", {"data": 2})
        
        callback.assert_not_called()
    
    def test_resume_dispatches_queued(self):
        """resume should dispatch queued events."""
        bus = EventBus()
        callback = MagicMock()
        
        bus.subscribe("test", callback)
        bus.pause()
        bus.emit("test", {"data": 1})
        bus.emit("test", {"data": 2})
        bus.resume()
        
        assert callback.call_count == 2


class TestEventBusHistory:
    """Tests for event history."""
    
    def test_history_limits_size(self):
        """History should respect max_history limit."""
        bus = EventBus(max_history=3)
        
        for i in range(5):
            bus.emit("test", {"i": i})
        
        history = bus.get_history()
        assert len(history) == 3
        # Should keep most recent
        assert history[0].payload == {"i": 2}
        assert history[2].payload == {"i": 4}
    
    def test_history_filter_by_topic(self):
        """get_history can filter by topic."""
        bus = EventBus()
        
        bus.emit("topic1", {"data": 1})
        bus.emit("topic2", {"data": 2})
        bus.emit("topic1", {"data": 3})
        
        history = bus.get_history(topic="topic1")
        assert len(history) == 2
    
    def test_clear_history(self):
        """clear_history should empty history."""
        bus = EventBus()
        
        bus.emit("test", {})
        bus.emit("test", {})
        bus.clear_history()
        
        assert len(bus.get_history()) == 0


class TestEventBusWebSocket:
    """Tests for WebSocket hooks."""
    
    def test_websocket_hook_called(self):
        """WebSocket hook should be called on emit."""
        bus = EventBus()
        ws_callback = MagicMock()
        
        bus.add_websocket_hook(ws_callback)
        bus.emit("test", {"data": 1})
        
        ws_callback.assert_called_once()
        event = ws_callback.call_args[0][0]
        assert event.topic == "test"
    
    def test_remove_websocket_hook(self):
        """Can remove WebSocket hook."""
        bus = EventBus()
        ws_callback = MagicMock()
        
        bus.add_websocket_hook(ws_callback)
        result = bus.remove_websocket_hook(ws_callback)
        bus.emit("test", {})
        
        assert result is True
        ws_callback.assert_not_called()
    
    def test_websocket_error_doesnt_stop_dispatch(self):
        """WebSocket error should not stop event dispatch."""
        bus = EventBus()
        bad_ws = MagicMock(side_effect=Exception("ws error"))
        callback = MagicMock()
        
        bus.add_websocket_hook(bad_ws)
        bus.subscribe("test", callback)
        bus.emit("test", {})  # Should not raise
        
        callback.assert_called_once()


class TestEventBusIntrospection:
    """Tests for introspection methods."""
    
    def test_get_subscriptions_all(self):
        """get_subscriptions returns all subscriptions."""
        bus = EventBus()
        bus.subscribe("topic1", MagicMock())
        bus.subscribe("topic2", MagicMock())
        bus.subscribe("*", MagicMock())
        
        subs = bus.get_subscriptions()
        assert len(subs) == 3
    
    def test_get_subscriptions_by_topic(self):
        """get_subscriptions can filter by topic."""
        bus = EventBus()
        bus.subscribe("topic1", MagicMock())
        bus.subscribe("topic1", MagicMock())
        bus.subscribe("topic2", MagicMock())
        
        subs = bus.get_subscriptions("topic1")
        assert len(subs) == 2
    
    def test_get_topics(self):
        """get_topics returns active topics."""
        bus = EventBus()
        bus.subscribe("alpha", MagicMock())
        bus.subscribe("beta", MagicMock())
        
        topics = bus.get_topics()
        assert "alpha" in topics
        assert "beta" in topics


# =============================================================================
# Global Event Bus Tests
# =============================================================================

class TestGlobalEventBus:
    """Tests for global event bus functions."""
    
    def test_get_event_bus_returns_singleton(self):
        """get_event_bus should return same instance."""
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        
        assert bus1 is bus2
    
    def test_reset_event_bus_creates_new(self):
        """reset_event_bus should create new instance."""
        bus1 = get_event_bus()
        reset_event_bus()
        bus2 = get_event_bus()
        
        assert bus1 is not bus2


# =============================================================================
# Convenience Function Tests
# =============================================================================

class TestConvenienceFunctions:
    """Tests for emit convenience functions."""
    
    def test_emit_plugin_loaded(self):
        """emit_plugin_loaded should emit correct event."""
        callback = MagicMock()
        get_event_bus().subscribe(EventTopic.PLUGIN_LOADED.value, callback)
        
        emit_plugin_loaded("test_plugin", "1.0.0")
        
        callback.assert_called_once()
        _, payload = callback.call_args[0]
        assert payload["plugin_id"] == "test_plugin"
        assert payload["version"] == "1.0.0"
    
    def test_emit_plugin_error(self):
        """emit_plugin_error should emit correct event."""
        callback = MagicMock()
        get_event_bus().subscribe(EventTopic.PLUGIN_ERROR.value, callback)
        
        emit_plugin_error("test_plugin", "Something failed", {"code": 500})
        
        callback.assert_called_once()
        _, payload = callback.call_args[0]
        assert payload["plugin_id"] == "test_plugin"
        assert payload["error"] == "Something failed"
        assert payload["details"]["code"] == 500
    
    def test_emit_scan_started(self):
        """emit_scan_started should emit correct event."""
        callback = MagicMock()
        get_event_bus().subscribe(EventTopic.SCAN_STARTED.value, callback)
        
        emit_scan_started("/path/to/project", {"incremental": True})
        
        callback.assert_called_once()
        _, payload = callback.call_args[0]
        assert payload["project_root"] == "/path/to/project"
        assert payload["options"]["incremental"] is True
    
    def test_emit_scan_progress(self):
        """emit_scan_progress should emit correct event."""
        callback = MagicMock()
        get_event_bus().subscribe(EventTopic.SCAN_PROGRESS.value, callback)
        
        emit_scan_progress(50, 100, "file.py")
        
        callback.assert_called_once()
        _, payload = callback.call_args[0]
        assert payload["current"] == 50
        assert payload["total"] == 100
        assert payload["current_file"] == "file.py"
    
    def test_emit_scan_finished(self):
        """emit_scan_finished should emit correct event."""
        callback = MagicMock()
        get_event_bus().subscribe(EventTopic.SCAN_FINISHED.value, callback)
        
        emit_scan_finished("/path", 150, 2500)
        
        callback.assert_called_once()
        _, payload = callback.call_args[0]
        assert payload["file_count"] == 150
        assert payload["duration_ms"] == 2500
    
    def test_emit_scan_error(self):
        """emit_scan_error should emit correct event."""
        callback = MagicMock()
        get_event_bus().subscribe(EventTopic.SCAN_ERROR.value, callback)
        
        emit_scan_error("/path", "Permission denied")
        
        callback.assert_called_once()
        _, payload = callback.call_args[0]
        assert payload["error"] == "Permission denied"
    
    def test_emit_config_changed(self):
        """emit_config_changed should emit correct event."""
        callback = MagicMock()
        get_event_bus().subscribe(EventTopic.CONFIG_CHANGED.value, callback)
        
        emit_config_changed("my_plugin", "api_key", "old", "new")
        
        callback.assert_called_once()
        _, payload = callback.call_args[0]
        assert payload["plugin_id"] == "my_plugin"
        assert payload["key"] == "api_key"
        assert payload["old_value"] == "old"
        assert payload["new_value"] == "new"
    
    def test_emit_job_started(self):
        """emit_job_started should emit correct event."""
        callback = MagicMock()
        get_event_bus().subscribe(EventTopic.JOB_STARTED.value, callback)
        
        emit_job_started("job-123", "analyzer", "full_scan")
        
        callback.assert_called_once()
        _, payload = callback.call_args[0]
        assert payload["job_id"] == "job-123"
        assert payload["plugin_id"] == "analyzer"
        assert payload["job_type"] == "full_scan"
    
    def test_emit_job_progress(self):
        """emit_job_progress should emit correct event."""
        callback = MagicMock()
        get_event_bus().subscribe(EventTopic.JOB_PROGRESS.value, callback)
        
        emit_job_progress("job-123", 0.5, "Processing...")
        
        callback.assert_called_once()
        _, payload = callback.call_args[0]
        assert payload["job_id"] == "job-123"
        assert payload["progress"] == 0.5
        assert payload["message"] == "Processing..."
    
    def test_emit_job_completed(self):
        """emit_job_completed should emit correct event."""
        callback = MagicMock()
        get_event_bus().subscribe(EventTopic.JOB_COMPLETED.value, callback)
        
        emit_job_completed("job-123", {"files_processed": 100})
        
        callback.assert_called_once()
        _, payload = callback.call_args[0]
        assert payload["job_id"] == "job-123"
        assert payload["result"]["files_processed"] == 100
    
    def test_emit_job_failed(self):
        """emit_job_failed should emit correct event."""
        callback = MagicMock()
        get_event_bus().subscribe(EventTopic.JOB_FAILED.value, callback)
        
        emit_job_failed("job-123", "Out of memory")
        
        callback.assert_called_once()
        _, payload = callback.call_args[0]
        assert payload["job_id"] == "job-123"
        assert payload["error"] == "Out of memory"
