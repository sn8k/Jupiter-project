"""Tests for Bridge Job Management System.

Version: 0.2.0 - Added tests for export_job and export_jobs
"""

import pytest
import asyncio
import time
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from jupiter.core.bridge.jobs import (
    JobManager,
    JobStatus,
    Job,
    get_job_manager,
    init_job_manager,
    submit_job,
    cancel_job,
    get_job,
    list_jobs,
    export_job,
    export_jobs,
)

# Use anyio for async tests
pytestmark = pytest.mark.anyio


class TestJob:
    """Test Job dataclass."""
    
    def test_create_job(self):
        """Test creating a Job."""
        job = Job(
            id="test123",
            name="Test Job",
            plugin_id="test_plugin",
        )
        
        assert job.id == "test123"
        assert job.name == "Test Job"
        assert job.status == JobStatus.PENDING
        assert job.progress == 0
        assert job.plugin_id == "test_plugin"
    
    def test_to_dict(self):
        """Test serializing Job to dict."""
        job = Job(
            id="test123",
            name="Test Job",
            status=JobStatus.RUNNING,
            progress=50,
        )
        
        d = job.to_dict()
        
        assert d["id"] == "test123"
        assert d["name"] == "Test Job"
        assert d["status"] == "running"
        assert d["progress"] == 50
        assert "created_at" in d
        assert "duration_ms" in d


class TestJobStatus:
    """Test JobStatus enum."""
    
    def test_status_values(self):
        """Test all status values exist."""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELLED.value == "cancelled"


