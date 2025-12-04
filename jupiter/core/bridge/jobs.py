"""Job System for Jupiter Plugin Bridge.

Version: 0.3.0 - Added export_job() and export_jobs() methods

This module provides a centralized job management system for background tasks.
Features include:
- Async job submission and execution
- Job progress tracking
- Job cancellation
- Job history and status queries
- Event emission for job lifecycle
- Circuit breaker per plugin
- Export job results to file (JSON/YAML)

Usage:
    from jupiter.core.bridge.jobs import (
        JobManager, get_job_manager,
        submit_job, cancel_job, get_job, list_jobs
    )
    
    # Submit a job
    async def my_task(progress_callback):
        for i in range(100):
            await asyncio.sleep(0.1)
            progress_callback(i + 1)
        return {"result": "done"}
    
    job_id = await submit_job("my_task", my_task, plugin_id="my_plugin")
    
    # Check status
    job = get_job(job_id)
    print(f"Status: {job.status}, Progress: {job.progress}%")
    
    # Export job result
    manager = get_job_manager()
    manager.export_job(job_id, Path("job_result.json"))
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Status of a job."""
    
    PENDING = "pending"      # Job is queued but not started
    RUNNING = "running"      # Job is currently executing
    COMPLETED = "completed"  # Job finished successfully
    FAILED = "failed"        # Job failed with an error
    CANCELLED = "cancelled"  # Job was cancelled


@dataclass
class Job:
    """Represents a background job."""
    
    id: str
    name: str
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    result: Optional[Any] = None
    error: Optional[str] = None
    plugin_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize job to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "plugin_id": self.plugin_id,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self._get_duration_ms(),
            "metadata": self.metadata,
        }
    
    def _get_duration_ms(self) -> Optional[float]:
        """Get job duration in milliseconds."""
        if self.started_at is None:
            return None
        end_time = self.completed_at or time.time()
        return (end_time - self.started_at) * 1000


# Type alias for job functions
JobFunction = Callable[[Callable[[int], None]], Coroutine[Any, Any, Any]]
SyncJobFunction = Callable[[Callable[[int], None]], Any]


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitState(str, Enum):
    """State of a circuit breaker."""
    
    CLOSED = "closed"    # Normal operation, requests allowed
    OPEN = "open"        # Too many failures, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreaker:
    """Circuit breaker for a plugin.
    
    Tracks failures and prevents requests when a plugin is failing.
    State transitions:
    - CLOSED: Normal operation
    - OPEN: After failure_threshold consecutive failures
    - HALF_OPEN: After cooldown_seconds, allows one test request
    - Back to CLOSED if test succeeds, OPEN if test fails
    """
    
    plugin_id: str
    failure_threshold: int = 5
    cooldown_seconds: float = 60.0
    
    # State
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    opened_at: Optional[float] = None
    
    # Stats
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0
    times_opened: int = 0
    
    def can_execute(self) -> bool:
        """Check if execution is allowed.
        
        Returns:
            True if execution is allowed
        """
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if cooldown has passed
            if self.opened_at is None:
                return True
            
            elapsed = time.time() - self.opened_at
            if elapsed >= self.cooldown_seconds:
                # Move to half-open to test
                self.state = CircuitState.HALF_OPEN
                logger.info(
                    "Circuit breaker for '%s' entering HALF_OPEN state after %.1fs cooldown",
                    self.plugin_id, elapsed
                )
                return True
            return False
        
        # HALF_OPEN: allow one test request
        if self.state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    def record_success(self) -> None:
        """Record a successful execution."""
        self.total_calls += 1
        self.total_successes += 1
        self.success_count += 1
        self.failure_count = 0  # Reset consecutive failures
        self.last_success_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            # Recovery successful, close the circuit
            self.state = CircuitState.CLOSED
            self.opened_at = None
            logger.info(
                "Circuit breaker for '%s' recovered, now CLOSED",
                self.plugin_id
            )
        
    def record_failure(self) -> None:
        """Record a failed execution."""
        self.total_calls += 1
        self.total_failures += 1
        self.failure_count += 1
        self.success_count = 0  # Reset consecutive successes
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            # Test failed, open the circuit again
            self.state = CircuitState.OPEN
            self.opened_at = time.time()
            self.times_opened += 1
            logger.warning(
                "Circuit breaker for '%s' test failed, OPEN again",
                self.plugin_id
            )
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.opened_at = time.time()
                self.times_opened += 1
                logger.warning(
                    "Circuit breaker for '%s' OPEN after %d consecutive failures",
                    self.plugin_id, self.failure_count
                )
    
    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.opened_at = None
        logger.info("Circuit breaker for '%s' manually reset", self.plugin_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "plugin_id": self.plugin_id,
            "state": self.state.value,
            "failure_threshold": self.failure_threshold,
            "cooldown_seconds": self.cooldown_seconds,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "opened_at": self.opened_at,
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "times_opened": self.times_opened,
        }


