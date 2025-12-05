"""
server/api.py – API routes for Metrics Manager plugin.
Version: 1.0.0

FastAPI router exposing standard plugin endpoints plus metrics-specific functionality.
Conforme à plugins_architecture.md v0.6.0

@module jupiter.plugins.metrics_manager.server.api
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

# Bridge reference (injected via register_api_contribution)
_bridge = None

# Router without prefix (prefix is added by server when mounting)
router = APIRouter(tags=["metrics_manager"])


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class RecordMetricRequest(BaseModel):
    """Request model for recording a custom metric."""
    name: str
    value: float
    labels: Optional[Dict[str, str]] = None


class MetricHistoryRequest(BaseModel):
    """Request model for metric history."""
    name: str
    limit: int = 100


# =============================================================================
# STANDARD PLUGIN ENDPOINTS
# =============================================================================

@router.get("/")
async def root() -> Dict[str, Any]:
    """
    Plugin root endpoint - basic info.
    """
    from jupiter.plugins import metrics_manager
    return {
        "plugin": "metrics_manager",
        "version": metrics_manager.__version__,
        "status": "active"
    }


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns plugin health status and details.
    """
    from jupiter.plugins import metrics_manager
    return metrics_manager.health()


@router.get("/metrics")
async def get_plugin_metrics() -> Dict[str, Any]:
    """
    Get plugin's own metrics.
    
    Returns metrics dictionary for monitoring and dashboards.
    """
    from jupiter.plugins import metrics_manager
    return metrics_manager.metrics()


@router.get("/logs")
async def download_logs() -> PlainTextResponse:
    """
    Download plugin log file.
    
    Returns the complete log file content as text.
    """
    if not _bridge:
        # Fallback: try to find logs in standard location
        try:
            log_path = Path(__file__).parent.parent.parent.parent.parent / "logs" / "metrics_manager.log"
            if log_path.exists():
                content = log_path.read_text(encoding="utf-8")
            else:
                content = "# No logs available yet\n"
        except Exception as e:
            content = f"# Error reading logs: {e}\n"
    else:
        try:
            log_path = Path(_bridge.services.get_log_dir()) / "metrics_manager.log"
            if log_path.exists():
                content = log_path.read_text(encoding="utf-8")
            else:
                content = "# No logs available yet\n"
        except Exception as e:
            content = f"# Error reading logs: {e}\n"
    
    return PlainTextResponse(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=metrics_manager.log"}
    )


@router.get("/logs/stream")
async def stream_logs(request: Request) -> StreamingResponse:
    """
    Stream logs via Server-Sent Events.
    """
    async def event_generator():
        # Locate log file
        try:
            log_path = Path(__file__).parent.parent.parent.parent.parent / "logs" / "metrics_manager.log"
        except Exception:
            yield "data: # Could not determine log path\n\n"
            return

        # Initial read of last lines
        if log_path.exists():
            try:
                lines = log_path.read_text(encoding="utf-8").splitlines()
                for line in lines[-50:]:
                    if await request.is_disconnected():
                        break
                    yield f"data: {line}\n\n"
            except Exception:
                pass
        
        # Tail the file
        if not log_path.exists():
            yield "data: # Log file not found\n\n"
            # Wait for file to appear
            while not log_path.exists():
                if await request.is_disconnected():
                    return
                await asyncio.sleep(1)

        try:
            with open(log_path, "r", encoding="utf-8") as f:
                f.seek(0, 2)  # Go to end
                while True:
                    if await request.is_disconnected():
                        break
                    
                    line = f.readline()
                    if line:
                        yield f"data: {line.strip()}\n\n"
                    else:
                        await asyncio.sleep(0.5)
        except Exception as e:
            yield f"data: # Error reading logs: {e}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/reset-settings")
async def reset_settings() -> Dict[str, Any]:
    """
    Reset plugin settings to defaults.
    
    Returns result with success status and message.
    """
    from jupiter.plugins import metrics_manager
    return metrics_manager.reset_settings()


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
# METRICS-SPECIFIC ENDPOINTS
# =============================================================================

@router.get("/all")
async def get_all_metrics() -> Dict[str, Any]:
    """
    Get all collected metrics from the MetricsCollector.
    
    Returns:
        Complete metrics dictionary with system, plugin, and custom metrics.
    """
    from jupiter.plugins import metrics_manager
    metrics_manager._get_state().api_calls += 1
    return metrics_manager.collect_all_metrics()


@router.get("/system")
async def get_system_metrics() -> Dict[str, Any]:
    """
    Get only system-level metrics.
    
    Returns:
        System metrics (uptime, collectors, etc.)
    """
    from jupiter.plugins import metrics_manager
    metrics_manager._get_state().api_calls += 1
    
    all_metrics = metrics_manager.collect_all_metrics()
    return {
        "system": all_metrics.get("system", {}),
        "collected_at": all_metrics.get("collected_at"),
    }


