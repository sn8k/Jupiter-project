"""Tests for Bridge Monitoring System.

Version: 0.1.0

Tests the monitoring capabilities including audit logging,
timeouts, and rate limiting.
"""

import asyncio
import pytest
import time
from unittest.mock import MagicMock, patch

from jupiter.core.bridge.monitoring import (
    AuditEventType,
    AuditEntry,
    AuditLogger,
    TimeoutError,
    TimeoutConfig,
    with_timeout,
    sync_with_timeout,
    RateLimitConfig,
    RateLimiter,
    PluginMonitor,
    get_monitor,
    init_monitor,
    reset_monitor,
    audit_log,
    check_rate_limit,
    get_timeout,
)

# Use anyio for async tests
pytestmark = pytest.mark.anyio


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def audit_logger():
    """Create an audit logger for testing."""
    return AuditLogger(max_entries=100)


@pytest.fixture
def timeout_config():
    """Create timeout config for testing."""
    return TimeoutConfig()


@pytest.fixture
def rate_limiter():
    """Create rate limiter for testing."""
    return RateLimiter()


@pytest.fixture
def monitor():
    """Create plugin monitor for testing."""
    return PluginMonitor(audit_max_entries=100)


@pytest.fixture(autouse=True)
def reset_global_monitor():
    """Reset global monitor after each test."""
    yield
    reset_monitor()


# =============================================================================
# TESTS: AUDIT EVENT TYPE
# =============================================================================

class TestAuditEventType:
    """Tests for AuditEventType enum."""
    
    def test_plugin_events(self):
        """Test plugin lifecycle event types."""
        assert AuditEventType.PLUGIN_INSTALLED.value == "plugin.installed"
        assert AuditEventType.PLUGIN_UNINSTALLED.value == "plugin.uninstalled"
        assert AuditEventType.PLUGIN_ENABLED.value == "plugin.enabled"
        assert AuditEventType.PLUGIN_DISABLED.value == "plugin.disabled"
    
    def test_security_events(self):
        """Test security event types."""
        assert AuditEventType.PERMISSION_GRANTED.value == "security.permission_granted"
        assert AuditEventType.PERMISSION_DENIED.value == "security.permission_denied"
        assert AuditEventType.SIGNATURE_VERIFIED.value == "security.signature_verified"
    
    def test_job_events(self):
        """Test job event types."""
        assert AuditEventType.JOB_SUBMITTED.value == "job.submitted"
        assert AuditEventType.JOB_COMPLETED.value == "job.completed"
        assert AuditEventType.JOB_FAILED.value == "job.failed"


# =============================================================================
# TESTS: AUDIT ENTRY
# =============================================================================

class TestAuditEntry:
    """Tests for AuditEntry dataclass."""
    
    def test_create(self):
        """Test creating an audit entry."""
        entry = AuditEntry(
            event_type="test.event",
            plugin_id="test-plugin",
            user="admin",
            details={"key": "value"},
        )
        
        assert entry.event_type == "test.event"
        assert entry.plugin_id == "test-plugin"
        assert entry.user == "admin"
        assert entry.success is True
    
    def test_to_dict(self):
        """Test serialization to dict."""
        entry = AuditEntry(
            event_type="test.event",
            plugin_id="test-plugin",
        )
        
        data = entry.to_dict()
        
        assert data["event_type"] == "test.event"
        assert data["plugin_id"] == "test-plugin"
        assert "timestamp_iso" in data
    
    def test_failed_entry(self):
        """Test failed audit entry."""
        entry = AuditEntry(
            event_type="test.event",
            success=False,
            error="Something went wrong",
        )
        
        assert entry.success is False
        assert entry.error == "Something went wrong"


# =============================================================================
# TESTS: AUDIT LOGGER
# =============================================================================

