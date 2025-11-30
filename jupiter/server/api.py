"""Lightweight API server using FastAPI."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List, Dict, Any

import uvicorn
from fastapi import FastAPI, WebSocket, HTTPException, Request, Depends, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from jupiter.core import ProjectAnalyzer, ProjectScanner
from jupiter.core.runner import run_command
from jupiter.core.exceptions import JupiterError, ScanError, AnalyzeError, RunError, MeetingError
from jupiter.core.cache import CacheManager
from jupiter.core.plugin_manager import PluginManager
from jupiter.core.history import HistoryManager
from jupiter.core.state import save_last_root
from jupiter.core.updater import apply_update
from jupiter.core.simulator import ProjectSimulator
from jupiter.core.graph import GraphBuilder
from jupiter.config import load_config, save_config, JupiterConfig, PluginsConfig, UserConfig
from jupiter.server.manager import ProjectManager
from jupiter.core.events import JupiterEvent, SCAN_STARTED, SCAN_FINISHED, RUN_STARTED, RUN_FINISHED, CONFIG_UPDATED, PLUGIN_TOGGLED
from jupiter.core.metrics import MetricsCollector
from .ws import websocket_endpoint, manager
from .meeting_adapter import MeetingAdapter
from .models import (
    ScanRequest,
    ScanReport,
    RunRequest,
    RunResponse,
    AnalyzeResponse,
    MeetingStatus,
    HealthStatus,
    RootUpdate,
    RootUpdateResponse,
    FSListResponse,
    FSListEntry,
    ErrorResponse,
    ConfigModel,
    RawConfigModel,
    UpdateRequest,
    FileAnalysis,
    SnapshotListResponse,
    SnapshotResponse,
    SnapshotDiffResponse,
    SnapshotMetadataModel,
    SimulateRequest,
    SimulateResponse,
    ImpactModel,
    UserModel,
)
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Jupiter API",
    description="API for scanning and analyzing projects.",
    version="1.0.1",
)

@app.exception_handler(JupiterError)
async def jupiter_exception_handler(request: Request, exc: JupiterError):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": exc.code, "message": str(exc), "details": exc.details}},
    )

@app.exception_handler(ScanError)
async def scan_exception_handler(request: Request, exc: ScanError):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": exc.code, "message": str(exc), "details": exc.details}},
    )

@app.exception_handler(AnalyzeError)
async def analyze_exception_handler(request: Request, exc: AnalyzeError):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": exc.code, "message": str(exc), "details": exc.details}},
    )

@app.exception_handler(RunError)
async def run_exception_handler(request: Request, exc: RunError):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": exc.code, "message": str(exc), "details": exc.details}},
    )

@app.exception_handler(MeetingError)
async def meeting_exception_handler(request: Request, exc: MeetingError):
    return JSONResponse(
        status_code=503,
        content={"error": {"code": exc.code, "message": str(exc), "details": exc.details}},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Using app.state to hold the root path, which will be set on server startup.
# This makes it available to endpoint functions.
# A more complex app might use dependency injection.
app.state.root_path = Path.cwd()

security_scheme = HTTPBearer(auto_error=False)

async def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> str:
    """Verify the authentication token and return the role."""
    try:
        config = app.state.project_manager.config
    except AttributeError:
        # Should not happen if server started correctly
        return "admin"

    # Check if any security is configured
    has_single_token = bool(config.security.token)
    has_multi_tokens = bool(config.security.tokens)
    has_users = bool(config.users)
    
    if not has_single_token and not has_multi_tokens and not has_users:
        return "admin"

    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authentication token")
    
    provided_token = credentials.credentials

    # Check single token (legacy/simple mode) -> Admin
    if has_single_token and provided_token == config.security.token:
        return "admin"

    # Check multi tokens
    if has_multi_tokens:
        for t in config.security.tokens:
            if t.token == provided_token:
                return t.role

    # Check users
    if has_users:
        for u in config.users:
            if u.token == provided_token:
                return u.role
    
    raise HTTPException(status_code=401, detail="Invalid authentication token")

async def require_admin(role: str = Depends(verify_token)) -> str:
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return role

def log_action(role: str, action: str, details: Any = None):
    """Log sensitive actions."""
    logger.info(f"ACTION | Role: {role} | Action: {action} | Details: {details}")


def _history_manager() -> HistoryManager:
    manager = getattr(app.state, "history_manager", None)
    if manager is None:
        manager = HistoryManager(app.state.root_path)
        app.state.history_manager = manager
    return manager


@app.get("/metrics", dependencies=[Depends(verify_token)])
async def get_metrics() -> Dict[str, Any]:
    """Get system metrics."""
    collector = MetricsCollector(
        history_manager=_history_manager(),
        plugin_manager=app.state.plugin_manager
    )
    return collector.collect()


@app.post("/login")
async def login(creds: LoginRequest) -> Dict[str, str]:
    """Login with username and password (token)."""
    config = app.state.project_manager.config
    
    # Check users
    for u in config.users:
        if u.name == creds.username and u.token == creds.password:
            return {"token": u.token, "role": u.role, "name": u.name}
            
    # Fallback to legacy single token if username is "admin"
    if creds.username == "admin" and config.security.token and creds.password == config.security.token:
        return {"token": config.security.token, "role": "admin", "name": "admin"}

    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/scan", response_model=ScanReport, dependencies=[Depends(verify_token)])
async def post_scan(options: ScanRequest) -> ScanReport:
    """Run a filesystem scan and return a JSON report."""
    root = app.state.root_path.resolve()
    logger.info("Scanning project at %s with options: %s", root, options)

    await manager.broadcast(JupiterEvent(type=SCAN_STARTED, payload={"root": str(root), "options": options.dict()}))

    if options.backend_name:
        connector = app.state.project_manager.get_connector(options.backend_name)
        if not connector:
            raise HTTPException(status_code=404, detail=f"Backend '{options.backend_name}' not found")
    else:
        connector = app.state.project_manager.get_default_connector()
    
    scan_options = {
        "show_hidden": options.show_hidden,
        "ignore_globs": options.ignore_globs,
        "incremental": options.incremental,
    }
    
    try:
        report_dict = await connector.scan(scan_options)
    except Exception as e:
        logger.error("Scan failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")
    
    # Convert core FileMetadata dicts to API FileAnalysis models
    from .models import FileAnalysis

    file_models = [
        FileAnalysis(
            path=f["path"],
            size_bytes=f["size_bytes"],
            modified_timestamp=f["modified_timestamp"],
            file_type=f["file_type"],
            language_analysis=f["language_analysis"],
        )
        for f in report_dict["files"]
    ]

    report = ScanReport(
        report_schema_version=report_dict.get("report_schema_version", "1.0"),
        root=report_dict["root"],
        files=file_models,
        dynamic=report_dict.get("dynamic"),
        plugins=app.state.plugin_manager.get_plugins_info(),
        quality=report_dict.get("quality"),
        refactoring=report_dict.get("refactoring"),
    )

    # Run plugin hooks
    app.state.plugin_manager.hook_on_scan(report.dict())

    # Enrich with API info if available (for ScanReport)
    if hasattr(connector, "get_api_info"):
        try:
            api_info = await connector.get_api_info()
            if api_info:
                report.api = api_info
        except Exception as e:
            logger.warning("Failed to fetch API info during scan: %s", e)

    await manager.broadcast(JupiterEvent(type=SCAN_FINISHED, payload={"file_count": len(report.files)}))

    if options.capture_snapshot:
        try:
            metadata = _history_manager().create_snapshot(
                report_dict,
                label=options.snapshot_label,
                backend_name=options.backend_name,
            )
            await manager.broadcast(f"Snapshot stored: {metadata.id}")
        except Exception as exc:  # pragma: no cover - logging only
            logger.warning("Failed to store snapshot: %s", exc)

    # Save to cache (Connector might have done it, but we ensure it here for API consistency if needed)
    # cache_manager = CacheManager(root)
    # cache_manager.save_last_scan(report.dict())

    await manager.broadcast(f"Scan completed. Found {len(file_models)} files.")

    return report


@app.get("/snapshots", response_model=SnapshotListResponse, dependencies=[Depends(verify_token)])
async def get_snapshots() -> SnapshotListResponse:
    history = _history_manager()
    entries = [SnapshotMetadataModel(**asdict(meta)) for meta in history.list_snapshots()]
    return SnapshotListResponse(snapshots=entries)


@app.get("/snapshots/{snapshot_id}", response_model=SnapshotResponse, dependencies=[Depends(verify_token)])
async def get_snapshot(snapshot_id: str) -> SnapshotResponse:
    snapshot = _history_manager().get_snapshot(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    metadata = SnapshotMetadataModel(**snapshot["metadata"])
    return SnapshotResponse(metadata=metadata, report=snapshot["report"])


@app.get("/snapshots/diff", response_model=SnapshotDiffResponse, dependencies=[Depends(verify_token)])
async def diff_snapshots(id_a: str, id_b: str) -> SnapshotDiffResponse:
    try:
        diff = _history_manager().compare_snapshots(id_a, id_b).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return SnapshotDiffResponse(**diff)


@app.post("/simulate/remove", response_model=SimulateResponse)
async def simulate_remove(request: SimulateRequest) -> SimulateResponse:
    """Simulate the removal of a file or function."""
    # We need the current scan state. We can load it from cache.
    root = app.state.root_path
    cache_manager = CacheManager(root)
    last_scan = cache_manager.load_last_scan()
    
    if not last_scan or "files" not in last_scan:
        raise HTTPException(status_code=400, detail="No scan data available. Please run a scan first.")
        
    simulator = ProjectSimulator(last_scan["files"])
    
    if request.target_type == "file":
        result = simulator.simulate_remove_file(request.path)
    elif request.target_type == "function":
        if not request.function_name:
            raise HTTPException(status_code=400, detail="function_name is required for function target")
        result = simulator.simulate_remove_function(request.path, request.function_name)
    else:
        raise HTTPException(status_code=400, detail="Invalid target_type")
        
    return SimulateResponse(
        target=result.target,
        impacts=[
            ImpactModel(
                target=i.target,
                impact_type=i.impact_type,
                details=i.details,
                severity=i.severity
            ) for i in result.impacts
        ],
        risk_score=result.risk_score
    )


@app.get("/graph", dependencies=[Depends(verify_token)])
async def get_graph(
    backend_name: Optional[str] = None,
    simplify: bool = False,
    max_nodes: int = 1000
) -> Dict[str, Any]:
    """Generate a dependency graph for the project."""
    # We try to use the cached scan first for speed
    root = app.state.root_path
    cache_manager = CacheManager(root)
    last_scan = cache_manager.load_last_scan()
    
    if not last_scan or "files" not in last_scan:
        # If no cache, try to scan using the connector
        connector = app.state.project_manager.get_connector(backend_name)
        if not connector:
            connector = app.state.project_manager.get_default_connector()
        
        try:
            last_scan = await connector.scan({})
        except Exception as e:
             raise HTTPException(status_code=500, detail=f"Failed to generate graph: {str(e)}")

    builder = GraphBuilder(last_scan["files"], simplify=simplify, max_nodes=max_nodes)
    graph = builder.build()
    
    return graph.to_dict()


@app.get("/analyze", response_model=AnalyzeResponse, dependencies=[Depends(verify_token)])
async def get_analyze(
    top: int = 5, 
    show_hidden: bool = False, 
    ignore_globs: Optional[list[str]] = None,
    backend_name: Optional[str] = None
) -> AnalyzeResponse:
    """Scan and analyze a project, returning a summary."""
    root = app.state.root_path
    logger.info("Analyzing project at %s", root)
    
    if backend_name:
        connector = app.state.project_manager.get_connector(backend_name)
        if not connector:
            raise HTTPException(status_code=404, detail=f"Backend '{backend_name}' not found")
    else:
        connector = app.state.project_manager.get_default_connector()
    
    analyze_options = {
        "top": top,
        "show_hidden": show_hidden,
        "ignore_globs": ignore_globs,
    }
    
    try:
        summary_dict = await connector.analyze(analyze_options)
        logger.info(f"Analysis complete. API data present: {'api' in summary_dict}")
    except Exception as e:
        logger.error("Analysis failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    # Convert to Pydantic model
    from .models import Hotspot, PythonProjectSummary, RefactoringRecommendation

    hotspots_dict = {
        key: [Hotspot(path=h["path"], details=h["details"]) for h in items]
        for key, items in summary_dict.get("hotspots", {}).items()
    }

    refactoring_list = [
        RefactoringRecommendation(
            path=r["path"],
            type=r["type"],
            details=r["details"],
            severity=r["severity"]
        )
        for r in summary_dict.get("refactoring", [])
    ]

    python_summary = None
    if summary_dict.get("python_summary"):
        ps = summary_dict["python_summary"]
        python_summary = PythonProjectSummary(
            total_files=ps["total_files"],
            total_functions=ps["total_functions"],
            total_potentially_unused_functions=ps["total_potentially_unused_functions"],
            avg_functions_per_file=ps["avg_functions_per_file"],
            quality_score=ps.get("quality_score"),
        )

    response = AnalyzeResponse(
        file_count=summary_dict["file_count"],
        total_size_bytes=summary_dict["total_size_bytes"],
        average_size_bytes=summary_dict["average_size_bytes"],
        by_extension=summary_dict["by_extension"],
        hotspots=hotspots_dict,
        python_summary=python_summary,
        plugins=app.state.plugin_manager.get_plugins_info(),
        refactoring=refactoring_list,
        api=summary_dict.get("api"),
    )
    
    # Run plugin hooks
    # We convert to dict to allow plugins to modify the response
    response_dict = response.dict()
    app.state.plugin_manager.hook_on_analyze(response_dict)
    
    return AnalyzeResponse(**response_dict)


@app.post("/run", response_model=RunResponse)
async def post_run(request: RunRequest, role: str = Depends(require_admin)) -> RunResponse:
    """Execute a command in the project root and return its output."""
    log_action(role, "run", request.command)
    # Check license
    app.state.meeting_adapter.validate_feature_access("run")

    # Check security config
    config = app.state.project_manager.config
    if not config.security.allow_run:
        raise HTTPException(status_code=403, detail="Run command is disabled by configuration.")
    
    if config.security.allowed_commands:
        cmd_str = " ".join(request.command)
        executable = request.command[0] if request.command else ""
        
        # Check if exact command string is allowed OR if the executable is allowed
        if cmd_str not in config.security.allowed_commands and executable not in config.security.allowed_commands:
             raise HTTPException(status_code=403, detail=f"Command '{cmd_str}' is not allowed by security policy.")

    if request.backend_name:
        connector = app.state.project_manager.get_connector(request.backend_name)
        if not connector:
            raise HTTPException(status_code=404, detail=f"Backend '{request.backend_name}' not found")
    else:
        connector = app.state.project_manager.get_default_connector()

    await manager.broadcast(JupiterEvent(type=RUN_STARTED, payload={"command": request.command}))

    try:
        result_dict = await connector.run_command(request.command, with_dynamic=request.with_dynamic)
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


@app.get("/health", response_model=HealthStatus)
async def get_health() -> HealthStatus:
    """Return the health status of the server."""
    return HealthStatus(status="ok", root=str(app.state.root_path))


@app.post("/config/root", response_model=RootUpdateResponse, dependencies=[Depends(require_admin)])
async def update_root(update: RootUpdate) -> RootUpdateResponse:
    """Update the project root path."""
    clean_path = update.path.strip('"\'')
    new_path = Path(clean_path)
    if not new_path.exists() or not new_path.is_dir():
        raise HTTPException(status_code=400, detail="Path does not exist or is not a directory")

    new_config = load_config(new_path)

    # Preserve Meeting configuration if not present in the new config
    # This allows keeping the license active when switching to a project without jupiter.yaml
    current_config = getattr(app.state.project_manager, "config", None)
    if current_config and current_config.meeting.deviceKey and not new_config.meeting.deviceKey:
        logger.info("Preserving Meeting configuration from previous root")
        new_config.meeting.deviceKey = current_config.meeting.deviceKey
        new_config.meeting.enabled = current_config.meeting.enabled

    app.state.root_path = new_path
    app.state.meeting_adapter.project_root = new_path
    # Update adapter key as well
    app.state.meeting_adapter.device_key = new_config.meeting.deviceKey

    if hasattr(app.state, "project_manager"):
        app.state.project_manager.refresh_for_root(new_config)
    else:
        app.state.project_manager = ProjectManager(new_config)

    plugin_manager = PluginManager(config=new_config.plugins)
    plugin_manager.discover_and_load()
    app.state.plugin_manager = plugin_manager

    save_last_root(new_path)

    app.state.history_manager = HistoryManager(new_path)

    logger.info("Updated project root to %s", new_path)
    await manager.broadcast(f"Project root changed to {new_path}")
    return RootUpdateResponse(status="ok", root=str(new_path))


@app.get("/me", dependencies=[Depends(verify_token)])
async def get_me(role: str = Depends(verify_token)):
    """Return current user information."""
    return {"role": role}


@app.get("/config", response_model=ConfigModel, dependencies=[Depends(verify_token)])
async def get_config() -> ConfigModel:
    """Get current configuration."""
    root = app.state.root_path
    install_path = getattr(app.state, "install_path", root)
    
    from jupiter.config.config import load_merged_config
    config = load_merged_config(install_path, root)
    
    # Debug log
    logger.info("Serving config: meeting_enabled=%s, device_key=%s", config.meeting.enabled, config.meeting.deviceKey)

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


@app.post("/config", response_model=ConfigModel)
async def update_config(new_config: ConfigModel, role: str = Depends(require_admin)) -> ConfigModel:
    """Update configuration."""
    log_action(role, "update_config", new_config.dict())
    root = app.state.root_path
    install_path = getattr(app.state, "install_path", root)
    
    from jupiter.config.config import load_merged_config, save_global_settings, save_project_settings
    
    # Load existing merged config to preserve fields not in ConfigModel
    current_config = load_merged_config(install_path, root)
    
    # Update object with new values
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
    
    # Performance
    current_config.performance.parallel_scan = new_config.perf_parallel_scan
    current_config.performance.max_workers = new_config.perf_max_workers
    current_config.performance.scan_timeout = new_config.perf_scan_timeout
    current_config.performance.graph_simplification = new_config.perf_graph_simplification
    current_config.performance.max_graph_nodes = new_config.perf_max_graph_nodes
    
    # Security
    current_config.security.allow_run = new_config.sec_allow_run

    # API Inspection
    from jupiter.config.config import ProjectApiConfig
    if not current_config.project_api:
        current_config.project_api = ProjectApiConfig()
    
    current_config.project_api.connector = new_config.api_connector
    current_config.project_api.app_var = new_config.api_app_var
    current_config.project_api.path = new_config.api_path
    
    try:
        # Save Global Settings to Install Path
        save_global_settings(current_config, install_path)
        
        # Save Project Settings to Project Path
        # Only if paths are different, otherwise save_global_settings already did part of it?
        # Actually save_global_settings only touches specific keys.
        # save_project_settings touches OTHER keys.
        # So we can call both safely even on same file.
        save_project_settings(current_config, root)
        
        # Update runtime state where applicable
        app.state.meeting_adapter.device_key = new_config.meeting_device_key
        
        # Refresh project manager to apply new settings (e.g. API connector)
        app.state.project_manager.refresh_for_root(current_config)

        await manager.broadcast(JupiterEvent(type=CONFIG_UPDATED, payload=new_config.dict()))
        return new_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {e}")


@app.get("/config/raw", response_model=RawConfigModel, dependencies=[Depends(require_admin)])
async def get_raw_config() -> RawConfigModel:
    """Get raw configuration file content."""
    root = app.state.root_path
    config_file = root / "jupiter.yaml"
    if not config_file.exists():
        return RawConfigModel(content="")
    try:
        return RawConfigModel(content=config_file.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read config file: {e}")


@app.post("/config/raw", response_model=RawConfigModel, dependencies=[Depends(require_admin)])
async def update_raw_config(raw_config: RawConfigModel) -> RawConfigModel:
    """Update raw configuration file content."""
    root = app.state.root_path
    config_file = root / "jupiter.yaml"
    try:
        config_file.write_text(raw_config.content, encoding="utf-8")
        return raw_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write config file: {e}")


@app.post("/update")
async def trigger_update(request: UpdateRequest, role: str = Depends(require_admin)) -> Dict[str, str]:
    """Trigger self-update."""
    log_action(role, "update_jupiter", request.source)
    # Check license
    app.state.meeting_adapter.validate_feature_access("update")
    
    try:
        apply_update(request.source, request.force)
        return {"status": "ok", "message": "Update applied successfully. Please restart."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users", response_model=List[UserModel], dependencies=[Depends(require_admin)])
async def get_users() -> List[UserModel]:
    """Get list of configured users."""
    root = app.state.root_path
    install_path = getattr(app.state, "install_path", root)
    from jupiter.config.config import load_merged_config
    config = load_merged_config(install_path, root)
    return [UserModel(name=u.name, token=u.token, role=u.role) for u in config.users]


@app.post("/users", response_model=List[UserModel], dependencies=[Depends(require_admin)])
async def add_user(user: UserModel, role: str = Depends(require_admin)) -> List[UserModel]:
    """Add or update a user."""
    log_action(role, "add_user", user.dict())
    root = app.state.root_path
    install_path = getattr(app.state, "install_path", root)
    from jupiter.config.config import load_merged_config, save_global_settings
    
    config = load_merged_config(install_path, root)
    
    # Update or append
    existing = next((u for u in config.users if u.name == user.name), None)
    if existing:
        existing.token = user.token
        existing.role = user.role
    else:
        config.users.append(UserConfig(name=user.name, token=user.token, role=user.role))
        
    save_global_settings(config, install_path)
    return [UserModel(name=u.name, token=u.token, role=u.role) for u in config.users]


@app.delete("/users/{name}", response_model=List[UserModel], dependencies=[Depends(require_admin)])
async def delete_user(name: str, role: str = Depends(require_admin)) -> List[UserModel]:
    """Delete a user."""
    log_action(role, "delete_user", {"name": name})
    root = app.state.root_path
    install_path = getattr(app.state, "install_path", root)
    from jupiter.config.config import load_merged_config, save_global_settings
    
    config = load_merged_config(install_path, root)
    config.users = [u for u in config.users if u.name != name]
    
    save_global_settings(config, install_path)
    return [UserModel(name=u.name, token=u.token, role=u.role) for u in config.users]


@app.post("/update/upload")
async def upload_update(file: UploadFile = File(...), role: str = Depends(require_admin)) -> Dict[str, str]:
    """Upload an update ZIP file."""
    log_action(role, "upload_update", {"filename": file.filename})
    import shutil
    import tempfile
    
    try:
        # Create a temp file
        fd, path = tempfile.mkstemp(suffix=".zip")
        with os.fdopen(fd, 'wb') as tmp:
            shutil.copyfileobj(file.file, tmp)
            
        return {"path": path, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {e}")


@app.get("/fs/list", response_model=FSListResponse, dependencies=[Depends(verify_token)])
async def list_fs(path: Optional[str] = None) -> FSListResponse:
    """List directories in the given path (or root if None)."""
    if path:
        # Strip quotes if present (Windows path issue)
        clean_path = path.strip('"\'')
        target_path = Path(clean_path)
    else:
        target_path = app.state.root_path

    if not target_path.exists() or not target_path.is_dir():
        # Fallback to root if invalid
        target_path = app.state.root_path

    entries = []
    try:
        # Parent directory navigation
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


@app.get("/reports/last", response_model=ScanReport, dependencies=[Depends(verify_token)])
async def get_last_report() -> ScanReport:
    """Return the cached report from the current root, if available."""
    root = app.state.root_path
    cache_manager = CacheManager(root)
    cached_report = cache_manager.load_last_scan()
    if not cached_report or not cached_report.get("files"):
        raise HTTPException(status_code=404, detail="No cached report available")

    files = [
        FileAnalysis(
            path=str(entry.get("path", "")),
            size_bytes=entry.get("size_bytes", 0),
            modified_timestamp=entry.get("modified_timestamp", 0.0),
            file_type=entry.get("file_type", "unknown"),
            language_analysis=entry.get("language_analysis"),
        )
        for entry in cached_report.get("files", [])
    ]

    plugin_manager = getattr(app.state, "plugin_manager", None)
    plugins = plugin_manager.get_plugins_info() if plugin_manager else []

    return ScanReport(
        report_schema_version=cached_report.get("report_schema_version", "1.0"),
        root=cached_report.get("root", str(root)),
        files=files,
        dynamic=cached_report.get("dynamic"),
        plugins=plugins,
    )


@app.get("/plugins", response_model=List[Dict[str, Any]], dependencies=[Depends(verify_token)])
async def get_plugins() -> List[Dict[str, Any]]:
    """Get list of all plugins."""
    pm: PluginManager = app.state.plugin_manager
    return pm.get_plugins_info()


@app.get("/backends", response_model=List[Dict[str, Any]], dependencies=[Depends(verify_token)])
async def get_backends() -> List[Dict[str, Any]]:
    """Get list of configured backends."""
    return app.state.project_manager.list_backends()


@app.post("/plugins/{name}/toggle")
async def toggle_plugin(name: str, enable: bool, role: str = Depends(require_admin)) -> Dict[str, bool]:
    """Enable or disable a plugin."""
    log_action(role, "toggle_plugin", {"name": name, "enable": enable})
    pm: PluginManager = app.state.plugin_manager
    if enable:
        pm.enable_plugin(name)
    else:
        pm.disable_plugin(name)
    
    await manager.broadcast(JupiterEvent(type=PLUGIN_TOGGLED, payload={"name": name, "enabled": enable}))
    return {"success": True, "enabled": pm.is_enabled(name)}


@app.post("/plugins/{name}/config")
async def configure_plugin(name: str, config: Dict[str, Any], role: str = Depends(require_admin)) -> Dict[str, bool]:
    """Configure a plugin."""
    log_action(role, "configure_plugin", {"name": name, "config": config})
    pm: PluginManager = app.state.plugin_manager
    pm.update_plugin_config(name, config)
    
    # Save config to disk
    try:
        project_manager = app.state.project_manager
        # Update the config object
        if project_manager.config:
            # Ensure settings dict exists
            if not hasattr(project_manager.config.plugins, "settings"):
                 # Should not happen if we updated PluginsConfig
                 pass
            project_manager.config.plugins.settings[name] = config
            
            # Save to disk
            from jupiter.config import save_config
            save_config(project_manager.config, app.state.root_path)
            
    except Exception as e:
        logger.error("Failed to save config: %s", e)
        # We don't fail the request if save fails, but we log it
        
    return {"success": True}


@app.get("/meeting/status", response_model=MeetingStatus)
async def get_meeting_status() -> MeetingStatus:
    """Return the status of the Meeting integration."""
    adapter: MeetingAdapter = app.state.meeting_adapter
    status_dict = adapter.check_license()

    return MeetingStatus(
        device_key=status_dict.get("device_key"),
        is_licensed=status_dict.get("is_licensed", False),
        session_active=status_dict.get("session_active", False),
        session_remaining_seconds=status_dict.get("session_remaining_seconds"),
        status=status_dict.get("status", "unknown"),
        message=status_dict.get("message"),
    )


@app.post("/init")
async def init_project() -> Dict[str, str]:
    """Initialize a new Jupiter project with default config."""
    root = app.state.root_path
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


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, token: Optional[str] = None):
    # Check security token
    try:
        config = app.state.project_manager.config
        if config.security.token:
            if token != config.security.token:
                await websocket.close(code=1008, reason="Invalid authentication token")
                return
    except AttributeError:
        pass

    # Check license for watch/realtime features
    try:
        app.state.meeting_adapter.validate_feature_access("watch")
    except MeetingError as e:
        await websocket.close(code=1008, reason=str(e))
        return

    await websocket_endpoint(websocket)



@dataclass
class JupiterAPIServer:
    """Server that runs the Jupiter FastAPI application."""

    root: Path
    host: str = "127.0.0.1"
    port: int = 8000
    device_key: Optional[str] = None
    plugins_config: Optional[PluginsConfig] = None
    config: Optional[JupiterConfig] = None
    install_path: Optional[Path] = None

    def start(self) -> None:
        """Start the API server using uvicorn."""
        app.state.root_path = self.root
        app.state.install_path = self.install_path or self.root
        save_last_root(self.root)
        app.state.meeting_adapter = MeetingAdapter(
            device_key=self.device_key,
            project_root=self.root
        )
        app.state.history_manager = HistoryManager(self.root)
        
        # Initialize ProjectManager
        if self.config:
            app.state.project_manager = ProjectManager(self.config)
        else:
            # Fallback if config not passed (should not happen in normal flow)
            # We load it here or create a default one
            logger.warning("JupiterConfig not passed to API Server, loading from root")
            from jupiter.config import load_config
            app.state.project_manager = ProjectManager(load_config(self.root))

        # Initialize plugins
        plugin_manager = PluginManager(config=self.plugins_config)
        plugin_manager.discover_and_load()
        app.state.plugin_manager = plugin_manager
        logger.info("Loaded %d plugins", len(plugin_manager.plugins))

        logger.info("Starting Jupiter API server on %s:%s for root %s", self.host, self.port, self.root)
        try:
            uvicorn.run(
                app,
                host=self.host,
                port=self.port,
                log_level="info",
            )
        except Exception as e:
            logger.error("Server crashed: %s", e)
            raise

    def stop(self) -> None:
        """Stop the API server."""
        logger.info("Stopping Jupiter API server is handled by Uvicorn (e.g., Ctrl+C).")