@router.get("/plugins")
async def get_plugin_metrics_all() -> Dict[str, Any]:
    """
    Get metrics from all plugins.
    
    Returns:
        Dictionary mapping plugin_id to their metrics.
    """
    from jupiter.plugins import metrics_manager
    metrics_manager._get_state().api_calls += 1
    
    all_metrics = metrics_manager.collect_all_metrics()
    return {
        "plugins": all_metrics.get("plugins", {}),
        "collected_at": all_metrics.get("collected_at"),
    }


@router.get("/counters")
async def get_counters() -> Dict[str, Any]:
    """
    Get all counter metrics.
    
    Returns:
        Dictionary of counter names to values.
    """
    from jupiter.plugins import metrics_manager
    metrics_manager._get_state().api_calls += 1
    
    all_metrics = metrics_manager.collect_all_metrics()
    return {
        "counters": all_metrics.get("counters", {}),
        "collected_at": all_metrics.get("collected_at"),
    }


@router.get("/history/{metric_name:path}")
async def get_metric_history(
    metric_name: str,
    limit: int = Query(default=100, ge=1, le=1000)
) -> Dict[str, Any]:
    """
    Get historical data points for a specific metric.
    
    Args:
        metric_name: The name of the metric
        limit: Maximum number of data points to return
        
    Returns:
        List of metric data points with timestamps.
    """
    from jupiter.plugins import metrics_manager
    metrics_manager._get_state().api_calls += 1
    
    history = metrics_manager.get_metric_history(metric_name, limit)
    return {
        "metric_name": metric_name,
        "points": history,
        "count": len(history),
    }


@router.get("/export")
async def export_metrics(
    format: str = Query(default="json", regex="^(json|prometheus)$")
) -> Any:
    """
    Export all metrics in specified format.
    
    Args:
        format: Export format ('json' or 'prometheus')
        
    Returns:
        Formatted metrics string.
    """
    from jupiter.plugins import metrics_manager
    metrics_manager._get_state().api_calls += 1
    
    content = metrics_manager.export_metrics(format)
    
    if format == "prometheus":
        return PlainTextResponse(
            content=content,
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=metrics.txt"}
        )
    else:
        return PlainTextResponse(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=metrics.json"}
        )


@router.post("/record")
async def record_metric(request: RecordMetricRequest) -> Dict[str, Any]:
    """
    Record a custom metric.
    
    Args:
        request: Metric recording request with name, value, and optional labels.
        
    Returns:
        Result dictionary with success status.
    """
    from jupiter.plugins import metrics_manager
    metrics_manager._get_state().api_calls += 1
    
    return metrics_manager.record_custom_metric(
        request.name,
        request.value,
        request.labels
    )


@router.post("/reset")
async def reset_metrics() -> Dict[str, Any]:
    """
    Reset all metrics in the collector.
    
    Returns:
        Result dictionary with success status.
    """
    from jupiter.plugins import metrics_manager
    metrics_manager._get_state().api_calls += 1
    
    return metrics_manager.reset_metrics()


# =============================================================================
# ALERTS ENDPOINTS
# =============================================================================

@router.get("/alerts")
async def get_alerts() -> Dict[str, Any]:
    """
    Get all active metric alerts.
    
    Returns:
        List of active alerts.
    """
    from jupiter.plugins import metrics_manager
    metrics_manager._get_state().api_calls += 1
    
    alerts = metrics_manager.get_active_alerts()
    return {
        "alerts": alerts,
        "count": len(alerts),
    }


@router.delete("/alerts")
async def clear_alerts() -> Dict[str, Any]:
    """
    Clear all active alerts.
    
    Returns:
        Result dictionary with cleared count.
    """
    from jupiter.plugins import metrics_manager
    metrics_manager._get_state().api_calls += 1
    
    return metrics_manager.clear_alerts()


# =============================================================================
# WEBSOCKET-LIKE STREAMING (SSE)
# =============================================================================

@router.get("/stream")
async def stream_metrics():
    """
    Server-Sent Events endpoint for real-time metrics streaming.
    
    Streams metric updates every second.
    """
    import json
    
    async def generate():
        """SSE generator for metrics streaming."""
        try:
            from jupiter.plugins import metrics_manager
            
            while True:
                try:
                    all_metrics = metrics_manager.collect_all_metrics()
                    data = json.dumps({
                        "system": all_metrics.get("system", {}),
                        "counters": all_metrics.get("counters", {}),
                        "timestamp": all_metrics.get("collected_at"),
                    }, default=str)
                    yield f"data: {data}\n\n"
                except Exception as e:
                    yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
                
                await asyncio.sleep(5)  # Stream every 5 seconds
        except asyncio.CancelledError:
            pass
    
    return StreamingResponse(generate(), media_type="text/event-stream")


# =============================================================================
# REGISTRATION FUNCTION
# =============================================================================

def register_api_contribution(bridge) -> APIRouter:
    """
    Register API contribution with the Bridge.
    
    Called by Bridge during API registration phase.
    
    Args:
        bridge: Bridge instance for service access.
        
    Returns:
        The configured APIRouter.
    """
    global _bridge
    _bridge = bridge
    
    return router
