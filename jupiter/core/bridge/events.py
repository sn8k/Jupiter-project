"""Event Bus for Jupiter Plugin Bridge.

Version: 0.1.0

This module provides a centralized event bus for pub/sub communication
between plugins and the Jupiter core. It supports:
- Topic-based event routing
- Plugin-scoped event emission
- Standard event topics for plugin lifecycle
- WebSocket propagation for UI updates

Standard Topics:
- PLUGIN_LOADED: When a plugin completes loading
- PLUGIN_ERROR: When a plugin encounters an error
- PLUGIN_DISABLED: When a plugin is disabled
- PLUGIN_RELOADED: When a plugin is hot-reloaded
- SCAN_STARTED: When a scan begins
- SCAN_PROGRESS: Progress updates during scan
- SCAN_FINISHED: When a scan completes
- SCAN_ERROR: When a scan fails
- CONFIG_CHANGED: When configuration is modified
- JOB_STARTED: When a background job starts
- JOB_PROGRESS: Progress updates for jobs
- JOB_COMPLETED: When a job completes successfully
- JOB_FAILED: When a job fails
- JOB_CANCELLED: When a job is cancelled
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from weakref import WeakSet

logger = logging.getLogger(__name__)


class EventTopic(str, Enum):
    """Standard event topics for Jupiter."""
    
    # Plugin lifecycle
    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_ERROR = "plugin.error"
    PLUGIN_DISABLED = "plugin.disabled"
    PLUGIN_RELOADED = "plugin.reloaded"
    PLUGIN_UNLOADED = "plugin.unloaded"
    
    # Scan events
    SCAN_STARTED = "scan.started"
    SCAN_PROGRESS = "scan.progress"
    SCAN_FINISHED = "scan.finished"
    SCAN_ERROR = "scan.error"
    
    # Analysis events
    ANALYZE_STARTED = "analyze.started"
    ANALYZE_FINISHED = "analyze.finished"
    ANALYZE_ERROR = "analyze.error"
    
    # Configuration events
    CONFIG_CHANGED = "config.changed"
    CONFIG_RESET = "config.reset"
    
    # Job events
    JOB_STARTED = "job.started"
    JOB_PROGRESS = "job.progress"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    JOB_CANCELLED = "job.cancelled"
    
    # Project events
    PROJECT_CHANGED = "project.changed"
    PROJECT_CREATED = "project.created"
    PROJECT_DELETED = "project.deleted"
    
    # System events
    SYSTEM_READY = "system.ready"
    SYSTEM_SHUTDOWN = "system.shutdown"


# Type alias for event callbacks
EventCallback = Callable[[str, Dict[str, Any]], None]
AsyncEventCallback = Callable[[str, Dict[str, Any]], Any]


@dataclass
class Event:
    """Represents an event in the system."""
    
    topic: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_plugin: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary."""
        return {
            "topic": self.topic,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "source_plugin": self.source_plugin,
        }


@dataclass
class Subscription:
    """Represents a subscription to an event topic."""
    
    topic: str
    callback: EventCallback
    plugin_id: Optional[str] = None
    async_callback: Optional[AsyncEventCallback] = None
    
    def __hash__(self) -> int:
        return hash((self.topic, id(self.callback)))
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Subscription):
            return False
        return self.topic == other.topic and self.callback is other.callback


