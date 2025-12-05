"""Plugin routes using the Bridge v2 system.

Version: 0.4.0 - Added hot reload endpoint

Exposes REST API endpoints for:
- Listing plugins (/plugins)
- Plugin details (/plugins/{id})
- Plugin health check (/plugins/{id}/health)
- Plugin metrics (/plugins/{id}/metrics)
- Plugin logs (/plugins/{id}/logs)
- Plugin logs WebSocket (/plugins/{id}/logs/stream)
- Plugin configuration (/plugins/{id}/config)
- Plugin hot reload (/plugins/{id}/reload) [NEW]
- Bridge status (/plugins/v2/status)
- UI/CLI/API manifests

This router works alongside the legacy system.py routes during migration.
Eventually, the legacy routes will be deprecated in favor of these.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, Request, Query, Body, status, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from jupiter.server.routers.auth import verify_token, require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plugins/v2", tags=["plugins-v2"])


# =============================================================================
# Response Models
# =============================================================================

class PluginSummary(BaseModel):
    """Summary information about a plugin."""
    id: str
    name: str
    version: str
    type: str
    state: str
    description: Optional[str] = None


class BridgeStatus(BaseModel):
    """Overall Bridge status."""
    version: str
    initialized: bool
    plugins_loaded: int
    plugins_ready: int
    plugins_error: int
    cli_commands: int
    api_routes: int
    ui_panels: int


class PluginListResponse(BaseModel):
    """Response for plugin list."""
    plugins: List[PluginSummary]
    total: int
    by_type: Dict[str, int]
    by_state: Dict[str, int]


class HealthCheckResponse(BaseModel):
    """Health check response for a plugin."""
    plugin_id: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: Optional[str] = None
    checks: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str


class MetricsResponse(BaseModel):
    """Metrics response for a plugin."""
    plugin_id: str
    uptime_seconds: float = 0.0
    request_count: int = 0
    error_count: int = 0
    last_activity: Optional[str] = None
    custom_metrics: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str


class PluginConfigResponse(BaseModel):
    """Configuration response for a plugin."""
    plugin_id: str
    config: Dict[str, Any]
    defaults: Dict[str, Any]
    config_schema: Optional[Dict[str, Any]] = None


class LogEntry(BaseModel):
    """Single log entry."""
    timestamp: str
    level: str
    message: str


# =============================================================================
# WebSocket Log Streaming Manager
# =============================================================================

class PluginLogConnectionManager:
    """Manager for plugin log WebSocket connections.
    
    Handles multiple concurrent connections per plugin, allowing
    real-time log streaming to multiple clients.
    """
    
    def __init__(self):
        """Initialize the connection manager."""
        # Map: plugin_id -> set of websockets
        self._connections: Dict[str, Set[WebSocket]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def connect(self, plugin_id: str, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection for a plugin.
        
        Args:
            plugin_id: The plugin to subscribe to
            websocket: The WebSocket connection
        """
        await websocket.accept()
        async with self._lock:
            if plugin_id not in self._connections:
                self._connections[plugin_id] = set()
            self._connections[plugin_id].add(websocket)
        logger.debug("WebSocket connected for plugin %s logs", plugin_id)
    
    async def disconnect(self, plugin_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection.
        
        Args:
            plugin_id: The plugin to unsubscribe from
            websocket: The WebSocket connection to remove
        """
        async with self._lock:
            if plugin_id in self._connections:
                self._connections[plugin_id].discard(websocket)
                if not self._connections[plugin_id]:
                    del self._connections[plugin_id]
        logger.debug("WebSocket disconnected for plugin %s logs", plugin_id)
    
    async def broadcast(self, plugin_id: str, message: Dict[str, Any]) -> None:
        """Broadcast a log message to all subscribers of a plugin.
        
        Args:
            plugin_id: The plugin whose subscribers should receive the message
            message: The log entry to broadcast
        """
        async with self._lock:
            connections = self._connections.get(plugin_id, set()).copy()
        
        if not connections:
            return
        
        payload = json.dumps(message)
        disconnected = []
        
        for websocket in connections:
            try:
                await websocket.send_text(payload)
            except Exception:
                disconnected.append(websocket)
        
        # Clean up disconnected sockets
        if disconnected:
            async with self._lock:
                if plugin_id in self._connections:
                    for ws in disconnected:
                        self._connections[plugin_id].discard(ws)
    
    def get_connection_count(self, plugin_id: str) -> int:
        """Get the number of active connections for a plugin.
        
        Args:
            plugin_id: The plugin to check
            
        Returns:
            Number of active WebSocket connections
        """
        return len(self._connections.get(plugin_id, set()))
    
    def get_all_stats(self) -> Dict[str, int]:
        """Get connection stats for all plugins.
        
        Returns:
            Dict mapping plugin_id to connection count
        """
        return {pid: len(conns) for pid, conns in self._connections.items()}


# Global connection manager for plugin logs
_log_manager = PluginLogConnectionManager()


def get_log_manager() -> PluginLogConnectionManager:
    """Get the global plugin log connection manager."""
    return _log_manager


# =============================================================================
# Helper Functions
# =============================================================================

def get_bridge(request: Optional[Request] = None):
    """Get the Bridge instance from app state.
    
    Args:
        request: Optional request object (not currently used, Bridge is singleton)
        
    Returns:
        Bridge instance or None if not available
    """
    try:
        from jupiter.core.bridge import Bridge
        return Bridge()
    except ImportError:
        logger.error("Bridge module not available")
        return None


def get_cli_registry():
    """Get the CLI registry."""
    try:
        from jupiter.core.bridge import get_cli_registry
        return get_cli_registry()
    except ImportError:
        return None


def get_api_registry():
    """Get the API registry."""
    try:
        from jupiter.core.bridge import get_api_registry
        return get_api_registry()
    except ImportError:
        return None


def get_ui_registry():
    """Get the UI registry."""
    try:
        from jupiter.core.bridge import get_ui_registry
        return get_ui_registry()
    except ImportError:
        return None


# =============================================================================
# Routes
# =============================================================================

@router.get("/status", response_model=BridgeStatus, dependencies=[Depends(verify_token)])
async def get_bridge_status(request: Request) -> BridgeStatus:
    """Get the Bridge v2 system status.
    
    Returns information about the plugin system including:
    - Number of loaded/ready/errored plugins
    - Number of registered CLI commands, API routes, UI panels
    """
    bridge = get_bridge(request)
    cli_registry = get_cli_registry()
    api_registry = get_api_registry()
    ui_registry = get_ui_registry()
    
    if not bridge:
        return BridgeStatus(
            version="0.0.0",
            initialized=False,
            plugins_loaded=0,
            plugins_ready=0,
            plugins_error=0,
            cli_commands=0,
            api_routes=0,
            ui_panels=0,
        )
    
    # Count plugins by state (get_all_plugins returns a list)
    all_plugins = bridge.get_all_plugins()
    plugins_ready = sum(1 for p in all_plugins if p.state.value == "ready")
    plugins_error = sum(1 for p in all_plugins if p.state.value == "error")
    
    # Count contributions
    cli_count = len(cli_registry.get_all_commands()) if cli_registry else 0
    api_count = len(api_registry.get_all_routes()) if api_registry else 0
    ui_count = len(ui_registry.get_sidebar_panels()) if ui_registry else 0
    
    from jupiter.core.bridge import __version__ as bridge_version
    
    return BridgeStatus(
        version=bridge_version,
        initialized=True,
        plugins_loaded=len(all_plugins),
        plugins_ready=plugins_ready,
        plugins_error=plugins_error,
        cli_commands=cli_count,
        api_routes=api_count,
        ui_panels=ui_count,
    )


@router.get("", response_model=PluginListResponse, dependencies=[Depends(verify_token)])
async def list_plugins(
    request: Request,
    type: Optional[str] = Query(None, description="Filter by plugin type"),
    state: Optional[str] = Query(None, description="Filter by plugin state"),
) -> PluginListResponse:
    """List all registered plugins.
    
    Returns summary information for all plugins managed by the Bridge v2.
    Use query parameters to filter the results.
    """
    bridge = get_bridge(request)
    
    if not bridge:
        return PluginListResponse(
            plugins=[],
            total=0,
            by_type={},
            by_state={},
        )
    
    all_plugins = bridge.get_all_plugins()
    
    # Convert to summaries and apply filters (get_all_plugins returns a list)
    summaries = []
    by_type: Dict[str, int] = {}
    by_state: Dict[str, int] = {}
    
    for info in all_plugins:
        plugin_id = info.manifest.id
        # Count by type and state
        plugin_type = info.manifest.plugin_type.value
        plugin_state = info.state.value
        
        by_type[plugin_type] = by_type.get(plugin_type, 0) + 1
        by_state[plugin_state] = by_state.get(plugin_state, 0) + 1
        
        # Apply filters
        if type and plugin_type != type:
            continue
        if state and plugin_state != state:
            continue
        
        summaries.append(PluginSummary(
            id=plugin_id,
            name=info.manifest.name,
            version=info.manifest.version,
            type=plugin_type,
            state=plugin_state,
            description=info.manifest.description,
        ))
    
    return PluginListResponse(
        plugins=summaries,
        total=len(summaries),
        by_type=by_type,
        by_state=by_state,
    )


@router.get("/{plugin_id}", dependencies=[Depends(verify_token)])
async def get_plugin_details(request: Request, plugin_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific plugin.
    
    Returns full plugin metadata including permissions, dependencies,
    and contribution counts.
    """
    bridge = get_bridge(request)
    
    if not bridge:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bridge v2 not available",
        )
    
    info = bridge.get_plugin(plugin_id)
    
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_id}' not found",
        )
    
    # Count contributions
    cli_registry = get_cli_registry()
    api_registry = get_api_registry()
    ui_registry = get_ui_registry()
    
    cli_count = len(cli_registry.get_plugin_commands(plugin_id)) if cli_registry else 0
    api_count = len(api_registry.get_plugin_routes(plugin_id)) if api_registry else 0
    ui_count = len(ui_registry.get_plugin_panels(plugin_id)) if ui_registry else 0
    
    # Use PluginInfo.to_dict() and add contribution counts
    result = info.to_dict()
    result["cli_commands"] = cli_count
    result["api_routes"] = api_count
    result["ui_panels"] = ui_count
    
    return result


