"""Jupiter Plugin Bridge - Monitoring and Limits.

Version: 0.1.0

Provides monitoring capabilities and resource limits for plugins:
- Operation timeouts
- Audit logging of sensitive actions
- Rate limiting (optional)
- Resource usage tracking

Usage:
    from jupiter.core.bridge.monitoring import (
        get_monitor,
        audit_log,
        with_timeout,
        check_rate_limit,
    )
    
    # Audit logging
    audit_log("plugin.installed", plugin_id="my-plugin", user="admin")
    
    # Operation with timeout
    result = await with_timeout(some_async_operation(), timeout=10.0)
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import (
    Any,
    Awaitable,
    Callable,
    Deque,
    Dict,
    List,
    Optional,
    TypeVar,
    Union,
)

logger = logging.getLogger(__name__)

__version__ = "0.1.0"


# =============================================================================
# AUDIT LOG
# =============================================================================

class AuditEventType(str, Enum):
    """Types of audit events."""
    
    # Plugin lifecycle
    PLUGIN_INSTALLED = "plugin.installed"
    PLUGIN_UNINSTALLED = "plugin.uninstalled"
    PLUGIN_ENABLED = "plugin.enabled"
    PLUGIN_DISABLED = "plugin.disabled"
    PLUGIN_RELOADED = "plugin.reloaded"
    PLUGIN_STARTED = "plugin.started"
    PLUGIN_STOPPED = "plugin.stopped"
    
    # Security
    PERMISSION_GRANTED = "security.permission_granted"
    PERMISSION_DENIED = "security.permission_denied"
    SIGNATURE_VERIFIED = "security.signature_verified"
    SIGNATURE_FAILED = "security.signature_failed"
    TRUST_LEVEL_CHANGED = "security.trust_level_changed"
    
    # Config
    CONFIG_CHANGED = "config.changed"
    CONFIG_RESET = "config.reset"
    
    # Jobs
    JOB_SUBMITTED = "job.submitted"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    JOB_CANCELLED = "job.cancelled"
    
    # Circuit breaker
    CIRCUIT_OPENED = "circuit.opened"
    CIRCUIT_CLOSED = "circuit.closed"
    CIRCUIT_RESET = "circuit.reset"
    
    # Commands
    COMMAND_EXECUTED = "command.executed"
    COMMAND_BLOCKED = "command.blocked"
    
    # File system
    FILE_READ = "fs.read"
    FILE_WRITE = "fs.write"
    FILE_DELETE = "fs.delete"
    
    # Network
    NETWORK_REQUEST = "network.request"
    NETWORK_BLOCKED = "network.blocked"
    
    # API
    API_ROUTE_REGISTERED = "api.route_registered"
    API_ROUTE_CALLED = "api.route_called"
    
    # Custom
    CUSTOM = "custom"


@dataclass
class AuditEntry:
    """An audit log entry."""
    
    event_type: str
    timestamp: float = field(default_factory=time.time)
    plugin_id: Optional[str] = None
    user: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(
                self.timestamp, tz=timezone.utc
            ).isoformat(),
            "plugin_id": self.plugin_id,
            "user": self.user,
            "details": self.details,
            "success": self.success,
            "error": self.error,
        }


class AuditLogger:
    """Audit logger for sensitive operations.
    
    Records all sensitive actions for security and compliance.
    """
    
    def __init__(
        self,
        max_entries: int = 10000,
        persist_path: Optional[Path] = None,
    ):
        """Initialize the audit logger.
        
        Args:
            max_entries: Maximum entries to keep in memory
            persist_path: Optional path to persist audit log
        """
        self._max_entries = max_entries
        self._persist_path = persist_path
        self._entries: Deque[AuditEntry] = deque(maxlen=max_entries)
        self._lock = Lock()
        self._handlers: List[Callable[[AuditEntry], None]] = []
    
    def log(
        self,
        event_type: Union[str, AuditEventType],
        plugin_id: Optional[str] = None,
        user: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error: Optional[str] = None,
    ) -> AuditEntry:
        """Log an audit event.
        
        Args:
            event_type: Type of event
            plugin_id: Related plugin ID
            user: User who triggered the action
            details: Additional details
            success: Whether the action succeeded
            error: Error message if failed
            
        Returns:
            The created audit entry
        """
        if isinstance(event_type, AuditEventType):
            event_type = event_type.value
        
        entry = AuditEntry(
            event_type=event_type,
            plugin_id=plugin_id,
            user=user,
            details=details or {},
            success=success,
            error=error,
        )
        
        with self._lock:
            self._entries.append(entry)
        
        # Log to standard logger as well
        log_msg = f"AUDIT: {event_type}"
        if plugin_id:
            log_msg += f" [plugin={plugin_id}]"
        if not success:
            log_msg += f" FAILED: {error}"
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
        
        # Notify handlers
        for handler in self._handlers:
            try:
                handler(entry)
            except Exception as e:
                logger.error("Audit handler failed: %s", e)
        
        return entry
    
    def add_handler(self, handler: Callable[[AuditEntry], None]) -> None:
        """Add a handler for audit events.
        
        Args:
            handler: Function to call for each audit entry
        """
        self._handlers.append(handler)
    
    def remove_handler(self, handler: Callable[[AuditEntry], None]) -> bool:
        """Remove a handler.
        
        Returns:
            True if removed, False if not found
        """
        try:
            self._handlers.remove(handler)
            return True
        except ValueError:
            return False
    
    def get_entries(
        self,
        limit: int = 100,
        event_type: Optional[str] = None,
        plugin_id: Optional[str] = None,
        since: Optional[float] = None,
        success_only: Optional[bool] = None,
    ) -> List[AuditEntry]:
        """Get audit entries with optional filters.
        
        Args:
            limit: Maximum entries to return
            event_type: Filter by event type
            plugin_id: Filter by plugin ID
            since: Only entries after this timestamp
            success_only: If True, only successful; if False, only failures
            
        Returns:
            List of matching entries (most recent first)
        """
        with self._lock:
            entries = list(self._entries)
        
        # Apply filters
        if event_type:
            entries = [e for e in entries if e.event_type == event_type]
        if plugin_id:
            entries = [e for e in entries if e.plugin_id == plugin_id]
        if since:
            entries = [e for e in entries if e.timestamp >= since]
        if success_only is not None:
            entries = [e for e in entries if e.success == success_only]
        
        # Return most recent first
        return list(reversed(entries[-limit:]))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get audit statistics.
        
        Returns:
            Dictionary with audit stats
        """
        with self._lock:
            entries = list(self._entries)
        
        if not entries:
            return {
                "total_entries": 0,
                "success_count": 0,
                "failure_count": 0,
                "by_event_type": {},
                "by_plugin": {},
            }
        
        success_count = sum(1 for e in entries if e.success)
        by_event: Dict[str, int] = {}
        by_plugin: Dict[str, int] = {}
        
        for entry in entries:
            by_event[entry.event_type] = by_event.get(entry.event_type, 0) + 1
            if entry.plugin_id:
                by_plugin[entry.plugin_id] = by_plugin.get(entry.plugin_id, 0) + 1
        
        return {
            "total_entries": len(entries),
            "success_count": success_count,
            "failure_count": len(entries) - success_count,
            "oldest_timestamp": entries[0].timestamp if entries else None,
            "newest_timestamp": entries[-1].timestamp if entries else None,
            "by_event_type": by_event,
            "by_plugin": by_plugin,
        }
    
    def clear(self) -> int:
        """Clear all audit entries.
        
        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._entries)
            self._entries.clear()
            return count


# =============================================================================
# TIMEOUT MANAGEMENT
# =============================================================================

class TimeoutError(Exception):
    """Operation timed out."""
    
    def __init__(self, operation: str, timeout: float):
        self.operation = operation
        self.timeout = timeout
        super().__init__(f"Operation '{operation}' timed out after {timeout}s")


@dataclass
class TimeoutConfig:
    """Timeout configuration for various operations."""
    
    # Plugin lifecycle
    plugin_load: float = 30.0
    plugin_unload: float = 10.0
    plugin_start: float = 30.0
    plugin_stop: float = 10.0
    
    # Jobs
    job_default: float = 300.0  # 5 minutes
    job_max: float = 3600.0     # 1 hour
    
    # Health checks
    health_check: float = 5.0
    
    # API
    api_request: float = 30.0
    
    # File operations
    file_read: float = 10.0
    file_write: float = 30.0
    
    # Network
    network_request: float = 30.0
    
    # Custom per-plugin overrides
    plugin_overrides: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    def get_timeout(
        self,
        operation: str,
        plugin_id: Optional[str] = None,
    ) -> float:
        """Get timeout for an operation.
        
        Args:
            operation: Operation name (e.g., 'plugin_load', 'job_default')
            plugin_id: Optional plugin ID for overrides
            
        Returns:
            Timeout in seconds
        """
        # Check plugin override
        if plugin_id and plugin_id in self.plugin_overrides:
            overrides = self.plugin_overrides[plugin_id]
            if operation in overrides:
                return overrides[operation]
        
        # Return default
        return getattr(self, operation, self.job_default)
    
    def set_plugin_timeout(
        self,
        plugin_id: str,
        operation: str,
        timeout: float,
    ) -> None:
        """Set a custom timeout for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            operation: Operation name
            timeout: Timeout in seconds
        """
        if plugin_id not in self.plugin_overrides:
            self.plugin_overrides[plugin_id] = {}
        self.plugin_overrides[plugin_id][operation] = timeout


T = TypeVar("T")


async def with_timeout(
    coro: Awaitable[T],
    timeout: float,
    operation: str = "operation",
) -> T:
    """Execute a coroutine with a timeout.
    
    Args:
        coro: Coroutine to execute
        timeout: Timeout in seconds
        operation: Operation name for error message
        
    Returns:
        Result of the coroutine
        
    Raises:
        TimeoutError: If operation times out
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(operation, timeout)


