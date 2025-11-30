from typing import Dict, Any, List, Optional
import logging
import os
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, File
from jupiter.server.routers.auth import verify_token, require_admin, log_action
from jupiter.core.metrics import MetricsCollector
from jupiter.core.plugin_manager import PluginManager
from jupiter.core.updater import apply_update
from jupiter.core.state import save_last_root
from jupiter.config import load_config, save_config
from jupiter.config.config import ProjectApiConfig
from jupiter.server.ws import manager
from jupiter.core.events import JupiterEvent, CONFIG_UPDATED, PLUGIN_TOGGLED, RUN_STARTED, RUN_FINISHED
from jupiter.server.meeting_adapter import MeetingAdapter
from jupiter.server.system_services import SystemState, preserve_meeting_config
from jupiter.server.models import (
    HealthStatus,
    RootUpdate,
    RootUpdateResponse,
    ConfigModel,
    RawConfigModel,
    UpdateRequest,
    FSListResponse,
    FSListEntry,
    MeetingStatus,
    RunRequest,
    RunResponse,
)

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
            meeting_enabled=False,
            meeting_device_key=None,
            ui_theme="dark",
            ui_language="en",
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
        meeting_enabled=config.meeting.enabled,
        meeting_device_key=config.meeting.deviceKey,
        ui_theme=config.ui.theme,
        ui_language=config.ui.language,
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
    current_config.meeting.enabled = new_config.meeting_enabled
    current_config.meeting.deviceKey = new_config.meeting_device_key
    current_config.ui.theme = new_config.ui_theme
    current_config.ui.language = new_config.ui_language
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
        return new_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {e}")

@router.get("/config/raw", response_model=RawConfigModel, dependencies=[Depends(require_admin)])
async def get_raw_config(request: Request) -> RawConfigModel:
    """Get raw configuration file content."""
    root = request.app.state.root_path
    config_file = root / "jupiter.yaml"
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
    config_file = root / "jupiter.yaml"
    try:
        config_file.write_text(raw_config.content, encoding="utf-8")
        return raw_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write config file: {e}")

@router.post("/update")
async def trigger_update(request: Request, update_req: UpdateRequest, role: str = Depends(require_admin)) -> Dict[str, str]:
    """Trigger self-update."""
    log_action(role, "update_jupiter", update_req.source)
    request.app.state.meeting_adapter.validate_feature_access("update")
    
    try:
        apply_update(update_req.source, update_req.force)
        return {"status": "ok", "message": "Update applied successfully. Please restart."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update/upload")
async def upload_update(file: UploadFile = File(...), role: str = Depends(require_admin)) -> Dict[str, str]:
    """Upload an update ZIP file."""
    log_action(role, "upload_update", {"filename": file.filename})
    
    try:
        fd, path = tempfile.mkstemp(suffix=".zip")
        with os.fdopen(fd, "wb") as tmp:
            shutil.copyfileobj(file.file, tmp)
            
        return {"path": path, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {e}")

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

@router.get("/plugins", response_model=List[Dict[str, Any]], dependencies=[Depends(verify_token)])
async def get_plugins(request: Request) -> List[Dict[str, Any]]:
    """Get list of all plugins."""
    pm: PluginManager = request.app.state.plugin_manager
    return pm.get_plugins_info()

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

@router.post("/plugins/{name}/config")
async def configure_plugin(request: Request, name: str, config: Dict[str, Any], role: str = Depends(require_admin)) -> Dict[str, bool]:
    """Configure a plugin."""
    log_action(role, "configure_plugin", {"name": name, "config": config})
    pm: PluginManager = request.app.state.plugin_manager
    pm.update_plugin_config(name, config)
    
    try:
        project_manager = request.app.state.project_manager
        if project_manager.config:
            if not hasattr(project_manager.config.plugins, "settings"):
                 pass
            project_manager.config.plugins.settings[name] = config
            
            save_config(project_manager.config, request.app.state.root_path)
            
    except Exception as e:
        logger.error("Failed to save config: %s", e)
        
    return {"success": True}

@router.get("/meeting/status", response_model=MeetingStatus)
async def get_meeting_status(request: Request) -> MeetingStatus:
    """Return the status of the Meeting integration."""
    adapter: MeetingAdapter = request.app.state.meeting_adapter
    status_dict = adapter.check_license()

    return MeetingStatus(
        device_key=status_dict.get("device_key"),
        is_licensed=status_dict.get("is_licensed", False),
        session_active=status_dict.get("session_active", False),
        session_remaining_seconds=status_dict.get("session_remaining_seconds"),
        status=status_dict.get("status", "unknown"),
        message=status_dict.get("message"),
    )

@router.post("/init")
async def init_project(request: Request) -> Dict[str, str]:
    """Initialize a new Jupiter project with default config."""
    root = request.app.state.root_path
    config_path = root / "jupiter.yaml"
    
    if config_path.exists():
        return {"message": "Project already initialized"}
        
    default_config = """
server:
  host: 127.0.0.1
  port: 8000

gui:
  host: 127.0.0.1
  port: 8050

meeting:
  enabled: false
  deviceKey: null

plugins:
  enabled: []
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

    await manager.broadcast(JupiterEvent(type=RUN_STARTED, payload={"command": run_req.command}))

    try:
        result_dict = await connector.run_command(run_req.command, with_dynamic=run_req.with_dynamic)
        await manager.broadcast(JupiterEvent(type=RUN_FINISHED, payload={"returncode": result_dict.get("returncode", 0)}))
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
            "is_active": p.id == pm.global_config.default_project_id
        }
        for p in pm.get_projects()
    ]


@router.post("/projects", dependencies=[Depends(require_admin)])
async def create_project(request: Request, payload: Dict[str, str]) -> Dict[str, Any]:
    """Create a new project."""
    path = payload.get("path")
    name = payload.get("name")
    if not path or not name:
        raise HTTPException(status_code=400, detail="Path and name are required")
    
    pm = request.app.state.project_manager
    try:
        project = pm.create_project(path, name)
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


