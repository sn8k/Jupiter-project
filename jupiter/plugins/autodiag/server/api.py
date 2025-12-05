"""
Autodiag Plugin - API Router
============================

FastAPI router providing endpoints for the autodiag plugin.
These endpoints are mounted at /api/plugins/autodiag/ by the Bridge v2 system.

Version: 1.4.0

Endpoints:
- GET /state - Get current plugin state
- POST /report - Update plugin state from autodiag report
- GET /config - Get plugin configuration
"""

import logging
import time
from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["autodiag-plugin"])

# In-memory state storage (shared with plugin module)
_plugin_state: Dict[str, Any] = {
    "last_run_timestamp": 0.0,
    "last_status": "idle",
    "false_positive_count": 0,
    "truly_unused_count": 0,
    "scenario_count": 0,
    "executed_functions_count": 0,
    "last_report": {},
}


@router.get("/state")
async def get_state() -> Dict[str, Any]:
    """
    Get the current autodiag plugin state.
    
    Returns:
        Dict with current state values including counts and last status.
    """
    return {
        "last_run_timestamp": _plugin_state["last_run_timestamp"],
        "last_status": _plugin_state["last_status"],
        "false_positive_count": _plugin_state["false_positive_count"],
        "truly_unused_count": _plugin_state["truly_unused_count"],
        "scenario_count": _plugin_state["scenario_count"],
        "executed_functions_count": _plugin_state["executed_functions_count"],
        "last_report": _plugin_state["last_report"],
    }


@router.post("/report", response_model=None)
async def update_report(request: Request):
    """
    Update plugin state from an autodiag report.
    
    Called by the UI after running autodiag to store the results
    in the plugin state for later retrieval.
    
    Args:
        request: FastAPI request with JSON body containing the report
        
    Returns:
        Dict with success status and updated counts
    """
    try:
        report = await request.json()
        
        # Update state from report
        _plugin_state["last_run_timestamp"] = time.time()
        _plugin_state["last_status"] = report.get("status", "success")
        _plugin_state["false_positive_count"] = len(report.get("false_positives", []))
        _plugin_state["truly_unused_count"] = len(report.get("truly_unused", []))
        _plugin_state["scenario_count"] = len(report.get("scenarios", []))
        _plugin_state["executed_functions_count"] = len(report.get("executed_functions", []))
        _plugin_state["last_report"] = report
        
        logger.info(
            "Autodiag report updated: fp=%d, unused=%d, scenarios=%d",
            _plugin_state["false_positive_count"],
            _plugin_state["truly_unused_count"],
            _plugin_state["scenario_count"],
        )
        
        return {
            "success": True,
            "message": "Report stored successfully",
            "false_positive_count": _plugin_state["false_positive_count"],
            "truly_unused_count": _plugin_state["truly_unused_count"],
            "scenario_count": _plugin_state["scenario_count"],
        }
        
    except Exception as e:
        logger.error("Failed to update autodiag report: %s", e)
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)}
        )


@router.get("/config")
async def get_config() -> Dict[str, Any]:
    """
    Get the current plugin configuration.
    
    Returns:
        Dict with plugin configuration options
    """
    return {
        "enabled": True,
        "auto_run_on_scan": False,
        "show_confidence_scores": True,
        "diag_port": 8081,
        "timeout": 30,
    }