def sync_with_timeout(
    func: Callable[..., T],
    timeout: float,
    operation: str = "operation",
    *args: Any,
    **kwargs: Any,
) -> T:
    """Execute a sync function with a timeout (using threads).
    
    Note: This uses threading and may not be suitable for all operations.
    
    Args:
        func: Function to execute
        timeout: Timeout in seconds
        operation: Operation name for error message
        *args, **kwargs: Arguments to pass to func
        
    Returns:
        Result of the function
        
    Raises:
        TimeoutError: If operation times out
    """
    import concurrent.futures
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(operation, timeout)


# =============================================================================
# RATE LIMITING
# =============================================================================

@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    
    # Requests per window
    requests: int = 100
    
    # Window size in seconds
    window_seconds: float = 60.0
    
    # Burst allowance
    burst: int = 10


class RateLimiter:
    """Token bucket rate limiter.
    
    Limits the rate of operations per plugin or globally.
    """
    
    def __init__(
        self,
        default_config: Optional[RateLimitConfig] = None,
    ):
        """Initialize the rate limiter.
        
        Args:
            default_config: Default rate limit configuration
        """
        self._default_config = default_config or RateLimitConfig()
        self._plugin_configs: Dict[str, RateLimitConfig] = {}
        self._buckets: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
    
    def set_plugin_limit(
        self,
        plugin_id: str,
        config: RateLimitConfig,
    ) -> None:
        """Set rate limit for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            config: Rate limit configuration
        """
        with self._lock:
            self._plugin_configs[plugin_id] = config
    
    def check(
        self,
        plugin_id: Optional[str] = None,
        key: str = "default",
        cost: int = 1,
    ) -> bool:
        """Check if an operation is allowed.
        
        Args:
            plugin_id: Plugin identifier
            key: Additional key for scoping
            cost: Cost of the operation
            
        Returns:
            True if allowed, False if rate limited
        """
        config = self._plugin_configs.get(plugin_id or "", self._default_config)
        key_str = key or "default"
        bucket_key = f"{plugin_id or 'global'}:{key_str}"
        
        now = time.time()
        
        with self._lock:
            if bucket_key not in self._buckets:
                self._buckets[bucket_key] = {
                    "tokens": config.requests + config.burst,
                    "last_refill": now,
                }
            
            bucket = self._buckets[bucket_key]
            
            # Refill tokens
            elapsed = now - bucket["last_refill"]
            refill_rate = config.requests / config.window_seconds
            new_tokens = elapsed * refill_rate
            bucket["tokens"] = min(
                bucket["tokens"] + new_tokens,
                config.requests + config.burst,
            )
            bucket["last_refill"] = now
            
            # Check if enough tokens
            if bucket["tokens"] >= cost:
                bucket["tokens"] -= cost
                return True
            
            return False
    
    def get_remaining(
        self,
        plugin_id: Optional[str] = None,
        key: str = "default",
    ) -> int:
        """Get remaining tokens.
        
        Args:
            plugin_id: Plugin identifier
            key: Additional key for scoping
            
        Returns:
            Number of remaining tokens
        """
        bucket_key = f"{plugin_id or 'global'}:{key}"
        
        with self._lock:
            bucket = self._buckets.get(bucket_key)
            if bucket:
                return int(bucket["tokens"])
            return self._default_config.requests + self._default_config.burst
    
    def reset(
        self,
        plugin_id: Optional[str] = None,
        key: Optional[str] = None,
    ) -> int:
        """Reset rate limits.
        
        Args:
            plugin_id: Optional plugin to reset (None for all)
            key: Optional key to reset
            
        Returns:
            Number of buckets reset
        """
        with self._lock:
            if plugin_id is None and key is None:
                count = len(self._buckets)
                self._buckets.clear()
                return count
            
            prefix = f"{plugin_id or 'global'}:"
            if key:
                prefix += key
            
            to_remove = [k for k in self._buckets if k.startswith(prefix)]
            for k in to_remove:
                del self._buckets[k]
            return len(to_remove)