class CircuitBreakerRegistry:
    """Registry of circuit breakers for plugins.
    
    Manages circuit breakers per plugin with configurable thresholds.
    """
    
    def __init__(
        self,
        default_threshold: int = 5,
        default_cooldown: float = 60.0,
    ):
        """Initialize the registry.
        
        Args:
            default_threshold: Default failure threshold
            default_cooldown: Default cooldown in seconds
        """
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._default_threshold = default_threshold
        self._default_cooldown = default_cooldown
        self._lock = Lock()
    
    def get_or_create(
        self,
        plugin_id: str,
        threshold: Optional[int] = None,
        cooldown: Optional[float] = None,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            threshold: Optional custom threshold
            cooldown: Optional custom cooldown
            
        Returns:
            The circuit breaker
        """
        with self._lock:
            if plugin_id not in self._breakers:
                self._breakers[plugin_id] = CircuitBreaker(
                    plugin_id=plugin_id,
                    failure_threshold=threshold or self._default_threshold,
                    cooldown_seconds=cooldown or self._default_cooldown,
                )
            return self._breakers[plugin_id]
    
    def get(self, plugin_id: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by plugin ID."""
        with self._lock:
            return self._breakers.get(plugin_id)
    
    def can_execute(self, plugin_id: str) -> bool:
        """Check if a plugin can execute.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if allowed, False if circuit is open
        """
        breaker = self.get(plugin_id)
        if breaker is None:
            return True
        return breaker.can_execute()
    
    def record_success(self, plugin_id: str) -> None:
        """Record a successful execution for a plugin."""
        with self._lock:
            breaker = self._breakers.get(plugin_id)
            if breaker:
                breaker.record_success()
    
    def record_failure(self, plugin_id: str) -> None:
        """Record a failed execution for a plugin."""
        with self._lock:
            breaker = self._breakers.get(plugin_id)
            if breaker:
                breaker.record_failure()
    
    def reset(self, plugin_id: str) -> bool:
        """Reset a circuit breaker.
        
        Returns:
            True if reset, False if not found
        """
        with self._lock:
            breaker = self._breakers.get(plugin_id)
            if breaker:
                breaker.reset()
                return True
            return False
    
    def reset_all(self) -> int:
        """Reset all circuit breakers.
        
        Returns:
            Number of breakers reset
        """
        with self._lock:
            count = 0
            for breaker in self._breakers.values():
                breaker.reset()
                count += 1
            return count
    
    def list_open(self) -> List[CircuitBreaker]:
        """List all open circuit breakers.
        
        Returns:
            List of open circuit breakers
        """
        with self._lock:
            return [
                b for b in self._breakers.values()
                if b.state in (CircuitState.OPEN, CircuitState.HALF_OPEN)
            ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics.
        
        Returns:
            Dictionary with stats
        """
        with self._lock:
            breakers = list(self._breakers.values())
        
        open_count = sum(1 for b in breakers if b.state == CircuitState.OPEN)
        half_open_count = sum(1 for b in breakers if b.state == CircuitState.HALF_OPEN)
        
        return {
            "total_breakers": len(breakers),
            "closed": len(breakers) - open_count - half_open_count,
            "open": open_count,
            "half_open": half_open_count,
            "total_trips": sum(b.times_opened for b in breakers),
        }
    
    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Serialize all breakers to dictionary."""
        with self._lock:
            return {
                plugin_id: breaker.to_dict()
                for plugin_id, breaker in self._breakers.items()
            }


# =============================================================================
# JOB MANAGER
# =============================================================================


class JobManager:
    """Manages background job execution and tracking.
    
    This manager handles:
    - Job submission and queuing
    - Async execution with progress callbacks
    - Job cancellation
    - Status and history queries
    - Event emission for job lifecycle
    - Circuit breaker per plugin
    """
    
    def __init__(
        self,
        max_concurrent: int = 5,
        max_history: int = 100,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_cooldown: float = 60.0,
        enable_circuit_breaker: bool = True,
    ):
        """Initialize the job manager.
        
        Args:
            max_concurrent: Maximum number of concurrent jobs
            max_history: Maximum number of completed jobs to retain
            circuit_breaker_threshold: Failures before circuit opens
            circuit_breaker_cooldown: Seconds before retrying after circuit opens
            enable_circuit_breaker: Whether to enable circuit breaker
        """
        self._max_concurrent = max_concurrent
        self._max_history = max_history
        self._enable_circuit_breaker = enable_circuit_breaker
        
        self._jobs: Dict[str, Job] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._lock = Lock()
        self._semaphore: Optional[asyncio.Semaphore] = None
        
        # Circuit breaker registry
        self._circuit_breakers = CircuitBreakerRegistry(
            default_threshold=circuit_breaker_threshold,
            default_cooldown=circuit_breaker_cooldown,
        )
        
        logger.debug(
            "JobManager initialized (max_concurrent=%d, max_history=%d, circuit_breaker=%s)",
            max_concurrent, max_history, enable_circuit_breaker
        )
    
    def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create the semaphore for concurrency control."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._max_concurrent)
        return self._semaphore
    
    async def submit(
        self,
        name: str,
        func: Union[JobFunction, SyncJobFunction],
        plugin_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        bypass_circuit_breaker: bool = False,
    ) -> str:
        """Submit a job for execution.
        
        Args:
            name: Human-readable job name
            func: Async or sync function to execute. Should accept a progress callback.
            plugin_id: Optional plugin that submitted the job
            metadata: Optional metadata for the job
            bypass_circuit_breaker: Skip circuit breaker check
            
        Returns:
            Job ID
            
        Raises:
            RuntimeError: If circuit breaker is open for the plugin
        """
        # Check circuit breaker
        if (
            self._enable_circuit_breaker
            and plugin_id
            and not bypass_circuit_breaker
        ):
            breaker = self._circuit_breakers.get_or_create(plugin_id)
            if not breaker.can_execute():
                raise RuntimeError(
                    f"Circuit breaker is open for plugin '{plugin_id}'. "
                    f"Too many consecutive failures. Will retry after cooldown."
                )
        
        job_id = str(uuid.uuid4())[:8]
        
        job = Job(
            id=job_id,
            name=name,
            plugin_id=plugin_id,
            metadata=metadata or {},
        )
        
        with self._lock:
            self._jobs[job_id] = job
        
        # Emit job started event
        self._emit_job_event("started", job)
        
        # Create the task
        task = asyncio.create_task(self._run_job(job, func))
        self._tasks[job_id] = task
        
        logger.info("Job submitted: %s (%s)", name, job_id)
        return job_id
    
    async def _run_job(
        self,
        job: Job,
        func: Union[JobFunction, SyncJobFunction],
    ) -> None:
        """Execute a job with progress tracking."""
        semaphore = self._get_semaphore()
        
        async with semaphore:
            # Update status
            with self._lock:
                job.status = JobStatus.RUNNING
                job.started_at = time.time()
            
            # Create progress callback
            def progress_callback(progress: int) -> None:
                with self._lock:
                    job.progress = min(max(progress, 0), 100)
                self._emit_job_event("progress", job)
            
            try:
                # Run the function
                if asyncio.iscoroutinefunction(func):
                    result = await func(progress_callback)
                else:
                    # Run sync function in executor
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, func, progress_callback
                    )
                
                # Mark as completed
                with self._lock:
                    job.status = JobStatus.COMPLETED
                    job.progress = 100
                    job.result = result
                    job.completed_at = time.time()
                
                # Record success in circuit breaker
                if self._enable_circuit_breaker and job.plugin_id:
                    self._circuit_breakers.record_success(job.plugin_id)
                
                self._emit_job_event("completed", job)
                logger.info("Job completed: %s (%s)", job.name, job.id)
                
            except asyncio.CancelledError:
                with self._lock:
                    job.status = JobStatus.CANCELLED
                    job.completed_at = time.time()
                
                # Note: Cancellation is not counted as a failure
                self._emit_job_event("cancelled", job)
                logger.info("Job cancelled: %s (%s)", job.name, job.id)
                
            except Exception as e:
                with self._lock:
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    job.completed_at = time.time()
                
                # Record failure in circuit breaker
                if self._enable_circuit_breaker and job.plugin_id:
                    self._circuit_breakers.record_failure(job.plugin_id)
                
                self._emit_job_event("failed", job)
                logger.error("Job failed: %s (%s): %s", job.name, job.id, e)
            
            finally:
                # Clean up task reference
                if job.id in self._tasks:
                    del self._tasks[job.id]
                
                # Prune old jobs
                self._prune_history()
    
    def _emit_job_event(self, event_type: str, job: Job) -> None:
        """Emit job lifecycle event."""
        try:
            from jupiter.core.bridge import (
                emit_job_started,
                emit_job_progress,
                emit_job_completed,
                emit_job_failed,
            )
            
            if event_type == "started":
                emit_job_started(job.id, job.name, job.plugin_id or "")
            elif event_type == "progress":
                emit_job_progress(job.id, job.progress)
            elif event_type == "completed":
                emit_job_completed(job.id, job.result)
            elif event_type == "failed":
                emit_job_failed(job.id, job.error or "Unknown error")
            elif event_type == "cancelled":
                # Use job_failed with cancelled message
                from jupiter.core.bridge.events import get_event_bus, EventTopic
                bus = get_event_bus()
                bus.emit(EventTopic.JOB_CANCELLED.value, {
                    "job_id": job.id,
                    "name": job.name,
                })
                
        except ImportError:
            logger.debug("Bridge events not available")
        except Exception as e:
            logger.warning("Failed to emit job event: %s", e)
    
    def _prune_history(self) -> None:
        """Remove old completed jobs to stay within history limit."""
        with self._lock:
            # Get completed jobs sorted by completion time
            completed = [
                j for j in self._jobs.values()
                if j.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)
            ]
            completed.sort(key=lambda j: j.completed_at or 0)
            
            # Remove oldest if over limit
            while len(completed) > self._max_history:
                oldest = completed.pop(0)
                del self._jobs[oldest.id]
    
    async def cancel(self, job_id: str) -> bool:
        """Cancel a running job.
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            True if cancelled, False if job not found or not cancellable
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            
            if job.status not in (JobStatus.PENDING, JobStatus.RUNNING):
                return False
        
        # Cancel the task
        task = self._tasks.get(job_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            return True
        
        # If no task (pending), mark as cancelled
        with self._lock:
            job.status = JobStatus.CANCELLED
            job.completed_at = time.time()
        
        self._emit_job_event("cancelled", job)
        return True
    
    def get(self, job_id: str) -> Optional[Job]:
        """Get a job by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job or None if not found
        """
        with self._lock:
            return self._jobs.get(job_id)
    
    def list(
        self,
        status: Optional[JobStatus] = None,
        plugin_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Job]:
        """List jobs with optional filters.
        
        Args:
            status: Optional status filter
            plugin_id: Optional plugin filter
            limit: Maximum number of jobs to return
            
        Returns:
            List of jobs (most recent first)
        """
        with self._lock:
            jobs = list(self._jobs.values())
        
        # Apply filters
        if status:
            jobs = [j for j in jobs if j.status == status]
        if plugin_id:
            jobs = [j for j in jobs if j.plugin_id == plugin_id]
        
        # Sort by creation time (most recent first)
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        
        return jobs[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get job statistics.
        
        Returns:
            Dictionary with job counts by status
        """
        with self._lock:
            jobs = list(self._jobs.values())
        
        stats = {
            "total": len(jobs),
            "pending": sum(1 for j in jobs if j.status == JobStatus.PENDING),
            "running": sum(1 for j in jobs if j.status == JobStatus.RUNNING),
            "completed": sum(1 for j in jobs if j.status == JobStatus.COMPLETED),
            "failed": sum(1 for j in jobs if j.status == JobStatus.FAILED),
            "cancelled": sum(1 for j in jobs if j.status == JobStatus.CANCELLED),
        }
        
        return stats
    
    def clear_history(self) -> int:
        """Clear completed jobs from history.
        
        Returns:
            Number of jobs cleared
        """
        with self._lock:
            to_remove = [
                job_id for job_id, job in self._jobs.items()
                if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)
            ]
            
            for job_id in to_remove:
                del self._jobs[job_id]
            
            return len(to_remove)
    
    # -------------------------------------------------------------------------
    # CIRCUIT BREAKER METHODS
    # -------------------------------------------------------------------------
    
    def get_circuit_breaker(self, plugin_id: str) -> Optional[CircuitBreaker]:
        """Get the circuit breaker for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            CircuitBreaker or None if not tracked
        """
        return self._circuit_breakers.get(plugin_id)
    
    def get_circuit_breaker_state(self, plugin_id: str) -> Optional[CircuitState]:
        """Get the circuit breaker state for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            CircuitState or None if not tracked
        """
        breaker = self._circuit_breakers.get(plugin_id)
        return breaker.state if breaker else None
    
    def is_circuit_open(self, plugin_id: str) -> bool:
        """Check if circuit breaker is open for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if circuit is open (requests blocked)
        """
        breaker = self._circuit_breakers.get(plugin_id)
        if breaker is None:
            return False
        return breaker.state == CircuitState.OPEN
    
    def reset_circuit_breaker(self, plugin_id: str) -> bool:
        """Reset the circuit breaker for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if reset, False if not found
        """
        return self._circuit_breakers.reset(plugin_id)
    
    def reset_all_circuit_breakers(self) -> int:
        """Reset all circuit breakers.
        
        Returns:
            Number of breakers reset
        """
        return self._circuit_breakers.reset_all()
    
    def list_open_circuits(self) -> List[CircuitBreaker]:
        """List all open circuit breakers.
        
        Returns:
            List of open circuit breakers
        """
        return self._circuit_breakers.list_open()
    
    def get_circuit_breaker_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics.
        
        Returns:
            Dictionary with stats
        """
        return self._circuit_breakers.get_stats()
    
    def get_all_circuit_breakers(self) -> Dict[str, Dict[str, Any]]:
        """Get all circuit breakers as dictionary.
        
        Returns:
            Dictionary mapping plugin_id to breaker info
        """
        return self._circuit_breakers.to_dict()
    
    # -------------------------------------------------------------------------
    # EXPORT METHODS
    # -------------------------------------------------------------------------
    
    def export_job(
        self,
        job_id: str,
        output_path: Optional[Path] = None,
        format: str = "json",
    ) -> Union[Dict[str, Any], Path]:
        """Export a job's result to file or return as dict.
        
        Args:
            job_id: Job ID to export
            output_path: Optional path to write the export file
            format: Export format ("json" or "yaml")
            
        Returns:
            If output_path is None: Dict with job data
            If output_path is set: Path to the exported file
            
        Raises:
            ValueError: If job not found or format invalid
        """
        job = self.get(job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")
        
        export_data = self._build_export_data(job)
        
        if output_path is None:
            return export_data
        
        return self._write_export_file(export_data, output_path, format)
    
    def export_jobs(
        self,
        output_path: Path,
        status: Optional[JobStatus] = None,
        plugin_id: Optional[str] = None,
        format: str = "json",
        include_results: bool = True,
    ) -> Path:
        """Export multiple jobs to a file.
        
        Args:
            output_path: Path to write the export file
            status: Optional status filter
            plugin_id: Optional plugin filter
            format: Export format ("json" or "yaml")
            include_results: Whether to include job results
            
        Returns:
            Path to the exported file
        """
        jobs = self.list(status=status, plugin_id=plugin_id, limit=10000)
        
        export_data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_jobs": len(jobs),
            "filters": {
                "status": status.value if status else None,
                "plugin_id": plugin_id,
            },
            "jobs": [
                self._build_export_data(job, include_results)
                for job in jobs
            ],
        }
        
        return self._write_export_file(export_data, output_path, format)
    
    def _build_export_data(
        self,
        job: Job,
        include_results: bool = True,
    ) -> Dict[str, Any]:
        """Build export data for a single job.
        
        Args:
            job: Job to export
            include_results: Whether to include the result field
            
        Returns:
            Dictionary with job data
        """
        data = job.to_dict()
        
        # Convert timestamps to ISO format for readability
        if data.get("created_at"):
            data["created_at_iso"] = datetime.fromtimestamp(
                data["created_at"], tz=timezone.utc
            ).isoformat()
        if data.get("started_at"):
            data["started_at_iso"] = datetime.fromtimestamp(
                data["started_at"], tz=timezone.utc
            ).isoformat()
        if data.get("completed_at"):
            data["completed_at_iso"] = datetime.fromtimestamp(
                data["completed_at"], tz=timezone.utc
            ).isoformat()
        
        if not include_results:
            data.pop("result", None)
        
        return data
    
    def _write_export_file(
        self,
        data: Dict[str, Any],
        output_path: Path,
        format: str,
    ) -> Path:
        """Write export data to a file.
        
        Args:
            data: Data to export
            output_path: Path to write to
            format: Export format ("json" or "yaml")
            
        Returns:
            Path to the written file
            
        Raises:
            ValueError: If format is invalid
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            import json
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        elif format == "yaml":
            import yaml
            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        logger.info("Exported job data to %s", output_path)
        return output_path


