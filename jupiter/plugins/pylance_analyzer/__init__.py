"""
Pylance Analyzer Plugin v2 - Jupiter Bridge Architecture

This plugin integrates with Pyright (the engine behind Pylance) to detect
type errors, unused imports, and other static analysis issues during scans.

Conforme à plugins_architecture.md v0.6.0

@version 1.0.0
@module jupiter.plugins.pylance_analyzer
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

__version__ = "1.0.0"

# Re-export data classes for backward compatibility
from .core.analyzer import (
    PylanceDiagnostic,
    PylanceFileReport,
    PylanceSummary,
    PylanceAnalyzer,
)

# =============================================================================
# BRIDGE REFERENCES (injected during init)
# =============================================================================

_bridge = None
_logger = None
_analyzer: Optional[PylanceAnalyzer] = None


# =============================================================================
# PLUGIN STATE
# =============================================================================

@dataclass
class PluginState:
    """Internal state of the Pylance Analyzer plugin."""
    enabled: bool = True
    strict: bool = False
    include_warnings: bool = True
    include_info: bool = False
    max_files: int = 500
    timeout: int = 120
    extra_args: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    last_run: Optional[datetime] = None
    execution_count: int = 0
    error_count: int = 0
    files_analyzed: int = 0
    total_errors: int = 0
    total_warnings: int = 0


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
    Initialize the Pylance Analyzer plugin.
    
    Called by Bridge during plugin initialization phase.
    
    Args:
        bridge: Instance du Bridge fournissant les registres et services.
    """
    global _bridge, _logger, _analyzer
    _bridge = bridge
    
    # Get dedicated logger via bridge.services (§3.3.1)
    _logger = bridge.services.get_logger("pylance_analyzer")
    
    # Load plugin config (global + project overrides merged by Bridge §3.1.1)
    config = bridge.services.get_config("pylance_analyzer") or {}
    
    state = _get_state()
    state.config = config
    state.enabled = config.get("enabled", True)
    state.strict = config.get("strict", False)
    state.include_warnings = config.get("include_warnings", True)
    state.include_info = config.get("include_info", False)
    state.max_files = config.get("max_files", 500)
    state.timeout = config.get("timeout", 120)
    state.extra_args = config.get("extra_args", [])
    
    # Create analyzer instance
    _analyzer = PylanceAnalyzer(
        enabled=state.enabled,
        strict=state.strict,
        include_warnings=state.include_warnings,
        include_info=state.include_info,
        max_files=state.max_files,
        timeout=state.timeout,
        extra_args=state.extra_args,
        logger=_logger,
    )
    
    _logger.info(
        "Pylance Analyzer initialized: enabled=%s, strict=%s, max_files=%d",
        state.enabled,
        state.strict,
        state.max_files,
    )


def shutdown() -> None:
    """Shutdown the plugin and cleanup resources."""
    global _analyzer
    if _logger:
        _logger.info("Pylance Analyzer shutting down")
    _analyzer = None


def health() -> Dict[str, Any]:
    """
    Return health status of the plugin.
    
    Returns:
        Dict with status, message, and details.
    """
    state = _get_state()
    
    # Check if pyright is available
    pyright_available = False
    pyright_path = None
    if _analyzer:
        pyright_available = _analyzer.check_pyright_available()
        pyright_path = _analyzer.pyright_path
    
    if not state.enabled:
        return {
            "status": "disabled",
            "message": "Plugin is disabled",
            "details": {"enabled": False},
        }
    
    if not pyright_available:
        return {
            "status": "degraded",
            "message": "Pyright not installed. Run: pip install pyright",
            "details": {
                "enabled": True,
                "pyright_available": False,
            },
        }
    
    return {
        "status": "healthy",
        "message": "Pylance Analyzer operational",
        "details": {
            "enabled": True,
            "pyright_available": True,
            "pyright_path": pyright_path,
            "strict_mode": state.strict,
            "max_files": state.max_files,
        },
    }


def metrics() -> Dict[str, Any]:
    """
    Return plugin metrics.
    
    Returns:
        Dict with execution counts and analysis statistics.
    """
    state = _get_state()
    return {
        "execution_count": state.execution_count,
        "error_count": state.error_count,
        "files_analyzed": state.files_analyzed,
        "total_errors_found": state.total_errors,
        "total_warnings_found": state.total_warnings,
        "last_run": state.last_run.isoformat() if state.last_run else None,
    }


def reset_settings() -> bool:
    """Reset plugin settings to defaults."""
    global _state
    _state = PluginState()
    if _analyzer:
        _analyzer.reset_config()
    if _logger:
        _logger.info("Pylance Analyzer settings reset to defaults")
    return True


# =============================================================================
# HOOKS (Legacy API - called by PluginManager)
# =============================================================================

