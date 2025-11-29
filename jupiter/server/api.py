"""Lightweight API server using FastAPI."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any

import uvicorn
from fastapi import FastAPI, WebSocket, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from jupiter.core import ProjectAnalyzer, ProjectScanner
from jupiter.core.runner import run_command
from jupiter.core.exceptions import JupiterError, ScanError, AnalyzeError, RunError, MeetingError
from jupiter.core.cache import CacheManager
from jupiter.core.plugin_manager import PluginManager
from jupiter.core.state import save_last_root
from jupiter.core.updater import apply_update
from jupiter.config import load_config, save_config, JupiterConfig, PluginsConfig
from jupiter.server.manager import ProjectManager
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
    UpdateRequest,
    FileAnalysis,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Jupiter API",
    description="API for scanning and analyzing projects.",
    version="1.0",
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

async def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)):
    """Verify the authentication token if configured."""
    try:
        config = app.state.project_manager.config
    except AttributeError:
        # Should not happen if server started correctly
        return

    token = config.security.token
    if not token:
        return

    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authentication token")
    
    if credentials.credentials != token:
        raise HTTPException(status_code=401, detail="Invalid authentication token")


@app.post("/scan", response_model=ScanReport)
async def post_scan(options: ScanRequest) -> ScanReport:
    """Run a filesystem scan and return a JSON report."""
    root = app.state.root_path.resolve()
    logger.info("Scanning project at %s with options: %s", root, options)

    await manager.broadcast(f"Scan started for {root}")

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
    )

    # Run plugin hooks
    app.state.plugin_manager.hook_on_scan(report.dict())

    # Save to cache (Connector might have done it, but we ensure it here for API consistency if needed)
    # cache_manager = CacheManager(root)
    # cache_manager.save_last_scan(report.dict())

    await manager.broadcast(f"Scan completed. Found {len(file_models)} files.")

    return report

@app.get("/analyze", response_model=AnalyzeResponse)
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
    )
    
    # Run plugin hooks
    app.state.plugin_manager.hook_on_analyze(response.dict())
    
    return response


@app.post("/run", response_model=RunResponse, dependencies=[Depends(verify_token)])
async def post_run(request: RunRequest) -> RunResponse:
    """Execute a command in the project root and return its output."""
    # Check license
    app.state.meeting_adapter.validate_feature_access("run")

    if request.backend_name:
        connector = app.state.project_manager.get_connector(request.backend_name)
        if not connector:
            raise HTTPException(status_code=404, detail=f"Backend '{request.backend_name}' not found")
    else:
        connector = app.state.project_manager.get_default_connector()

    try:
        result_dict = await connector.run_command(request.command, with_dynamic=request.with_dynamic)
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


@app.post("/config/root", response_model=RootUpdateResponse, dependencies=[Depends(verify_token)])
async def update_root(update: RootUpdate) -> RootUpdateResponse:
    """Update the project root path."""
    clean_path = update.path.strip('"\'')
    new_path = Path(clean_path)
    if not new_path.exists() or not new_path.is_dir():
        raise HTTPException(status_code=400, detail="Path does not exist or is not a directory")

    new_config = load_config(new_path)

    app.state.root_path = new_path
    app.state.meeting_adapter.project_root = new_path

    if hasattr(app.state, "project_manager"):
        app.state.project_manager.refresh_for_root(new_config)
    else:
        app.state.project_manager = ProjectManager(new_config)

    plugin_manager = PluginManager(config=new_config.plugins)
    plugin_manager.discover_and_load()
    app.state.plugin_manager = plugin_manager

    save_last_root(new_path)

    logger.info("Updated project root to %s", new_path)
    await manager.broadcast(f"Project root changed to {new_path}")
    return RootUpdateResponse(status="ok", root=str(new_path))


@app.get("/config", response_model=ConfigModel)
async def get_config() -> ConfigModel:
    """Get current configuration."""
    root = app.state.root_path
    config = load_config(root)
    
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
    )


@app.post("/config", response_model=ConfigModel, dependencies=[Depends(verify_token)])
async def update_config(new_config: ConfigModel) -> ConfigModel:
    """Update configuration."""
    root = app.state.root_path
    
    # Load existing to preserve other fields if any (though we overwrite mostly)
    current_config = load_config(root)
    
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
    
    try:
        save_config(current_config, root)
        
        # Update runtime state where applicable
        app.state.meeting_adapter.device_key = new_config.meeting_device_key
        
        return new_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {e}")


@app.post("/update", dependencies=[Depends(verify_token)])
async def trigger_update(request: UpdateRequest) -> Dict[str, str]:
    """Trigger self-update."""
    # Check license
    app.state.meeting_adapter.validate_feature_access("update")
    
    try:
        apply_update(request.source, request.force)
        return {"status": "ok", "message": "Update applied successfully. Please restart."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/fs/list", response_model=FSListResponse)
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


@app.get("/reports/last", response_model=ScanReport)
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


@app.get("/plugins", response_model=List[Dict[str, Any]])
async def get_plugins() -> List[Dict[str, Any]]:
    """Get list of all plugins."""
    pm: PluginManager = app.state.plugin_manager
    return pm.get_plugins_info()


@app.get("/backends", response_model=List[Dict[str, Any]])
async def get_backends() -> List[Dict[str, Any]]:
    """Get list of configured backends."""
    return app.state.project_manager.list_backends()


@app.post("/plugins/{name}/toggle", dependencies=[Depends(verify_token)])
async def toggle_plugin(name: str, enable: bool) -> Dict[str, bool]:
    """Enable or disable a plugin."""
    pm: PluginManager = app.state.plugin_manager
    if enable:
        pm.enable_plugin(name)
    else:
        pm.disable_plugin(name)
    return {"enabled": pm.is_enabled(name)}


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

    def start(self) -> None:
        """Start the API server using uvicorn."""
        app.state.root_path = self.root
        save_last_root(self.root)
        app.state.meeting_adapter = MeetingAdapter(
            device_key=self.device_key,
            project_root=self.root
        )
        
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
        uvicorn.run(
            app,
            host=self.host,
            port=self.port,
            log_level="info",
        )

    def stop(self) -> None:
        """Stop the API server."""
        logger.info("Stopping Jupiter API server is handled by Uvicorn (e.g., Ctrl+C).")