class EventBus:
    """Central event bus for pub/sub communication.
    
    Features:
    - Synchronous and asynchronous event emission
    - Topic-based subscription with wildcards
    - Plugin-scoped event tracking
    - Event history for debugging
    - WebSocket propagation hooks
    
    Usage:
        bus = EventBus()
        
        def on_scan_finished(topic, payload):
            print(f"Scan completed: {payload}")
        
        bus.subscribe("scan.finished", on_scan_finished)
        bus.emit("scan.finished", {"files": 100})
    """
    
    def __init__(self, max_history: int = 100):
        """Initialize the event bus.
        
        Args:
            max_history: Maximum number of events to keep in history
        """
        self._subscriptions: Dict[str, List[Subscription]] = {}
        self._wildcard_subscriptions: List[Subscription] = []
        self._history: List[Event] = []
        self._max_history = max_history
        self._ws_callbacks: List[Callable[[Event], None]] = []
        self._paused = False
        self._queued_events: List[Event] = []
    
    def subscribe(
        self,
        topic: str,
        callback: EventCallback,
        plugin_id: Optional[str] = None,
    ) -> Subscription:
        """Subscribe to events on a topic.
        
        Args:
            topic: Event topic to subscribe to (use "*" for all events)
            callback: Function to call when event is emitted
            plugin_id: Optional plugin ID for tracking
            
        Returns:
            Subscription object for later unsubscribe
        """
        subscription = Subscription(
            topic=topic,
            callback=callback,
            plugin_id=plugin_id,
        )
        
        if topic == "*":
            self._wildcard_subscriptions.append(subscription)
        else:
            if topic not in self._subscriptions:
                self._subscriptions[topic] = []
            self._subscriptions[topic].append(subscription)
        
        logger.debug(
            "Subscribed to topic '%s' (plugin: %s)",
            topic,
            plugin_id or "core"
        )
        
        return subscription
    
    def subscribe_async(
        self,
        topic: str,
        callback: AsyncEventCallback,
        plugin_id: Optional[str] = None,
    ) -> Subscription:
        """Subscribe with an async callback.
        
        Args:
            topic: Event topic
            callback: Async function to call
            plugin_id: Optional plugin ID
            
        Returns:
            Subscription object
        """
        # Wrap async callback in a sync wrapper
        def sync_wrapper(t: str, p: Dict[str, Any]) -> None:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(callback(t, p))
                else:
                    loop.run_until_complete(callback(t, p))
            except RuntimeError:
                # No event loop, create one
                asyncio.run(callback(t, p))
        
        subscription = Subscription(
            topic=topic,
            callback=sync_wrapper,
            plugin_id=plugin_id,
            async_callback=callback,
        )
        
        if topic == "*":
            self._wildcard_subscriptions.append(subscription)
        else:
            if topic not in self._subscriptions:
                self._subscriptions[topic] = []
            self._subscriptions[topic].append(subscription)
        
        return subscription
    
    def unsubscribe(
        self,
        topic: str,
        callback: EventCallback,
    ) -> bool:
        """Unsubscribe from a topic.
        
        Args:
            topic: Event topic
            callback: The callback function to remove
            
        Returns:
            True if unsubscribed, False if not found
        """
        if topic == "*":
            for sub in self._wildcard_subscriptions:
                if sub.callback is callback:
                    self._wildcard_subscriptions.remove(sub)
                    logger.debug("Unsubscribed from wildcard")
                    return True
        elif topic in self._subscriptions:
            for sub in self._subscriptions[topic]:
                if sub.callback is callback:
                    self._subscriptions[topic].remove(sub)
                    logger.debug("Unsubscribed from topic '%s'", topic)
                    return True
        
        return False
    
    def unsubscribe_plugin(self, plugin_id: str) -> int:
        """Remove all subscriptions for a plugin.
        
        Args:
            plugin_id: Plugin to unsubscribe
            
        Returns:
            Number of subscriptions removed
        """
        count = 0
        
        # Remove from wildcard subscriptions
        original_wildcard_len = len(self._wildcard_subscriptions)
        self._wildcard_subscriptions = [
            sub for sub in self._wildcard_subscriptions
            if sub.plugin_id != plugin_id
        ]
        count += original_wildcard_len - len(self._wildcard_subscriptions)
        
        # Remove from topic subscriptions
        for topic in list(self._subscriptions.keys()):
            original_len = len(self._subscriptions[topic])
            self._subscriptions[topic] = [
                sub for sub in self._subscriptions[topic]
                if sub.plugin_id != plugin_id
            ]
            count += original_len - len(self._subscriptions[topic])
            
            # Clean up empty lists
            if not self._subscriptions[topic]:
                del self._subscriptions[topic]
        
        if count > 0:
            logger.debug(
                "Unsubscribed %d callbacks for plugin '%s'",
                count,
                plugin_id
            )
        
        return count
    
    def emit(
        self,
        topic: str,
        payload: Dict[str, Any],
        source_plugin: Optional[str] = None,
    ) -> None:
        """Emit an event to all subscribers.
        
        Args:
            topic: Event topic
            payload: Event data
            source_plugin: Plugin that emitted the event
        """
        event = Event(
            topic=topic,
            payload=payload,
            source_plugin=source_plugin,
        )
        
        # Add to history
        self._add_to_history(event)
        
        # If paused, queue the event
        if self._paused:
            self._queued_events.append(event)
            return
        
        self._dispatch_event(event)
    
    def _dispatch_event(self, event: Event) -> None:
        """Dispatch event to all subscribers."""
        callbacks_called = 0
        
        # Call topic-specific subscribers
        if event.topic in self._subscriptions:
            for sub in self._subscriptions[event.topic]:
                try:
                    sub.callback(event.topic, event.payload)
                    callbacks_called += 1
                except Exception as e:
                    logger.error(
                        "Error in event callback for topic '%s' (plugin: %s): %s",
                        event.topic,
                        sub.plugin_id or "core",
                        e
                    )
        
        # Call wildcard subscribers
        for sub in self._wildcard_subscriptions:
            try:
                sub.callback(event.topic, event.payload)
                callbacks_called += 1
            except Exception as e:
                logger.error(
                    "Error in wildcard callback (plugin: %s): %s",
                    sub.plugin_id or "core",
                    e
                )
        
        # Notify WebSocket hooks
        for ws_callback in self._ws_callbacks:
            try:
                ws_callback(event)
            except Exception as e:
                logger.error("Error in WebSocket callback: %s", e)
        
        logger.debug(
            "Emitted '%s' to %d callbacks (source: %s)",
            event.topic,
            callbacks_called,
            event.source_plugin or "core"
        )
    
    def _add_to_history(self, event: Event) -> None:
        """Add event to history with size limit."""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
    
    def pause(self) -> None:
        """Pause event dispatch (events are queued)."""
        self._paused = True
        logger.debug("Event bus paused")
    
    def resume(self) -> None:
        """Resume event dispatch and process queued events."""
        self._paused = False
        
        # Dispatch queued events
        queued = self._queued_events
        self._queued_events = []
        
        for event in queued:
            self._dispatch_event(event)
        
        logger.debug("Event bus resumed, dispatched %d queued events", len(queued))
    
    def get_history(
        self,
        topic: Optional[str] = None,
        limit: int = 50,
    ) -> List[Event]:
        """Get event history.
        
        Args:
            topic: Optional filter by topic
            limit: Maximum events to return
            
        Returns:
            List of events (most recent last)
        """
        events = self._history
        
        if topic:
            events = [e for e in events if e.topic == topic]
        
        return events[-limit:]
    
    def clear_history(self) -> None:
        """Clear event history."""
        self._history = []
    
    def add_websocket_hook(
        self,
        callback: Callable[[Event], None],
    ) -> None:
        """Add a callback for WebSocket propagation.
        
        Args:
            callback: Function to call with events for WS broadcast
        """
        self._ws_callbacks.append(callback)
    
    def remove_websocket_hook(
        self,
        callback: Callable[[Event], None],
    ) -> bool:
        """Remove a WebSocket hook.
        
        Args:
            callback: The callback to remove
            
        Returns:
            True if removed
        """
        if callback in self._ws_callbacks:
            self._ws_callbacks.remove(callback)
            return True
        return False
    
    def get_subscriptions(self, topic: Optional[str] = None) -> List[Subscription]:
        """Get current subscriptions.
        
        Args:
            topic: Optional filter by topic
            
        Returns:
            List of subscriptions
        """
        if topic:
            return self._subscriptions.get(topic, []).copy()
        
        all_subs = []
        for subs in self._subscriptions.values():
            all_subs.extend(subs)
        all_subs.extend(self._wildcard_subscriptions)
        return all_subs
    
    def get_topics(self) -> List[str]:
        """Get all topics with active subscriptions.
        
        Returns:
            List of topic names
        """
        return list(self._subscriptions.keys())


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance.
    
    Returns:
        EventBus singleton
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def reset_event_bus() -> None:
    """Reset the global event bus (for testing)."""
    global _event_bus
    _event_bus = None