def on_scan(report: Dict[str, Any]) -> None:
    """
    Hook called after scan to analyze Python files.
    
    Args:
        report: The scan report dict to enrich with Pylance diagnostics.
    """
    global _analyzer
    state = _get_state()
    
    if not state.enabled:
        if _logger:
            _logger.debug("Pylance Analyzer disabled, skipping scan hook")
        return
    
    if not _analyzer:
        if _logger:
            _logger.warning("Analyzer not initialized, skipping scan hook")
        return
    
    state.execution_count += 1
    state.last_run = datetime.now()
    
    try:
        result = _analyzer.analyze_report(report)
        
        if result:
            state.files_analyzed += result.total_files
            state.total_errors += result.total_errors
            state.total_warnings += result.total_warnings
            
            report["pylance"] = {
                "status": "ok",
                "summary": result.to_dict(),
            }
            
            if _logger:
                _logger.info(
                    "Pylance analysis complete: %d errors, %d warnings in %d files",
                    result.total_errors,
                    result.total_warnings,
                    result.total_files,
                )
        else:
            report["pylance"] = {
                "status": "skipped",
                "reason": _analyzer.last_error or "no_python_files",
            }
    except Exception as e:
        state.error_count += 1
        if _logger:
            _logger.error("Pylance analysis failed: %s", e)
        report["pylance"] = {
            "status": "error",
            "reason": "analysis_failed",
            "message": str(e),
        }


def on_analyze(summary: Dict[str, Any]) -> None:
    """
    Hook called after analyze to add Pylance metrics.
    
    Args:
        summary: The analysis summary dict to enrich.
    """
    if not _analyzer or not _analyzer.last_summary:
        return
    
    last = _analyzer.last_summary
    payload = {
        "total_errors": last.total_errors,
        "total_warnings": last.total_warnings,
        "files_with_errors": last.files_with_errors,
        "pyright_version": last.pyright_version,
    }
    summary["pylance"] = payload
    
    # Add to quality metrics if present
    if "quality" in summary and isinstance(summary["quality"], dict):
        summary["quality"]["pylance_errors"] = last.total_errors
        summary["quality"]["pylance_warnings"] = last.total_warnings


# =============================================================================
# PUBLIC API
# =============================================================================

def get_summary() -> Optional[PylanceSummary]:
    """Get the summary from the last analysis."""
    if _analyzer:
        return _analyzer.last_summary
    return None


def get_diagnostics_for_file(file_path: str) -> List[PylanceDiagnostic]:
    """Get diagnostics for a specific file from the last analysis."""
    if _analyzer:
        return _analyzer.get_diagnostics_for_file(file_path)
    return []


def configure(config: Dict[str, Any]) -> None:
    """
    Configure the plugin (legacy API).
    
    Args:
        config: Configuration dictionary.
    """
    state = _get_state()
    state.config = config
    state.enabled = config.get("enabled", True)
    state.strict = config.get("strict", False)
    state.include_warnings = config.get("include_warnings", True)
    state.include_info = config.get("include_info", False)
    state.max_files = config.get("max_files", 500)
    state.timeout = config.get("timeout", 120)
    state.extra_args = config.get("extra_args", [])
    
    if _analyzer:
        _analyzer.configure(
            enabled=state.enabled,
            strict=state.strict,
            include_warnings=state.include_warnings,
            include_info=state.include_info,
            max_files=state.max_files,
            timeout=state.timeout,
            extra_args=state.extra_args,
        )
    
    if _logger:
        _logger.info(
            "Pylance Analyzer configured: enabled=%s, strict=%s",
            state.enabled,
            state.strict,
        )


# =============================================================================
# LEGACY COMPATIBILITY - Class-based plugin interface
# =============================================================================

class PylanceAnalyzerPlugin:
    """
    Legacy class-based plugin interface for backward compatibility.
    
    The PluginManager may instantiate this class directly for plugins
    that haven't been fully migrated.
    """
    
    name = "pylance_analyzer"
    version = __version__
    description = "Static type analysis using Pyright (Pylance engine)."
    trust_level = "stable"
    
    # UI Configuration
    from jupiter.plugins import PluginUIConfig, PluginUIType
    ui_config = PluginUIConfig(
        ui_type=PluginUIType.SIDEBAR,
        menu_icon="🔍",
        menu_label_key="pylance_view",
        menu_order=75,
        view_id="pylance",
    )
    
    def __init__(self) -> None:
        self._state = _get_state()
    
    def configure(self, config: Dict[str, Any]) -> None:
        configure(config)
    
    def on_scan(self, report: Dict[str, Any]) -> None:
        on_scan(report)
    
    def on_analyze(self, summary: Dict[str, Any]) -> None:
        on_analyze(summary)
    
    def get_summary(self) -> Optional[PylanceSummary]:
        return get_summary()
    
    def get_diagnostics_for_file(self, file_path: str) -> List[PylanceDiagnostic]:
        return get_diagnostics_for_file(file_path)
    
    def get_ui_html(self) -> str:
        """Return HTML for legacy UI rendering."""
        from .web.ui import get_ui_html
        return get_ui_html()
    
    def get_ui_js(self) -> str:
        """Return JS for legacy UI rendering."""
        from .web.ui import get_ui_js
        return get_ui_js()
    
    def get_settings_html(self) -> str:
        """Return settings HTML for legacy UI rendering."""
        from .web.ui import get_settings_html
        return get_settings_html()
    
    def get_settings_js(self) -> str:
        """Return settings JS for legacy UI rendering."""
        from .web.ui import get_settings_js
        return get_settings_js()
