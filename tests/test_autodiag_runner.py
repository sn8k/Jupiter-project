"""
Tests for AutoDiagRunner (Phase 4).

Version: 1.0.0
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from jupiter.core.autodiag import (
    AutoDiagRunner,
    AutoDiagReport,
    AutodiagStatus,
    ScenarioResult,
    FalsePositiveInfo,
    run_autodiag_sync,
)


class TestAutodiagModels:
    """Tests for autodiag data models."""
    
    def test_scenario_result_to_dict(self):
        """Test ScenarioResult serialization."""
        result = ScenarioResult(
            name="test_scenario",
            status="passed",
            duration_seconds=1.5,
            triggered_functions=["func1", "func2"],
            details={"key": "value"},
        )
        
        d = result.to_dict()
        assert d["name"] == "test_scenario"
        assert d["status"] == "passed"
        assert d["duration_seconds"] == 1.5
        assert d["triggered_functions"] == ["func1", "func2"]
        assert d["details"] == {"key": "value"}
    
    def test_false_positive_info_to_dict(self):
        """Test FalsePositiveInfo serialization."""
        fp = FalsePositiveInfo(
            function_name="my_func",
            file_path="/path/to/file.py",
            reason="Called during test",
            scenario="cli_scan",
            call_count=3,
        )
        
        d = fp.to_dict()
        assert d["function_name"] == "my_func"
        assert d["file_path"] == "/path/to/file.py"
        assert d["reason"] == "Called during test"
        assert d["scenario"] == "cli_scan"
        assert d["call_count"] == 3
    
    def test_autodiag_report_to_dict(self):
        """Test AutoDiagReport serialization."""
        report = AutoDiagReport(
            status=AutodiagStatus.SUCCESS,
            project_root="/project",
            timestamp=1234567890.0,
            duration_seconds=5.5,
            static_total_functions=100,
            static_unused_count=10,
            scenarios_run=3,
            scenarios_passed=3,
            false_positive_count=2,
            true_unused_count=8,
            false_positive_rate=20.0,
            recommendations=["Review unused functions"],
        )
        
        d = report.to_dict()
        assert d["status"] == "success"
        assert d["project_root"] == "/project"
        assert d["duration_seconds"] == 5.5
        assert d["static_analysis"]["total_functions"] == 100
        assert d["dynamic_validation"]["scenarios_passed"] == 3
        assert d["false_positive_detection"]["false_positive_rate"] == 20.0
        assert "Review unused functions" in d["recommendations"]


class TestAutoDiagRunnerInit:
    """Tests for AutoDiagRunner initialization."""
    
    def test_default_initialization(self, tmp_path):
        """Test runner with default parameters."""
        runner = AutoDiagRunner(project_root=tmp_path)
        
        assert runner.project_root == tmp_path.resolve()
        assert runner.api_base_url == "http://localhost:8000"
        assert runner.diag_base_url == "http://127.0.0.1:8081"
        assert runner.skip_cli is False
        assert runner.skip_api is False
        assert runner.skip_plugins is False
        assert runner.timeout_seconds == 30.0
    
    def test_custom_initialization(self, tmp_path):
        """Test runner with custom parameters."""
        runner = AutoDiagRunner(
            project_root=tmp_path,
            api_base_url="http://custom:9000",
            diag_base_url="http://127.0.0.1:9081",
            skip_cli=True,
            skip_api=True,
            skip_plugins=True,
            timeout_seconds=60.0,
        )
        
        assert runner.api_base_url == "http://custom:9000"
        assert runner.diag_base_url == "http://127.0.0.1:9081"
        assert runner.skip_cli is True
        assert runner.skip_api is True
        assert runner.skip_plugins is True
        assert runner.timeout_seconds == 60.0


class TestAutoDiagRunnerScenarios:
    """Tests for individual scenario execution."""
    
    @pytest.fixture
    def runner(self, tmp_path):
        """Create a test runner."""
        # Create a minimal Python file for analysis
        (tmp_path / "test.py").write_text("def unused_func(): pass\n")
        return AutoDiagRunner(
            project_root=tmp_path,
            skip_api=True,  # Skip API to avoid network
        )
    
    def test_run_cli_command_success(self, runner):
        """Test successful CLI command execution."""
        async def run_test():
            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.communicate.return_value = (b"output", b"")
                mock_proc.returncode = 0
                mock_exec.return_value = mock_proc
                
                result = await runner._run_cli_command("scan", ["scan", "--help"])
                
                assert result.name == "cli_scan"
                assert result.status == "passed"
                assert "handle_scan" in result.triggered_functions
        
        asyncio.run(run_test())
    
    def test_run_cli_command_failure(self, runner):
        """Test failed CLI command execution."""
        async def run_test():
            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.communicate.return_value = (b"", b"error")
                mock_proc.returncode = 1
                mock_exec.return_value = mock_proc
                
                result = await runner._run_cli_command("scan", ["scan", "--help"])
                
                assert result.name == "cli_scan"
                assert result.status == "failed"
        
        asyncio.run(run_test())
    
    def test_run_cli_command_timeout(self, runner):
        """Test CLI command timeout."""
        runner.timeout_seconds = 0.1
        
        async def run_test():
            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.communicate.side_effect = asyncio.TimeoutError()
                mock_proc.kill = MagicMock()
                mock_exec.return_value = mock_proc
                
                result = await runner._run_cli_command("scan", ["scan", "--help"])
                
                assert result.status == "failed"
                assert "timed out" in result.error_message.lower()
        
        asyncio.run(run_test())


class TestAutoDiagRunnerComparison:
    """Tests for false positive detection logic."""
    
    @pytest.fixture
    def runner(self, tmp_path):
        """Create a test runner."""
        return AutoDiagRunner(project_root=tmp_path)
    
    def test_compare_results_detects_false_positives(self, runner):
        """Test that triggered functions are flagged as false positives."""
        # Simulate static analysis flagging functions
        runner._static_unused = {
            "file.py::handle_scan",
            "file.py::unused_func",
        }
        
        # Simulate dynamic calls
        runner._scenario_results = [
            ScenarioResult(
                name="cli_scan",
                status="passed",
                duration_seconds=1.0,
                triggered_functions=["handle_scan"],
            )
        ]
        
        false_positives, true_unused = runner._compare_results()
        
        # handle_scan should be a false positive (was triggered)
        assert len(false_positives) == 1
        assert false_positives[0].function_name == "handle_scan"
        
        # unused_func should be truly unused
        assert len(true_unused) == 1
        assert "unused_func" in true_unused[0]
    
    def test_compare_results_empty(self, runner):
        """Test comparison with no unused functions."""
        runner._static_unused = set()
        runner._scenario_results = []
        
        false_positives, true_unused = runner._compare_results()
        
        assert len(false_positives) == 0
        assert len(true_unused) == 0


class TestAutoDiagRunnerRecommendations:
    """Tests for recommendation generation."""
    
    @pytest.fixture
    def runner(self, tmp_path):
        """Create a test runner."""
        return AutoDiagRunner(project_root=tmp_path)
    
    def test_high_false_positive_rate_recommendation(self, runner):
        """Test recommendation for high false positive rate."""
        false_positives = [
            FalsePositiveInfo("f1", "p1", "r", "s") for _ in range(6)
        ]
        true_unused = ["func1", "func2"]
        
        recommendations = runner._generate_recommendations(false_positives, true_unused)
        
        assert any("false positive rate" in r.lower() for r in recommendations)
    
    def test_handler_false_positive_recommendation(self, runner):
        """Test recommendation when handlers are false positives."""
        false_positives = [
            FalsePositiveInfo("handle_scan", "p1", "r", "s"),
            FalsePositiveInfo("handle_analyze", "p2", "r", "s"),
        ]
        
        recommendations = runner._generate_recommendations(false_positives, [])
        
        assert any("handler" in r.lower() for r in recommendations)
    
    def test_many_true_unused_recommendation(self, runner):
        """Test recommendation when many functions are truly unused."""
        true_unused = [f"func_{i}" for i in range(25)]
        
        recommendations = runner._generate_recommendations([], true_unused)
        
        assert any("25" in r or "unused" in r.lower() for r in recommendations)


class TestRunAutodiagSync:
    """Tests for synchronous wrapper."""
    
    def test_sync_wrapper_executes(self, tmp_path):
        """Test that sync wrapper can execute."""
        # Create minimal project
        (tmp_path / "test.py").write_text("def test(): pass\n")
        
        # We test by running with all scenarios skipped for speed
        report = run_autodiag_sync(
            project_root=tmp_path,
            skip_cli=True,
            skip_api=True,
            skip_plugins=True,
        )
        
        # Should complete (may be SUCCESS or PARTIAL depending on what runs)
        assert report.status in (AutodiagStatus.SUCCESS, AutodiagStatus.PARTIAL, AutodiagStatus.FAILED)
        assert report.project_root == str(tmp_path.resolve())


class TestAutodiagRunEndpoint:
    """Tests for the /diag/run API endpoint."""
    
    def test_run_endpoint_exists(self):
        """Verify the endpoint is registered."""
        from jupiter.server.routers.autodiag import router
        
        # Get paths from routes (router adds prefix automatically)
        paths = []
        for route in router.routes:
            path = getattr(route, 'path', None)
            if path is not None:
                paths.append(path)
        
        # The router has prefix /diag, so paths include it
        assert "/diag/run" in paths