# =============================================================================
# UI Manifest Routes (for Web UI)
# =============================================================================

@router.get("/ui/manifest", dependencies=[Depends(verify_token)])
async def get_ui_manifest(request: Request) -> Dict[str, Any]:
    """Get the UI manifest for all plugins.
    
    Returns the combined UI contributions (panels, menu items, settings)
    for rendering in the Web UI.
    """
    ui_registry = get_ui_registry()
    
    if not ui_registry:
        return {
            "plugins": {},
            "sidebar_panels": [],
            "settings_panels": [],
            "menu_items": [],
            "plugin_count": 0,
        }
    
    return ui_registry.get_ui_manifest()


@router.get("/cli/manifest", dependencies=[Depends(verify_token)])
async def get_cli_manifest(request: Request) -> Dict[str, Any]:
    """Get the CLI manifest for all plugins.
    
    Returns the registered CLI commands for documentation purposes.
    """
    cli_registry = get_cli_registry()
    
    if not cli_registry:
        return {
            "commands": [],
            "groups": [],
            "total": 0,
        }
    
    return cli_registry.to_dict()


@router.get("/api/manifest", dependencies=[Depends(verify_token)])
async def get_api_manifest(request: Request) -> Dict[str, Any]:
    """Get the API manifest for all plugins.
    
    Returns the registered API routes for documentation purposes.
    """
    api_registry = get_api_registry()
    
    if not api_registry:
        return {
            "routes": [],
            "plugins": [],
            "total": 0,
        }
    
    return api_registry.to_dict()


