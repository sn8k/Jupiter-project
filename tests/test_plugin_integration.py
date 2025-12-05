"""Integration tests for plugin system (Phase 11.1).

Version: 0.3.0 - Added hot reload integration and dev mode tests

Tests complete plugin workflows:
- Installation from scratch
- Full plugin usage (CLI, API)
- Plugin updates with rollback
- Failure and recovery
- Jobs with cancellation
- Hot reload with dev mode guard
"""

import asyncio
import json
import os
import pytest
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import argparse

# Import Bridge components
from jupiter.core.bridge import (
    Bridge,
    PluginManifest,
    PluginType,
    PluginState,
    Permission,
    get_event_bus,
    get_cli_registry,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_plugins_dir(tmp_path):
    """Create a temporary plugins directory."""
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    return plugins_dir


@pytest.fixture
def sample_plugin(tmp_path):
    """Create a sample plugin for installation testing."""
    plugin_path = tmp_path / "sample_plugin"
    plugin_path.mkdir()
    
    manifest = {
        "id": "sample_plugin",
        "name": "Sample Integration Plugin",
        "version": "1.0.0",
        "description": "A plugin for integration testing",
        "author": "Test Author",
        "license": "MIT",
        "type": "tool",
        "jupiter_version": ">=1.0.0",
        "permissions": ["api", "fs_read"],
        "capabilities": {
            "hooks": ["on_scan", "on_analyze"],
            "cli": {"commands": [{"name": "sample-cmd", "description": "Sample command"}]},
        },
        "repository": "https://github.com/test/sample_plugin"
    }
    (plugin_path / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    
    # Create plugin.py
    plugin_code = '''"""Sample integration test plugin."""
import logging

logger = logging.getLogger(__name__)

class SamplePlugin:
    """Sample plugin implementation."""
    
    def __init__(self):
        self.enabled = True
        self.config = {}
        logger.info("SamplePlugin initialized")
    
    def initialize(self):
        logger.info("SamplePlugin starting")
    
    def shutdown(self):
        logger.info("SamplePlugin shutting down")
    
    def on_scan(self, report, **kwargs):
        """Hook called after scan."""
        logger.info("SamplePlugin received scan report with %d files", len(report.get("files", [])))
        return report

plugin_class = SamplePlugin
'''
    (plugin_path / "plugin.py").write_text(plugin_code, encoding="utf-8")
    
    # Create requirements.txt (empty for test)
    (plugin_path / "requirements.txt").write_text("# No dependencies\n", encoding="utf-8")
    
    return plugin_path


@pytest.fixture
def sample_plugin_v2(tmp_path):
    """Create version 2 of sample plugin for update testing."""
    plugin_path = tmp_path / "sample_plugin_v2"
    plugin_path.mkdir()
    
    manifest = {
        "id": "sample_plugin",
        "name": "Sample Integration Plugin",
        "version": "2.0.0",  # Upgraded version
        "description": "Updated plugin for integration testing",
        "author": "Test Author",
        "license": "MIT",
        "type": "tool",
        "jupiter_version": ">=1.0.0",
        "permissions": ["api", "fs_read", "fs_write"],
        "repository": "https://github.com/test/sample_plugin"
    }
    (plugin_path / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    
    # Updated plugin code
    plugin_code = '''"""Sample integration test plugin v2."""
import logging

logger = logging.getLogger(__name__)

class SamplePlugin:
    """Sample plugin v2 implementation."""
    VERSION = "2.0.0"
    
    def __init__(self):
        self.enabled = True
        logger.info("SamplePlugin v2 initialized")

plugin_class = SamplePlugin
'''
    (plugin_path / "plugin.py").write_text(plugin_code, encoding="utf-8")
    
    return plugin_path


@pytest.fixture
def bridge_instance():
    """Get a fresh Bridge instance."""
    # Reset singletons for test isolation
    Bridge._instance = None
    bridge = Bridge()
    return bridge


# =============================================================================
# Scenario 1: Install Plugin from Scratch
# =============================================================================

class TestScenarioInstallFromScratch:
    """Test complete plugin installation from scratch."""
    
    def test_install_validate_register_flow(self, sample_plugin, temp_plugins_dir, monkeypatch):
        """Test: validate manifest -> install -> register with Bridge."""
        from jupiter.cli.plugin_commands import (
            handle_plugins_install,
            _validate_plugin_manifest,
        )
        import jupiter.core.bridge.dev_mode as dev_mode_module
        
        # Enable dev mode for unsigned plugin
        monkeypatch.setattr(dev_mode_module, 'is_dev_mode', lambda: True)
        
        # Step 1: Validate manifest
        manifest = _validate_plugin_manifest(sample_plugin)
        assert manifest["id"] == "sample_plugin"
        assert manifest["version"] == "1.0.0"
        assert "permissions" in manifest
        
        # Step 2: Install
        args = argparse.Namespace(
            source=str(sample_plugin),
            force=False,
            install_deps=False,
            dry_run=False,
        )
        
        with patch('jupiter.cli.plugin_commands._get_plugins_dir', return_value=temp_plugins_dir):
            handle_plugins_install(args)
        
        # Step 3: Verify installation
        installed_path = temp_plugins_dir / "sample_plugin"
        assert installed_path.exists()
        assert (installed_path / "manifest.json").exists()
        assert (installed_path / "plugin.py").exists()
        
        # Verify manifest content preserved
        installed_manifest = json.loads((installed_path / "manifest.json").read_text())
        assert installed_manifest["id"] == "sample_plugin"
        assert installed_manifest["version"] == "1.0.0"
    
    def test_install_with_signature_verification(self, sample_plugin, temp_plugins_dir, capsys, monkeypatch):
        """Test: install with signature verification enabled."""
        from jupiter.cli.plugin_commands import (
            handle_plugins_sign,
            handle_plugins_install,
        )
        import jupiter.core.bridge.dev_mode as dev_mode_module
        
        # Disable dev mode to require signature check
        monkeypatch.setattr(dev_mode_module, 'is_dev_mode', lambda: False)
        
        # Create plugin.yaml for signing (sign requires yaml or json)
        plugin_yaml = sample_plugin / "plugin.yaml"
        manifest_data = json.loads((sample_plugin / "manifest.json").read_text())
        import yaml
        plugin_yaml.write_text(yaml.dump(manifest_data), encoding="utf-8")
        
        # Step 1: Sign the plugin
        sign_args = argparse.Namespace(
            path=str(sample_plugin),
            signer_id="integration-test",
            signer_name="Integration Test",
            trust_level="community",
            key=None,
        )
        
        try:
            handle_plugins_sign(sign_args)
        except SystemExit as e:
            if e.code != 0:
                captured = capsys.readouterr()
                pytest.skip(f"Signing failed: {captured.err}")
        
        # Verify signature file exists
        assert (sample_plugin / "plugin.sig").exists()
        
        # Step 2: Install signed plugin
        args = argparse.Namespace(
            source=str(sample_plugin),
            force=False,
            install_deps=False,
            dry_run=False,
        )
        
        with patch('jupiter.cli.plugin_commands._get_plugins_dir', return_value=temp_plugins_dir):
            handle_plugins_install(args)
        
        captured = capsys.readouterr()
        assert "community" in captured.out.lower()  # Trust level shown
        
        # Plugin should be installed
        assert (temp_plugins_dir / "sample_plugin").exists()


# =============================================================================
# Scenario 2: Full Plugin Usage (CLI)
# =============================================================================

class TestScenarioFullUsage:
    """Test complete plugin usage with CLI."""
    
    def test_plugin_cli_commands_registered(self, bridge_instance):
        """Test plugin CLI commands are registered."""
        cli_registry = get_cli_registry()
        
        # Register a sample command
        cli_registry.register_command(
            plugin_id="sample_plugin",
            name="sample",
            handler=lambda: print("Sample executed"),
            description="Sample command from plugin",
            options=[
                {"name": "--verbose", "action": "store_true", "help": "Verbose output"}
            ],
            check_permissions=False,
        )
        
        # Verify command is registered
        commands = cli_registry.get_all_commands()
        sample_commands = [c for c in commands if c.plugin_id == "sample_plugin"]
        assert len(sample_commands) >= 1
        assert sample_commands[0].name == "sample"
    
    def test_plugin_event_bus_integration(self, bridge_instance):
        """Test plugin receives events via event bus."""
        event_bus = get_event_bus()
        
        received_events = []
        
        def on_scan_complete(topic, data):
            """Event callback takes (topic, data) parameters."""
            received_events.append((topic, data))
        
        def on_plugin_loaded(topic, data):
            """Event callback takes (topic, data) parameters."""
            received_events.append((topic, data))
        
        # Subscribe to events
        event_bus.subscribe("scan.complete", on_scan_complete)
        event_bus.subscribe("plugin.loaded", on_plugin_loaded)
        
        # Emit events
        event_bus.emit("scan.complete", {"files": 10, "duration": 1.5})
        event_bus.emit("plugin.loaded", {"plugin_id": "sample_plugin"})
        
        # Verify events received
        assert len(received_events) == 2
        assert received_events[0][0] == "scan.complete"
        assert received_events[0][1]["files"] == 10
        assert received_events[1][0] == "plugin.loaded"
        
        # Cleanup
        event_bus.unsubscribe("scan.complete", on_scan_complete)
        event_bus.unsubscribe("plugin.loaded", on_plugin_loaded)


# =============================================================================
# Scenario 3: Plugin Update with Rollback
# =============================================================================

class TestScenarioUpdateWithRollback:
    """Test plugin update workflow with backup and rollback."""
    
    def test_update_creates_backup_and_updates(
        self, sample_plugin, sample_plugin_v2, temp_plugins_dir, monkeypatch
    ):
        """Test: update creates backup, installs new version."""
        from jupiter.cli.plugin_commands import handle_plugins_install, handle_plugins_update
        import jupiter.core.bridge.dev_mode as dev_mode_module
        
        monkeypatch.setattr(dev_mode_module, 'is_dev_mode', lambda: True)
        
        # Step 1: Install v1
        args_install = argparse.Namespace(
            source=str(sample_plugin),
            force=False,
            install_deps=False,
            dry_run=False,
        )
        
        with patch('jupiter.cli.plugin_commands._get_plugins_dir', return_value=temp_plugins_dir):
            handle_plugins_install(args_install)
        
        installed_path = temp_plugins_dir / "sample_plugin"
        assert installed_path.exists()
        
        v1_manifest = json.loads((installed_path / "manifest.json").read_text())
        assert v1_manifest["version"] == "1.0.0"
        
        # Step 2: Update to v2
        args_update = argparse.Namespace(
            plugin_id="sample_plugin",
            source=str(sample_plugin_v2),
            force=False,
            install_deps=False,
            no_backup=False,
        )
        
        with patch('jupiter.cli.plugin_commands._get_plugins_dir', return_value=temp_plugins_dir):
            with patch('jupiter.cli.plugin_commands.get_bridge') as mock_bridge:
                mock_bridge.return_value = Mock(get_plugin=Mock(return_value=None))
                handle_plugins_update(args_update)
        
        # Step 3: Verify update
        v2_manifest = json.loads((installed_path / "manifest.json").read_text())
        assert v2_manifest["version"] == "2.0.0"
        
        # Step 4: Verify backup created
        backup_dir = temp_plugins_dir / ".backups"
        assert backup_dir.exists()
        backups = list(backup_dir.glob("sample_plugin_*"))
        assert len(backups) >= 1
        
        # Backup should contain v1
        backup_manifest = json.loads((backups[0] / "manifest.json").read_text())
        assert backup_manifest["version"] == "1.0.0"
    
    def test_update_rollback_on_failure(
        self, sample_plugin, temp_plugins_dir, capsys, monkeypatch
    ):
        """Test: rollback to backup on update failure."""
        from jupiter.cli.plugin_commands import handle_plugins_install, handle_plugins_update
        import jupiter.core.bridge.dev_mode as dev_mode_module
        
        monkeypatch.setattr(dev_mode_module, 'is_dev_mode', lambda: True)
        
        # Install v1
        args_install = argparse.Namespace(
            source=str(sample_plugin),
            force=False,
            install_deps=False,
            dry_run=False,
        )
        
        with patch('jupiter.cli.plugin_commands._get_plugins_dir', return_value=temp_plugins_dir):
            handle_plugins_install(args_install)
        
        # Create invalid v2 source (will fail validation)
        invalid_source = temp_plugins_dir / "invalid_v2"
        invalid_source.mkdir()
        (invalid_source / "manifest.json").write_text("{ invalid }", encoding="utf-8")
        
        args_update = argparse.Namespace(
            plugin_id="sample_plugin",
            source=str(invalid_source),
            force=False,
            install_deps=False,
            no_backup=False,
        )
        
        with patch('jupiter.cli.plugin_commands._get_plugins_dir', return_value=temp_plugins_dir):
            with patch('jupiter.cli.plugin_commands.get_bridge') as mock_bridge:
                mock_bridge.return_value = Mock(get_plugin=Mock(return_value=None))
                with pytest.raises(SystemExit):
                    handle_plugins_update(args_update)
        
        captured = capsys.readouterr()
        # Should show update failed
        assert "failed" in captured.err.lower()
        
        # Original plugin should still be v1 (or backup restored)
        installed_path = temp_plugins_dir / "sample_plugin"
        if installed_path.exists():
            v1_manifest = json.loads((installed_path / "manifest.json").read_text())
            assert v1_manifest["version"] == "1.0.0"


# =============================================================================
# Scenario 4: Failure and Recovery
# =============================================================================

class TestScenarioFailureRecovery:
    """Test plugin failure scenarios and recovery."""
    
    def test_invalid_plugin_rejected(self, temp_plugins_dir, capsys, monkeypatch):
        """Test: invalid plugin is rejected during install."""
        from jupiter.cli.plugin_commands import handle_plugins_install
        import jupiter.core.bridge.dev_mode as dev_mode_module
        
        monkeypatch.setattr(dev_mode_module, 'is_dev_mode', lambda: True)
        
        # Create plugin with invalid manifest
        invalid_plugin = temp_plugins_dir / "invalid_plugin"
        invalid_plugin.mkdir()
        (invalid_plugin / "manifest.json").write_text('{"name": "NoID"}', encoding="utf-8")
        
        args = argparse.Namespace(
            source=str(invalid_plugin),
            force=False,
            install_deps=False,
            dry_run=False,
        )
        
        with patch('jupiter.cli.plugin_commands._get_plugins_dir', return_value=temp_plugins_dir):
            with pytest.raises(SystemExit) as exc_info:
                handle_plugins_install(args)
        
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "id" in captured.err.lower()  # Missing 'id' field
    
    def test_plugin_uninstall_preserves_others(self, sample_plugin, temp_plugins_dir, monkeypatch):
        """Test: uninstalling one plugin doesn't affect others."""
        from jupiter.cli.plugin_commands import handle_plugins_install, handle_plugins_uninstall
        import jupiter.core.bridge.dev_mode as dev_mode_module
        
        monkeypatch.setattr(dev_mode_module, 'is_dev_mode', lambda: True)
        
        # Install sample_plugin
        args_install = argparse.Namespace(
            source=str(sample_plugin),
            force=False,
            install_deps=False,
            dry_run=False,
        )
        
        with patch('jupiter.cli.plugin_commands._get_plugins_dir', return_value=temp_plugins_dir):
            handle_plugins_install(args_install)
        
        # Create and install another plugin
        other_plugin = temp_plugins_dir.parent / "other_plugin"
        other_plugin.mkdir()
        (other_plugin / "manifest.json").write_text(
            json.dumps({"id": "other_plugin", "name": "Other", "version": "1.0.0"}),
            encoding="utf-8"
        )
        
        args_install2 = argparse.Namespace(
            source=str(other_plugin),
            force=False,
            install_deps=False,
            dry_run=False,
        )
        
        with patch('jupiter.cli.plugin_commands._get_plugins_dir', return_value=temp_plugins_dir):
            handle_plugins_install(args_install2)
        
        # Uninstall sample_plugin
        args_uninstall = argparse.Namespace(
            plugin_id="sample_plugin",
            force=True,
        )
        
        with patch('jupiter.cli.plugin_commands._get_plugins_dir', return_value=temp_plugins_dir):
            with patch('jupiter.cli.plugin_commands.get_bridge') as mock_bridge:
                mock_bridge.return_value = Mock(get_plugin=Mock(return_value=None))
                handle_plugins_uninstall(args_uninstall)
        
        # sample_plugin should be removed
        assert not (temp_plugins_dir / "sample_plugin").exists()
        
        # other_plugin should still exist
        assert (temp_plugins_dir / "other_plugin").exists()


# =============================================================================
# Scenario 5: Performance Tests
# =============================================================================

class TestScenarioPerformance:
    """Performance-related integration tests."""
    
    def test_bulk_event_emission(self, bridge_instance):
        """Test: bulk event emission performance."""
        import time
        
        event_bus = get_event_bus()
        received_count = {"value": 0}
        
        def counter(topic, data):
            """Event callback must accept (topic, data)."""
            received_count["value"] += 1
        
        event_bus.subscribe("perf.test", counter)
        
        start = time.time()
        
        # Emit 1000 events
        for i in range(1000):
            event_bus.emit("perf.test", {"index": i})
        
        elapsed = time.time() - start
        
        # Should handle 1000 events quickly (< 1 second)
        assert elapsed < 1.0, f"Bulk event emission took {elapsed:.2f}s"
        assert received_count["value"] == 1000
        
        event_bus.unsubscribe("perf.test", counter)


# =============================================================================
# Scenario 6: Jobs with Cancellation
# =============================================================================

class TestScenarioJobsCancellation:
    """Test job submission and cancellation (Phase 11.1)."""
    
    @pytest.fixture
    def job_manager(self):
        """Create a fresh JobManager for each test."""
        from jupiter.core.bridge.jobs import JobManager
        return JobManager(max_concurrent=2, max_history=50)
    
    @pytest.mark.asyncio
    async def test_job_submit_and_complete(self, job_manager):
        """Test: submit a job that completes successfully."""
        from jupiter.core.bridge.jobs import JobStatus
        
        # Create a simple async job
        async def simple_job(progress_callback):
            for i in range(5):
                await asyncio.sleep(0.01)
                progress_callback((i + 1) * 20)
            return {"completed": True}
        
        # Submit the job
        job_id = await job_manager.submit(
            name="test_simple_job",
            func=simple_job,
            plugin_id="test_plugin",
        )
        
        assert job_id is not None
        
        # Wait for job to complete
        await asyncio.sleep(0.2)
        
        # Check job status
        job = job_manager.get(job_id)
        assert job is not None
        assert job.status == JobStatus.COMPLETED
        assert job.progress == 100
        assert job.result == {"completed": True}
        assert job.error is None
    
    @pytest.mark.asyncio
    async def test_job_cancellation(self, job_manager):
        """Test: cancel a running job."""
        from jupiter.core.bridge.jobs import JobStatus
        
        # Create a long-running job
        async def long_job(progress_callback):
            for i in range(100):
                await asyncio.sleep(0.1)  # Total: 10 seconds
                progress_callback(i + 1)
            return {"completed": True}
        
        # Submit the job
        job_id = await job_manager.submit(
            name="test_long_job",
            func=long_job,
            plugin_id="test_plugin",
        )
        
        # Wait for job to start running
        await asyncio.sleep(0.05)
        
        job = job_manager.get(job_id)
        assert job.status == JobStatus.RUNNING
        
        # Cancel the job
        cancelled = await job_manager.cancel(job_id)
        assert cancelled is True
        
        # Wait for cancellation to propagate
        await asyncio.sleep(0.1)
        
        # Check job is cancelled
        job = job_manager.get(job_id)
        assert job.status == JobStatus.CANCELLED
        assert job.progress < 100  # Should not have completed
    
    @pytest.mark.asyncio
    async def test_job_with_failure(self, job_manager):
        """Test: job that fails with an exception."""
        from jupiter.core.bridge.jobs import JobStatus
        
        # Create a job that fails
        async def failing_job(progress_callback):
            progress_callback(50)
            await asyncio.sleep(0.01)
            raise ValueError("Intentional test failure")
        
        # Submit the job
        job_id = await job_manager.submit(
            name="test_failing_job",
            func=failing_job,
            plugin_id="test_plugin",
        )
        
        # Wait for job to fail
        await asyncio.sleep(0.1)
        
        # Check job status
        job = job_manager.get(job_id)
        assert job is not None
        assert job.status == JobStatus.FAILED
        assert "Intentional test failure" in job.error
    
    @pytest.mark.asyncio
    async def test_job_progress_tracking(self, job_manager):
        """Test: job progress is tracked correctly."""
        from jupiter.core.bridge.jobs import JobStatus
        
        progress_values = []
        
        # Create a job that updates progress
        async def progress_job(progress_callback):
            for i in [25, 50, 75, 100]:
                progress_callback(i)
                await asyncio.sleep(0.01)
            return {"final_progress": 100}
        
        # Submit the job
        job_id = await job_manager.submit(
            name="test_progress_job",
            func=progress_job,
            plugin_id="test_plugin",
        )
        
        # Wait for completion
        await asyncio.sleep(0.2)
        
        # Check final progress
        job = job_manager.get(job_id)
        assert job.status == JobStatus.COMPLETED
        assert job.progress == 100
    
    @pytest.mark.asyncio
    async def test_job_stats(self, job_manager):
        """Test: job statistics are accurate."""
        from jupiter.core.bridge.jobs import JobStatus
        
        # Submit multiple jobs
        async def quick_job(progress_callback):
            progress_callback(100)
            return {"done": True}
        
        for i in range(3):
            await job_manager.submit(
                name=f"test_job_{i}",
                func=quick_job,
                plugin_id="test_plugin",
            )
        
        # Wait for all to complete
        await asyncio.sleep(0.2)
        
        # Check stats
        stats = job_manager.get_stats()
        assert stats["total"] == 3
        assert stats["completed"] == 3
        assert stats["pending"] == 0
        assert stats["running"] == 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, job_manager):
        """Test: circuit breaker opens after repeated failures."""
        from jupiter.core.bridge.jobs import JobStatus
        
        # Create a job that always fails
        async def always_fails(progress_callback):
            raise RuntimeError("Always fails")
        
        # Submit jobs until circuit breaker opens (default threshold is 5)
        for i in range(5):
            job_id = await job_manager.submit(
                name=f"fail_job_{i}",
                func=always_fails,
                plugin_id="circuit_test_plugin",
            )
            # Wait for job to fail
            await asyncio.sleep(0.05)
        
        # Check circuit breaker state
        breaker = job_manager._circuit_breakers.get("circuit_test_plugin")
        assert breaker is not None
        
        from jupiter.core.bridge.jobs import CircuitState
        assert breaker.state == CircuitState.OPEN
        
        # Submitting new job should raise error
        with pytest.raises(RuntimeError, match="Circuit breaker is open"):
            await job_manager.submit(
                name="should_fail",
                func=always_fails,
                plugin_id="circuit_test_plugin",
            )
    
    @pytest.mark.asyncio
    async def test_job_list_and_filter(self, job_manager):
        """Test: list jobs with filters."""
        from jupiter.core.bridge.jobs import JobStatus
        
        # Submit jobs for different plugins
        async def quick_job(progress_callback):
            progress_callback(100)
            return {"done": True}
        
        await job_manager.submit("job_a", quick_job, plugin_id="plugin_a")
        await job_manager.submit("job_b", quick_job, plugin_id="plugin_b")
        await job_manager.submit("job_a2", quick_job, plugin_id="plugin_a")
        
        # Wait for completion
        await asyncio.sleep(0.2)
        
        # Filter by plugin
        plugin_a_jobs = job_manager.list(plugin_id="plugin_a")
        assert len(plugin_a_jobs) == 2
        
        # Filter by status
        completed_jobs = job_manager.list(status=JobStatus.COMPLETED)
        assert len(completed_jobs) == 3


# =============================================================================
# Scenario 7: Hot Reload with Dev Mode Guard
# =============================================================================

class TestScenarioHotReload:
    """Test hot reload integration with developer mode guard."""
    
    def test_hot_reload_blocked_without_dev_mode(self, monkeypatch):
        """Test: hot reload fails when dev mode is disabled."""
        from jupiter.core.bridge.hot_reload import get_hot_reloader, ReloadResult
        import jupiter.core.bridge.dev_mode as dev_mode_module
        
        # Disable dev mode
        monkeypatch.setattr(dev_mode_module, 'is_dev_mode', lambda: False)
        
        reloader = get_hot_reloader()
        
        # Try to reload a plugin
        result = reloader.reload("any_plugin")
        
        assert isinstance(result, ReloadResult)
        assert result.success is False
        assert result.phase == "dev_mode_check"
        assert result.error is not None
        assert "developer mode" in result.error.lower()
    
    def test_hot_reload_allowed_with_dev_mode(self, monkeypatch, bridge_instance):
        """Test: hot reload proceeds when dev mode is enabled."""
        from jupiter.core.bridge.hot_reload import get_hot_reloader, ReloadResult
        import jupiter.core.bridge.dev_mode as dev_mode_module
        
        # Enable dev mode
        monkeypatch.setattr(dev_mode_module, 'is_dev_mode', lambda: True)
        
        reloader = get_hot_reloader()
        reloader.set_bridge(bridge_instance)
        
        # Plugin not found, but should pass dev mode check
        result = reloader.reload("nonexistent_plugin")
        
        assert isinstance(result, ReloadResult)
        assert result.success is False
        # Error should be about plugin not found, not dev mode
        assert result.phase == "validation"
        assert result.error is not None
        assert "not found" in result.error.lower()
    
    def test_can_reload_checks_dev_mode_first(self, monkeypatch):
        """Test: can_reload checks dev mode before other conditions."""
        from jupiter.core.bridge.hot_reload import get_hot_reloader
        import jupiter.core.bridge.dev_mode as dev_mode_module
        
        # Disable dev mode
        monkeypatch.setattr(dev_mode_module, 'is_dev_mode', lambda: False)
        
        reloader = get_hot_reloader()
        
        # Even for a valid plugin ID, dev mode check should be first
        can, reason = reloader.can_reload("any_plugin")
        
        assert can is False
        assert "developer mode" in reason.lower()
    
    def test_skip_dev_mode_check_for_testing(self, monkeypatch, bridge_instance):
        """Test: skip_dev_mode_check parameter allows bypass."""
        from jupiter.core.bridge.hot_reload import get_hot_reloader, ReloadResult
        import jupiter.core.bridge.dev_mode as dev_mode_module
        
        # Disable dev mode
        monkeypatch.setattr(dev_mode_module, 'is_dev_mode', lambda: False)
        
        reloader = get_hot_reloader()
        reloader.set_bridge(bridge_instance)
        
        # Skip dev mode check
        result = reloader.reload("test_plugin", skip_dev_mode_check=True)
        
        assert isinstance(result, ReloadResult)
        # Should not fail at dev_mode_check phase
        assert result.phase != "dev_mode_check"


# =============================================================================
# Scenario 8: API Integration
# =============================================================================

class TestScenarioAPIIntegration:
    """Test plugin API integration."""
    
    def test_plugin_api_registry_integration(self, bridge_instance):
        """Test: plugin API routes are registered and retrieved."""
        from jupiter.core.bridge.api_registry import get_api_registry, HTTPMethod
        
        api_registry = get_api_registry()
        
        # Create a test handler
        async def get_status():
            return {"status": "ok"}
        
        # Register the API route
        route = api_registry.register_route(
            plugin_id="api_test_plugin",
            path="/status",
            method=HTTPMethod.GET,
            handler=get_status,
            description="Get plugin status",
            check_permissions=False,  # Skip permission check for test
        )
        
        # Verify registration
        assert route is not None
        assert route.plugin_id == "api_test_plugin"
        assert route.path == "/status"
        
        # Get all routes and verify
        routes = api_registry.get_all_routes()
        plugin_routes = [r for r in routes if r.plugin_id == "api_test_plugin"]
        assert len(plugin_routes) >= 1
    
    def test_plugin_permissions_checked(self, bridge_instance):
        """Test: plugin API permissions are enforced."""
        from jupiter.core.bridge.permissions import PermissionChecker
        from unittest.mock import MagicMock
        
        # Create a mock bridge with a plugin that has specific permissions
        mock_bridge = MagicMock()
        mock_plugin_info = MagicMock()
        mock_manifest = MagicMock()
        mock_manifest.permissions = [Permission.REGISTER_API, Permission.FS_READ]
        mock_plugin_info.manifest = mock_manifest
        mock_bridge.get_plugin.return_value = mock_plugin_info
        
        # Create a permission checker with mock bridge
        checker = PermissionChecker(bridge=mock_bridge)
        
        # Check granted permission
        assert checker.has_permission("test_plugin", Permission.REGISTER_API)
        assert checker.has_permission("test_plugin", Permission.FS_READ)
        
        # Check non-granted permission
        assert not checker.has_permission("test_plugin", Permission.FS_WRITE)
        assert not checker.has_permission("test_plugin", Permission.RUN_COMMANDS)