class TestJobManager:
    """Test JobManager class."""
    
    def test_init(self):
        """Test manager initialization."""
        manager = JobManager(max_concurrent=3, max_history=50)
        
        assert manager._max_concurrent == 3
        assert manager._max_history == 50
        assert len(manager._jobs) == 0
    
    async def test_submit_job(self):
        """Test submitting a job."""
        manager = JobManager()
        
        async def task(progress_cb):
            progress_cb(50)
            return "done"
        
        # Mock event emission
        with patch('jupiter.core.bridge.jobs.JobManager._emit_job_event'):
            job_id = await manager.submit("Test Task", task)
        
        assert job_id is not None
        assert len(job_id) == 8
        
        # Wait for completion
        await asyncio.sleep(0.1)
        
        job = manager.get(job_id)
        assert job is not None
        assert job.status == JobStatus.COMPLETED
        assert job.result == "done"
    
    async def test_job_progress(self):
        """Test job progress updates."""
        manager = JobManager()
        progress_values = []
        
        async def task(progress_cb):
            for i in range(0, 101, 25):
                progress_cb(i)
                await asyncio.sleep(0.01)
            return "done"
        
        with patch('jupiter.core.bridge.jobs.JobManager._emit_job_event'):
            job_id = await manager.submit("Progress Task", task)
        
        # Wait for completion
        await asyncio.sleep(0.2)
        
        job = manager.get(job_id)
        assert job is not None
        assert job.progress == 100
        assert job.status == JobStatus.COMPLETED
    
    async def test_job_failure(self):
        """Test job failure handling."""
        manager = JobManager()
        
        async def failing_task(progress_cb):
            raise ValueError("Test error")
        
        with patch('jupiter.core.bridge.jobs.JobManager._emit_job_event'):
            job_id = await manager.submit("Failing Task", failing_task)
        
        # Wait for failure
        await asyncio.sleep(0.1)
        
        job = manager.get(job_id)
        assert job is not None
        assert job.status == JobStatus.FAILED
        assert job.error is not None and "Test error" in job.error
    
    async def test_cancel_job(self):
        """Test cancelling a running job."""
        manager = JobManager()
        
        async def long_task(progress_cb):
            for i in range(100):
                progress_cb(i)
                await asyncio.sleep(0.1)
            return "done"
        
        with patch('jupiter.core.bridge.jobs.JobManager._emit_job_event'):
            job_id = await manager.submit("Long Task", long_task)
        
        # Give it time to start
        await asyncio.sleep(0.05)
        
        # Cancel
        result = await manager.cancel(job_id)
        assert result is True
        
        job = manager.get(job_id)
        assert job is not None
        assert job.status == JobStatus.CANCELLED
    
    async def test_cancel_nonexistent_job(self):
        """Test cancelling a non-existent job."""
        manager = JobManager()
        
        result = await manager.cancel("nonexistent")
        assert result is False
    
    def test_get_nonexistent(self):
        """Test getting a non-existent job."""
        manager = JobManager()
        
        job = manager.get("nonexistent")
        assert job is None
    
    async def test_list_jobs(self):
        """Test listing jobs."""
        manager = JobManager()
        
        async def quick_task(progress_cb):
            return "done"
        
        with patch('jupiter.core.bridge.jobs.JobManager._emit_job_event'):
            await manager.submit("Task 1", quick_task)
            await manager.submit("Task 2", quick_task)
            await manager.submit("Task 3", quick_task)
        
        # Wait for completion
        await asyncio.sleep(0.1)
        
        jobs = manager.list()
        assert len(jobs) == 3
    
    async def test_list_by_status(self):
        """Test filtering jobs by status."""
        manager = JobManager()
        
        async def quick_task(progress_cb):
            return "done"
        
        with patch('jupiter.core.bridge.jobs.JobManager._emit_job_event'):
            await manager.submit("Task 1", quick_task)
            await manager.submit("Task 2", quick_task)
        
        # Wait for completion
        await asyncio.sleep(0.1)
        
        completed = manager.list(status=JobStatus.COMPLETED)
        assert len(completed) == 2
        
        pending = manager.list(status=JobStatus.PENDING)
        assert len(pending) == 0
    
    async def test_list_by_plugin(self):
        """Test filtering jobs by plugin."""
        manager = JobManager()
        
        async def quick_task(progress_cb):
            return "done"
        
        with patch('jupiter.core.bridge.jobs.JobManager._emit_job_event'):
            await manager.submit("Task 1", quick_task, plugin_id="plugin_a")
            await manager.submit("Task 2", quick_task, plugin_id="plugin_b")
            await manager.submit("Task 3", quick_task, plugin_id="plugin_a")
        
        await asyncio.sleep(0.1)
        
        plugin_a_jobs = manager.list(plugin_id="plugin_a")
        assert len(plugin_a_jobs) == 2
    
    async def test_get_stats(self):
        """Test getting job statistics."""
        manager = JobManager()
        
        async def quick_task(progress_cb):
            return "done"
        
        with patch('jupiter.core.bridge.jobs.JobManager._emit_job_event'):
            await manager.submit("Task 1", quick_task)
            await manager.submit("Task 2", quick_task)
        
        await asyncio.sleep(0.1)
        
        stats = manager.get_stats()
        
        assert stats["total"] == 2
        assert stats["completed"] == 2
        assert stats["pending"] == 0
    
    async def test_clear_history(self):
        """Test clearing job history."""
        manager = JobManager()
        
        async def quick_task(progress_cb):
            return "done"
        
        with patch('jupiter.core.bridge.jobs.JobManager._emit_job_event'):
            await manager.submit("Task 1", quick_task)
            await manager.submit("Task 2", quick_task)
        
        await asyncio.sleep(0.1)
        
        cleared = manager.clear_history()
        assert cleared == 2
        
        jobs = manager.list()
        assert len(jobs) == 0
    
    async def test_history_limit(self):
        """Test history limit is enforced."""
        manager = JobManager(max_history=2)
        
        async def quick_task(progress_cb):
            return "done"
        
        with patch('jupiter.core.bridge.jobs.JobManager._emit_job_event'):
            for i in range(5):
                await manager.submit(f"Task {i}", quick_task)
        
        await asyncio.sleep(0.2)
        
        jobs = manager.list()
        # Should only have max_history completed jobs
        assert len(jobs) <= 2


class TestSyncJob:
    """Test sync job execution."""
    
    async def test_sync_function(self):
        """Test running a sync function as a job."""
        manager = JobManager()
        
        def sync_task(progress_cb):
            progress_cb(50)
            time.sleep(0.01)
            progress_cb(100)
            return "sync_done"
        
        with patch('jupiter.core.bridge.jobs.JobManager._emit_job_event'):
            job_id = await manager.submit("Sync Task", sync_task)
        
        # Wait for completion
        await asyncio.sleep(0.2)
        
        job = manager.get(job_id)
        assert job is not None
        assert job.status == JobStatus.COMPLETED
        assert job.result == "sync_done"