# Global job manager instance
_manager: Optional[JobManager] = None
_manager_lock = Lock()


def get_job_manager() -> JobManager:
    """Get the global job manager instance.
    
    Returns:
        The global JobManager instance
    """
    global _manager
    
    with _manager_lock:
        if _manager is None:
            _manager = JobManager()
    
    return _manager


def init_job_manager(
    max_concurrent: int = 5,
    max_history: int = 100,
    circuit_breaker_threshold: int = 5,
    circuit_breaker_cooldown: float = 60.0,
    enable_circuit_breaker: bool = True,
) -> JobManager:
    """Initialize or reinitialize the global job manager.
    
    Args:
        max_concurrent: Maximum concurrent jobs
        max_history: Maximum job history size
        circuit_breaker_threshold: Failures before circuit opens
        circuit_breaker_cooldown: Seconds before retrying after circuit opens
        enable_circuit_breaker: Whether to enable circuit breaker
        
    Returns:
        The initialized JobManager
    """
    global _manager
    
    with _manager_lock:
        _manager = JobManager(
            max_concurrent=max_concurrent,
            max_history=max_history,
            circuit_breaker_threshold=circuit_breaker_threshold,
            circuit_breaker_cooldown=circuit_breaker_cooldown,
            enable_circuit_breaker=enable_circuit_breaker,
        )
    
    logger.info("Global job manager initialized")
    return _manager


