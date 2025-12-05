"""
AI Helper Plugin v2 - Jupiter Bridge Architecture

This plugin provides AI-assisted code analysis with suggestions for:
- Refactoring opportunities
- Documentation improvements  
- Security concerns
- Performance optimizations
- Test coverage gaps

Conforme à plugins_architecture.md v0.4.0

@version 1.3.0
@module jupiter.plugins.ai_helper
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime

__version__ = "1.3.0"

# =============================================================================
# BRIDGE REFERENCES (injected during init)
# =============================================================================

_bridge = None
_logger = None


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class AISuggestion:
    """Represents a single AI-generated suggestion."""
    path: str
    type: str  # refactoring, doc, security, optimization, testing, cleanup
    details: str
    severity: str  # info, low, medium, high, critical
    code_snippet: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None


@dataclass 
class PluginState:
    """Internal state of the AI Helper plugin."""
    enabled: bool = True
    provider: str = "mock"
    api_key: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)
    scanned_files: List[Dict[str, Any]] = field(default_factory=list)
    last_suggestions: List[AISuggestion] = field(default_factory=list)
    last_run: Optional[datetime] = None
    execution_count: int = 0
    error_count: int = 0
    total_suggestions: int = 0


# =============================================================================
# PLUGIN SINGLETON
# =============================================================================

_state: Optional[PluginState] = None


def _get_state() -> PluginState:
    """Get or create plugin state."""
    global _state
    if _state is None:
        _state = PluginState()
    return _state


# =============================================================================
# PLUGIN LIFECYCLE (Bridge v2 API)
# =============================================================================

def init(bridge) -> None:
    """
    Initialize the AI Helper plugin.
    
    Called by Bridge during plugin initialization phase.
    
    Args:
        bridge: Instance du Bridge fournissant les registres et services.
        
    Le Bridge expose un namespace `bridge.services` (§3.3.1) pour accéder
    aux services Jupiter sans importer directement `jupiter.core.*`.
    """
    global _bridge, _logger
    _bridge = bridge
    
    # Get dedicated logger via bridge.services (§3.3.1)
    _logger = bridge.services.get_logger("ai_helper")
    
    # Load plugin config (global + project overrides merged by Bridge §3.1.1)
    config = bridge.services.get_config("ai_helper") or {}
    
    state = _get_state()
    state.config = config
    state.enabled = config.get("enabled", True)
    state.provider = config.get("provider", "mock")
    state.api_key = config.get("api_key")
    
    _logger.info(
        "AI Helper initialized: enabled=%s, provider=%s",
        state.enabled,
        state.provider
    )
    _logger.debug(
        "AI Helper config keys=%s, api_key_present=%s",
        sorted(state.config.keys()),
        bool(state.api_key)
    )


def health() -> Dict[str, Any]:
    """
    Health check for the plugin.
    
    Returns:
        Health status dictionary with status, message, and details.
    """
    state = _get_state()
    
    # Check provider connectivity (mock always healthy)
    provider_healthy = True
    provider_message = "OK"
    
    if state.provider != "mock" and state.enabled:
        if not state.api_key:
            provider_healthy = False
            provider_message = "API key not configured"
    
    is_healthy = state.enabled and provider_healthy
    
    return {
        "status": "healthy" if is_healthy else "degraded",
        "message": provider_message if not provider_healthy else "AI Helper operational",
        "details": {
            "enabled": state.enabled,
            "provider": state.provider,
            "provider_connected": provider_healthy,
            "last_run": state.last_run.isoformat() if state.last_run else None,
            "execution_count": state.execution_count,
            "error_count": state.error_count
        }
    }


def metrics() -> Dict[str, Any]:
    """
    Return plugin metrics.
    
    Appelé périodiquement si `capabilities.metrics.enabled: true` dans le manifest.
    Si `capabilities.metrics.enabled` → carte de stats auto-générée dans l'UI (§3.4.3).
    
    Returns:
        Metrics dictionary for monitoring and dashboards.
    """
    state = _get_state()
    
    avg_duration = (
        state.total_suggestions / state.execution_count
        if state.execution_count > 0 else 0
    )
    
    return {
        "ai_helper_executions_total": state.execution_count,
        "ai_helper_errors_total": state.error_count,
        "ai_helper_suggestions_total": state.total_suggestions,
        "ai_helper_last_suggestions_count": len(state.last_suggestions),
        "ai_helper_last_execution": state.last_run.isoformat() if state.last_run else None,
        "ai_helper_avg_suggestions_per_run": avg_duration,
        "ai_helper_provider": state.provider,
        "ai_helper_enabled": state.enabled
    }


def reset_settings() -> Dict[str, Any]:
    """
    Reset plugin settings to defaults.
    
    Called by Bridge via `reset_settings(plugin_id)` or remote Meeting action (§8).
    
    Returns:
        dict with `success` and `message`.
    """
    default_config = {
        "enabled": True,
        "provider": "mock",
        "api_key": "",
        "suggestion_types": ["refactoring", "doc", "testing"],
        "severity_threshold": "info",
        "large_file_threshold_kb": 50,
        "max_functions_threshold": 20
    }
    
    if _bridge:
        _bridge.config.set("ai_helper", default_config)
    
    # Reset local state
    state = _get_state()
    state.config = default_config
    state.enabled = default_config["enabled"]
    state.provider = default_config["provider"]
    state.api_key = default_config.get("api_key")
    
    if _logger:
        _logger.info("AI Helper settings reset to defaults")
    
    return {"success": True, "message": "Settings reset to defaults"}


# =============================================================================
# ASYNC JOBS SUPPORT (§10.6)
# =============================================================================

async def submit_analysis_job(params: Dict[str, Any]) -> str:
    """
    Submit a long-running analysis task to the Bridge job system.
    
    Args:
        params: Parameters including files to analyze.
    
    Returns:
        job_id: Unique job identifier for tracking.
    """
    if not _bridge:
        raise RuntimeError("Plugin not initialized")
    
    job_id = await _bridge.jobs.submit(
        plugin_id="ai_helper",
        handler=_analysis_job_handler,
        params=params
    )
    return job_id


async def _analysis_job_handler(job, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handler for long-running analysis with cooperative cancellation (§10.6).
    
    Args:
        job: Job object with is_cancelled(), update_progress() methods.
        params: Task parameters.
    
    Returns:
        Analysis results.
    """
    import asyncio
    
    files = params.get("files", [])
    results = []
    
    for i, file_path in enumerate(files):
        # Cooperative cancellation check
        if job.is_cancelled():
            if _logger:
                _logger.info(f"AI analysis job {job.id} cancelled at file {i}")
            return {"status": "cancelled", "completed_files": i}
        
        # Simulate analysis (in real impl, would call LLM)
        await asyncio.sleep(0.1)
        results.append({
            "file": file_path,
            "analyzed": True,
            "suggestions": []
        })
        
        # Update progress via WebSocket
        job.update_progress(
            progress=int((i + 1) / len(files) * 100),
            message=f"Analyzing {i + 1}/{len(files)}",
            eta_seconds=int((len(files) - i - 1) * 0.1)
        )
    
    # Update stats
    state = _get_state()
    state.execution_count += 1
    state.last_run = datetime.now()
    
    return {"status": "completed", "results": results}


