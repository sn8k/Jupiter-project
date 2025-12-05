"""
Autodiag Plugin - Bridge v2 Structure
=====================================

Automatic diagnostic tool for false-positive detection in unused code analysis.
Communicates with a separate autodiag server on configurable port (default 8081).

Version: 1.2.0

Changelog:
- v1.2.0: Fixed API endpoint URLs in Web UI, added inline CSS injection
- v1.1.0: Initial Bridge v2 implementation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__version__ = "1.2.0"

# Module-level logger (set during init)
_logger: Any = None


@dataclass
class AutodiagPluginState:
    """State for the autodiag plugin."""
    
    last_run_timestamp: float = 0.0
    last_status: str = "idle"  # idle, running, success, error
    false_positive_count: int = 0
    truly_unused_count: int = 0
    scenario_count: int = 0
    executed_functions: list[str] = field(default_factory=list)
    last_report: dict[str, Any] = field(default_factory=dict)


# Global plugin state
_state: AutodiagPluginState = AutodiagPluginState()


def init(bridge) -> bool:
    """
    Initialize the autodiag plugin.
    
    Args:
        bridge: The plugin bridge instance
        
    Returns:
        True if initialization successful
    """
    global _logger
    _logger = bridge.services.get_logger("autodiag")
    
    if _logger:
        _logger.info("Autodiag plugin initialized (v%s)", __version__)
    
    return True


def shutdown() -> None:
    """Clean up plugin resources."""
    global _state
    if _logger:
        _logger.info("Autodiag plugin shutting down")
    _state = AutodiagPluginState()


def configure(config: dict[str, Any]) -> None:
    """
    Apply configuration to the plugin.
    
    Args:
        config: Plugin configuration dictionary
    """
    if _logger:
        _logger.debug("Autodiag configured: enabled=%s, auto_run=%s, port=%s",
                      config.get("enabled", True),
                      config.get("auto_run_on_scan", False),
                      config.get("diag_port", 8081))


def on_scan(scan_result: dict[str, Any], config: dict[str, Any]) -> None:
    """
    Hook called after a scan completes.
    
    Args:
        scan_result: The scan result dictionary
        config: Plugin configuration
    """
    if not config.get("auto_run_on_scan", False):
        return
    
    if _logger:
        _logger.info("Auto-run triggered after scan (auto_run_on_scan enabled)")
    
    # Note: Actual auto-run logic would trigger the autodiag server here
    # For now, just log the event


def on_analyze(analysis_result: dict[str, Any], config: dict[str, Any]) -> None:
    """
    Hook called after analysis completes.
    
    Args:
        analysis_result: The analysis result dictionary
        config: Plugin configuration
    """
    if _logger:
        _logger.debug("Autodiag received analysis result with %d items",
                      len(analysis_result) if isinstance(analysis_result, dict) else 0)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_state() -> dict[str, Any]:
    """
    Get the current plugin state.
    
    Returns:
        Dictionary with current state values
    """
    return {
        "last_run_timestamp": _state.last_run_timestamp,
        "last_status": _state.last_status,
        "false_positive_count": _state.false_positive_count,
        "truly_unused_count": _state.truly_unused_count,
        "scenario_count": _state.scenario_count,
        "executed_functions_count": len(_state.executed_functions),
    }


def get_last_report() -> dict[str, Any]:
    """
    Get the last autodiag report.
    
    Returns:
        The last report dictionary or empty dict
    """
    return _state.last_report.copy()


def update_from_report(report: dict[str, Any]) -> None:
    """
    Update plugin state from an autodiag report.
    
    Args:
        report: Report dictionary from autodiag server
    """
    import time
    
    _state.last_run_timestamp = time.time()
    _state.last_report = report.copy()
    
    if "false_positives" in report:
        _state.false_positive_count = len(report["false_positives"])
    if "truly_unused" in report:
        _state.truly_unused_count = len(report["truly_unused"])
    if "scenarios" in report:
        _state.scenario_count = len(report["scenarios"])
    if "executed_functions" in report:
        _state.executed_functions = report["executed_functions"]
    
    _state.last_status = "success" if report.get("status") != "error" else "error"
    
    if _logger:
        _logger.info("Updated from report: %d false positives, %d truly unused",
                     _state.false_positive_count, _state.truly_unused_count)