# =============================================================================
# Standard Plugin Endpoints (Phase 4.2)
# =============================================================================

@router.get("/{plugin_id}/health", response_model=HealthCheckResponse, dependencies=[Depends(verify_token)])
async def get_plugin_health(request: Request, plugin_id: str) -> HealthCheckResponse:
    """Get health status for a specific plugin.
    
    Returns:
        HealthCheckResponse with status, message, and individual checks
        
    The health check calls the plugin's health() method if it implements
    the IPluginHealth interface, otherwise returns basic status.
    """
    bridge = get_bridge(request)
    
    if not bridge:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bridge v2 not available",
        )
    
    info = bridge.get_plugin(plugin_id)
    
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_id}' not found",
        )
    
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    # Check if plugin implements IPluginHealth
    from jupiter.core.bridge.interfaces import IPluginHealth
    
    if info.instance and isinstance(info.instance, IPluginHealth):
        try:
            health_result = info.instance.health()
            return HealthCheckResponse(
                plugin_id=plugin_id,
                status=health_result.status.value,
                message=health_result.message,
                checks=health_result.details,  # Interface uses 'details'
                timestamp=timestamp,
            )
        except Exception as e:
            logger.warning("Health check failed for plugin %s: %s", plugin_id, e)
            return HealthCheckResponse(
                plugin_id=plugin_id,
                status="unhealthy",
                message=f"Health check failed: {str(e)}",
                checks={},
                timestamp=timestamp,
            )
    
    # Derive basic health from plugin state
    state_to_status = {
        "ready": "healthy",
        "loading": "degraded",
        "discovered": "degraded",
        "error": "unhealthy",
        "disabled": "unhealthy",
    }
    
    return HealthCheckResponse(
        plugin_id=plugin_id,
        status=state_to_status.get(info.state.value, "unknown"),
        message=info.error if info.error else f"Plugin is {info.state.value}",
        checks={"state": info.state.value},
        timestamp=timestamp,
    )


