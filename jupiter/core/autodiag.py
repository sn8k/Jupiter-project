"""
Autodiagnostic Runner for Jupiter.

This module provides automated self-analysis capabilities for Jupiter,
comparing static analysis results with dynamic runtime observations
to identify false positives in unused function detection.

Version: 1.4.0

Changelog:
- v1.4.0: Fixed error_message population for failed CLI/API scenarios
- v1.3.0: Fixed auth token loading from merged config
- v1.2.0: Added auth token support for protected API endpoints
- v1.1.0: Use CallGraphService for accurate unused function detection
- v1.0.0: Initial implementation
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    httpx = None  # type: ignore[assignment]
    HTTPX_AVAILABLE = False

from jupiter.core.scanner import ProjectScanner
from jupiter.core.report import ScanReport
from jupiter.core.analyzer import ProjectAnalyzer, FunctionUsageStatus, FunctionUsageInfo
from jupiter.core.callgraph import CallGraphService
from jupiter.core.cache import CacheManager
from jupiter.core.plugin_manager import PluginManager
from jupiter.config import load_merged_config

logger = logging.getLogger(__name__)


# =============================================================================
# AUTODIAG RESULT MODELS
# =============================================================================

class AutodiagStatus(str, Enum):
    """Overall status of autodiag run."""
    SUCCESS = "success"
    PARTIAL = "partial"  # Some scenarios failed
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ScenarioResult:
    """Result of running a single test scenario."""
    name: str
    status: str  # "passed", "failed", "skipped"
    duration_seconds: float
    triggered_functions: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FalsePositiveInfo:
    """Information about a detected false positive."""
    function_name: str
    file_path: str
    reason: str  # Why it was flagged as false positive
    scenario: str  # Which scenario triggered it
    call_count: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AutoDiagReport:
    """Complete report from an autodiag run."""
    status: AutodiagStatus
    project_root: str
    timestamp: float
    duration_seconds: float
    
    # Static analysis results
    static_total_functions: int = 0
    static_unused_count: int = 0
    static_possibly_unused_count: int = 0
    static_likely_used_count: int = 0
    
    # Dynamic validation results
    scenarios_run: int = 0
    scenarios_passed: int = 0
    scenarios_failed: int = 0
    
    # False positive detection
    false_positive_count: int = 0
    true_unused_count: int = 0
    false_positive_rate: float = 0.0  # % of flagged that were false positives
    accuracy_rate: float = 100.0  # % of total functions correctly classified
    
    # Details
    scenario_results: List[ScenarioResult] = field(default_factory=list)
    false_positives: List[FalsePositiveInfo] = field(default_factory=list)
    true_unused: List[str] = field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "project_root": self.project_root,
            "timestamp": self.timestamp,
            "duration_seconds": round(self.duration_seconds, 2),
            "static_analysis": {
                "total_functions": self.static_total_functions,
                "unused_count": self.static_unused_count,
                "possibly_unused_count": self.static_possibly_unused_count,
                "likely_used_count": self.static_likely_used_count,
            },
            "dynamic_validation": {
                "scenarios_run": self.scenarios_run,
                "scenarios_passed": self.scenarios_passed,
                "scenarios_failed": self.scenarios_failed,
            },
            "false_positive_detection": {
                "false_positive_count": self.false_positive_count,
                "true_unused_count": self.true_unused_count,
                "false_positive_rate": round(self.false_positive_rate, 2),
                "accuracy_rate": round(self.accuracy_rate, 2),
            },
            "scenario_results": [s.to_dict() for s in self.scenario_results],
            "false_positives": [fp.to_dict() for fp in self.false_positives],
            "true_unused": self.true_unused,
            "recommendations": self.recommendations,
        }


# =============================================================================
# AUTODIAG RUNNER
# =============================================================================

class AutoDiagRunner:
    """
    Run Jupiter against itself to validate unused function detection.
    
    The runner:
    1. Performs static analysis to identify potentially unused functions
    2. Executes test scenarios (CLI commands, API calls, plugin hooks)
    3. Compares static predictions with dynamic observations
    4. Reports false positives and true unused functions
    
    Usage:
        runner = AutoDiagRunner(project_root)
        report = await runner.run()
        print(report.false_positive_rate)
    """
    
    # Default CLI commands to test
    DEFAULT_CLI_SCENARIOS = [
        ("scan", ["scan", "--help"]),
        ("analyze", ["analyze", "--help"]),
        ("ci", ["ci", "--help"]),
        ("snapshots", ["snapshots", "list", "--help"]),
        ("server", ["server", "--help"]),
    ]
    
    def __init__(
        self,
        project_root: Path,
        api_base_url: Optional[str] = None,
        diag_base_url: Optional[str] = None,
        skip_cli: bool = False,
        skip_api: bool = False,
        skip_plugins: bool = False,
        timeout_seconds: float = 30.0,
        auth_token: Optional[str] = None,
    ):
        """
        Initialize the AutoDiagRunner.
        
        Args:
            project_root: Path to the project to analyze
            api_base_url: Base URL for main API (e.g., http://localhost:8000)
            diag_base_url: Base URL for diag API (e.g., http://127.0.0.1:8081)
            skip_cli: Skip CLI scenario tests
            skip_api: Skip API scenario tests
            skip_plugins: Skip plugin hook tests
            timeout_seconds: Timeout for each scenario
            auth_token: Optional auth token for protected API endpoints
        """
        self.project_root = Path(project_root).resolve()
        self.api_base_url = api_base_url or "http://localhost:8000"
        self.diag_base_url = diag_base_url or "http://127.0.0.1:8081"
        self.skip_cli = skip_cli
        self.skip_api = skip_api
        self.skip_plugins = skip_plugins
        self.timeout_seconds = timeout_seconds
        
        # Auth token for protected endpoints
        if auth_token:
            self.auth_token = auth_token
        else:
            # Try to load from merged config (global + project)
            try:
                # load_merged_config requires install_path and project_path
                # Use project_root as both (it will find global_config.yaml from install location)
                config = load_merged_config(self.project_root, self.project_root)
                self.auth_token = None
                
                # 1. Try security.tokens (list of TokenConfig)
                if config.security.tokens:
                    for tok_config in config.security.tokens:
                        if tok_config.role == "admin":
                            self.auth_token = tok_config.token
                            break
                    else:
                        self.auth_token = config.security.tokens[0].token
                
                # 2. Try security.token (single token)
                elif config.security.token:
                    self.auth_token = config.security.token
                
                # 3. Try users list (UserConfig with name, token, role)
                elif config.users:
                    for user in config.users:
                        if user.role == "admin" and user.token:
                            self.auth_token = user.token
                            logger.debug("Using admin token from user '%s'", user.name)
                            break
                    else:
                        # Fall back to first user with a token
                        for user in config.users:
                            if user.token:
                                self.auth_token = user.token
                                logger.debug("Using token from user '%s'", user.name)
                                break
                                
            except Exception as e:
                logger.debug("Could not load auth token from config: %s", e)
                self.auth_token = None
        self.timeout_seconds = timeout_seconds
        
        # Will be populated during run
        self._static_unused: Set[str] = set()
        self._dynamically_called: Set[str] = set()
        self._scenario_results: List[ScenarioResult] = []
    
    async def run(self) -> AutoDiagReport:
        """
        Execute the full autodiag workflow.
        
        Returns:
            AutoDiagReport with complete analysis results
        """
        start_time = time.time()
        logger.info("Starting autodiag for %s", self.project_root)
        
        try:
            # 1. Run static analysis
            static_results = await self._run_static_analysis()
            
            # 2. Execute test scenarios
            if not self.skip_cli:
                await self._run_cli_scenarios()
            
            if not self.skip_api and HTTPX_AVAILABLE:
                await self._run_api_scenarios()
            
            if not self.skip_plugins:
                await self._run_plugin_scenarios()
            
            # 3. Compare results
            false_positives, true_unused = self._compare_results()
            
            # 4. Generate recommendations
            recommendations = self._generate_recommendations(false_positives, true_unused)
            
            # 5. Build report
            duration = time.time() - start_time
            
            # Calculate metrics
            total_flagged = len(self._static_unused)
            total_functions = static_results.get("total_functions", 0)
            
            # False positive rate: % of flagged functions that were false positives
            # (100% means all flagged functions were actually used - good!)
            fp_rate = (len(false_positives) / total_flagged * 100) if total_flagged > 0 else 0.0
            
            # Accuracy rate: % of total functions correctly classified
            # High accuracy = good static analysis
            correctly_classified = total_functions - len(false_positives)
            accuracy_rate = (correctly_classified / total_functions * 100) if total_functions > 0 else 100.0
            
            # Determine overall status
            failed_scenarios = sum(1 for s in self._scenario_results if s.status == "failed")
            if failed_scenarios == len(self._scenario_results):
                status = AutodiagStatus.FAILED
            elif failed_scenarios > 0:
                status = AutodiagStatus.PARTIAL
            else:
                status = AutodiagStatus.SUCCESS
            
            report = AutoDiagReport(
                status=status,
                project_root=str(self.project_root),
                timestamp=start_time,
                duration_seconds=duration,
                static_total_functions=static_results.get("total_functions", 0),
                static_unused_count=static_results.get("unused_count", 0),
                static_possibly_unused_count=static_results.get("possibly_unused_count", 0),
                static_likely_used_count=static_results.get("likely_used_count", 0),
                scenarios_run=len(self._scenario_results),
                scenarios_passed=sum(1 for s in self._scenario_results if s.status == "passed"),
                scenarios_failed=failed_scenarios,
                false_positive_count=len(false_positives),
                true_unused_count=len(true_unused),
                false_positive_rate=fp_rate,
                accuracy_rate=accuracy_rate,
                scenario_results=self._scenario_results,
                false_positives=false_positives,
                true_unused=true_unused,
                recommendations=recommendations,
            )
            
            logger.info(
                "Autodiag completed: %d false positives (accuracy: %.1f%%), %d truly unused",
                len(false_positives), accuracy_rate, len(true_unused)
            )
            
            return report
            
        except Exception as e:
            logger.error("Autodiag failed: %s", e)
            return AutoDiagReport(
                status=AutodiagStatus.FAILED,
                project_root=str(self.project_root),
                timestamp=start_time,
                duration_seconds=time.time() - start_time,
                recommendations=[f"Autodiag failed with error: {e}"],
            )
    
    async def _run_static_analysis(self) -> Dict[str, int]:
        """Run static analysis using CallGraphService for accurate detection."""
        logger.debug("Running static analysis on %s using CallGraphService", self.project_root)
        
        # Use CallGraphService for accurate unused detection
        callgraph_service = CallGraphService(self.project_root)
        
        try:
            # Run call graph analysis
            callgraph_service.analyze(force=True)
            stats = callgraph_service.get_statistics()
            unused_functions = callgraph_service.get_unused_functions()
            
            # Collect unused functions
            for func in unused_functions:
                func_key = f"{func.get('file_path', '')}::{func.get('name', '')}"
                self._static_unused.add(func_key)
            
            logger.info(
                "Call graph analysis: %d total, %d used, %d unused",
                stats.get("total_functions", 0),
                stats.get("used_functions", 0),
                stats.get("unused_functions", 0),
            )
            
            return {
                "total_functions": stats.get("total_functions", 0),
                "unused_count": stats.get("unused_functions", 0),
                "possibly_unused_count": 0,  # Call graph doesn't have "possibly" state
                "likely_used_count": stats.get("used_functions", 0),
                "entry_points_count": stats.get("entry_points", 0),
            }
        except Exception as e:
            logger.warning("CallGraphService failed, falling back to analyzer: %s", e)
            # Fallback to ProjectAnalyzer if callgraph fails
            return await self._run_static_analysis_fallback()
    
    async def _run_static_analysis_fallback(self) -> Dict[str, int]:
        """Fallback static analysis using ProjectAnalyzer."""
        logger.debug("Running fallback static analysis on %s", self.project_root)
        
        # Initialize scanner with correct parameters
        scanner = ProjectScanner(
            root=self.project_root,
            ignore_hidden=True,
        )
        
        # Initialize analyzer with root path
        analyzer = ProjectAnalyzer(
            root=self.project_root,
        )
        
        # Run analysis: scanner.iter_files() returns files, analyzer.summarize() analyzes them
        files = list(scanner.iter_files())
        summary = analyzer.summarize(files).to_dict()
        
        # Extract function usage info (need to cast from object to Dict)
        python_summary_raw = summary.get("python_summary")
        python_summary: Dict[str, Any] = python_summary_raw if isinstance(python_summary_raw, dict) else {}
        usage_details: List[Dict[str, Any]] = python_summary.get("function_usage_details") or []
        usage_summary: Dict[str, Any] = python_summary.get("usage_summary") or {}
        
        # Collect functions that are flagged as unused or possibly_unused
        for info in usage_details:
            status = info.get("status", "")
            if status in (FunctionUsageStatus.UNUSED.value, FunctionUsageStatus.POSSIBLY_UNUSED.value):
                func_key = f"{info.get('file_path', '')}::{info.get('name', '')}"
                self._static_unused.add(func_key)
        
        return {
            "total_functions": usage_summary.get("total", 0),
            "unused_count": usage_summary.get("unused", 0),
            "possibly_unused_count": usage_summary.get("possibly_unused", 0),
            "likely_used_count": usage_summary.get("likely_used", 0),
        }
    
    async def _run_cli_scenarios(self) -> None:
        """Execute CLI commands to trigger handlers."""
        logger.debug("Running CLI scenarios")
        
        for name, args in self.DEFAULT_CLI_SCENARIOS:
            result = await self._run_cli_command(name, args)
            self._scenario_results.append(result)
    
    async def _run_cli_command(self, name: str, args: List[str]) -> ScenarioResult:
        """Run a single CLI command and capture results."""
        start_time = time.time()
        full_command = ["python", "-m", "jupiter.cli.main"] + args
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.project_root),
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.timeout_seconds
                )
                
                # Mark the handler as called
                handler_name = f"handle_{name.replace('-', '_')}"
                self._dynamically_called.add(handler_name)
                
                duration = time.time() - start_time
                
                # Build error message from stderr if command failed
                error_msg = None
                if proc.returncode != 0:
                    stderr_text = stderr.decode(errors='replace').strip() if stderr else ""
                    stdout_text = stdout.decode(errors='replace').strip() if stdout else ""
                    # Use stderr first, fallback to stdout, then generic message
                    error_msg = stderr_text or stdout_text or f"Exit code {proc.returncode}"
                    # Truncate very long error messages
                    if len(error_msg) > 500:
                        error_msg = error_msg[:500] + "..."
                
                return ScenarioResult(
                    name=f"cli_{name}",
                    status="passed" if proc.returncode == 0 else "failed",
                    duration_seconds=duration,
                    triggered_functions=[handler_name],
                    error_message=error_msg,
                    details={
                        "exit_code": proc.returncode,
                        "command": " ".join(full_command),
                    }
                )
                
            except asyncio.TimeoutError:
                proc.kill()
                return ScenarioResult(
                    name=f"cli_{name}",
                    status="failed",
                    duration_seconds=self.timeout_seconds,
                    error_message="Command timed out",
                )
                
        except Exception as e:
            return ScenarioResult(
                name=f"cli_{name}",
                status="failed",
                duration_seconds=time.time() - start_time,
                error_message=str(e),
            )
    
    async def _run_api_scenarios(self) -> None:
        """Call API endpoints to trigger handlers."""
        if not HTTPX_AVAILABLE:
            logger.warning("httpx not available, skipping API scenarios")
            return
        
        logger.debug("Running API scenarios")
        
        # First, call the exercise-dynamic endpoint to trigger dynamic functions
        await self._run_exercise_dynamic_scenario()
        
        # Then get the list of endpoints from diag API
        endpoints = await self._get_api_endpoints()
        
        if not endpoints:
            # Fall back to known endpoints
            endpoints = [
                {"path": "/health", "methods": ["GET"]},
                {"path": "/reports/last", "methods": ["GET"]},
                {"path": "/config", "methods": ["GET"]},
                {"path": "/projects", "methods": ["GET"]},
            ]
        
        for endpoint in endpoints:
            path = endpoint.get("path", "")
            methods = endpoint.get("methods", ["GET"])
            
            # Only test GET endpoints for safety
            if "GET" in methods:
                result = await self._call_api_endpoint(path)
                self._scenario_results.append(result)
    
    async def _run_exercise_dynamic_scenario(self) -> None:
        """Call the /diag/exercise-dynamic endpoint to trigger dynamic functions."""
        if httpx is None:
            return
        
        start_time = time.time()
        url = f"{self.diag_base_url}/diag/exercise-dynamic"
        
        try:
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.get(url, headers=headers)
                
                if resp.status_code == 200:
                    data = resp.json()
                    exercised = data.get("exercised_functions", [])
                    
                    # Record each exercised function as triggered
                    for func_info in exercised:
                        func_name = func_info.get("function", "")
                        # Extract just the method name (e.g., "get_state" from "autodiag_plugin.get_state")
                        if "." in func_name:
                            method_name = func_name.split(".")[-1]
                        else:
                            method_name = func_name
                        
                        self._dynamically_called.add(method_name)
                    
                    self._scenario_results.append(ScenarioResult(
                        name="diag_exercise_dynamic",
                        status="passed",
                        duration_seconds=time.time() - start_time,
                        triggered_functions=[f.get("function", "") for f in exercised],
                        details={
                            "total_exercised": data.get("total_exercised", 0),
                            "errors": data.get("errors", []),
                        },
                    ))
                    
                    logger.info(
                        "Exercise-dynamic scenario: %d functions exercised",
                        data.get("total_exercised", 0),
                    )
                else:
                    self._scenario_results.append(ScenarioResult(
                        name="diag_exercise_dynamic",
                        status="failed",
                        duration_seconds=time.time() - start_time,
                        error_message=f"HTTP {resp.status_code}",
                    ))
                    
        except Exception as e:
            logger.debug("Exercise-dynamic scenario failed: %s", e)
            self._scenario_results.append(ScenarioResult(
                name="diag_exercise_dynamic",
                status="failed",
                duration_seconds=time.time() - start_time,
                error_message=str(e),
            ))

    async def _get_api_endpoints(self) -> List[Dict[str, Any]]:
        """Fetch endpoint list from diag API if available."""
        if httpx is None:
            return []
        try:
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.diag_base_url}/diag/introspect", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("endpoints", [])
        except Exception as e:
            logger.debug("Could not fetch endpoints from diag API: %s", e)
        return []
    
    async def _call_api_endpoint(self, path: str) -> ScenarioResult:
        """Call a single API endpoint."""
        start_time = time.time()
        url = f"{self.api_base_url}{path}"
        
        if httpx is None:
            return ScenarioResult(
                name=f"api_{path}",
                status="skipped",
                duration_seconds=0.0,
                error_message="httpx not available",
            )
        
        try:
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.get(url, headers=headers)
                
                # Extract handler name from path
                handler_name = path.strip("/").replace("/", "_").replace("-", "_")
                if handler_name:
                    self._dynamically_called.add(handler_name)
                
                duration = time.time() - start_time
                is_success = resp.status_code < 400
                
                # Build error message for failed requests
                error_msg = None
                if not is_success:
                    try:
                        body = resp.text[:200] if resp.text else ""
                        error_msg = f"HTTP {resp.status_code}: {body}" if body else f"HTTP {resp.status_code}"
                    except Exception:
                        error_msg = f"HTTP {resp.status_code}"
                
                return ScenarioResult(
                    name=f"api_{handler_name}",
                    status="passed" if is_success else "failed",
                    duration_seconds=duration,
                    triggered_functions=[handler_name],
                    error_message=error_msg,
                    details={
                        "status_code": resp.status_code,
                        "url": url,
                    }
                )
                
        except Exception as e:
            return ScenarioResult(
                name=f"api_{path.strip('/').replace('/', '_')}",
                status="failed",
                duration_seconds=time.time() - start_time,
                error_message=str(e),
            )
    
    async def _run_plugin_scenarios(self) -> None:
        """Trigger plugin hooks."""
        logger.debug("Running plugin scenarios")
        
        start_time = time.time()
        triggered = []
        
        try:
            # Initialize plugin manager
            plugin_mgr = PluginManager(self.project_root)
            
            # Trigger available hooks with empty data
            hooks_to_test = [
                ("on_scan", {}),
                ("on_analyze", {}),
                ("on_ci", {}),
            ]
            
            for hook_name, data in hooks_to_test:
                try:
                    method = getattr(plugin_mgr, f"hook_{hook_name}", None)
                    if method:
                        method(data)
                        triggered.append(hook_name)
                except Exception as e:
                    logger.debug("Hook %s failed: %s", hook_name, e)
            
            # Mark plugin methods as called
            for hook in triggered:
                self._dynamically_called.add(f"hook_{hook}")
            
            self._scenario_results.append(ScenarioResult(
                name="plugins_hooks",
                status="passed" if triggered else "skipped",
                duration_seconds=time.time() - start_time,
                triggered_functions=triggered,
                details={"hooks_triggered": len(triggered)},
            ))
            
            # === NEW: Exercise plugin API methods ===
            # These methods are part of the plugin interface and may be called
            # dynamically. We exercise them here to detect false positives.
            await self._run_plugin_api_scenarios(plugin_mgr)
            
        except Exception as e:
            self._scenario_results.append(ScenarioResult(
                name="plugins_hooks",
                status="failed",
                duration_seconds=time.time() - start_time,
                error_message=str(e),
            ))
    
    async def _run_plugin_api_scenarios(self, plugin_mgr: PluginManager) -> None:
        """Exercise plugin API methods to detect false positives.
        
        These methods are part of the plugin interface but may not be called
        during normal hook execution. We explicitly call them here to verify
        they are reachable and to reduce false positive reports.
        """
        # Plugin API methods to exercise
        # Format: (plugin_name, method_name, args, kwargs)
        plugin_api_methods = [
            # AutodiagPlugin methods
            ("autodiag", "get_state", [], {}),
            ("autodiag", "get_last_report", [], {}),
            ("autodiag", "update_from_report", [{"status": "test", "timestamp": time.time()}], {}),
            # CodeQualityPlugin methods
            ("code_quality", "get_last_summary", [], {}),
            # PylanceAnalyzerPlugin methods
            ("pylance_analyzer", "get_summary", [], {}),
            ("pylance_analyzer", "get_diagnostics_for_file", ["test.py"], {}),
        ]
        
        for plugin_name, method_name, args, kwargs in plugin_api_methods:
            start_time = time.time()
            try:
                plugin = plugin_mgr.get_plugin(plugin_name)
                if plugin is None:
                    continue
                
                method = getattr(plugin, method_name, None)
                if method is None or not callable(method):
                    continue
                
                # Call the method
                result = method(*args, **kwargs)
                
                # Record as triggered
                self._dynamically_called.add(method_name)
                
                self._scenario_results.append(ScenarioResult(
                    name=f"plugin_api_{plugin_name}_{method_name}",
                    status="passed",
                    duration_seconds=time.time() - start_time,
                    triggered_functions=[method_name],
                    details={"plugin": plugin_name, "method": method_name, "result_type": type(result).__name__},
                ))
                
                logger.debug("Exercised %s.%s() -> %s", plugin_name, method_name, type(result).__name__)
                
            except Exception as e:
                logger.debug("Plugin API method %s.%s failed: %s", plugin_name, method_name, e)
                self._scenario_results.append(ScenarioResult(
                    name=f"plugin_api_{plugin_name}_{method_name}",
                    status="failed",
                    duration_seconds=time.time() - start_time,
                    error_message=str(e),
                    triggered_functions=[method_name],
                ))
    
    def _compare_results(self) -> tuple[List[FalsePositiveInfo], List[str]]:
        """Compare static analysis with dynamic observations."""
        false_positives: List[FalsePositiveInfo] = []
        true_unused: List[str] = []
        
        for func_key in self._static_unused:
            # Extract function name from key (path::func_name)
            parts = func_key.split("::")
            func_name = parts[-1] if len(parts) > 1 else func_key
            file_path = parts[0] if len(parts) > 1 else ""
            
            # Check if this function was triggered dynamically
            # We check both exact match and handler-style names
            triggered = False
            trigger_scenario = ""
            
            for scenario in self._scenario_results:
                for triggered_func in scenario.triggered_functions:
                    # Check if function name matches (fuzzy)
                    if (func_name == triggered_func or
                        func_name.replace("_", "") == triggered_func.replace("_", "") or
                        func_name in triggered_func or
                        triggered_func in func_name):
                        triggered = True
                        trigger_scenario = scenario.name
                        break
                if triggered:
                    break
            
            if triggered:
                false_positives.append(FalsePositiveInfo(
                    function_name=func_name,
                    file_path=file_path,
                    reason="Called during dynamic scenario execution",
                    scenario=trigger_scenario,
                ))
            else:
                true_unused.append(func_key)
        
        return false_positives, true_unused
    
    def _generate_recommendations(
        self,
        false_positives: List[FalsePositiveInfo],
        true_unused: List[str],
    ) -> List[str]:
        """Generate actionable recommendations based on results."""
        recommendations = []
        
        # Check absolute numbers, not just rates
        # A high "false positive rate among flagged" is actually GOOD if total flagged is low
        total_flagged = len(false_positives) + len(true_unused)
        
        # Only warn about FP rate if there are many flagged functions
        if total_flagged > 10 and len(false_positives) > 5:
            fp_rate = len(false_positives) / total_flagged * 100
            if fp_rate > 50:
                recommendations.append(
                    f"High false positive rate ({fp_rate:.1f}%) among {total_flagged} flagged functions. "
                    "Consider adding more framework decorator patterns to FRAMEWORK_DECORATORS."
                )
        
        # Common patterns in false positives
        if len(false_positives) > 3:
            handlers = [fp for fp in false_positives if "handle" in fp.function_name.lower()]
            if handlers:
                recommendations.append(
                    f"Found {len(handlers)} handler functions flagged incorrectly. "
                    "Consider registering them in CLI_HANDLERS or API_HANDLERS."
                )
        
        # True unused functions
        if true_unused:
            if len(true_unused) > 20:
                recommendations.append(
                    f"Found {len(true_unused)} truly unused functions. Consider "
                    "removing or documenting them as intentionally unused."
                )
            else:
                recommendations.append(
                    f"Review these {len(true_unused)} potentially unused functions: "
                    f"{', '.join(true_unused[:5])}{'...' if len(true_unused) > 5 else ''}"
                )
        
        # No recommendations needed
        if not recommendations:
            recommendations.append(
                "Analysis complete. No significant issues detected."
            )
        
        return recommendations


# =============================================================================
# SYNC WRAPPER FOR CLI
# =============================================================================

def run_autodiag_sync(
    project_root: Path,
    api_base_url: Optional[str] = None,
    diag_base_url: Optional[str] = None,
    skip_cli: bool = False,
    skip_api: bool = False,
    skip_plugins: bool = False,
    timeout_seconds: float = 30.0,
) -> AutoDiagReport:
    """
    Synchronous wrapper for running autodiag.
    
    This is the main entry point for CLI usage.
    """
    runner = AutoDiagRunner(
        project_root=project_root,
        api_base_url=api_base_url,
        diag_base_url=diag_base_url,
        skip_cli=skip_cli,
        skip_api=skip_api,
        skip_plugins=skip_plugins,
        timeout_seconds=timeout_seconds,
    )
    return asyncio.run(runner.run())