# =============================================================================
# ANALYSIS HOOKS
# =============================================================================

def on_scan(report: Dict[str, Any]) -> None:
    """
    Hook called after a scan is complete.
    
    Captures file list for later analysis.
    
    Args:
        report: Scan report containing files list
    """
    state = _get_state()
    files = report.get("files", [])
    state.scanned_files = files
    
    if _logger:
        _logger.info("AI Helper captured %d files from scan", len(files))
        if _logger.isEnabledFor(10):  # DEBUG level
            sample = [f.get("path") for f in files[:5]]
            _logger.debug("AI Helper sample files=%s", sample)


def on_analyze(summary: Dict[str, Any]) -> None:
    """
    Hook called after analysis.
    
    Generates AI suggestions and populates summary['refactoring'].
    
    Args:
        summary: Analysis summary to enrich with suggestions
    """
    state = _get_state()
    
    if not state.enabled:
        if _logger:
            _logger.debug("AI Helper disabled; skipping on_analyze")
        return
    
    try:
        start_time = time.time()
        state.execution_count += 1
        
        suggestions = _generate_suggestions(summary)
        state.last_suggestions = suggestions
        state.total_suggestions += len(suggestions)
        state.last_run = datetime.now()
        
        if _logger:
            _logger.info("AI Helper generated %d suggestion(s) in %.2fs",
                        len(suggestions), time.time() - start_time)
            if _logger.isEnabledFor(10):  # DEBUG level
                _logger.debug("AI Helper suggestions=%s",
                             [asdict(s) for s in suggestions])
        
        # Merge into existing refactoring list
        if "refactoring" not in summary:
            summary["refactoring"] = []
        
        # Filter by severity threshold
        threshold = state.config.get("severity_threshold", "info")
        severity_order = ["info", "low", "medium", "high", "critical"]
        threshold_idx = severity_order.index(threshold) if threshold in severity_order else 0
        
        for s in suggestions:
            s_idx = severity_order.index(s.severity) if s.severity in severity_order else 0
            if s_idx >= threshold_idx:
                summary["refactoring"].append({
                    "path": s.path,
                    "type": s.type,
                    "details": f"[AI] {s.details}",
                    "severity": s.severity
                })
                
    except Exception as e:
        state.error_count += 1
        if _logger:
            _logger.error("AI Helper error during analysis: %s", e, exc_info=True)


