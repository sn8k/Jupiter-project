"""Tests for Circuit Breaker functionality in jobs.py.

Version: 0.1.0

Tests the circuit breaker system that prevents job submission
when a plugin has too many consecutive failures.
"""

import asyncio
import pytest
import time
from unittest.mock import MagicMock, patch

from jupiter.core.bridge.jobs import (
    CircuitState,
    CircuitBreaker,
    CircuitBreakerRegistry,
    JobManager,
    JobStatus,
    get_job_manager,
    init_job_manager,
)

# Use anyio for async tests
pytestmark = pytest.mark.anyio


# =============================================================================
# TESTS: CIRCUIT STATE
# =============================================================================

class TestCircuitState:
    """Tests for CircuitState enum."""
    
    def test_values(self):
        """Test circuit state values."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"
    
    def test_all_states(self):
        """Test all states exist."""
        states = list(CircuitState)
        assert len(states) == 3


# =============================================================================
# TESTS: CIRCUIT BREAKER
# =============================================================================

class TestCircuitBreaker:
    """Tests for CircuitBreaker dataclass."""
    
    def test_create(self):
        """Test creating a circuit breaker."""
        breaker = CircuitBreaker(
            plugin_id="test-plugin",
            failure_threshold=3,
            cooldown_seconds=30.0,
        )
        
        assert breaker.plugin_id == "test-plugin"
        assert breaker.failure_threshold == 3
        assert breaker.cooldown_seconds == 30.0
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
    
    def test_default_values(self):
        """Test default values."""
        breaker = CircuitBreaker(plugin_id="test")
        
        assert breaker.failure_threshold == 5
        assert breaker.cooldown_seconds == 60.0
        assert breaker.state == CircuitState.CLOSED
    
    def test_can_execute_closed(self):
        """Test can_execute when closed."""
        breaker = CircuitBreaker(plugin_id="test")
        assert breaker.can_execute() is True
    
    def test_record_success(self):
        """Test recording success."""
        breaker = CircuitBreaker(plugin_id="test")
        breaker.record_success()
        
        assert breaker.total_successes == 1
        assert breaker.total_calls == 1
        assert breaker.success_count == 1
        assert breaker.failure_count == 0
    
    def test_record_failure(self):
        """Test recording failure."""
        breaker = CircuitBreaker(plugin_id="test")
        breaker.record_failure()
        
        assert breaker.total_failures == 1
        assert breaker.total_calls == 1
        assert breaker.failure_count == 1
        assert breaker.success_count == 0
    
    def test_open_after_threshold(self):
        """Test circuit opens after threshold failures."""
        breaker = CircuitBreaker(plugin_id="test", failure_threshold=3)
        
        for _ in range(3):
            breaker.record_failure()
        
        assert breaker.state == CircuitState.OPEN
        assert breaker.times_opened == 1
        assert breaker.can_execute() is False
    
    def test_success_resets_failure_count(self):
        """Test that success resets consecutive failure count."""
        breaker = CircuitBreaker(plugin_id="test", failure_threshold=3)
        
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_success()  # Reset
        
        assert breaker.failure_count == 0
        assert breaker.state == CircuitState.CLOSED
    
    def test_half_open_after_cooldown(self):
        """Test transition to half-open after cooldown."""
        breaker = CircuitBreaker(
            plugin_id="test",
            failure_threshold=2,
            cooldown_seconds=0.1,  # Short for testing
        )
        
        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        
        # Wait for cooldown
        time.sleep(0.15)
        
        # Should transition to half-open
        assert breaker.can_execute() is True
        assert breaker.state == CircuitState.HALF_OPEN
    
    def test_half_open_success_closes(self):
        """Test successful test in half-open closes circuit."""
        breaker = CircuitBreaker(
            plugin_id="test",
            failure_threshold=2,
            cooldown_seconds=0.05,
        )
        
        # Open and wait for half-open
        breaker.record_failure()
        breaker.record_failure()
        time.sleep(0.06)
        breaker.can_execute()  # Transition to half-open
        
        # Record success
        breaker.record_success()
        
        assert breaker.state == CircuitState.CLOSED
        assert breaker.opened_at is None
    
    def test_half_open_failure_reopens(self):
        """Test failure in half-open reopens circuit."""
        breaker = CircuitBreaker(
            plugin_id="test",
            failure_threshold=2,
            cooldown_seconds=0.05,
        )
        
        # Open and wait for half-open
        breaker.record_failure()
        breaker.record_failure()
        time.sleep(0.06)
        breaker.can_execute()  # Transition to half-open
        
        # Record another failure
        breaker.record_failure()
        
        assert breaker.state == CircuitState.OPEN
        assert breaker.times_opened == 2
    
    def test_reset(self):
        """Test manual reset."""
        breaker = CircuitBreaker(plugin_id="test", failure_threshold=2)
        
        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        
        # Reset
        breaker.reset()
        
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.success_count == 0
        assert breaker.opened_at is None
    
    def test_to_dict(self):
        """Test serialization to dict."""
        breaker = CircuitBreaker(plugin_id="test")
        breaker.record_success()
        
        data = breaker.to_dict()
        
        assert data["plugin_id"] == "test"
        assert data["state"] == "closed"
        assert data["total_successes"] == 1


# =============================================================================
# TESTS: CIRCUIT BREAKER REGISTRY
# =============================================================================

class TestCircuitBreakerRegistry:
    """Tests for CircuitBreakerRegistry."""
    
    def test_create(self):
        """Test creating a registry."""
        registry = CircuitBreakerRegistry(
            default_threshold=3,
            default_cooldown=30.0,
        )
        
        assert registry._default_threshold == 3
        assert registry._default_cooldown == 30.0
    
    def test_get_or_create(self):
        """Test get_or_create creates new breaker."""
        registry = CircuitBreakerRegistry()
        
        breaker = registry.get_or_create("plugin-a")
        
        assert breaker is not None
        assert breaker.plugin_id == "plugin-a"
    
    def test_get_or_create_returns_same(self):
        """Test get_or_create returns same instance."""
        registry = CircuitBreakerRegistry()
        
        breaker1 = registry.get_or_create("plugin-a")
        breaker2 = registry.get_or_create("plugin-a")
        
        assert breaker1 is breaker2
    
    def test_get_nonexistent(self):
        """Test get returns None for unknown plugin."""
        registry = CircuitBreakerRegistry()
        
        assert registry.get("unknown") is None
    
    def test_can_execute(self):
        """Test can_execute checks breaker."""
        registry = CircuitBreakerRegistry()
        
        # Unknown plugin - allowed
        assert registry.can_execute("unknown") is True
        
        # Known plugin with closed circuit
        registry.get_or_create("plugin-a")
        assert registry.can_execute("plugin-a") is True
    
    def test_record_success(self):
        """Test record_success updates breaker."""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("plugin-a")
        
        registry.record_success("plugin-a")
        
        breaker = registry.get("plugin-a")
        assert breaker is not None
        assert breaker.total_successes == 1
    
    def test_record_failure(self):
        """Test record_failure updates breaker."""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("plugin-a")
        
        registry.record_failure("plugin-a")
        
        breaker = registry.get("plugin-a")
        assert breaker is not None
        assert breaker.total_failures == 1
    
    def test_reset(self):
        """Test reset resets a breaker."""
        registry = CircuitBreakerRegistry(default_threshold=2)
        breaker = registry.get_or_create("plugin-a")
        
        # Open it
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        
        # Reset
        assert registry.reset("plugin-a") is True
        assert breaker.state == CircuitState.CLOSED
    
    def test_reset_nonexistent(self):
        """Test reset returns False for unknown plugin."""
        registry = CircuitBreakerRegistry()
        assert registry.reset("unknown") is False
    
    def test_reset_all(self):
        """Test reset_all resets all breakers."""
        registry = CircuitBreakerRegistry(default_threshold=2)
        
        for name in ["a", "b", "c"]:
            b = registry.get_or_create(name)
            b.record_failure()
            b.record_failure()
        
        count = registry.reset_all()
        
        assert count == 3
        for name in ["a", "b", "c"]:
            breaker = registry.get(name)
            assert breaker is not None
            assert breaker.state == CircuitState.CLOSED
    
    def test_list_open(self):
        """Test list_open returns open breakers."""
        registry = CircuitBreakerRegistry(default_threshold=2)
        
        # Create some breakers
        registry.get_or_create("closed-1")
        
        open_breaker = registry.get_or_create("open-1")
        open_breaker.record_failure()
        open_breaker.record_failure()
        
        open_list = registry.list_open()
        
        assert len(open_list) == 1
        assert open_list[0].plugin_id == "open-1"
    
    def test_get_stats(self):
        """Test get_stats returns statistics."""
        registry = CircuitBreakerRegistry(default_threshold=2)
        
        registry.get_or_create("closed-1")
        registry.get_or_create("closed-2")
        
        open_breaker = registry.get_or_create("open-1")
        open_breaker.record_failure()
        open_breaker.record_failure()
        
        stats = registry.get_stats()
        
        assert stats["total_breakers"] == 3
        assert stats["closed"] == 2
        assert stats["open"] == 1
    
    def test_to_dict(self):
        """Test to_dict serializes all breakers."""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("a")
        registry.get_or_create("b")
        
        data = registry.to_dict()
        
        assert "a" in data
        assert "b" in data
        assert data["a"]["plugin_id"] == "a"


# =============================================================================
# TESTS: JOB MANAGER WITH CIRCUIT BREAKER
# =============================================================================

class TestJobManagerCircuitBreaker:
    """Tests for JobManager circuit breaker integration."""
    
    @pytest.fixture
    def manager(self):
        """Create a job manager with circuit breaker."""
        return JobManager(
            max_concurrent=5,
            circuit_breaker_threshold=3,
            circuit_breaker_cooldown=60.0,
            enable_circuit_breaker=True,
        )
    
    
    async def test_submit_with_circuit_breaker_check(self, manager):
        """Test that submit checks circuit breaker."""
        # Trigger enough failures to open circuit
        breaker = manager._circuit_breakers.get_or_create("failing-plugin")
        for _ in range(3):
            breaker.record_failure()
        
        # Try to submit job - should fail
        with pytest.raises(RuntimeError, match="Circuit breaker is open"):
            async def task(progress):
                pass
            await manager.submit("test", task, plugin_id="failing-plugin")
    
    
    async def test_submit_bypass_circuit_breaker(self, manager):
        """Test bypass_circuit_breaker flag."""
        # Open the circuit
        breaker = manager._circuit_breakers.get_or_create("failing-plugin")
        for _ in range(3):
            breaker.record_failure()
        
        # Submit with bypass
        async def task(progress):
            return "done"
        
        job_id = await manager.submit(
            "test",
            task,
            plugin_id="failing-plugin",
            bypass_circuit_breaker=True,
        )
        
        # Should succeed
        assert job_id is not None
        
        # Wait for completion
        await asyncio.sleep(0.1)
    
    
    async def test_success_records_to_circuit_breaker(self, manager):
        """Test successful job records to circuit breaker."""
        async def successful_task(progress):
            return "success"
        
        job_id = await manager.submit("test", successful_task, plugin_id="test-plugin")
        
        # Wait for completion
        await asyncio.sleep(0.1)
        
        breaker = manager.get_circuit_breaker("test-plugin")
        assert breaker.total_successes == 1
    
    
    async def test_failure_records_to_circuit_breaker(self, manager):
        """Test failed job records to circuit breaker."""
        async def failing_task(progress):
            raise ValueError("Test error")
        
        job_id = await manager.submit("test", failing_task, plugin_id="test-plugin")
        
        # Wait for completion
        await asyncio.sleep(0.1)
        
        breaker = manager.get_circuit_breaker("test-plugin")
        assert breaker.total_failures == 1
    
    
    async def test_circuit_opens_after_failures(self, manager):
        """Test circuit opens after threshold failures."""
        async def failing_task(progress):
            raise ValueError("Test error")
        
        plugin_id = "test-plugin"
        
        # Submit failing jobs
        for i in range(3):
            job_id = await manager.submit(f"test-{i}", failing_task, plugin_id=plugin_id)
            await asyncio.sleep(0.1)  # Wait for each job
        
        # Circuit should now be open
        assert manager.is_circuit_open(plugin_id) is True
    
    def test_get_circuit_breaker(self, manager):
        """Test get_circuit_breaker returns breaker."""
        # Not tracked yet
        assert manager.get_circuit_breaker("unknown") is None
        
        # Create one
        manager._circuit_breakers.get_or_create("test")
        assert manager.get_circuit_breaker("test") is not None
    
    def test_get_circuit_breaker_state(self, manager):
        """Test get_circuit_breaker_state."""
        assert manager.get_circuit_breaker_state("unknown") is None
        
        manager._circuit_breakers.get_or_create("test")
        assert manager.get_circuit_breaker_state("test") == CircuitState.CLOSED
    
    def test_is_circuit_open(self, manager):
        """Test is_circuit_open."""
        assert manager.is_circuit_open("unknown") is False
        
        breaker = manager._circuit_breakers.get_or_create("test")
        assert manager.is_circuit_open("test") is False
        
        # Open it
        for _ in range(3):
            breaker.record_failure()
        assert manager.is_circuit_open("test") is True
    
    def test_reset_circuit_breaker(self, manager):
        """Test reset_circuit_breaker."""
        breaker = manager._circuit_breakers.get_or_create("test")
        for _ in range(3):
            breaker.record_failure()
        
        assert manager.is_circuit_open("test") is True
        
        result = manager.reset_circuit_breaker("test")
        
        assert result is True
        assert manager.is_circuit_open("test") is False
    
    def test_reset_all_circuit_breakers(self, manager):
        """Test reset_all_circuit_breakers."""
        for name in ["a", "b"]:
            b = manager._circuit_breakers.get_or_create(name)
            for _ in range(3):
                b.record_failure()
        
        count = manager.reset_all_circuit_breakers()
        
        assert count == 2
        assert not manager.is_circuit_open("a")
        assert not manager.is_circuit_open("b")
    
    def test_list_open_circuits(self, manager):
        """Test list_open_circuits."""
        manager._circuit_breakers.get_or_create("closed")
        
        open_breaker = manager._circuit_breakers.get_or_create("open")
        for _ in range(3):
            open_breaker.record_failure()
        
        open_list = manager.list_open_circuits()
        
        assert len(open_list) == 1
        assert open_list[0].plugin_id == "open"
    
    def test_get_circuit_breaker_stats(self, manager):
        """Test get_circuit_breaker_stats."""
        manager._circuit_breakers.get_or_create("closed")
        
        open_breaker = manager._circuit_breakers.get_or_create("open")
        for _ in range(3):
            open_breaker.record_failure()
        
        stats = manager.get_circuit_breaker_stats()
        
        assert stats["total_breakers"] == 2
        assert stats["closed"] == 1
        assert stats["open"] == 1
    
    def test_get_all_circuit_breakers(self, manager):
        """Test get_all_circuit_breakers."""
        manager._circuit_breakers.get_or_create("a")
        manager._circuit_breakers.get_or_create("b")
        
        data = manager.get_all_circuit_breakers()
        
        assert "a" in data
        assert "b" in data


class TestJobManagerCircuitBreakerDisabled:
    """Tests for JobManager with circuit breaker disabled."""
    
    @pytest.fixture
    def manager(self):
        """Create a job manager without circuit breaker."""
        return JobManager(enable_circuit_breaker=False)
    
    
    async def test_submit_without_circuit_breaker_check(self, manager):
        """Test submit doesn't check circuit breaker when disabled."""
        # Open circuit manually (shouldn't matter)
        breaker = manager._circuit_breakers.get_or_create("test-plugin")
        for _ in range(5):
            breaker.record_failure()
        
        # Should still allow submission
        async def task(progress):
            return "done"
        
        job_id = await manager.submit("test", task, plugin_id="test-plugin")
        assert job_id is not None


# =============================================================================
# TESTS: GLOBAL FUNCTION WITH CIRCUIT BREAKER
# =============================================================================

class TestGlobalCircuitBreakerInit:
    """Tests for global init with circuit breaker params."""
    
    def test_init_with_circuit_breaker_params(self):
        """Test init_job_manager accepts circuit breaker params."""
        manager = init_job_manager(
            circuit_breaker_threshold=10,
            circuit_breaker_cooldown=120.0,
            enable_circuit_breaker=True,
        )
        
        assert manager._circuit_breakers._default_threshold == 10
        assert manager._circuit_breakers._default_cooldown == 120.0
        assert manager._enable_circuit_breaker is True