@router.get("/{plugin_id}/metrics", response_model=MetricsResponse, dependencies=[Depends(verify_token)])
async def get_plugin_metrics(request: Request, plugin_id: str) -> MetricsResponse:
    """Get metrics for a specific plugin.
    
    Returns:
        MetricsResponse with uptime, request count, error count, etc.
        
    If the plugin implements IPluginMetrics, its metrics() method is called.
    Otherwise, basic metrics are derived from the plugin state.
    """
    bridge = get_bridge(request)
    
    if not bridge:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bridge v2 not available",
        )
    
    info = bridge.get_plugin(plugin_id)
    
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_id}' not found",
        )
    
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    # Check if plugin implements IPluginMetrics
    from jupiter.core.bridge.interfaces import IPluginMetrics
    
    if info.instance and isinstance(info.instance, IPluginMetrics):
        try:
            metrics_data = info.instance.metrics()
            # Interface uses execution_count, error_count, last_execution (timestamp float)
            last_act = None
            if metrics_data.last_execution:
                from datetime import datetime as dt
                last_act = dt.fromtimestamp(metrics_data.last_execution).isoformat()
            return MetricsResponse(
                plugin_id=plugin_id,
                uptime_seconds=0.0,  # Not tracked in current interface
                request_count=metrics_data.execution_count,
                error_count=metrics_data.error_count,
                last_activity=last_act,
                custom_metrics=metrics_data.custom,
                timestamp=timestamp,
            )
        except Exception as e:
            logger.warning("Metrics collection failed for plugin %s: %s", plugin_id, e)
    
    # Return basic metrics
    return MetricsResponse(
        plugin_id=plugin_id,
        uptime_seconds=0.0,
        request_count=0,
        error_count=1 if info.state.value == "error" else 0,
        last_activity=None,
        custom_metrics={
            "state": info.state.value,
            "load_order": info.load_order,
            "legacy": info.legacy,
        },
        timestamp=timestamp,
    )