# =============================================================================
# SUGGESTION GENERATION
# =============================================================================

def _generate_suggestions(summary: Dict[str, Any]) -> List[AISuggestion]:
    """
    Generate suggestions based on the analysis summary.
    
    In a real implementation, this would call an LLM API.
    Currently implements heuristic-based mock suggestions.
    
    Args:
        summary: Analysis summary
        
    Returns:
        List of AI suggestions
    """
    state = _get_state()
    suggestions: List[AISuggestion] = []
    
    allowed_types = state.config.get("suggestion_types", 
                                      ["refactoring", "doc", "testing"])
    large_threshold = state.config.get("large_file_threshold_kb", 50) * 1024
    func_threshold = state.config.get("max_functions_threshold", 20)
    
    if _logger:
        _logger.debug("AI Helper generating suggestions: provider=%s, types=%s",
                     state.provider, allowed_types)
    
    if state.provider == "mock":
        # Documentation suggestions
        if "doc" in allowed_types and "python_summary" in summary:
            py_sum = summary.get("python_summary", {})
            if py_sum.get("avg_functions_per_file", 0) > 3:
                suggestions.append(AISuggestion(
                    path="Global",
                    type="doc",
                    details="High function density detected. Consider adding module-level docstrings.",
                    severity="info"
                ))
        
        # Cleanup suggestions
        if "cleanup" in allowed_types and "python_summary" in summary:
            py_sum = summary.get("python_summary", {})
            unused = py_sum.get("total_potentially_unused_functions", 0)
            if unused > 10:
                suggestions.append(AISuggestion(
                    path="Global",
                    type="cleanup",
                    details=f"Found {unused} potentially unused functions. Run 'jupiter check' to verify.",
                    severity="low"
                ))
        
        # Refactoring suggestions for large files
        if "refactoring" in allowed_types and "hotspots" in summary:
            hotspots = summary.get("hotspots", {})
            
            for item in hotspots.get("largest_files", []):
                try:
                    size_str = item.get("details", "0").split()[0]
                    size = int(size_str)
                    if size > large_threshold:
                        suggestions.append(AISuggestion(
                            path=item["path"],
                            type="refactoring",
                            details=f"File is large ({size // 1024}KB). Consider splitting into smaller modules.",
                            severity="medium"
                        ))
                except (ValueError, IndexError):
                    pass
            
            # God Object detection
            for item in hotspots.get("most_functions", []):
                try:
                    count_str = item.get("details", "0").split()[0]
                    count = int(count_str)
                    if count > func_threshold:
                        suggestions.append(AISuggestion(
                            path=item["path"],
                            type="refactoring",
                            details=f"High function count ({count}). This might be a 'God Object'. Consider extracting logic.",
                            severity="high"
                        ))
                except (ValueError, IndexError):
                    pass
        
        # Test coverage suggestions
        if "testing" in allowed_types and state.scanned_files:
            test_files = {
                f["path"] for f in state.scanned_files 
                if "test" in f["path"].lower() or "tests" in f["path"].lower()
            }
            source_files = [
                f for f in state.scanned_files 
                if f.get("file_type") == "py" and "test" not in f["path"].lower()
            ]
            
            missing_tests = 0
            for src in source_files:
                src_name = src["path"].replace("\\", "/").split("/")[-1]
                has_test = any(src_name in t for t in test_files)
                if not has_test:
                    missing_tests += 1
            
            if missing_tests > 0:
                suggestions.append(AISuggestion(
                    path="Global",
                    type="testing",
                    details=f"Detected {missing_tests} source files without obvious corresponding tests.",
                    severity="medium"
                ))
    
    return suggestions


# =============================================================================
# API HELPERS
# =============================================================================

def get_suggestions() -> List[Dict[str, Any]]:
    """
    Get the last generated suggestions.
    
    Returns:
        List of suggestions as dictionaries
    """
    state = _get_state()
    return [asdict(s) for s in state.last_suggestions]


def configure(settings: Dict[str, Any]) -> None:
    """
    Update plugin configuration.
    
    For backward compatibility with legacy code.
    
    Args:
        settings: New configuration values
    """
    init(settings)


def get_config() -> Dict[str, Any]:
    """
    Get current plugin configuration.
    
    Returns:
        Current configuration dictionary
    """
    state = _get_state()
    return state.config.copy()