class TestAuditLogger:
    """Tests for AuditLogger."""
    
    def test_create(self, audit_logger):
        """Test creating an audit logger."""
        assert audit_logger._max_entries == 100
    
    def test_log_event(self, audit_logger):
        """Test logging an event."""
        entry = audit_logger.log(
            "test.event",
            plugin_id="test-plugin",
            details={"action": "test"},
        )
        
        assert entry.event_type == "test.event"
        assert entry.plugin_id == "test-plugin"
    
    def test_log_with_enum(self, audit_logger):
        """Test logging with enum event type."""
        entry = audit_logger.log(
            AuditEventType.PLUGIN_INSTALLED,
            plugin_id="test-plugin",
        )
        
        assert entry.event_type == "plugin.installed"
    
    def test_get_entries(self, audit_logger):
        """Test getting entries."""
        for i in range(5):
            audit_logger.log(f"event.{i}", plugin_id="test")
        
        entries = audit_logger.get_entries()
        
        assert len(entries) == 5
        # Most recent first
        assert entries[0].event_type == "event.4"
    
    def test_get_entries_with_limit(self, audit_logger):
        """Test getting entries with limit."""
        for i in range(10):
            audit_logger.log(f"event.{i}")
        
        entries = audit_logger.get_entries(limit=3)
        
        assert len(entries) == 3
    
    def test_filter_by_event_type(self, audit_logger):
        """Test filtering by event type."""
        audit_logger.log("type.a")
        audit_logger.log("type.b")
        audit_logger.log("type.a")
        
        entries = audit_logger.get_entries(event_type="type.a")
        
        assert len(entries) == 2
        assert all(e.event_type == "type.a" for e in entries)
    
    def test_filter_by_plugin(self, audit_logger):
        """Test filtering by plugin ID."""
        audit_logger.log("event", plugin_id="plugin-a")
        audit_logger.log("event", plugin_id="plugin-b")
        audit_logger.log("event", plugin_id="plugin-a")
        
        entries = audit_logger.get_entries(plugin_id="plugin-a")
        
        assert len(entries) == 2
        assert all(e.plugin_id == "plugin-a" for e in entries)
    
    def test_filter_by_success(self, audit_logger):
        """Test filtering by success status."""
        audit_logger.log("event", success=True)
        audit_logger.log("event", success=False)
        audit_logger.log("event", success=True)
        
        entries = audit_logger.get_entries(success_only=True)
        assert len(entries) == 2
        
        entries = audit_logger.get_entries(success_only=False)
        assert len(entries) == 1
    
    def test_max_entries(self):
        """Test max entries limit."""
        logger = AuditLogger(max_entries=5)
        
        for i in range(10):
            logger.log(f"event.{i}")
        
        entries = logger.get_entries()
        
        assert len(entries) == 5
    
    def test_handler(self, audit_logger):
        """Test audit handler."""
        handler = MagicMock()
        audit_logger.add_handler(handler)
        
        entry = audit_logger.log("test.event")
        
        handler.assert_called_once_with(entry)
    
    def test_remove_handler(self, audit_logger):
        """Test removing handler."""
        handler = MagicMock()
        audit_logger.add_handler(handler)
        
        result = audit_logger.remove_handler(handler)
        assert result is True
        
        audit_logger.log("test.event")
        handler.assert_not_called()
    
    def test_get_stats(self, audit_logger):
        """Test getting statistics."""
        audit_logger.log("type.a", plugin_id="p1")
        audit_logger.log("type.b", plugin_id="p1", success=False, error="err")
        audit_logger.log("type.a", plugin_id="p2")
        
        stats = audit_logger.get_stats()
        
        assert stats["total_entries"] == 3
        assert stats["success_count"] == 2
        assert stats["failure_count"] == 1
        assert stats["by_event_type"]["type.a"] == 2
        assert stats["by_plugin"]["p1"] == 2
    
    def test_clear(self, audit_logger):
        """Test clearing entries."""
        for i in range(5):
            audit_logger.log(f"event.{i}")
        
        count = audit_logger.clear()
        
        assert count == 5
        assert len(audit_logger.get_entries()) == 0


# =============================================================================
# TESTS: TIMEOUT CONFIG
# =============================================================================

