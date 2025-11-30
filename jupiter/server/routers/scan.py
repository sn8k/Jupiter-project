import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from jupiter.server.models import ScanRequest, ScanReport, FileAnalysis
from jupiter.server.routers.auth import verify_token
from jupiter.core.events import JupiterEvent, SCAN_STARTED, SCAN_FINISHED
from jupiter.core.cache import CacheManager
from jupiter.server.ws import manager
from jupiter.server.system_services import SystemState

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/scan", response_model=ScanReport, dependencies=[Depends(verify_token)])
async def post_scan(request: Request, options: ScanRequest) -> ScanReport:
    """Run a filesystem scan and return a JSON report."""
    app = request.app
    root = app.state.root_path.resolve()
    logger.info("Scanning project at %s with options: %s", root, options)

    cache_manager = CacheManager(root)

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
    # Apply default ignore globs from active project if none provided
    if not scan_options["ignore_globs"]:
        active_project = app.state.project_manager.get_active_project()
        if active_project:
            scan_options["ignore_globs"] = active_project.ignore_globs

    try:
        report_dict = await connector.scan(scan_options)
    except Exception as e:
        logger.error("Scan failed: %s", e)
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


@router.get("/reports/last", response_model=ScanReport, dependencies=[Depends(verify_token)])
async def get_last_report(request: Request) -> ScanReport:
    """Retrieve the last scan report from cache."""
    cache_manager = CacheManager(request.app.state.root_path)
    report_dict = cache_manager.load_last_scan()
    if not report_dict:
        raise HTTPException(status_code=404, detail="No previous scan report found")
    
    return ScanReport(**report_dict)