@router.get("/{plugin_id}/logs", dependencies=[Depends(verify_token)])
async def get_plugin_logs(
    request: Request,
    plugin_id: str,
    lines: int = Query(100, ge=1, le=10000, description="Number of log lines to return"),
    level: Optional[str] = Query(None, description="Filter by log level"),
) -> Dict[str, Any]:
    """Get recent logs for a specific plugin.
    
    Returns:
        Dictionary with log entries and metadata
        
    Logs are read from the plugin's dedicated log file if available,
    or from the main Jupiter logs filtered by plugin ID.
    """
    bridge = get_bridge(request)
    
    if not bridge:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bridge v2 not available",
        )
    
    info = bridge.get_plugin(plugin_id)
    
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_id}' not found",
        )
    
    # Try to read plugin-specific log file
    from pathlib import Path
    logs_dir = Path(__file__).parent.parent.parent.parent / "logs"
    plugin_log = logs_dir / f"plugin_{plugin_id}.log"
    
    log_entries: List[Dict[str, str]] = []
    
    if plugin_log.exists():
        try:
            with open(plugin_log, "r", encoding="utf-8", errors="ignore") as f:
                # Read last N lines
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:]
                
                for line in recent_lines:
                    # Simple parsing: try to extract timestamp, level, message
                    parts = line.strip().split(" - ", 3)
                    if len(parts) >= 3:
                        entry = {
                            "timestamp": parts[0] if len(parts) > 0 else "",
                            "level": parts[1].strip() if len(parts) > 1 else "INFO",
                            "message": parts[2] if len(parts) > 2 else line.strip(),
                        }
                    else:
                        entry = {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "level": "INFO",
                            "message": line.strip(),
                        }
                    
                    # Apply level filter
                    if level and entry["level"].upper() != level.upper():
                        continue
                    
                    log_entries.append(entry)
        except Exception as e:
            logger.warning("Failed to read logs for plugin %s: %s", plugin_id, e)
    else:
        # Try to read from main Jupiter log filtered by plugin ID
        main_log = logs_dir / "jupiter.log"
        plugin_marker = f"[plugin:{plugin_id}]"
        
        if main_log.exists():
            try:
                with open(main_log, "r", encoding="utf-8", errors="ignore") as f:
                    all_lines = f.readlines()
                    
                    # Filter lines containing the plugin marker
                    plugin_lines = [l for l in all_lines if plugin_marker in l]
                    recent_lines = plugin_lines[-lines:]
                    
                    for line in recent_lines:
                        parts = line.strip().split(" - ", 3)
                        entry = {
                            "timestamp": parts[0] if len(parts) > 0 else "",
                            "level": parts[1].strip() if len(parts) > 1 else "INFO",
                            "message": parts[-1] if parts else line.strip(),
                        }
                        
                        if level and entry["level"].upper() != level.upper():
                            continue
                        
                        log_entries.append(entry)
            except Exception as e:
                logger.warning("Failed to read main logs for plugin %s: %s", plugin_id, e)
    
    return {
        "plugin_id": plugin_id,
        "entries": log_entries,
        "total": len(log_entries),
        "source": str(plugin_log) if plugin_log.exists() else str(logs_dir / "jupiter.log"),
    }


