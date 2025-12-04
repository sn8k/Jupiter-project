"""
System router for Jupiter API.

Version: 1.9.0
"""
from typing import Dict, Any, List, Optional, cast
import inspect
import logging
import os
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, File, Body
from fastapi.responses import PlainTextResponse
from jupiter.server.routers.auth import verify_token, require_admin, log_action
from jupiter.core.metrics import MetricsCollector
from jupiter.core.plugin_manager import PluginManager
from jupiter.core.state import save_last_root
from jupiter.core.logging_utils import normalize_log_level
from jupiter.config import load_config, save_config
from jupiter.config.config import save_global_config
from jupiter.config.config import ProjectApiConfig, get_project_config_path
from jupiter.server.ws import manager
from jupiter.core.events import JupiterEvent, CONFIG_UPDATED, PLUGIN_TOGGLED, RUN_STARTED, RUN_FINISHED
from jupiter.server.meeting_adapter import MeetingAdapter
from jupiter.server.system_services import SystemState, preserve_meeting_config
from jupiter.server.models import (
    HealthStatus,
    RootUpdate,
    RootUpdateResponse,
    ConfigModel,
    PartialConfigModel,
    RawConfigModel,
    UpdateRequest,
    FSListResponse,
    FSListEntry,
    MeetingStatus,
    LicenseStatus,
    RunRequest,
    RunResponse,
)

# Bridge event system for plugin notifications
from jupiter.core.bridge import emit_config_changed

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/metrics", dependencies=[Depends(verify_token)])
async def get_metrics(request: Request) -> Dict[str, Any]:
    """Get system metrics."""
    state = SystemState(request.app)
    collector = MetricsCollector(
        history_manager=state.history_manager(),
        plugin_manager=request.app.state.plugin_manager,
    )
    return collector.collect()


@router.get("/metrics/bridge", dependencies=[Depends(verify_token)])
async def get_bridge_metrics(request: Request) -> Dict[str, Any]:
    """Get Bridge plugin system metrics.
    
    Returns comprehensive metrics from the Bridge including:
    - System metrics (uptime, counters)
    - Plugin metrics (from IPluginMetrics implementations)
    - Custom recorded metrics
    """
    try:
        from jupiter.core.bridge import (
            get_metrics_collector,
            is_initialized as bridge_initialized,
        )
        
        if not bridge_initialized():
            return {
                "error": "Bridge not initialized",
                "bridge_active": False,
            }
        
        collector = get_metrics_collector()
        
        # Collect fresh plugin metrics
        collector.collect_plugin_metrics()
        
        # Return all metrics
        metrics = collector.get_all_metrics()
        metrics["bridge_active"] = True
        
        return metrics
        
    except ImportError:
        return {
            "error": "Bridge module not available",
            "bridge_active": False,
        }
    except Exception as e:
        logger.error("Error collecting bridge metrics: %s", e)
        return {
            "error": str(e),
            "bridge_active": False,
        }


@router.get("/metrics/prometheus", dependencies=[Depends(verify_token)])
async def get_prometheus_metrics(request: Request) -> PlainTextResponse:
    """Get metrics in Prometheus text format.
    
    Returns metrics formatted for Prometheus scraping.
    """
    try:
        from jupiter.core.bridge import get_metrics_collector, is_initialized
        
        if not is_initialized():
            return PlainTextResponse(
                "# Jupiter Bridge not initialized\n",
                media_type="text/plain"
            )
        
        collector = get_metrics_collector()
        prometheus_output = collector.to_prometheus()
        
        return PlainTextResponse(prometheus_output, media_type="text/plain")
        
    except ImportError:
        return PlainTextResponse(
            "# Jupiter Bridge not available\n",
            media_type="text/plain"
        )
    except Exception as e:
        logger.error("Error generating Prometheus metrics: %s", e)
        return PlainTextResponse(
            f"# Error: {e}\n",
            media_type="text/plain"
        )