class TestTimeoutConfig:
    """Tests for TimeoutConfig."""
    
    def test_defaults(self, timeout_config):
        """Test default timeout values."""
        assert timeout_config.plugin_load == 30.0
        assert timeout_config.plugin_unload == 10.0
        assert timeout_config.job_default == 300.0
        assert timeout_config.health_check == 5.0
    
    def test_get_timeout(self, timeout_config):
        """Test getting timeout value."""
        assert timeout_config.get_timeout("plugin_load") == 30.0
        assert timeout_config.get_timeout("health_check") == 5.0
    
    def test_plugin_override(self, timeout_config):
        """Test plugin-specific override."""
        timeout_config.set_plugin_timeout("slow-plugin", "plugin_load", 120.0)
        
        # Default for other plugins
        assert timeout_config.get_timeout("plugin_load", "normal-plugin") == 30.0
        
        # Override for slow-plugin
        assert timeout_config.get_timeout("plugin_load", "slow-plugin") == 120.0
    
    def test_fallback_to_default(self, timeout_config):
        """Test fallback to job_default for unknown operations."""
        # Unknown operation returns job_default
        assert timeout_config.get_timeout("unknown_op") == 300.0


# =============================================================================
# TESTS: TIMEOUT FUNCTIONS
# =============================================================================

class TestWithTimeout:
    """Tests for with_timeout function."""
    
    async def test_success(self):
        """Test successful operation within timeout."""
        async def fast_op():
            await asyncio.sleep(0.01)
            return "result"
        
        result = await with_timeout(fast_op(), timeout=1.0)
        assert result == "result"
    
    async def test_timeout(self):
        """Test operation that times out."""
        async def slow_op():
            await asyncio.sleep(10)
            return "result"
        
        with pytest.raises(TimeoutError) as exc_info:
            await with_timeout(slow_op(), timeout=0.1, operation="slow_op")
        
        assert exc_info.value.operation == "slow_op"
        assert exc_info.value.timeout == 0.1


class TestSyncWithTimeout:
    """Tests for sync_with_timeout function."""
    
    def test_success(self):
        """Test successful operation within timeout."""
        def fast_op():
            return "result"
        
        result = sync_with_timeout(fast_op, timeout=1.0)
        assert result == "result"
    
    def test_timeout(self):
        """Test operation that times out."""
        def slow_op():
            time.sleep(10)
            return "result"
        
        with pytest.raises(TimeoutError) as exc_info:
            sync_with_timeout(slow_op, timeout=0.1, operation="slow_op")
        
        assert exc_info.value.operation == "slow_op"


# =============================================================================
# TESTS: RATE LIMIT CONFIG
# =============================================================================

class TestRateLimitConfig:
    """Tests for RateLimitConfig."""
    
    def test_defaults(self):
        """Test default values."""
        config = RateLimitConfig()
        
        assert config.requests == 100
        assert config.window_seconds == 60.0
        assert config.burst == 10
    
    def test_custom_values(self):
        """Test custom values."""
        config = RateLimitConfig(
            requests=50,
            window_seconds=30.0,
            burst=5,
        )
        
        assert config.requests == 50
        assert config.window_seconds == 30.0
        assert config.burst == 5


# =============================================================================
# TESTS: RATE LIMITER
# =============================================================================

class TestRateLimiter:
    """Tests for RateLimiter."""
    
    def test_create(self, rate_limiter):
        """Test creating rate limiter."""
        assert rate_limiter._default_config is not None
    
    def test_check_allowed(self, rate_limiter):
        """Test check returns True when allowed."""
        assert rate_limiter.check("test-plugin") is True
    
    def test_check_after_exhausted(self):
        """Test check returns False when exhausted."""
        limiter = RateLimiter(
            default_config=RateLimitConfig(requests=2, window_seconds=60.0, burst=0)
        )
        
        assert limiter.check("plugin") is True
        assert limiter.check("plugin") is True
        assert limiter.check("plugin") is False
    
    def test_get_remaining(self, rate_limiter):
        """Test get_remaining."""
        initial = rate_limiter.get_remaining("plugin")
        assert initial == 110  # 100 + 10 burst
        
        rate_limiter.check("plugin", cost=10)
        
        remaining = rate_limiter.get_remaining("plugin")
        assert remaining == 100
    
    def test_reset(self, rate_limiter):
        """Test reset."""
        rate_limiter.check("plugin-a")
        rate_limiter.check("plugin-b")
        
        count = rate_limiter.reset()
        
        assert count == 2
        assert len(rate_limiter._buckets) == 0
    
    def test_reset_single_plugin(self, rate_limiter):
        """Test resetting single plugin."""
        rate_limiter.check("plugin-a")
        rate_limiter.check("plugin-b")
        
        count = rate_limiter.reset(plugin_id="plugin-a")
        
        assert count == 1
        assert "plugin-a:default" not in rate_limiter._buckets
    
    def test_plugin_specific_limit(self, rate_limiter):
        """Test plugin-specific rate limit."""
        rate_limiter.set_plugin_limit(
            "special-plugin",
            RateLimitConfig(requests=5, window_seconds=60.0, burst=0),
        )
        
        for _ in range(5):
            assert rate_limiter.check("special-plugin") is True
        
        assert rate_limiter.check("special-plugin") is False
    
    def test_refill(self):
        """Test token refill over time."""
        limiter = RateLimiter(
            default_config=RateLimitConfig(requests=10, window_seconds=1.0, burst=0)
        )
        
        # Use all tokens
        for _ in range(10):
            limiter.check("plugin")
        
        assert limiter.check("plugin") is False
        
        # Wait for some refill
        time.sleep(0.2)
        
        # Should have some tokens now (approximately 2)
        assert limiter.check("plugin") is True


