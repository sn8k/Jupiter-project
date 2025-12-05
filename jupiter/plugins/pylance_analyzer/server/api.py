"""
Pylance Analyzer - API Routes

FastAPI router for the Pylance Analyzer plugin.

@version 1.0.0
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class DiagnosticModel(BaseModel):
    """A single diagnostic."""
    file: str
    line: int
    column: int
    end_line: int
    end_column: int
    severity: str
    message: str
    rule: Optional[str] = None


class FileReportModel(BaseModel):
    """Diagnostics for a file."""
    path: str
    error_count: int
    warning_count: int
    info_count: int
    diagnostics: List[DiagnosticModel]


class SummaryModel(BaseModel):
    """Analysis summary."""
    total_files: int
    files_with_errors: int
    total_errors: int
    total_warnings: int
    total_info: int
    pyright_version: Optional[str]
    file_reports: List[FileReportModel]


class StatusResponse(BaseModel):
    """Plugin status response."""
    status: str
    enabled: bool
    pyright_available: bool
    pyright_path: Optional[str]
    last_analysis: Optional[Dict[str, Any]]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    message: str
    details: Dict[str, Any]


class MetricsResponse(BaseModel):
    """Metrics response."""
    execution_count: int
    error_count: int
    files_analyzed: int
    total_errors_found: int
    total_warnings_found: int
    last_run: Optional[str]


# =============================================================================
# API ROUTES
# =============================================================================

@router.get("/status", response_model=StatusResponse)
async def get_status():
    """Get plugin status."""
    from jupiter.plugins.pylance_analyzer import (
        _get_state,
        _analyzer,
        get_summary,
    )
    
    state = _get_state()
    summary = get_summary()
    
    pyright_available = False
    pyright_path = None
    if _analyzer:
        pyright_available = _analyzer.check_pyright_available()
        pyright_path = _analyzer.pyright_path
    
    return StatusResponse(
        status="ok" if state.enabled else "disabled",
        enabled=state.enabled,
        pyright_available=pyright_available,
        pyright_path=pyright_path,
        last_analysis={
            "total_errors": summary.total_errors if summary else 0,
            "total_warnings": summary.total_warnings if summary else 0,
            "files_analyzed": summary.total_files if summary else 0,
        } if summary else None,
    )


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """Get plugin health status."""
    from jupiter.plugins.pylance_analyzer import health
    result = health()
    return HealthResponse(**result)


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get plugin metrics."""
    from jupiter.plugins.pylance_analyzer import metrics
    return MetricsResponse(**metrics())


@router.get("/summary")
async def get_analysis_summary():
    """Get the last analysis summary."""
    from jupiter.plugins.pylance_analyzer import get_summary
    
    summary = get_summary()
    if not summary:
        return {"status": "no_data", "message": "No analysis has been run yet"}
    
    return {
        "status": "ok",
        "summary": summary.to_dict(),
    }


@router.get("/diagnostics/{file_path:path}")
async def get_file_diagnostics(file_path: str):
    """Get diagnostics for a specific file."""
    from jupiter.plugins.pylance_analyzer import get_diagnostics_for_file
    
    diagnostics = get_diagnostics_for_file(file_path)
    return {
        "file": file_path,
        "count": len(diagnostics),
        "diagnostics": [d.to_dict() for d in diagnostics],
    }


@router.get("/files")
async def get_files_with_issues():
    """Get list of files with issues."""
    from jupiter.plugins.pylance_analyzer import get_summary
    
    summary = get_summary()
    if not summary:
        return {"status": "no_data", "files": []}
    
    files = []
    for fr in summary.file_reports:
        if fr.error_count > 0 or fr.warning_count > 0:
            files.append({
                "path": fr.path,
                "errors": fr.error_count,
                "warnings": fr.warning_count,
                "info": fr.info_count,
            })
    
    # Sort by errors desc, then warnings desc
    files.sort(key=lambda x: (-x["errors"], -x["warnings"]))
    
    return {
        "status": "ok",
        "total": len(files),
        "files": files,
    }


@router.post("/config")
async def update_config(config: Dict[str, Any]):
    """Update plugin configuration."""
    from jupiter.plugins.pylance_analyzer import configure
    
    configure(config)
    return {"status": "ok", "message": "Configuration updated"}


@router.post("/reset-settings")
async def reset_plugin_settings():
    """Reset plugin settings to defaults."""
    from jupiter.plugins.pylance_analyzer import reset_settings
    
    success = reset_settings()
    return {
        "status": "ok" if success else "error",
        "message": "Settings reset to defaults" if success else "Failed to reset",
    }


# =============================================================================
# REGISTRATION
# =============================================================================

def register_api_contribution(app, bridge) -> None:
    """
    Register API routes with the FastAPI app.
    
    Args:
        app: FastAPI application instance.
        bridge: Bridge instance for service access.
    """
    app.include_router(router, prefix="/pylance_analyzer", tags=["pylance"])