# =============================================================================
# JOB MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/jobs", dependencies=[Depends(verify_token)])
async def list_jobs_endpoint(
    request: Request,
    status: Optional[str] = None,
    plugin_id: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """List background jobs.
    
    Args:
        status: Filter by status (pending, running, completed, failed, cancelled)
        plugin_id: Filter by plugin ID
        limit: Maximum jobs to return
    """
    try:
        from jupiter.core.bridge import get_job_manager, JobStatus, is_initialized
        
        if not is_initialized():
            return {"jobs": [], "error": "Bridge not initialized"}
        
        manager = get_job_manager()
        
        # Parse status filter
        status_filter = None
        if status:
            try:
                status_filter = JobStatus(status)
            except ValueError:
                pass
        
        jobs = manager.list(status=status_filter, plugin_id=plugin_id, limit=limit)
        
        return {
            "jobs": [j.to_dict() for j in jobs],
            "stats": manager.get_stats(),
        }
        
    except ImportError:
        return {"jobs": [], "error": "Bridge not available"}
    except Exception as e:
        logger.error("Error listing jobs: %s", e)
        return {"jobs": [], "error": str(e)}


@router.get("/jobs/{job_id}", dependencies=[Depends(verify_token)])
async def get_job_endpoint(request: Request, job_id: str) -> Dict[str, Any]:
    """Get a specific job by ID."""
    try:
        from jupiter.core.bridge import get_job, is_initialized
        
        if not is_initialized():
            raise HTTPException(status_code=503, detail="Bridge not initialized")
        
        job = get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return job.to_dict()
        
    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(status_code=503, detail="Bridge not available")
    except Exception as e:
        logger.error("Error getting job %s: %s", job_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/cancel", dependencies=[Depends(require_admin)])
async def cancel_job_endpoint(request: Request, job_id: str) -> Dict[str, Any]:
    """Cancel a running job."""
    try:
        from jupiter.core.bridge import cancel_job, get_job, is_initialized
        
        if not is_initialized():
            raise HTTPException(status_code=503, detail="Bridge not initialized")
        
        result = await cancel_job(job_id)
        
        if not result:
            job = get_job(job_id)
            if job is None:
                raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
            raise HTTPException(
                status_code=400,
                detail=f"Job {job_id} cannot be cancelled (status: {job.status.value})"
            )
        
        return {"status": "cancelled", "job_id": job_id}
        
    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(status_code=503, detail="Bridge not available")
    except Exception as e:
        logger.error("Error cancelling job %s: %s", job_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs/history", dependencies=[Depends(require_admin)])
async def clear_job_history(request: Request) -> Dict[str, Any]:
    """Clear completed job history."""
    try:
        from jupiter.core.bridge import get_job_manager, is_initialized
        
        if not is_initialized():
            raise HTTPException(status_code=503, detail="Bridge not initialized")
        
        manager = get_job_manager()
        cleared = manager.clear_history()
        
        return {"status": "ok", "cleared": cleared}
        
    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(status_code=503, detail="Bridge not available")
    except Exception as e:
        logger.error("Error clearing job history: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthStatus)
async def get_health(request: Request) -> HealthStatus:
    """Return the health status of the server."""
    return HealthStatus(status="ok", root=str(request.app.state.root_path))

@router.post("/config/root", response_model=RootUpdateResponse, dependencies=[Depends(require_admin)])
async def update_root(request: Request, update: RootUpdate) -> RootUpdateResponse:
    """Update the project root path."""
    state = SystemState(request.app)
    clean_path = update.path.strip("\"'")
    new_path = Path(clean_path)
    if not new_path.exists() or not new_path.is_dir():
        raise HTTPException(status_code=400, detail="Path does not exist or is not a directory")

    new_config = load_config(new_path)
    current_config = getattr(getattr(request.app.state, "project_manager", None), "config", None)
    preserve_meeting_config(current_config, new_config)

    state.rebuild_runtime(new_config, new_root=new_path, reset_history=True)
    save_last_root(new_path)

    logger.info("Updated project root to %s", new_path)
    await manager.broadcast(f"Project root changed to {new_path}")
    return RootUpdateResponse(status="ok", root=str(new_path))

@router.get("/config", response_model=ConfigModel, dependencies=[Depends(verify_token)])
async def get_config(request: Request) -> ConfigModel:
    """Get current configuration."""
    state = SystemState(request.app)
    try:
        config = state.load_effective_config()
    except Exception:
        # If no config loaded (setup mode), return defaults
        return ConfigModel(
            server_host="127.0.0.1",
            server_port=8000,
            gui_host="127.0.0.1",
            gui_port=8050,
            meeting_device_key=None,
            meeting_heartbeat_interval=60,
            ui_theme="dark",
            ui_language="en",
            log_level="INFO",
            plugins_enabled=[],
            plugins_disabled=[],
            perf_parallel_scan=True,
            perf_max_workers=None,
            perf_scan_timeout=300,
            perf_graph_simplification=False,
            perf_max_graph_nodes=1000,
            sec_allow_run=False,
            api_connector=None,
            api_app_var=None,
            api_path=None,
        )
    
    return ConfigModel(
        server_host=config.server.host,
        server_port=config.server.port,
        gui_host=config.gui.host,
        gui_port=config.gui.port,
        meeting_device_key=config.meeting.deviceKey,
        meeting_auth_token=config.meeting.auth_token,
        meeting_heartbeat_interval=config.meeting.heartbeat_interval_seconds,
        ui_theme=config.ui.theme,
        ui_language=config.ui.language,
        log_level=normalize_log_level(config.logging.level),
        log_path=config.logging.path,
        log_reset_on_start=config.logging.reset_on_start,
        plugins_enabled=config.plugins.enabled,
        plugins_disabled=config.plugins.disabled,
        perf_parallel_scan=config.performance.parallel_scan,
        perf_max_workers=config.performance.max_workers,
        perf_scan_timeout=config.performance.scan_timeout,
        perf_graph_simplification=config.performance.graph_simplification,
        perf_max_graph_nodes=config.performance.max_graph_nodes,
        sec_allow_run=config.security.allow_run,
        api_connector=config.project_api.connector if config.project_api else None,
        api_app_var=config.project_api.app_var if config.project_api else None,
        api_path=config.project_api.path if config.project_api else None,
    )


@router.post("/config", response_model=ConfigModel)
async def update_config(request: Request, new_config: ConfigModel, role: str = Depends(require_admin)) -> ConfigModel:
    """Update configuration."""
    log_action(role, "update_config", new_config.dict())
    state = SystemState(request.app)
    current_config = state.load_effective_config()
    
    current_config.server.host = new_config.server_host
    current_config.server.port = new_config.server_port
    current_config.gui.host = new_config.gui_host
    current_config.gui.port = new_config.gui_port
    current_config.meeting.deviceKey = new_config.meeting_device_key
    current_config.meeting.auth_token = new_config.meeting_auth_token
    current_config.meeting.heartbeat_interval_seconds = new_config.meeting_heartbeat_interval
    current_config.ui.theme = new_config.ui_theme
    current_config.ui.language = new_config.ui_language
    current_config.logging.level = normalize_log_level(new_config.log_level)
    current_config.logging.path = new_config.log_path
    current_config.logging.reset_on_start = new_config.log_reset_on_start
    current_config.plugins.enabled = new_config.plugins_enabled
    current_config.plugins.disabled = new_config.plugins_disabled
    
    current_config.performance.parallel_scan = new_config.perf_parallel_scan
    current_config.performance.max_workers = new_config.perf_max_workers
    current_config.performance.scan_timeout = new_config.perf_scan_timeout
    current_config.performance.graph_simplification = new_config.perf_graph_simplification
    current_config.performance.max_graph_nodes = new_config.perf_max_graph_nodes
    
    current_config.security.allow_run = new_config.sec_allow_run

    if not current_config.project_api:
        current_config.project_api = ProjectApiConfig()
    
    current_config.project_api.connector = new_config.api_connector
    current_config.project_api.app_var = new_config.api_app_var
    current_config.project_api.path = new_config.api_path
    
    try:
        state.save_effective_config(current_config)
        state.rebuild_runtime(current_config)

        await manager.broadcast(JupiterEvent(type=CONFIG_UPDATED, payload=new_config.dict()))
        
        # Emit via Bridge event system for plugin notifications
        # For full config updates, we emit a bulk "config" change
        emit_config_changed(None, "config", None, new_config.dict())
        
        return new_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {e}")


@router.patch("/config", dependencies=[Depends(require_admin)])
async def patch_config(request: Request, partial_config: PartialConfigModel, role: str = Depends(require_admin)) -> Dict[str, Any]:
    """Partially update configuration. Only provided fields are updated."""
    log_action(role, "patch_config", partial_config.dict(exclude_none=True))
    state = SystemState(request.app)
    current_config = state.load_effective_config()
    
    # Apply only the fields that are not None
    updates = partial_config.dict(exclude_none=True)
    
    if "server_host" in updates:
        current_config.server.host = updates["server_host"]
    if "server_port" in updates:
        current_config.server.port = updates["server_port"]
    if "gui_host" in updates:
        current_config.gui.host = updates["gui_host"]
    if "gui_port" in updates:
        current_config.gui.port = updates["gui_port"]
    if "meeting_device_key" in updates:
        current_config.meeting.deviceKey = updates["meeting_device_key"]
    if "meeting_auth_token" in updates:
        current_config.meeting.auth_token = updates["meeting_auth_token"]
    if "meeting_heartbeat_interval" in updates:
        current_config.meeting.heartbeat_interval_seconds = updates["meeting_heartbeat_interval"]
    if "ui_theme" in updates:
        current_config.ui.theme = updates["ui_theme"]
    if "ui_language" in updates:
        current_config.ui.language = updates["ui_language"]
    if "log_level" in updates:
        current_config.logging.level = normalize_log_level(updates["log_level"])
    if "log_path" in updates:
        current_config.logging.path = updates["log_path"]
    if "log_reset_on_start" in updates:
        current_config.logging.reset_on_start = updates["log_reset_on_start"]
    if "plugins_enabled" in updates:
        current_config.plugins.enabled = updates["plugins_enabled"]
    if "plugins_disabled" in updates:
        current_config.plugins.disabled = updates["plugins_disabled"]
    if "perf_parallel_scan" in updates:
        current_config.performance.parallel_scan = updates["perf_parallel_scan"]
    if "perf_max_workers" in updates:
        current_config.performance.max_workers = updates["perf_max_workers"]
    if "perf_scan_timeout" in updates:
        current_config.performance.scan_timeout = updates["perf_scan_timeout"]
    if "perf_graph_simplification" in updates:
        current_config.performance.graph_simplification = updates["perf_graph_simplification"]
    if "perf_max_graph_nodes" in updates:
        current_config.performance.max_graph_nodes = updates["perf_max_graph_nodes"]
    if "sec_allow_run" in updates:
        current_config.security.allow_run = updates["sec_allow_run"]
    
    if not current_config.project_api:
        current_config.project_api = ProjectApiConfig()
    if "api_connector" in updates:
        current_config.project_api.connector = updates["api_connector"]
    if "api_app_var" in updates:
        current_config.project_api.app_var = updates["api_app_var"]
    if "api_path" in updates:
        current_config.project_api.path = updates["api_path"]
    
    try:
        state.save_effective_config(current_config)
        state.rebuild_runtime(current_config)
        
        await manager.broadcast(JupiterEvent(type=CONFIG_UPDATED, payload=updates))
        
        # Emit via Bridge event system for plugin notifications
        # For partial updates, emit each key change
        for key, value in updates.items():
            emit_config_changed(None, key, None, value)
        
        return {"status": "ok", "updated": list(updates.keys())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {e}")


@router.get("/config/raw", response_model=RawConfigModel, dependencies=[Depends(require_admin)])
async def get_raw_config(request: Request) -> RawConfigModel:
    """Get raw configuration file content."""
    root = request.app.state.root_path
    config_file = get_project_config_path(root)
    if not config_file.exists():
        return RawConfigModel(content="")
    try:
        return RawConfigModel(content=config_file.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read config file: {e}")

@router.post("/config/raw", response_model=RawConfigModel, dependencies=[Depends(require_admin)])
async def update_raw_config(request: Request, raw_config: RawConfigModel) -> RawConfigModel:
    """Update raw configuration file content."""
    root = request.app.state.root_path
    config_file = get_project_config_path(root)
    try:
        config_file.write_text(raw_config.content, encoding="utf-8")
        return raw_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write config file: {e}")

# ─────────────────────────────────────────────────────────────────────────
# Settings Update Plugin Routes
# ─────────────────────────────────────────────────────────────────────────

@router.get("/plugins/settings_update/version")
async def get_update_version(request: Request, role: str = Depends(verify_token)) -> Dict[str, str]:
    """Get current Jupiter version via settings_update plugin."""
    pm: PluginManager = request.app.state.plugin_manager
    plugin = pm.get_plugin("settings_update")
    if not plugin or not pm.is_enabled("settings_update"):
        raise HTTPException(status_code=404, detail="settings_update plugin not available")
    
    plugin_obj = cast(Any, plugin)
    version = plugin_obj.get_current_version()
    return {"version": version}


@router.post("/plugins/settings_update/apply")
async def apply_update_via_plugin(request: Request, update_req: UpdateRequest, role: str = Depends(require_admin)) -> Dict[str, str]:
    """Apply self-update via settings_update plugin."""
    log_action(role, "update_jupiter", update_req.source)
    
    pm: PluginManager = request.app.state.plugin_manager
    plugin = pm.get_plugin("settings_update")
    if not plugin or not pm.is_enabled("settings_update"):
        raise HTTPException(status_code=404, detail="settings_update plugin not available")
    
    plugin_obj = cast(Any, plugin)
    # Set meeting adapter for feature access validation
    plugin_obj.set_meeting_adapter(request.app.state.meeting_adapter)
    
    try:
        result = plugin_obj.apply_update(update_req.source, update_req.force)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {e}")


@router.post("/plugins/settings_update/upload")
async def upload_update_via_plugin(request: Request, file: UploadFile = File(...), role: str = Depends(require_admin)) -> Dict[str, Optional[str]]:
    """Upload an update ZIP file via settings_update plugin."""
    log_action(role, "upload_update", {"filename": file.filename})
    
    pm: PluginManager = request.app.state.plugin_manager
    plugin = pm.get_plugin("settings_update")
    if not plugin or not pm.is_enabled("settings_update"):
        raise HTTPException(status_code=404, detail="settings_update plugin not available")
    
    plugin_obj = cast(Any, plugin)
    try:
        content = await file.read()
        result = plugin_obj.upload_update_file(content, file.filename or "update.zip")
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {e}")


# Legacy endpoints - redirect to plugin routes for backward compatibility
@router.post("/update")
async def trigger_update_legacy(request: Request, update_req: UpdateRequest, role: str = Depends(require_admin)) -> Dict[str, str]:
    """Legacy endpoint - redirects to settings_update plugin."""
    return await apply_update_via_plugin(request, update_req, role)


@router.post("/update/upload")
async def upload_update_legacy(request: Request, file: UploadFile = File(...), role: str = Depends(require_admin)) -> Dict[str, Optional[str]]:
    """Legacy endpoint - redirects to settings_update plugin."""
    return await upload_update_via_plugin(request, file, role)

@router.get("/fs/list", response_model=FSListResponse)
async def list_fs(request: Request, path: Optional[str] = None, role: str = Depends(verify_token)) -> FSListResponse:
    """List directories in the given path (or root if None)."""
    if path:
        clean_path = path.strip("\"'")
        target_path = Path(clean_path)
    else:
        # If no path provided, default to current working directory or root path
        # In setup mode, root_path might be where the server is running from, which is fine.
        target_path = Path.cwd()

    if not target_path.exists() or not target_path.is_dir():
        # Fallback to CWD if invalid
        target_path = Path.cwd()

    entries = []
    try:
        if target_path.parent != target_path:
            entries.append(FSListEntry(name="..", path=str(target_path.parent), is_dir=True))

        for p in target_path.iterdir():
            if p.is_dir() and not p.name.startswith("."):
                entries.append(FSListEntry(name=p.name, path=str(p), is_dir=True))
    except PermissionError:
        pass

    return FSListResponse(
        current=str(target_path),
        entries=sorted(entries, key=lambda x: x.name),
    )


@router.get("/project/root-entries", dependencies=[Depends(verify_token)])
async def get_project_root_entries(request: Request) -> Dict[str, Any]:
    """List all files and directories at the project root for ignore configuration."""
    root_path = request.app.state.root_path
    
    if not root_path or not root_path.exists():
        return {"entries": [], "root": str(root_path) if root_path else None}
    
    entries = []
    try:
        for p in sorted(root_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            # Skip .jupiter folder itself
            if p.name == ".jupiter":
                continue
            entries.append({
                "name": p.name,
                "path": str(p),
                "is_dir": p.is_dir(),
                "is_hidden": p.name.startswith("."),
            })
    except PermissionError:
        pass
    
    # Get current ignore globs from active project
    pm = request.app.state.project_manager
    default_id = pm.global_config.default_project_id
    active_project = next((p for p in pm.global_config.projects if p.id == default_id), None) if default_id else None
    current_ignores = active_project.ignore_globs if active_project else []
    
    return {
        "entries": entries,
        "root": str(root_path),
        "current_ignores": current_ignores,
    }


@router.get("/plugins", response_model=List[Dict[str, Any]], dependencies=[Depends(verify_token)])
async def get_plugins(request: Request) -> List[Dict[str, Any]]:
    """Get list of all plugins."""
    pm: PluginManager = request.app.state.plugin_manager
    return pm.get_plugins_info()

@router.post("/plugins/reload", dependencies=[Depends(require_admin)])
async def reload_plugins(request: Request, role: str = Depends(require_admin)) -> Dict[str, Any]:
    """Reload all plugins from disk.
    
    Useful when plugin files have been modified.
    """
    log_action(role, "reload_plugins", {})
    pm: PluginManager = request.app.state.plugin_manager
    result = pm.reload_all_plugins()
    await manager.broadcast(JupiterEvent(type=PLUGIN_TOGGLED, payload={"action": "reload_all"}))
    return result

@router.post("/plugins/{name}/restart", dependencies=[Depends(require_admin)])
async def restart_plugin(
    request: Request, 
    name: str, 
    role: str = Depends(require_admin),
    internal: bool = False  # Set to True when called by watchdog
) -> Dict[str, Any]:
    """Restart a specific plugin.
    
    Reloads the plugin module and re-registers the plugin.
    Preserves enabled state and configuration.
    
    Note: Some plugins (like 'bridge') cannot be restarted by users,
    only by the watchdog or internal system calls.
    """
    pm: PluginManager = request.app.state.plugin_manager
    
    # Check if plugin is restartable by user
    plugin = pm.get_plugin(name)
    if plugin:
        restartable = getattr(plugin, "restartable", True)
        if not restartable and not internal:
            raise HTTPException(
                status_code=403, 
                detail=f"Plugin '{name}' cannot be restarted by user. It can only be restarted by the system or watchdog."
            )
    
    log_action(role, "restart_plugin", {"name": name})
    result = pm.restart_plugin(name)
    await manager.broadcast(JupiterEvent(type=PLUGIN_TOGGLED, payload={"action": "restart", "name": name}))
    return result

@router.get("/backends", response_model=List[Dict[str, Any]], dependencies=[Depends(verify_token)])
async def get_backends(request: Request) -> List[Dict[str, Any]]:
    """Get list of configured backends."""
    return request.app.state.project_manager.list_backends()

@router.post("/plugins/{name}/toggle")
async def toggle_plugin(request: Request, name: str, enable: bool, role: str = Depends(require_admin)) -> Dict[str, bool]:
    """Enable or disable a plugin."""
    log_action(role, "toggle_plugin", {"name": name, "enable": enable})
    pm: PluginManager = request.app.state.plugin_manager
    if enable:
        pm.enable_plugin(name)
    else:
        pm.disable_plugin(name)
    
    await manager.broadcast(JupiterEvent(type=PLUGIN_TOGGLED, payload={"name": name, "enabled": enable}))
    return {"success": True, "enabled": pm.is_enabled(name)}

@router.get("/plugins/{name}/config", dependencies=[Depends(verify_token)])
async def get_plugin_config(request: Request, name: str) -> Dict[str, Any]:
    """Return the persisted configuration for a plugin."""
    pm: PluginManager = request.app.state.plugin_manager
    plugin = pm.get_plugin(name)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")

    stored_config: Dict[str, Any] = {}
    if pm.config and name in pm.config.settings:
        stored_config = pm.config.settings[name]
    elif hasattr(plugin, "config"):
        stored_config = getattr(plugin, "config") or {}

    return stored_config or {}

@router.post("/plugins/{name}/config")
async def configure_plugin(request: Request, name: str, config: Dict[str, Any] = Body(...), role: str = Depends(require_admin)) -> Dict[str, bool]:
    """Configure a plugin."""
    log_action(role, "configure_plugin", {"name": name, "config": config})
    pm: PluginManager = request.app.state.plugin_manager
    pm.update_plugin_config(name, config)

    # Keep runtime config in sync
    try:
        project_manager = getattr(request.app.state, "project_manager", None)
        if project_manager and getattr(project_manager, "config", None):
            project_manager.config.plugins.settings[name] = config
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.warning("Failed to update in-memory plugin settings for %s: %s", name, exc)

    # Persist settings to disk (global install + project config)
    state = SystemState(request.app)
    try:
        current_config = state.load_effective_config()
        current_config.plugins.settings[name] = config
        state.save_effective_config(current_config)
    except Exception as exc:
        logger.error("Failed to persist plugin config for %s: %s", name, exc)

    return {"success": True}


@router.post("/plugins/{name}/test")
async def test_plugin(request: Request, name: str, role: str = Depends(require_admin)) -> Dict[str, Any]:
    """Trigger a plugin-provided self-test hook."""
    log_action(role, "test_plugin", {"name": name})
    pm: PluginManager = request.app.state.plugin_manager
    plugin = pm.get_plugin(name)
    if not plugin or not pm.is_enabled(name):
        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found or disabled")

    test_handler = getattr(plugin, "run_test", None)
    if test_handler is None:
        raise HTTPException(status_code=400, detail=f"Plugin '{name}' does not support test requests")

    if inspect.iscoroutinefunction(test_handler):
        result = await test_handler()
    else:
        result = test_handler()

    return {"status": "ok", "result": result or {}}


@router.post("/plugins/code_quality/manual-links", dependencies=[Depends(require_admin)])
async def create_manual_duplication_link(request: Request, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a manual duplication link from selected clusters."""
    pm: PluginManager = request.app.state.plugin_manager
    plugin = pm.get_plugin("code_quality")
    if not plugin or not pm.is_enabled("code_quality") or not hasattr(plugin, "create_manual_link"):
        raise HTTPException(status_code=404, detail="Code Quality plugin not available")

    hashes = payload.get("hashes") or payload.get("clusters")
    if not isinstance(hashes, list) or not hashes:
        raise HTTPException(status_code=400, detail="Provide at least two cluster hashes")
    label = payload.get("label")
    plugin_obj = cast(Any, plugin)
    try:
        cluster = plugin_obj.create_manual_link(label, hashes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok", "cluster": cluster}


@router.delete("/plugins/code_quality/manual-links/{link_id}", dependencies=[Depends(require_admin)])
async def delete_manual_duplication_link(request: Request, link_id: str) -> Dict[str, Any]:
    pm: PluginManager = request.app.state.plugin_manager
    plugin = pm.get_plugin("code_quality")
    if not plugin or not pm.is_enabled("code_quality") or not hasattr(plugin, "delete_manual_link"):
        raise HTTPException(status_code=404, detail="Code Quality plugin not available")
    plugin_obj = cast(Any, plugin)
    try:
        plugin_obj.delete_manual_link(link_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok"}


@router.post("/plugins/code_quality/manual-links/recheck", dependencies=[Depends(require_admin)])
async def recheck_manual_duplication_links(request: Request, payload: Optional[Dict[str, Any]] = Body(None)) -> Dict[str, Any]:
    pm: PluginManager = request.app.state.plugin_manager
    plugin = pm.get_plugin("code_quality")
    if not plugin or not pm.is_enabled("code_quality") or not hasattr(plugin, "recheck_manual_links"):
        raise HTTPException(status_code=404, detail="Code Quality plugin not available")
    link_id = None
    if payload:
        link_id = payload.get("link_id")
    plugin_obj = cast(Any, plugin)
    try:
        return plugin_obj.recheck_manual_links(link_id=link_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- Live Map Plugin Endpoints ---

@router.get("/plugins/livemap/graph", dependencies=[Depends(verify_token)])
async def get_livemap_graph(request: Request, simplify: bool = False, max_nodes: int = 1000) -> Dict[str, Any]:
    """Generate a dependency graph for the Live Map visualization.
    
    Args:
        simplify: If True, group by directory instead of showing individual files.
        max_nodes: Maximum number of nodes before auto-simplification.
        
    Returns:
        Graph data with nodes and links for D3.js visualization.
    """
    from jupiter.core.cache import CacheManager
    
    pm: PluginManager = request.app.state.plugin_manager
    plugin = pm.get_plugin("livemap")
    
    if not plugin or not pm.is_enabled("livemap"):
        raise HTTPException(status_code=404, detail="Live Map plugin not available")
    
    # Try cached scan first
    root = request.app.state.root_path
    cache_manager = CacheManager(root)
    last_scan = cache_manager.load_last_scan()
    
    if not last_scan or "files" not in last_scan:
        # Try scanning via connector
        connector = request.app.state.project_manager.get_default_connector()
        if not connector:
            raise HTTPException(status_code=500, detail="No project connector available")
        try:
            last_scan = await connector.scan({})
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get scan data: {str(e)}")
    
    plugin_obj = cast(Any, plugin)
    try:
        graph = plugin_obj.build_graph(last_scan["files"], simplify=simplify, max_nodes=max_nodes)
        return graph.to_dict()
    except Exception as e:
        logger.error("LiveMap graph generation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Graph generation failed: {str(e)}")


@router.get("/plugins/livemap/config", dependencies=[Depends(verify_token)])
async def get_livemap_config(request: Request) -> Dict[str, Any]:
    """Get Live Map plugin configuration."""
    pm: PluginManager = request.app.state.plugin_manager
    plugin = pm.get_plugin("livemap")
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Live Map plugin not found")
    
    plugin_obj = cast(Any, plugin)
    if hasattr(plugin_obj, "get_config"):
        return plugin_obj.get_config()
    
    return {
        "enabled": pm.is_enabled("livemap"),
        "simplify": getattr(plugin_obj, "simplify", False),
        "max_nodes": getattr(plugin_obj, "max_nodes", 1000),
        "show_functions": getattr(plugin_obj, "show_functions", False),
        "link_distance": getattr(plugin_obj, "link_distance", 60),
        "charge_strength": getattr(plugin_obj, "charge_strength", -100),
    }


@router.post("/plugins/livemap/config", dependencies=[Depends(verify_token)])
async def save_livemap_config(request: Request, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Save Live Map plugin configuration."""
    pm: PluginManager = request.app.state.plugin_manager
    plugin = pm.get_plugin("livemap")
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Live Map plugin not found")
    
    plugin_obj = cast(Any, plugin)
    
    # Apply configuration
    if hasattr(plugin_obj, "configure"):
        plugin_obj.configure(payload)
    
    # Toggle enabled state
    if "enabled" in payload:
        if payload["enabled"]:
            pm.enable_plugin("livemap")
        else:
            pm.disable_plugin("livemap")
    
    logger.info("LiveMap configuration updated: %s", payload)
    return {"status": "ok", "config": plugin_obj.get_config() if hasattr(plugin_obj, "get_config") else payload}


# --- Plugin Watchdog Endpoints ---

@router.get("/plugins/watchdog/config", dependencies=[Depends(verify_token)])
async def get_watchdog_config(request: Request) -> Dict[str, Any]:
    """Get Plugin Watchdog configuration."""
    pm: PluginManager = request.app.state.plugin_manager
    plugin = pm.get_plugin("watchdog")
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Watchdog plugin not found")
    
    plugin_obj = cast(Any, plugin)
    if hasattr(plugin_obj, "get_config"):
        return plugin_obj.get_config()
    
    return {
        "enabled": pm.is_enabled("watchdog"),
        "check_interval": getattr(plugin_obj, "check_interval", 2.0),
        "auto_reload": getattr(plugin_obj, "auto_reload", True),
    }


@router.post("/plugins/watchdog/config", dependencies=[Depends(verify_token)])
async def save_watchdog_config(request: Request, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Save Plugin Watchdog configuration."""
    pm: PluginManager = request.app.state.plugin_manager
    plugin = pm.get_plugin("watchdog")
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Watchdog plugin not found")
    
    plugin_obj = cast(Any, plugin)
    
    # Inject the plugin_manager reference for reload functionality
    config_with_manager = {
        **payload,
        "plugin_manager": pm,
    }
    
    # Apply configuration
    if hasattr(plugin_obj, "configure"):
        plugin_obj.configure(config_with_manager)
    
    # Toggle enabled state
    if "enabled" in payload:
        if payload["enabled"]:
            pm.enable_plugin("watchdog")
        else:
            pm.disable_plugin("watchdog")
    
    logger.info("Watchdog configuration updated: %s", payload)
    return {"status": "ok", "config": plugin_obj.get_config() if hasattr(plugin_obj, "get_config") else payload}


@router.get("/plugins/watchdog/status", dependencies=[Depends(verify_token)])
async def get_watchdog_status(request: Request) -> Dict[str, Any]:
    """Get Plugin Watchdog status."""
    pm: PluginManager = request.app.state.plugin_manager
    plugin = pm.get_plugin("watchdog")
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Watchdog plugin not found")
    
    plugin_obj = cast(Any, plugin)
    if hasattr(plugin_obj, "get_status"):
        return plugin_obj.get_status()
    
    return {"error": "Status not available"}


@router.post("/plugins/watchdog/check", dependencies=[Depends(verify_token)])
async def watchdog_force_check(request: Request) -> Dict[str, Any]:
    """Force watchdog to check for changes immediately."""
    pm: PluginManager = request.app.state.plugin_manager
    plugin = pm.get_plugin("watchdog")
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Watchdog plugin not found")
    
    plugin_obj = cast(Any, plugin)
    
    # Ensure plugin_manager is set
    if hasattr(plugin_obj, "_plugin_manager") and plugin_obj._plugin_manager is None:
        plugin_obj._plugin_manager = pm
    
    if hasattr(plugin_obj, "force_check"):
        return plugin_obj.force_check()
    
    return {"error": "Force check not available"}


# =============================================================================
# BRIDGE PLUGIN ENDPOINTS
# =============================================================================

@router.get("/plugins/bridge/status", dependencies=[Depends(verify_token)])
async def get_bridge_status(request: Request) -> Dict[str, Any]:
    """Get Plugin Bridge status and available services."""
    pm: PluginManager = request.app.state.plugin_manager
    plugin = pm.get_plugin("bridge")
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Bridge plugin not found")
    
    plugin_obj = cast(Any, plugin)
    
    # Initialize bridge if needed
    if hasattr(plugin_obj, "initialize") and not getattr(plugin_obj, "_initialized", False):
        plugin_obj.initialize(
            app_state=request.app.state,
            plugin_manager=pm
        )
    
    if hasattr(plugin_obj, "get_status"):
        return plugin_obj.get_status()
    
    return {"error": "Status not available"}


@router.post("/plugins/bridge/config", dependencies=[Depends(verify_token)])
async def save_bridge_config(request: Request, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Save Plugin Bridge configuration."""
    pm: PluginManager = request.app.state.plugin_manager
    plugin = pm.get_plugin("bridge")
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Bridge plugin not found")
    
    plugin_obj = cast(Any, plugin)
    
    # Apply configuration
    if hasattr(plugin_obj, "configure"):
        plugin_obj.configure(payload)
    
    logger.info("Bridge configuration updated: %s", payload)
    return {"status": "ok"}


@router.get("/plugins/bridge/services", dependencies=[Depends(verify_token)])
async def get_bridge_services(request: Request) -> Dict[str, Any]:
    """Get list of all available Bridge services."""
    pm: PluginManager = request.app.state.plugin_manager
    plugin = pm.get_plugin("bridge")
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Bridge plugin not found")
    
    plugin_obj = cast(Any, plugin)
    
    # Get the bridge context
    context = plugin_obj.get_context() if hasattr(plugin_obj, "get_context") else None
    if not context:
        return {"services": [], "message": "Bridge not initialized"}
    
    return {
        "services": context.list_services(),
        "api_version": context.api_version
    }


@router.get("/plugins/bridge/capabilities", dependencies=[Depends(verify_token)])
async def get_bridge_capabilities(request: Request) -> Dict[str, Any]:
    """Get list of all available Bridge capabilities."""
    pm: PluginManager = request.app.state.plugin_manager
    plugin = pm.get_plugin("bridge")
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Bridge plugin not found")
    
    plugin_obj = cast(Any, plugin)
    
    context = plugin_obj.get_context() if hasattr(plugin_obj, "get_context") else None
    if not context:
        return {"capabilities": [], "message": "Bridge not initialized"}
    
    return {
        "capabilities": context.list_capabilities(),
        "api_version": context.api_version
    }


@router.get("/plugins/bridge/service/{service_name}", dependencies=[Depends(verify_token)])
async def get_bridge_service_info(request: Request, service_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific Bridge service."""
    pm: PluginManager = request.app.state.plugin_manager
    plugin = pm.get_plugin("bridge")
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Bridge plugin not found")
    
    plugin_obj = cast(Any, plugin)
    
    context = plugin_obj.get_context() if hasattr(plugin_obj, "get_context") else None
    if not context:
        raise HTTPException(status_code=503, detail="Bridge not initialized")
    
    if not context.has_service(service_name):
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    
    # Find the descriptor
    services = context.list_services()
    for svc in services:
        if svc["name"] == service_name:
            return {"service": svc}
    
    return {"error": "Service descriptor not found"}


@router.get("/plugins/sidebar", response_model=List[Dict[str, Any]], dependencies=[Depends(verify_token)])
async def get_sidebar_plugins(request: Request) -> List[Dict[str, Any]]:
    """Get plugins that should appear in the sidebar menu."""
    pm: PluginManager = request.app.state.plugin_manager
    return pm.get_sidebar_plugins()


@router.get("/plugins/settings", response_model=List[Dict[str, Any]], dependencies=[Depends(verify_token)])
async def get_settings_plugins(request: Request) -> List[Dict[str, Any]]:
    """Get plugins that should appear in the settings page."""
    pm: PluginManager = request.app.state.plugin_manager
    return pm.get_settings_plugins()


@router.get("/plugins/{name}/ui")
async def get_plugin_ui(request: Request, name: str, role: str = Depends(verify_token)) -> Dict[str, Any]:
    """Get UI content (HTML and JS) for a plugin view."""
    pm: PluginManager = request.app.state.plugin_manager
    
    html = pm.get_plugin_ui_html(name)
    js = pm.get_plugin_ui_js(name)
    
    if html is None and js is None:
        raise HTTPException(status_code=404, detail=f"Plugin {name} has no UI or is not enabled")
    
    return {
        "name": name,
        "html": html or "",
        "js": js or "",
    }


@router.get("/plugins/{name}/settings-ui")
async def get_plugin_settings_ui(request: Request, name: str, role: str = Depends(verify_token)) -> Dict[str, Any]:
    """Get settings UI content (HTML and JS) for a plugin."""
    pm: PluginManager = request.app.state.plugin_manager
    
    html = pm.get_plugin_settings_html(name)
    js = pm.get_plugin_settings_js(name)
    
    if html is None and js is None:
        raise HTTPException(status_code=404, detail=f"Plugin {name} has no settings UI or is not enabled")
    
    return {
        "name": name,
        "html": html or "",
        "js": js or "",
    }


# --- Plugin Install / Uninstall Routes ---

@router.post("/plugins/install", dependencies=[Depends(require_admin)])
async def install_plugin_from_url(request: Request, payload: Dict[str, Any], role: str = Depends(require_admin)) -> Dict[str, Any]:
    """Install a plugin from a URL (ZIP or Git).
    
    Args:
        payload: Dict containing 'url' key with the plugin source URL
        
    Returns:
        Status of installation including plugin name if successful
    """
    log_action(role, "install_plugin", {"url": payload.get("url")})
    pm: PluginManager = request.app.state.plugin_manager
    
    url = payload.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    try:
        result = pm.install_plugin_from_url(url)
        if result.get("status") == "ok":
            await manager.broadcast(JupiterEvent(type=PLUGIN_TOGGLED, payload={"action": "install", "name": result.get("plugin_name")}))
        return result
    except Exception as exc:
        logger.error("Failed to install plugin from URL %s: %s", url, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/plugins/install/upload", dependencies=[Depends(require_admin)])
async def install_plugin_from_file(request: Request, file: UploadFile = File(...), role: str = Depends(require_admin)) -> Dict[str, Any]:
    """Install a plugin from an uploaded file (ZIP or .py).
    
    Args:
        file: Uploaded file (ZIP archive or single .py file)
        
    Returns:
        Status of installation including plugin name if successful
    """
    log_action(role, "install_plugin_upload", {"filename": file.filename})
    pm: PluginManager = request.app.state.plugin_manager
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Validate file extension
    if not file.filename.endswith(('.zip', '.py')):
        raise HTTPException(status_code=400, detail="Only .zip and .py files are supported")
    
    try:
        content = await file.read()
        result = pm.install_plugin_from_bytes(content, file.filename)
        if result.get("status") == "ok":
            await manager.broadcast(JupiterEvent(type=PLUGIN_TOGGLED, payload={"action": "install", "name": result.get("plugin_name")}))
        return result
    except Exception as exc:
        logger.error("Failed to install plugin from file %s: %s", file.filename, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/plugins/{name}/uninstall", dependencies=[Depends(require_admin)])
async def uninstall_plugin(request: Request, name: str, role: str = Depends(require_admin)) -> Dict[str, Any]:
    """Uninstall a plugin by name.
    
    Removes the plugin files from the plugins directory.
    Core plugins cannot be uninstalled.
    
    Args:
        name: Name of the plugin to uninstall
        
    Returns:
        Status of uninstallation
    """
    log_action(role, "uninstall_plugin", {"name": name})
    pm: PluginManager = request.app.state.plugin_manager
    
    try:
        result = pm.uninstall_plugin(name)
        if result.get("status") == "ok":
            await manager.broadcast(JupiterEvent(type=PLUGIN_TOGGLED, payload={"action": "uninstall", "name": name}))
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Failed to uninstall plugin %s: %s", name, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/meeting/status", response_model=MeetingStatus)
async def get_meeting_status(request: Request) -> MeetingStatus:
    """Return the status of the Meeting integration."""
    adapter: MeetingAdapter = request.app.state.meeting_adapter
    status_dict = adapter.check_license()

    return MeetingStatus(
        device_key=cast(Optional[str], status_dict.get("device_key")),
        is_licensed=bool(status_dict.get("is_licensed", False)),
        session_active=bool(status_dict.get("session_active", False)),
        session_remaining_seconds=cast(Optional[int], status_dict.get("session_remaining_seconds")),
        status=str(status_dict.get("status", "unknown")),
        message=cast(Optional[str], status_dict.get("message")),
    )

@router.get("/license/status", response_model=LicenseStatus)
async def get_license_status(request: Request) -> LicenseStatus:
    """Return detailed Meeting license verification status.
    
    This endpoint provides comprehensive information about the Jupiter license
    verification against the Meeting backend API, including:
    - The overall status (valid, invalid, network_error, config_error)
    - HTTP response details from Meeting API
    - Business rule validation results (authorized, device_type, token_count)
    """
    adapter: MeetingAdapter = request.app.state.meeting_adapter
    result = adapter.get_license_status()
    result_dict = result.to_dict()

    return LicenseStatus(
        status=str(result_dict.get("status", "unknown")),
        message=str(result_dict.get("message", "Unknown status")),
        device_key=cast(Optional[str], result_dict.get("device_key")),
        http_status=cast(Optional[int], result_dict.get("http_status")),
        authorized=cast(Optional[bool], result_dict.get("authorized")),
        device_type=cast(Optional[str], result_dict.get("device_type")),
        token_count=cast(Optional[int], result_dict.get("token_count")),
        checked_at=cast(Optional[str], result_dict.get("checked_at")),
        meeting_base_url=cast(Optional[str], result_dict.get("meeting_base_url")),
        device_type_expected=cast(Optional[str], result_dict.get("device_type_expected")),
    )

@router.post("/license/refresh", response_model=LicenseStatus)
async def refresh_license(request: Request, role: str = Depends(require_admin)) -> LicenseStatus:
    """Re-check the Jupiter license against Meeting API.
    
    This endpoint forces a fresh license verification against the Meeting backend.
    Requires admin privileges.
    """
    log_action(role, "refresh_license", {})
    adapter: MeetingAdapter = request.app.state.meeting_adapter
    result = adapter.refresh_license()
    result_dict = result.to_dict()

    return LicenseStatus(
        status=str(result_dict.get("status", "unknown")),
        message=str(result_dict.get("message", "Unknown status")),
        device_key=cast(Optional[str], result_dict.get("device_key")),
        http_status=cast(Optional[int], result_dict.get("http_status")),
        authorized=cast(Optional[bool], result_dict.get("authorized")),
        device_type=cast(Optional[str], result_dict.get("device_type")),
        token_count=cast(Optional[int], result_dict.get("token_count")),
        checked_at=cast(Optional[str], result_dict.get("checked_at")),
        meeting_base_url=cast(Optional[str], result_dict.get("meeting_base_url")),
        device_type_expected=cast(Optional[str], result_dict.get("device_type_expected")),
    )

@router.post("/init")
async def init_project(request: Request) -> Dict[str, str]:
    """Initialize a new Jupiter project with default config.
    
    Creates a project-specific config file with performance, ci, backends, and api settings.
    Global settings (server, gui, meeting, plugins, security, users, logging)
    are stored in global_config.yaml and should not be duplicated here.
    """
    root = request.app.state.root_path
    config_path = get_project_config_path(root)
    
    if config_path.exists():
        return {"message": "Project already initialized"}
        
    # Project-specific settings only - global settings are in global_config.yaml
    default_config = """# Jupiter Project Configuration
# Project-specific settings only
# Global settings (server, gui, meeting, ui, security, plugins, users, logging)
# are stored in global_config.yaml

api:
  type: openapi
  openapi_url: /openapi.json
  base_url: null
  path: null
  connector: null
  app_var: null

backends: []

ci:
  fail_on: {}

performance:
  parallel_scan: true
  max_workers: null
  scan_timeout: 300
  large_file_threshold: 1048576
  max_graph_nodes: 1000
  graph_simplification: false
  excluded_dirs:
    - node_modules
    - venv
    - .venv
    - dist
    - build
"""
    try:
        config_path.write_text(default_config, encoding="utf-8")
        return {"message": "Project initialized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create config: {e}")

@router.post("/run", response_model=RunResponse)
async def post_run(request: Request, run_req: RunRequest, role: str = Depends(require_admin)) -> RunResponse:
    """Execute a command in the project root and return its output."""
    log_action(role, "run", run_req.command)
    app = request.app
    app.state.meeting_adapter.validate_feature_access("run")

    config = app.state.project_manager.config
    if not config:
        raise HTTPException(status_code=400, detail="No active project configuration.")

    if not config.security.allow_run:
        raise HTTPException(status_code=403, detail="Run command is disabled by configuration.")
    
    if config.security.allowed_commands:
        cmd_str = " ".join(run_req.command)
        executable = run_req.command[0] if run_req.command else ""
        
        if cmd_str not in config.security.allowed_commands and executable not in config.security.allowed_commands:
             raise HTTPException(status_code=403, detail=f"Command {cmd_str} is not allowed by security policy.")

    if run_req.backend_name:
        connector = app.state.project_manager.get_connector(run_req.backend_name)
        if not connector:
            raise HTTPException(status_code=404, detail=f"Backend {run_req.backend_name} not found")
    else:
        connector = app.state.project_manager.get_default_connector()

    await manager.broadcast(JupiterEvent(type=RUN_STARTED, payload={"command": run_req.command, "cwd": run_req.cwd}))

    try:
        result_dict = await connector.run_command(run_req.command, with_dynamic=run_req.with_dynamic, cwd=run_req.cwd)
        await manager.broadcast(JupiterEvent(type=RUN_FINISHED, payload={"returncode": result_dict.get("returncode", 0)}))
        
        # If dynamic analysis was enabled and we have call data, record it for the watch feature
        if run_req.with_dynamic and result_dict.get("dynamic_data"):
            dynamic_data = result_dict["dynamic_data"]
            calls = dynamic_data.get("calls", {})
            if calls:
                from jupiter.server.routers.watch import record_function_calls
                await record_function_calls(calls)
                
    except Exception as e:
        logger.error("Run failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Run failed: {str(e)}")
    
    return RunResponse(
        stdout=result_dict["stdout"],
        stderr=result_dict["stderr"],
        returncode=result_dict["returncode"],
        dynamic_analysis=result_dict.get("dynamic_data"),
    )



@router.get("/projects", dependencies=[Depends(verify_token)])
async def list_projects(request: Request) -> List[Dict[str, Any]]:
    """List all configured projects."""
    pm = request.app.state.project_manager
    return [
        {
            "id": p.id,
            "name": p.name,
            "path": p.path,
            "config_file": p.config_file,
            "ignore_globs": p.ignore_globs,
            "is_active": p.id == pm.global_config.default_project_id
        }
        for p in pm.get_projects()
    ]


@router.post("/projects", dependencies=[Depends(require_admin)])
async def create_project(request: Request, payload: Dict[str, str]) -> Dict[str, Any]:
    """Create a new project."""
    path = payload.get("path")
    name = payload.get("name")
    ignore_globs = payload.get("ignore_globs") or []
    if not path or not name:
        raise HTTPException(status_code=400, detail="Path and name are required")
    
    pm = request.app.state.project_manager
    try:
        project = pm.create_project(path, name)
        project.ignore_globs = ignore_globs if isinstance(ignore_globs, list) else []
        save_global_config(pm.global_config)
        return {
            "id": project.id,
            "name": project.name,
            "path": project.path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/activate", dependencies=[Depends(require_admin)])
async def activate_project(request: Request, project_id: str) -> Dict[str, Any]:
    """Switch to another project."""
    pm = request.app.state.project_manager
    
    # Find project first
    project = next((p for p in pm.global_config.projects if p.id == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Use ProjectManager to switch (it updates global config)
    success = pm.set_active_project(project_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to load project")
    
    # Rebuild runtime
    state = SystemState(request.app)
    new_config = pm.config
    state.rebuild_runtime(new_config, new_root=new_config.project_root, reset_history=True)
    
    return {"status": "ok", "project_id": project_id}


@router.delete("/projects/{project_id}", dependencies=[Depends(require_admin)])
async def delete_project(request: Request, project_id: str) -> Dict[str, Any]:
    """Delete a project."""
    pm = request.app.state.project_manager
    success = pm.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "ok", "project_id": project_id}


@router.post("/projects/{project_id}/ignore", dependencies=[Depends(require_admin)])
async def update_project_ignore(request: Request, project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update ignore globs for a project."""
    pm = request.app.state.project_manager
    project = next((p for p in pm.global_config.projects if p.id == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    ignore_globs = payload.get("ignore_globs") or []
    if not isinstance(ignore_globs, list):
        raise HTTPException(status_code=400, detail="ignore_globs must be a list of patterns")

    project.ignore_globs = ignore_globs
    save_global_config(pm.global_config)
    return {"status": "ok", "ignore_globs": project.ignore_globs}


@router.get("/projects/{project_id}/api_config", dependencies=[Depends(verify_token)])
async def get_project_api_config(request: Request, project_id: str) -> Dict[str, Any]:
    """Return API inspection settings for a project."""
    pm = request.app.state.project_manager
    project = next((p for p in pm.global_config.projects if p.id == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_path = Path(project.path)
    config = load_config(project_path, config_file=project.config_file)
    api_cfg = config.project_api or ProjectApiConfig()
    return {
        "connector": api_cfg.connector,
        "app_var": api_cfg.app_var,
        "path": api_cfg.path,
        "base_url": api_cfg.base_url,
        "openapi_url": api_cfg.openapi_url,
    }


@router.post("/projects/{project_id}/api_config", dependencies=[Depends(require_admin)])
async def update_project_api_config(request: Request, project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update API inspection settings for a project."""
    pm = request.app.state.project_manager
    project = next((p for p in pm.global_config.projects if p.id == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    connector = payload.get("connector")
    app_var = payload.get("app_var")
    path = payload.get("path")

    project_path = Path(project.path)
    config = load_config(project_path, config_file=project.config_file)
    if not config.project_api:
        config.project_api = ProjectApiConfig()

    config.project_api.connector = connector
    config.project_api.app_var = app_var
    config.project_api.path = path

    save_config(config, project_path)

    if pm.global_config.default_project_id == project_id:
        # Refresh runtime for active project
        SystemState(request.app).rebuild_runtime(config, new_root=config.project_root, reset_history=False)

    return {
        "connector": connector,
        "app_var": app_var,
        "path": path,
    }

@router.get("/projects/{project_id}/api_status", dependencies=[Depends(verify_token)])
async def get_project_api_status(request: Request, project_id: str) -> Dict[str, Any]:
    """Check the status of the project's API."""
    pm = request.app.state.project_manager
    project = next((p for p in pm.global_config.projects if p.id == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_path = Path(project.path)
    config = load_config(project_path, config_file=project.config_file)
    api_cfg = config.project_api

    if not api_cfg or not api_cfg.base_url:
        return {"status": "not_configured", "message": "No API configured"}

    # Try to reach the API
    import httpx
    try:
        # We check the base URL or openapi URL
        url = api_cfg.base_url
        if api_cfg.openapi_url:
             url = f"{api_cfg.base_url.rstrip('/')}/{api_cfg.openapi_url.lstrip('/')}"
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            if resp.status_code < 500:
                return {"status": "ok", "message": f"API OK ({api_cfg.base_url})"}
            else:
                return {"status": "error", "message": f"API Error {resp.status_code} ({api_cfg.base_url})"}
    except Exception as e:
        return {"status": "unreachable", "message": f"API Unreachable ({api_cfg.base_url})"}


# =============================================================================
# PHASE 2: DIAGNOSTIC ENDPOINTS
# =============================================================================

@router.get("/diag/handlers", dependencies=[Depends(verify_token)])
async def get_all_handlers(request: Request) -> Dict[str, Any]:
    """
    Get all registered handlers across CLI, API, and plugins.
    
    This endpoint is used for autodiag to reduce false positives
    by providing a complete list of dynamically registered handlers.
    
    Returns:
        Dict with:
        - api_handlers: List of FastAPI route handlers
        - cli_handlers: List of CLI command handlers
        - plugin_handlers: List of plugin hook handlers
        - total: Total count of all handlers
    """
    app = request.app
    
    # 1. API Handlers (FastAPI routes)
    api_handlers = _collect_api_handlers(app)
    
    # 2. CLI Handlers
    cli_handlers = _collect_cli_handlers()
    
    # 3. Plugin Handlers
    plugin_handlers = _collect_plugin_handlers(app)
    
    return {
        "api_handlers": api_handlers,
        "cli_handlers": cli_handlers,
        "plugin_handlers": plugin_handlers,
        "total": len(api_handlers) + len(cli_handlers) + len(plugin_handlers),
    }


def _collect_api_handlers(app) -> List[Dict[str, Any]]:
    """Collect all FastAPI route handlers with their function names."""
    handlers = []
    
    for route in app.routes:
        if not hasattr(route, "endpoint"):
            continue
        
        endpoint = route.endpoint
        handler_info = {
            "type": "api",
            "path": getattr(route, "path", None),
            "methods": sorted(list(getattr(route, "methods", []))) if hasattr(route, "methods") else [],
            "function_name": getattr(endpoint, "__name__", str(endpoint)),
            "module": getattr(endpoint, "__module__", "unknown"),
            "qualname": getattr(endpoint, "__qualname__", None),
        }
        handlers.append(handler_info)
    
    return handlers


def _collect_cli_handlers() -> List[Dict[str, Any]]:
    """Collect all CLI command handlers from jupiter.cli.main."""
    handlers = []
    
    try:
        from jupiter.cli.main import get_cli_handlers
        
        for handler in get_cli_handlers():
            handlers.append({
                "type": "cli",
                "command": handler["command"],
                "function_name": handler["function_name"],
                "module": handler["module"],
                "qualname": handler["qualname"],
            })
    except ImportError as e:
        logger.warning("Could not import get_cli_handlers: %s", e)
        # Fallback: try command_handlers directly
        try:
            from jupiter.cli import command_handlers
            
            for name in dir(command_handlers):
                if name.startswith("handle_"):
                    func = getattr(command_handlers, name)
                    if callable(func):
                        command_name = name.replace("handle_", "")
                        handlers.append({
                            "type": "cli",
                            "command": command_name,
                            "function_name": name,
                            "module": "jupiter.cli.command_handlers",
                            "qualname": getattr(func, "__qualname__", name),
                        })
        except ImportError:
            pass
    
    return handlers


def _collect_plugin_handlers(app) -> List[Dict[str, Any]]:
    """Collect all plugin hook handlers from the plugin manager."""
    handlers = []
    
    plugin_manager = getattr(app.state, "plugin_manager", None)
    if not plugin_manager:
        return handlers
    
    # Known plugin hooks
    hook_names = [
        "on_scan", "on_analyze", "on_report", 
        "on_startup", "on_shutdown",
        "setup", "cleanup", "configure",
    ]
    
    for plugin in plugin_manager.get_enabled_plugins():
        plugin_name = getattr(plugin, "name", type(plugin).__name__)
        
        for hook in hook_names:
            if hasattr(plugin, hook) and callable(getattr(plugin, hook)):
                method = getattr(plugin, hook)
                handlers.append({
                    "type": "plugin",
                    "plugin_name": plugin_name,
                    "hook": hook,
                    "function_name": hook,
                    "module": getattr(method, "__module__", "unknown"),
                    "qualname": getattr(method, "__qualname__", f"{plugin_name}.{hook}"),
                })
    
    return handlers


@router.get("/diag/functions", dependencies=[Depends(verify_token)])
async def get_function_usage_details(request: Request) -> Dict[str, Any]:
    """
    Get detailed function usage information with confidence scores.
    
    This endpoint provides the Phase 2 confidence-scored function
    analysis for reducing false positives in unused detection.
    
    Returns:
        Dict with:
        - functions: List of function usage details (non-USED only)
        - summary: Count by usage status
        - total_analyzed: Total functions analyzed
    """
    from jupiter.core.cache import CacheManager
    from jupiter.core.analyzer import ProjectAnalyzer, FunctionUsageStatus
    from jupiter.core.scanner import ProjectScanner
    
    root = request.app.state.root_path
    cache_manager = CacheManager(root)
    last_scan = cache_manager.load_last_scan()
    
    if not last_scan:
        return {
            "functions": [],
            "summary": {},
            "total_analyzed": 0,
            "error": "No scan data available. Run a scan first.",
        }
    
    # Get python_summary from cached analysis or compute fresh
    python_summary = last_scan.get("python_summary")
    
    if not python_summary:
        # Compute analysis on-the-fly
        scanner = ProjectScanner(root=root)
        analyzer = ProjectAnalyzer(root=root, no_cache=False)
        summary = analyzer.summarize(scanner.iter_files())
        if summary.python_summary:
            return {
                "functions": summary.python_summary.function_usage_details,
                "summary": summary.python_summary.usage_summary,
                "total_analyzed": summary.python_summary.total_functions,
            }
        return {
            "functions": [],
            "summary": {},
            "total_analyzed": 0,
        }
    
    return {
        "functions": python_summary.get("function_usage_details", []),
        "summary": python_summary.get("usage_summary", {}),
        "total_analyzed": python_summary.get("total_functions", 0),
    }



