"""
server/api.py – API routes for AI Helper plugin.
Version: 1.1.0

FastAPI router exposing standard plugin endpoints plus AI-specific functionality.
Conforme à plugins_architecture.md v0.4.0

@module jupiter.plugins.ai_helper.server.api
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse, StreamingResponse

# Bridge reference (injected via register_api_contribution)
_bridge = None

# Router with plugin prefix
router = APIRouter(prefix="/ai_helper", tags=["ai_helper"])


# =============================================================================
# STANDARD PLUGIN ENDPOINTS
# =============================================================================

@router.get("/")
async def root() -> Dict[str, Any]:
    """
    Plugin root endpoint - basic info.
    """
    from jupiter.plugins import ai_helper
    return {
        "plugin": "ai_helper",
        "version": ai_helper.__version__,
        "status": "active"
    }


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns plugin health status and details.
    """
    from jupiter.plugins import ai_helper
    return ai_helper.health()


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """
    Get plugin metrics.
    
    Returns metrics dictionary for monitoring and dashboards.
    """
    from jupiter.plugins import ai_helper
    return ai_helper.metrics()


@router.get("/logs")
async def download_logs() -> PlainTextResponse:
    """
    Download plugin log file.
    
    Returns the complete log file content as text.
    """
    if not _bridge:
        raise HTTPException(status_code=503, detail="Bridge not initialized")
    
    try:
        log_handler = _bridge.services.get_logger("ai_helper")
        log_path = Path(_bridge.services.get_log_dir()) / "ai_helper.log"
        
        if log_path.exists():
            content = log_path.read_text(encoding="utf-8")
        else:
            content = "# No logs available yet\n"
        
        return PlainTextResponse(
            content=content,
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=ai_helper.log"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {e}")


@router.get("/logs/stream")
async def stream_logs():
    """
    WebSocket endpoint for real-time log streaming.
    
    Note: This is a simplified SSE implementation.
    For full WebSocket, use the Bridge's ws.py infrastructure.
    """
    if not _bridge:
        raise HTTPException(status_code=503, detail="Bridge not initialized")
    
    async def generate():
        """Server-Sent Events generator for log streaming."""
        try:
            log_path = Path(_bridge.services.get_log_dir()) / "ai_helper.log"
            last_pos = 0
            
            while True:
                if log_path.exists():
                    content = log_path.read_text(encoding="utf-8")
                    if len(content) > last_pos:
                        new_content = content[last_pos:]
                        last_pos = len(content)
                        for line in new_content.strip().split("\n"):
                            if line:
                                yield f"data: {line}\n\n"
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/reset-settings")
async def reset_settings() -> Dict[str, Any]:
    """
    Reset plugin settings to defaults.
    
    Returns result with success status and message.
    """
    from jupiter.plugins import ai_helper
    return ai_helper.reset_settings()


@router.get("/changelog")
async def get_changelog() -> Dict[str, str]:
    """
    Get plugin changelog.
    
    Returns changelog content.
    """
    try:
        changelog_path = Path(__file__).parent.parent / "CHANGELOG.md"
        if changelog_path.exists():
            content = changelog_path.read_text(encoding="utf-8")
        else:
            content = "# Changelog\n\nNo changelog available."
        return {"changelog": content}
    except Exception as e:
        return {"changelog": f"# Error reading changelog\n\n{e}"}


# =============================================================================
# JOB MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/jobs")
async def list_jobs() -> List[Dict[str, Any]]:
    """
    List all jobs for this plugin.
    
    Returns list of job status objects.
    """
    if not _bridge:
        raise HTTPException(status_code=503, detail="Bridge not initialized")
    
    try:
        jobs = await _bridge.jobs.list(plugin_id="ai_helper")
        return jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {e}")


@router.post("/jobs")
async def create_job(params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Submit a new analysis job.
    
    Args:
        params: Job parameters including files to analyze.
    
    Returns:
        Job creation result with job_id.
    """
    if not _bridge:
        raise HTTPException(status_code=503, detail="Bridge not initialized")
    
    try:
        from jupiter.plugins import ai_helper
        job_id = await ai_helper.submit_analysis_job(params or {})
        return {"success": True, "job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job: {e}")


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Get status of a specific job.
    
    Args:
        job_id: Job identifier.
    
    Returns:
        Job status object.
    """
    if not _bridge:
        raise HTTPException(status_code=503, detail="Bridge not initialized")
    
    try:
        status = await _bridge.jobs.get(job_id)
        if status is None:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {e}")


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str) -> Dict[str, Any]:
    """
    Cancel a running job.
    
    Args:
        job_id: Job identifier.
    
    Returns:
        Cancellation result.
    """
    if not _bridge:
        raise HTTPException(status_code=503, detail="Bridge not initialized")
    
    try:
        result = await _bridge.jobs.cancel(job_id)
        return {"success": result, "job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {e}")


# =============================================================================
# AI HELPER SPECIFIC ENDPOINTS
# =============================================================================

@router.get("/suggestions")
async def get_suggestions() -> List[Dict[str, Any]]:
    """
    Get the last generated AI suggestions.
    
    Returns list of suggestion objects.
    """
    from jupiter.plugins import ai_helper
    return ai_helper.get_suggestions()


@router.post("/suggestions/file")
async def analyze_file(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze a specific file and generate suggestions.
    
    Args:
        request: Dict with 'path' key for file to analyze.
    
    Returns:
        Analysis result with suggestions.
    """
    from jupiter.plugins import ai_helper
    from jupiter.plugins.ai_helper.core.logic import analyze_single_file
    
    file_path = request.get("path")
    if not file_path:
        raise HTTPException(status_code=400, detail="Missing 'path' in request")
    
    try:
        config = ai_helper.get_config()
        result = analyze_single_file(file_path, config, _bridge)
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@router.get("/config")
async def get_config() -> Dict[str, Any]:
    """
    Get current plugin configuration.
    """
    from jupiter.plugins import ai_helper
    return ai_helper.get_config()


@router.put("/config")
async def update_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update plugin configuration.
    
    Args:
        config: New configuration values.
    
    Returns:
        Update result.
    """
    if not _bridge:
        raise HTTPException(status_code=503, detail="Bridge not initialized")
    
    try:
        _bridge.config.set("ai_helper", config)
        from jupiter.plugins import ai_helper
        ai_helper.configure(config)
        return {"success": True, "message": "Configuration updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update config: {e}")


# =============================================================================
# REGISTRATION
# =============================================================================

def register_api_contribution(app, bridge=None) -> None:
    """
    Register plugin API routes with the main FastAPI app.
    
    Called by Bridge during plugin registration phase.
    
    Args:
        app: FastAPI application instance.
        bridge: Bridge instance for service access.
    """
    global _bridge
    _bridge = bridge
    
    app.include_router(router)