# =============================================================================
# TESTS: PLUGIN MONITOR
# =============================================================================

class TestPluginMonitor:
    """Tests for PluginMonitor."""
    
    def test_create(self, monitor):
        """Test creating monitor."""
        assert monitor.audit is not None
        assert monitor.timeouts is not None
        assert monitor.rate_limiter is not None
        assert monitor.enabled is True
    
    def test_disable(self, monitor):
        """Test disabling monitor."""
        monitor.enabled = False
        
        # Log should return None when disabled
        result = monitor.log("test.event")
        assert result is None
        
        # Rate check should return True when disabled
        assert monitor.check_rate("plugin") is True
    
    def test_log(self, monitor):
        """Test logging through monitor."""
        entry = monitor.log(
            AuditEventType.PLUGIN_INSTALLED,
            plugin_id="test-plugin",
        )
        
        assert entry is not None
        assert entry.event_type == "plugin.installed"
    
    def test_check_rate(self, monitor):
        """Test rate checking through monitor."""
        result = monitor.check_rate("test-plugin")
        assert result is True
    
    def test_get_timeout(self, monitor):
        """Test getting timeout through monitor."""
        timeout = monitor.get_timeout("plugin_load")
        assert timeout == 30.0
    
    def test_get_stats(self, monitor):
        """Test getting stats."""
        monitor.log("event")
        
        stats = monitor.get_stats()
        
        assert stats["enabled"] is True
        assert stats["audit"]["total_entries"] == 1


# =============================================================================
# TESTS: GLOBAL FUNCTIONS
# =============================================================================

class TestGlobalFunctions:
    """Tests for global convenience functions."""
    
    def test_get_monitor_singleton(self):
        """Test get_monitor returns singleton."""
        m1 = get_monitor()
        m2 = get_monitor()
        
        assert m1 is m2
    
    def test_init_monitor(self):
        """Test init_monitor creates new instance."""
        m1 = get_monitor()
        m2 = init_monitor(audit_max_entries=50)
        
        assert m1 is not m2
        assert m2.audit._max_entries == 50
    
    def test_audit_log(self):
        """Test audit_log convenience function."""
        entry = audit_log(
            AuditEventType.PLUGIN_INSTALLED,
            plugin_id="test-plugin",
        )
        
        assert entry is not None
        assert entry.event_type == "plugin.installed"
    
    def test_check_rate_limit(self):
        """Test check_rate_limit convenience function."""
        result = check_rate_limit("test-plugin")
        assert result is True
    
    def test_get_timeout_function(self):
        """Test get_timeout convenience function."""
        timeout = get_timeout("plugin_load")
        assert timeout == 30.0


# =============================================================================
# TESTS: TIMEOUT ERROR
# =============================================================================

class TestTimeoutError:
    """Tests for TimeoutError exception."""
    
    def test_attributes(self):
        """Test error attributes."""
        error = TimeoutError("my_operation", 10.0)
        
        assert error.operation == "my_operation"
        assert error.timeout == 10.0
    
    def test_message(self):
        """Test error message."""
        error = TimeoutError("my_operation", 10.0)
        
        assert "my_operation" in str(error)
        assert "10.0s" in str(error)