class TestGlobalFunctions:
    """Test global convenience functions."""
    
    def test_get_job_manager_singleton(self):
        """Test get_job_manager returns singleton."""
        m1 = get_job_manager()
        m2 = get_job_manager()
        
        assert m1 is m2
    
    def test_init_job_manager(self):
        """Test initializing new manager."""
        import jupiter.core.bridge.jobs as jobs_mod
        jobs_mod._manager = None
        
        manager = init_job_manager(max_concurrent=10, max_history=200)
        
        assert manager._max_concurrent == 10
        assert manager._max_history == 200
        assert get_job_manager() is manager
    
    async def test_submit_job_function(self):
        """Test submit_job convenience function."""
        init_job_manager()
        
        async def task(progress_cb):
            return "result"
        
        with patch.object(get_job_manager(), '_emit_job_event'):
            job_id = await submit_job("Test", task)
        
        assert job_id is not None
        
        await asyncio.sleep(0.1)
        
        job = get_job(job_id)
        assert job is not None
    
    def test_list_jobs_function(self):
        """Test list_jobs convenience function."""
        init_job_manager()
        
        jobs = list_jobs()
        assert isinstance(jobs, list)


class TestJobMetadata:
    """Test job metadata handling."""
    
    async def test_job_with_metadata(self):
        """Test job with custom metadata."""
        manager = JobManager()
        
        async def task(progress_cb):
            return "done"
        
        with patch('jupiter.core.bridge.jobs.JobManager._emit_job_event'):
            job_id = await manager.submit(
                "Task with Metadata",
                task,
                metadata={"key": "value", "count": 42}
            )
        
        await asyncio.sleep(0.1)
        
        job = manager.get(job_id)
        assert job is not None
        assert job.metadata["key"] == "value"
        assert job.metadata["count"] == 42


class TestJobExport:
    """Test job export functionality."""
    
    async def test_export_job_to_file(self, tmp_path):
        """Test exporting a single job to file."""
        manager = JobManager()
        
        async def task(progress_cb):
            progress_cb(100)
            return {"result": "success"}
        
        with patch('jupiter.core.bridge.jobs.JobManager._emit_job_event'):
            job_id = await manager.submit(
                "Export Test",
                task,
                plugin_id="test_plugin",
                metadata={"test": True}
            )
        
        # Wait for job to complete
        await asyncio.sleep(0.1)
        
        # Export to file
        output_file = tmp_path / "job_export.json"
        result_path = manager.export_job(job_id, output_file)
        
        assert isinstance(result_path, Path)
        assert result_path.exists()
        
        # Verify content
        with open(result_path) as f:
            data = json.load(f)
        
        assert data["id"] == job_id
        assert data["name"] == "Export Test"
        assert data["status"] == "completed"
        assert data["result"]["result"] == "success"
        assert data["plugin_id"] == "test_plugin"
    
    async def test_export_job_to_dict(self):
        """Test exporting a single job as dict (no output_path)."""
        manager = JobManager()
        
        async def task(progress_cb):
            return {"value": 42}
        
        with patch('jupiter.core.bridge.jobs.JobManager._emit_job_event'):
            job_id = await manager.submit("Dict Export", task)
        
        await asyncio.sleep(0.1)
        
        # Export without path returns dict
        result = manager.export_job(job_id)
        
        assert isinstance(result, dict)
        assert result["id"] == job_id
        assert result["name"] == "Dict Export"
        assert result["result"]["value"] == 42
    
    async def test_export_job_creates_directory(self, tmp_path):
        """Test that export_job creates missing directories."""
        manager = JobManager()
        
        async def task(progress_cb):
            return "done"
        
        with patch('jupiter.core.bridge.jobs.JobManager._emit_job_event'):
            job_id = await manager.submit("Dir Test", task)
        
        await asyncio.sleep(0.1)
        
        # Export to nested path that doesn't exist
        output_file = tmp_path / "nested" / "dir" / "export.json"
        result_path = manager.export_job(job_id, output_file)
        
        assert isinstance(result_path, Path)
        assert result_path.exists()
        assert result_path.parent.exists()
    
    def test_export_job_not_found(self):
        """Test exporting non-existent job raises ValueError."""
        manager = JobManager()
        
        with pytest.raises(ValueError, match="Job not found"):
            manager.export_job("nonexistent_id")
    
    async def test_export_jobs_all(self, tmp_path):
        """Test exporting all jobs."""
        manager = JobManager()
        
        async def task1(progress_cb):
            return "result1"
        
        async def task2(progress_cb):
            return "result2"
        
        with patch('jupiter.core.bridge.jobs.JobManager._emit_job_event'):
            await manager.submit("Job 1", task1, plugin_id="plugin_a")
            await manager.submit("Job 2", task2, plugin_id="plugin_b")
        
        await asyncio.sleep(0.2)
        
        output_file = tmp_path / "all_jobs.json"
        result_path = manager.export_jobs(output_file)
        
        assert isinstance(result_path, Path)
        assert result_path.exists()
        
        # Verify content
        with open(result_path) as f:
            data = json.load(f)
        
        assert len(data["jobs"]) == 2
        assert data["total_jobs"] == 2
    
    async def test_export_jobs_filter_status(self, tmp_path):
        """Test exporting jobs filtered by status."""
        manager = JobManager()
        
        async def success_task(progress_cb):
            return "ok"
        
        async def fail_task(progress_cb):
            raise Exception("fail")
        
        with patch('jupiter.core.bridge.jobs.JobManager._emit_job_event'):
            await manager.submit("Success", success_task)
            await manager.submit("Fail", fail_task)
        
        await asyncio.sleep(0.2)
        
        # Export only completed jobs
        output_file = tmp_path / "completed_jobs.json"
        result_path = manager.export_jobs(output_file, status=JobStatus.COMPLETED)
        
        with open(result_path) as f:
            data = json.load(f)
        
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["status"] == "completed"
    
    async def test_export_jobs_filter_plugin(self, tmp_path):
        """Test exporting jobs filtered by plugin."""
        manager = JobManager()
        
        async def task(progress_cb):
            return "done"
        
        with patch('jupiter.core.bridge.jobs.JobManager._emit_job_event'):
            await manager.submit("Job A", task, plugin_id="plugin_a")
            await manager.submit("Job B", task, plugin_id="plugin_b")
            await manager.submit("Job A2", task, plugin_id="plugin_a")
        
        await asyncio.sleep(0.2)
        
        output_file = tmp_path / "plugin_a_jobs.json"
        result_path = manager.export_jobs(output_file, plugin_id="plugin_a")
        
        with open(result_path) as f:
            data = json.load(f)
        
        assert len(data["jobs"]) == 2
        for job in data["jobs"]:
            assert job["plugin_id"] == "plugin_a"
    
    async def test_export_jobs_empty(self, tmp_path):
        """Test exporting when no jobs match."""
        manager = JobManager()
        
        output_file = tmp_path / "empty_jobs.json"
        result_path = manager.export_jobs(output_file, status=JobStatus.COMPLETED)
        
        # Should still create a file with empty jobs array
        with open(result_path) as f:
            data = json.load(f)
        
        assert data["total_jobs"] == 0
        assert len(data["jobs"]) == 0
    
    async def test_export_jobs_yaml_format(self, tmp_path):
        """Test exporting jobs in YAML format."""
        manager = JobManager()
        
        async def task(progress_cb):
            return "result"
        
        with patch('jupiter.core.bridge.jobs.JobManager._emit_job_event'):
            await manager.submit("YAML Test", task)
        
        await asyncio.sleep(0.1)
        
        output_file = tmp_path / "jobs.yaml"
        result_path = manager.export_jobs(output_file, format="yaml")
        
        assert result_path.exists()
        assert result_path.suffix == ".yaml"