async def submit_job(
    name: str,
    func: Union[JobFunction, SyncJobFunction],
    plugin_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Convenience function to submit a job.
    
    Args:
        name: Job name
        func: Function to execute
        plugin_id: Optional plugin ID
        metadata: Optional metadata
        
    Returns:
        Job ID
    """
    return await get_job_manager().submit(name, func, plugin_id, metadata)


async def cancel_job(job_id: str) -> bool:
    """Convenience function to cancel a job.
    
    Args:
        job_id: Job ID to cancel
        
    Returns:
        True if cancelled
    """
    return await get_job_manager().cancel(job_id)


def get_job(job_id: str) -> Optional[Job]:
    """Convenience function to get a job.
    
    Args:
        job_id: Job ID
        
    Returns:
        Job or None
    """
    return get_job_manager().get(job_id)


def list_jobs(
    status: Optional[JobStatus] = None,
    plugin_id: Optional[str] = None,
    limit: int = 50,
) -> List[Job]:
    """Convenience function to list jobs.
    
    Args:
        status: Optional status filter
        plugin_id: Optional plugin filter
        limit: Maximum jobs to return
        
    Returns:
        List of jobs
    """
    return get_job_manager().list(status, plugin_id, limit)


def export_job(
    job_id: str,
    output_path: Optional[Path] = None,
    format: str = "json",
) -> Union[Dict[str, Any], Path]:
    """Convenience function to export a job's result.
    
    Args:
        job_id: Job ID to export
        output_path: Optional path to write the export file
        format: Export format ("json" or "yaml")
        
    Returns:
        If output_path is None: Dict with job data
        If output_path is set: Path to the exported file
    """
    return get_job_manager().export_job(job_id, output_path, format)


def export_jobs(
    output_path: Path,
    status: Optional[JobStatus] = None,
    plugin_id: Optional[str] = None,
    format: str = "json",
    include_results: bool = True,
) -> Path:
    """Convenience function to export multiple jobs to file.
    
    Args:
        output_path: Path to write the export file
        status: Optional status filter
        plugin_id: Optional plugin filter
        format: Export format ("json" or "yaml")
        include_results: Whether to include job results
        
    Returns:
        Path to the exported file
    """
    return get_job_manager().export_jobs(
        output_path, status, plugin_id, format, include_results
    )