@router.websocket("/{plugin_id}/logs/stream")
async def stream_plugin_logs(
    websocket: WebSocket,
    plugin_id: str,
    level: Optional[str] = Query(None, description="Filter by log level"),
    tail: int = Query(50, ge=0, le=500, description="Number of historical lines to send initially"),
) -> None:
    """WebSocket endpoint for real-time plugin log streaming.
    
    Connects to a WebSocket that streams log entries for the specified plugin.
    On connection:
    1. Validates that the plugin exists
    2. Sends the last `tail` log entries as history
    3. Streams new log entries in real-time
    
    Message format (JSON):
    {
        "type": "log" | "history" | "info" | "error",
        "plugin_id": "...",
        "entry": {"timestamp": "...", "level": "...", "message": "..."} | null,
        "entries": [...] | null  // For history only
    }
    
    Query Parameters:
        level: Filter logs by level (DEBUG, INFO, WARNING, ERROR)
        tail: Number of historical log lines to send on connect (default: 50)
    """
    bridge = get_bridge()  # No request needed for WebSocket
    
    if not bridge:
        await websocket.close(code=1011, reason="Bridge v2 not available")
        return
    
    info = bridge.get_plugin(plugin_id)
    
    if not info:
        await websocket.close(code=1008, reason=f"Plugin '{plugin_id}' not found")
        return
    
    log_manager = get_log_manager()
    
    try:
        # Accept connection and register
        await log_manager.connect(plugin_id, websocket)
        
        # Send connection info
        await websocket.send_json({
            "type": "info",
            "plugin_id": plugin_id,
            "message": f"Connected to log stream for plugin '{plugin_id}'",
            "filter": {"level": level} if level else None,
        })
        
        # Send historical logs if requested
        if tail > 0:
            history = await _get_log_history(plugin_id, tail, level)
            await websocket.send_json({
                "type": "history",
                "plugin_id": plugin_id,
                "entries": history,
                "total": len(history),
            })
        
        # Keep connection alive and wait for disconnect
        # New logs will be pushed via the log_manager.broadcast() method
        # which can be called from a log handler or other code
        while True:
            try:
                # Wait for messages from client (keepalive, filter updates)
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0,  # Ping interval
                )
                
                # Handle client commands
                try:
                    cmd = json.loads(message)
                    if cmd.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif cmd.get("type") == "set_filter":
                        # Update filter (would need to store per-connection state)
                        await websocket.send_json({
                            "type": "info",
                            "message": "Filter update acknowledged",
                        })
                except json.JSONDecodeError:
                    pass
                    
            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected for plugin %s logs", plugin_id)
    except Exception as e:
        logger.warning("WebSocket error for plugin %s: %s", plugin_id, e)
    finally:
        await log_manager.disconnect(plugin_id, websocket)