class TestJobExportConvenienceFunctions:
    """Test module-level export convenience functions."""
    
    async def test_export_job_function(self, tmp_path):
        """Test export_job convenience function."""
        init_job_manager()
        
        async def task(progress_cb):
            return "result"
        
        with patch.object(get_job_manager(), '_emit_job_event'):
            job_id = await submit_job("Export Func Test", task)
        
        await asyncio.sleep(0.1)
        
        output_file = tmp_path / "func_export.json"
        result = export_job(job_id, output_file)
        
        assert isinstance(result, Path)
        assert result.exists()
    
    async def test_export_job_function_as_dict(self):
        """Test export_job convenience function returning dict."""
        init_job_manager()
        
        async def task(progress_cb):
            return {"data": "test"}
        
        with patch.object(get_job_manager(), '_emit_job_event'):
            job_id = await submit_job("Dict Func Test", task)
        
        await asyncio.sleep(0.1)
        
        result = export_job(job_id)
        
        assert isinstance(result, dict)
        assert result["id"] == job_id
    
    async def test_export_jobs_function(self, tmp_path):
        """Test export_jobs convenience function."""
        init_job_manager()
        
        async def task(progress_cb):
            return "data"
        
        with patch.object(get_job_manager(), '_emit_job_event'):
            await submit_job("Multi Export 1", task)
            await submit_job("Multi Export 2", task)
        
        await asyncio.sleep(0.2)
        
        output_file = tmp_path / "multi_export.json"
        result_path = export_jobs(output_file)
        
        assert isinstance(result_path, Path)
        assert result_path.exists()