# =============================================================================
# PLUGIN MONITOR
# =============================================================================

class PluginMonitor:
    """Central monitoring for the plugin system.
    
    Combines audit logging, timeouts, and rate limiting.
    """
    
    def __init__(
        self,
        audit_max_entries: int = 10000,
        default_rate_limit: Optional[RateLimitConfig] = None,
    ):
        """Initialize the monitor.
        
        Args:
            audit_max_entries: Maximum audit entries to keep
            default_rate_limit: Default rate limit config
        """
        self.audit = AuditLogger(max_entries=audit_max_entries)
        self.timeouts = TimeoutConfig()
        self.rate_limiter = RateLimiter(default_config=default_rate_limit)
        self._enabled = True
    
    @property
    def enabled(self) -> bool:
        """Whether monitoring is enabled."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable or disable monitoring."""
        self._enabled = value
    
    def log(
        self,
        event_type: Union[str, AuditEventType],
        plugin_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[AuditEntry]:
        """Log an audit event.
        
        Args:
            event_type: Type of event
            plugin_id: Related plugin ID
            **kwargs: Additional arguments for AuditLogger.log
            
        Returns:
            The audit entry, or None if disabled
        """
        if not self._enabled:
            return None
        return self.audit.log(event_type, plugin_id=plugin_id, **kwargs)
    
    def check_rate(
        self,
        plugin_id: Optional[str] = None,
        key: str = "default",
        cost: int = 1,
    ) -> bool:
        """Check rate limit.
        
        Args:
            plugin_id: Plugin identifier
            key: Rate limit key
            cost: Operation cost
            
        Returns:
            True if allowed
        """
        if not self._enabled:
            return True
        return self.rate_limiter.check(plugin_id, key, cost)
    
    def get_timeout(
        self,
        operation: str,
        plugin_id: Optional[str] = None,
    ) -> float:
        """Get timeout for an operation.
        
        Args:
            operation: Operation name
            plugin_id: Optional plugin for overrides
            
        Returns:
            Timeout in seconds
        """
        return self.timeouts.get_timeout(operation, plugin_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics.
        
        Returns:
            Dictionary with stats from all components
        """
        return {
            "enabled": self._enabled,
            "audit": self.audit.get_stats(),
            "rate_limiter": {
                "buckets": len(self.rate_limiter._buckets),
            },
        }


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_monitor: Optional[PluginMonitor] = None
_monitor_lock = Lock()


def get_monitor() -> PluginMonitor:
    """Get the global plugin monitor.
    
    Returns:
        The global PluginMonitor instance
    """
    global _monitor
    
    with _monitor_lock:
        if _monitor is None:
            _monitor = PluginMonitor()
    
    return _monitor


def init_monitor(
    audit_max_entries: int = 10000,
    default_rate_limit: Optional[RateLimitConfig] = None,
) -> PluginMonitor:
    """Initialize or reinitialize the global monitor.
    
    Args:
        audit_max_entries: Maximum audit entries
        default_rate_limit: Default rate limit config
        
    Returns:
        The initialized PluginMonitor
    """
    global _monitor
    
    with _monitor_lock:
        _monitor = PluginMonitor(
            audit_max_entries=audit_max_entries,
            default_rate_limit=default_rate_limit,
        )
    
    logger.info("Global plugin monitor initialized")
    return _monitor


def reset_monitor() -> None:
    """Reset the global monitor."""
    global _monitor
    
    with _monitor_lock:
        _monitor = None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def audit_log(
    event_type: Union[str, AuditEventType],
    plugin_id: Optional[str] = None,
    **kwargs: Any,
) -> Optional[AuditEntry]:
    """Log an audit event.
    
    Convenience function that uses the global monitor.
    
    Args:
        event_type: Type of event
        plugin_id: Related plugin ID
        **kwargs: Additional arguments
        
    Returns:
        The audit entry or None
    """
    return get_monitor().log(event_type, plugin_id=plugin_id, **kwargs)


def check_rate_limit(
    plugin_id: Optional[str] = None,
    key: str = "default",
    cost: int = 1,
) -> bool:
    """Check rate limit.
    
    Convenience function that uses the global monitor.
    
    Args:
        plugin_id: Plugin identifier
        key: Rate limit key
        cost: Operation cost
        
    Returns:
        True if allowed
    """
    return get_monitor().check_rate(plugin_id, key, cost)


def get_timeout(
    operation: str,
    plugin_id: Optional[str] = None,
) -> float:
    """Get timeout for an operation.
    
    Convenience function that uses the global monitor.
    
    Args:
        operation: Operation name
        plugin_id: Optional plugin for overrides
        
    Returns:
        Timeout in seconds
    """
    return get_monitor().get_timeout(operation, plugin_id)