async def _get_log_history(
    plugin_id: str,
    lines: int = 50,
    level: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Get historical log entries for a plugin.
    
    Args:
        plugin_id: Plugin identifier
        lines: Number of lines to retrieve
        level: Optional level filter
        
    Returns:
        List of log entry dictionaries
    """
    logs_dir = Path(__file__).parent.parent.parent.parent / "logs"
    plugin_log = logs_dir / f"plugin_{plugin_id}.log"
    
    log_entries: List[Dict[str, str]] = []
    
    def parse_log_line(line: str) -> Dict[str, str]:
        """Parse a log line into structured format."""
        parts = line.strip().split(" - ", 3)
        if len(parts) >= 3:
            return {
                "timestamp": parts[0] if parts else "",
                "level": parts[1].strip() if len(parts) > 1 else "INFO",
                "message": parts[2] if len(parts) > 2 else line.strip(),
            }
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "INFO",
            "message": line.strip(),
        }
    
    try:
        if plugin_log.exists():
            with open(plugin_log, "r", encoding="utf-8", errors="ignore") as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if lines else all_lines
                
                for line in recent_lines:
                    if not line.strip():
                        continue
                    entry = parse_log_line(line)
                    if level and entry["level"].upper() != level.upper():
                        continue
                    log_entries.append(entry)
        else:
            # Try main log filtered by plugin marker
            main_log = logs_dir / "jupiter.log"
            plugin_marker = f"[plugin:{plugin_id}]"
            
            if main_log.exists():
                with open(main_log, "r", encoding="utf-8", errors="ignore") as f:
                    all_lines = f.readlines()
                    plugin_lines = [l for l in all_lines if plugin_marker in l]
                    recent_lines = plugin_lines[-lines:] if lines else plugin_lines
                    
                    for line in recent_lines:
                        if not line.strip():
                            continue
                        entry = parse_log_line(line)
                        if level and entry["level"].upper() != level.upper():
                            continue
                        log_entries.append(entry)
    except Exception as e:
        logger.warning("Failed to read log history for plugin %s: %s", plugin_id, e)
    
    return log_entries


async def broadcast_plugin_log(plugin_id: str, entry: Dict[str, str]) -> None:
    """Broadcast a log entry to all WebSocket subscribers.
    
    This function should be called by log handlers when a new log entry
    is written for a plugin. It broadcasts the entry to all connected
    WebSocket clients.
    
    Args:
        plugin_id: The plugin that generated the log
        entry: Log entry with timestamp, level, message
    """
    log_manager = get_log_manager()
    await log_manager.broadcast(plugin_id, {
        "type": "log",
        "plugin_id": plugin_id,
        "entry": entry,
    })


@router.get("/{plugin_id}/config", response_model=PluginConfigResponse, dependencies=[Depends(verify_token)])
async def get_plugin_config(request: Request, plugin_id: str) -> PluginConfigResponse:
    """Get configuration for a specific plugin.
    
    Returns:
        PluginConfigResponse with current config, defaults, and schema
    """
    bridge = get_bridge(request)
    
    if not bridge:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bridge v2 not available",
        )
    
    info = bridge.get_plugin(plugin_id)
    
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_id}' not found",
        )
    
    # Get config using service locator
    try:
        from jupiter.core.bridge.services import create_service_locator
        from jupiter.core.bridge.manifest import PluginManifest
        
        # Get defaults and schema from manifest properties
        manifest = info.manifest
        defaults = {}
        schema = None
        
        if isinstance(manifest, PluginManifest):
            defaults = manifest.config_defaults or {}
            schema = manifest.config_schema
        
        services = create_service_locator(
            plugin_id=plugin_id,
            bridge=bridge,
            permissions=list(manifest.permissions),
            config_defaults=defaults,
        )
        
        config_proxy = services.get_config()
        current_config = config_proxy.get_all()
        
    except Exception as e:
        logger.warning("Failed to get config for plugin %s: %s", plugin_id, e)
        current_config = {}
        defaults = {}
        schema = None
    
    return PluginConfigResponse(
        plugin_id=plugin_id,
        config=current_config,
        defaults=defaults,
        config_schema=schema,
    )


@router.put("/{plugin_id}/config", dependencies=[Depends(require_admin)])
async def update_plugin_config(
    request: Request,
    plugin_id: str,
    config_update: Dict[str, Any] = Body(..., description="Configuration values to update"),
) -> Dict[str, Any]:
    """Update configuration for a specific plugin.
    
    Requires admin authentication.
    
    Args:
        plugin_id: Plugin identifier
        config_update: Configuration values to merge with existing config
        
    Returns:
        Updated configuration
    """
    bridge = get_bridge(request)
    
    if not bridge:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bridge v2 not available",
        )
    
    info = bridge.get_plugin(plugin_id)
    
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_id}' not found",
        )
    
    # Write config to project overrides using plugins.settings
    try:
        from jupiter.core.state import load_last_root
        from jupiter.config.config import load_config, save_config, PluginsConfig
        from pathlib import Path
        
        project_root = load_last_root()
        if not project_root:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active project",
            )
        
        config = load_config(project_root)
        
        # Ensure plugins config exists
        if config.plugins is None:
            config.plugins = PluginsConfig()
        
        # Initialize settings dict if needed
        if config.plugins.settings is None:
            config.plugins.settings = {}
        
        # Ensure plugin entry exists in settings
        if plugin_id not in config.plugins.settings:
            config.plugins.settings[plugin_id] = {}
        
        # Update plugin settings
        config.plugins.settings[plugin_id].update(config_update)
        
        # Save configuration
        save_config(config, project_root)
        
        logger.info("Updated config for plugin %s", plugin_id)
        
        return {
            "plugin_id": plugin_id,
            "updated": True,
            "config": config.plugins.settings[plugin_id],
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update config for plugin %s: %s", plugin_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save configuration: {str(e)}",
        )


@router.post("/{plugin_id}/reset-settings", dependencies=[Depends(require_admin)])
async def reset_plugin_settings(request: Request, plugin_id: str) -> Dict[str, Any]:
    """Reset plugin settings to defaults.
    
    Requires admin authentication.
    
    Args:
        plugin_id: Plugin identifier
        
    Returns:
        Confirmation with default config values
    """
    bridge = get_bridge(request)
    
    if not bridge:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bridge v2 not available",
        )
    
    info = bridge.get_plugin(plugin_id)
    
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_id}' not found",
        )
    
    # Remove plugin settings from project config
    try:
        from jupiter.core.state import load_last_root
        from jupiter.config.config import load_config, save_config
        from jupiter.core.bridge.manifest import PluginManifest
        
        project_root = load_last_root()
        if not project_root:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active project",
            )
        
        config = load_config(project_root)
        
        # Remove plugin settings if they exist
        if (config.plugins is not None and 
            config.plugins.settings is not None and 
            plugin_id in config.plugins.settings):
            del config.plugins.settings[plugin_id]
        
        # Save configuration
        save_config(config, project_root)
        
        logger.info("Reset settings for plugin %s to defaults", plugin_id)
        
        # Get defaults from manifest
        defaults = {}
        if isinstance(info.manifest, PluginManifest):
            defaults = info.manifest.config_defaults or {}
        
        return {
            "plugin_id": plugin_id,
            "reset": True,
            "defaults": defaults,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to reset settings for plugin %s: %s", plugin_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset settings: {str(e)}",
        )


# =============================================================================
# Hot Reload Endpoint (Developer Mode Only)
# =============================================================================

class HotReloadResponse(BaseModel):
    """Response model for hot reload operation."""
    success: bool
    plugin_id: str
    duration_ms: float = 0.0
    phase: str = "completed"
    error: Optional[str] = None
    warnings: List[str] = []
    old_version: Optional[str] = None
    new_version: Optional[str] = None
    contributions_reloaded: bool = False


@router.post("/{plugin_id}/reload", response_model=HotReloadResponse, dependencies=[Depends(require_admin)])
async def hot_reload_plugin(request: Request, plugin_id: str) -> HotReloadResponse:
    """Hot reload a plugin without restarting the server.
    
    Requires developer_mode to be enabled in the configuration.
    
    This endpoint:
    1. Verifies developer_mode is enabled
    2. Gracefully unloads the plugin
    3. Reloads the plugin module from disk
    4. Re-initializes the plugin with fresh state
    
    Args:
        plugin_id: Plugin identifier
        
    Returns:
        HotReloadResponse with reload result details
        
    Raises:
        HTTPException 403: If developer_mode is not enabled
        HTTPException 404: If plugin not found
        HTTPException 500: If reload fails
    """
    from jupiter.core.state import load_last_root
    from jupiter.config.config import load_config
    from jupiter.core.bridge.hot_reload import get_hot_reloader
    
    # Check developer mode is enabled
    try:
        project_root = load_last_root()
        if project_root:
            config = load_config(project_root)
            if not config.developer_mode:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Hot reload requires developer_mode to be enabled in configuration",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active project",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Could not check developer_mode: %s", e)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hot reload requires developer_mode to be enabled",
        )
    
    # Get bridge and verify plugin exists
    bridge = get_bridge(request)
    
    if not bridge:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bridge v2 not available",
        )
    
    info = bridge.get_plugin(plugin_id)
    
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_id}' not found",
        )
    
    # Perform hot reload
    try:
        reloader = get_hot_reloader()
        result = reloader.reload(plugin_id)
        
        logger.info(
            "Hot reload for plugin %s: success=%s, duration=%.1fms",
            plugin_id, result.success, result.duration_ms
        )
        
        return HotReloadResponse(
            success=result.success,
            plugin_id=result.plugin_id,
            duration_ms=result.duration_ms,
            phase=result.phase,
            error=result.error,
            warnings=result.warnings,
            old_version=result.old_version,
            new_version=result.new_version,
            contributions_reloaded=result.contributions_reloaded,
        )
        
    except Exception as e:
        logger.error("Failed to hot reload plugin %s: %s", plugin_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hot reload failed: {str(e)}",
        )