# Convenience functions for common events

def emit_plugin_loaded(plugin_id: str, version: str) -> None:
    """Emit plugin loaded event."""
    get_event_bus().emit(
        EventTopic.PLUGIN_LOADED.value,
        {"plugin_id": plugin_id, "version": version}
    )


def emit_plugin_error(plugin_id: str, error: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Emit plugin error event."""
    get_event_bus().emit(
        EventTopic.PLUGIN_ERROR.value,
        {"plugin_id": plugin_id, "error": error, "details": details or {}}
    )


def emit_scan_started(project_root: str, options: Optional[Dict[str, Any]] = None) -> None:
    """Emit scan started event."""
    get_event_bus().emit(
        EventTopic.SCAN_STARTED.value,
        {"project_root": project_root, "options": options or {}}
    )


def emit_scan_progress(current: int, total: int, current_file: Optional[str] = None) -> None:
    """Emit scan progress event."""
    get_event_bus().emit(
        EventTopic.SCAN_PROGRESS.value,
        {"current": current, "total": total, "current_file": current_file}
    )


def emit_scan_finished(project_root: str, file_count: int, duration_ms: int) -> None:
    """Emit scan finished event."""
    get_event_bus().emit(
        EventTopic.SCAN_FINISHED.value,
        {
            "project_root": project_root,
            "file_count": file_count,
            "duration_ms": duration_ms,
        }
    )


def emit_scan_error(project_root: str, error: str) -> None:
    """Emit scan error event."""
    get_event_bus().emit(
        EventTopic.SCAN_ERROR.value,
        {"project_root": project_root, "error": error}
    )


def emit_config_changed(plugin_id: Optional[str], key: str, old_value: Any, new_value: Any) -> None:
    """Emit configuration changed event."""
    get_event_bus().emit(
        EventTopic.CONFIG_CHANGED.value,
        {
            "plugin_id": plugin_id,
            "key": key,
            "old_value": old_value,
            "new_value": new_value,
        }
    )


def emit_job_started(job_id: str, plugin_id: str, job_type: str) -> None:
    """Emit job started event."""
    get_event_bus().emit(
        EventTopic.JOB_STARTED.value,
        {"job_id": job_id, "plugin_id": plugin_id, "job_type": job_type}
    )


def emit_job_progress(job_id: str, progress: float, message: Optional[str] = None) -> None:
    """Emit job progress event."""
    get_event_bus().emit(
        EventTopic.JOB_PROGRESS.value,
        {"job_id": job_id, "progress": progress, "message": message}
    )


def emit_job_completed(job_id: str, result: Optional[Dict[str, Any]] = None) -> None:
    """Emit job completed event."""
    get_event_bus().emit(
        EventTopic.JOB_COMPLETED.value,
        {"job_id": job_id, "result": result or {}}
    )


def emit_job_failed(job_id: str, error: str) -> None:
    """Emit job failed event."""
    get_event_bus().emit(
        EventTopic.JOB_FAILED.value,
        {"job_id": job_id, "error": error}
    )
