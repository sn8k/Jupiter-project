"""
Scan router for Jupiter API.

Version: 1.2.0
"""
import logging
import time
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Request
from jupiter.server.models import ScanRequest, ScanReport, FileAnalysis
from jupiter.server.routers.auth import verify_token
from jupiter.core.events import JupiterEvent, SCAN_STARTED, SCAN_FINISHED
from jupiter.core.cache import CacheManager
from jupiter.server.ws import manager
from jupiter.server.system_services import SystemState
from jupiter.server.routers.watch import create_scan_progress_callback, get_watch_state

# Bridge event system for plugin notifications
from jupiter.core.bridge import emit_scan_started, emit_scan_finished, emit_scan_error

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/scan", response_model=ScanReport, dependencies=[Depends(verify_token)])
async def post_scan(request: Request, options: ScanRequest) -> ScanReport:
    """Run a filesystem scan and return a JSON report."""
    app = request.app
    root = app.state.root_path.resolve()
    logger.info("Scanning project at %s with options: %s", root, options)

    cache_manager = CacheManager(root)
    start_time = time.time()

    # Emit via both WebSocket and Bridge event system
    await manager.broadcast(JupiterEvent(type=SCAN_STARTED, payload={"root": str(root), "options": options.dict()}))
    emit_scan_started(str(root), options.dict())

    if options.backend_name:
        connector = app.state.project_manager.get_connector(options.backend_name)
        if not connector:
            raise HTTPException(status_code=404, detail=f"Backend '{options.backend_name}' not found")
    else:
        connector = app.state.project_manager.get_default_connector()
    
    # Set up progress callback if watch is active
    watch_state = get_watch_state()
    if watch_state.active and hasattr(connector, 'set_progress_callback'):
        progress_callback = create_scan_progress_callback()
        connector.set_progress_callback(progress_callback)
    
    scan_options = {
        "show_hidden": options.show_hidden,
        "ignore_globs": options.ignore_globs,
        "incremental": options.incremental,
    }
    # Apply default ignore globs from active project if none provided
    if not scan_options["ignore_globs"]:
        active_project = app.state.project_manager.get_active_project()
        if active_project:
            scan_options["ignore_globs"] = active_project.ignore_globs

    try:
        report_dict = await connector.scan(scan_options)
    except Exception as e:
        logger.error("Scan failed: %s", e)
        # Emit scan error via Bridge event system
        emit_scan_error(str(root), str(e))
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")
    
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

    # Build report dict for plugin hooks
    report_for_plugins = {
        "report_schema_version": report_dict.get("report_schema_version", "1.0"),
        "root": report_dict["root"],
        "files": report_dict["files"],
        "dynamic": report_dict.get("dynamic"),
        "plugins": app.state.plugin_manager.get_plugins_info(),
        "quality": report_dict.get("quality"),
        "refactoring": report_dict.get("refactoring"),
        "project_path": str(root),  # Add project path for plugins
    }

    # Run plugin hooks - plugins enrich the report dict in place
    app.state.plugin_manager.hook_on_scan(report_for_plugins, project_root=root)

    # Now build the response model with enriched data
    report = ScanReport(
        report_schema_version=report_for_plugins.get("report_schema_version", "1.0"),
        root=report_for_plugins["root"],
        files=file_models,
        dynamic=report_for_plugins.get("dynamic"),
        plugins=report_for_plugins.get("plugins"),
        quality=report_for_plugins.get("quality"),
        refactoring=report_for_plugins.get("refactoring"),
        pylance=report_for_plugins.get("pylance"),
        code_quality=report_for_plugins.get("code_quality"),
    )

    # Enrich with API info if available (for ScanReport)
    if hasattr(connector, "get_api_info"):
        try:
            api_info = await connector.get_api_info()
            if api_info:
                report.api = api_info
        except Exception as e:
            logger.warning("Failed to fetch API info during scan: %s", e)

    await manager.broadcast(JupiterEvent(type=SCAN_FINISHED, payload={"file_count": len(report.files)}))

    # Emit scan finished via Bridge event system
    duration_ms = int((time.time() - start_time) * 1000)
    emit_scan_finished(str(root), len(report.files), duration_ms)

    try:
        cache_manager.save_last_scan(report.dict())
    except Exception as exc:  # pragma: no cover - logging only
        logger.warning("Failed to persist last scan cache: %s", exc)

    if options.capture_snapshot:
        try:
            metadata = SystemState(app).history_manager().create_snapshot(
                report_dict,
                label=options.snapshot_label,
                backend_name=options.backend_name,
            )
            await manager.broadcast(f"Snapshot stored: {metadata.id}")
        except Exception as exc:  # pragma: no cover - logging only
            logger.warning("Failed to store snapshot: %s", exc)

    await manager.broadcast(f"Scan completed. Found {len(file_models)} files.")

    return report


@router.get("/api/endpoints", dependencies=[Depends(verify_token)])
async def get_api_endpoints(request: Request) -> Dict[str, Any]:
    """
    Fetch API endpoints from the configured connector without a full scan.
    
    Phase 2 enhancement: Also includes handler function names and modules
    for autodiag introspection.
    """
    app = request.app
    pm = getattr(app.state, "project_manager", None)
    if not pm:
        return {"endpoints": [], "config": None, "handlers": []}
    
    connector = pm.get_connector("local")
    if not connector:
        return {"endpoints": [], "config": None, "handlers": []}
    
    result: Dict[str, Any] = {"endpoints": [], "config": None, "handlers": []}
    
    if hasattr(connector, "get_api_info"):
        try:
            api_info = await connector.get_api_info()
            if api_info:
                result["endpoints"] = api_info.get("endpoints", [])
                result["config"] = api_info.get("config")
        except Exception as e:
            logger.warning("Failed to fetch API endpoints: %s", e)
            result["error"] = str(e)
    
    # Phase 2: Add handler introspection for Jupiter's own API
    result["handlers"] = get_registered_handlers(app)
    
    return result


def get_registered_handlers(app) -> List[Dict[str, Any]]:
    """
    Extract all registered route handlers from the FastAPI app.
    
    Returns a list of handler info including:
    - path: The route path
    - methods: HTTP methods
    - handler_name: Function name
    - handler_module: Module where handler is defined
    - handler_qualname: Qualified name (includes class if method)
    """
    handlers: List[Dict[str, Any]] = []
    
    for route in app.routes:
        if not hasattr(route, "endpoint"):
            continue
        
        endpoint = route.endpoint
        handler_info = {
            "path": getattr(route, "path", None),
            "name": getattr(route, "name", None),
            "methods": sorted(list(getattr(route, "methods", []))) if hasattr(route, "methods") else [],
            "handler_name": getattr(endpoint, "__name__", str(endpoint)),
            "handler_module": getattr(endpoint, "__module__", "unknown"),
            "handler_qualname": getattr(endpoint, "__qualname__", getattr(endpoint, "__name__", str(endpoint))),
        }
        handlers.append(handler_info)
    
    return handlers


@router.get("/reports/last", response_model=ScanReport, dependencies=[Depends(verify_token)])
async def get_last_report(request: Request) -> ScanReport:
    """Retrieve the last scan report from cache."""
    cache_manager = CacheManager(request.app.state.root_path)
    report_dict = cache_manager.load_last_scan()
    if not report_dict:
        raise HTTPException(status_code=404, detail="No previous scan report found")
    
    return ScanReport(**report_dict)
