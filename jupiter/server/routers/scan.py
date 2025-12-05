"""
Scan router for Jupiter API.

Version: 1.3.1
"""
import asyncio
import logging
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
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


# =============================================================================
# Background Scan State Management
# =============================================================================

class ScanStatus(str, Enum):
    """Status of a background scan job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BackgroundScanJob:
    """Represents a background scan job."""
    
    def __init__(self, job_id: str, options: ScanRequest):
        self.job_id = job_id
        self.options = options
        self.status = ScanStatus.PENDING
        self.started_at: Optional[float] = None
        self.finished_at: Optional[float] = None
        self.progress: int = 0
        self.files_processed: int = 0
        self.files_total: int = 0
        self.current_file: Optional[str] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "progress": self.progress,
            "files_processed": self.files_processed,
            "files_total": self.files_total,
            "current_file": self.current_file,
            "error": self.error,
            "duration_ms": int((self.finished_at - self.started_at) * 1000) if self.started_at and self.finished_at else None,
        }


# Global storage for background scan jobs (in production, use Redis or similar)
_background_jobs: Dict[str, BackgroundScanJob] = {}
_current_scan_job: Optional[str] = None  # Track if a scan is already running


def get_background_job(job_id: str) -> Optional[BackgroundScanJob]:
    """Get a background scan job by ID."""
    return _background_jobs.get(job_id)


def get_current_scan() -> Optional[BackgroundScanJob]:
    """Get the currently running scan job, if any."""
    if _current_scan_job:
        return _background_jobs.get(_current_scan_job)
    return None

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


# =============================================================================
# Background Scan Endpoints
# =============================================================================

# Store reference to running scan task
_scan_task: Optional[asyncio.Task] = None

async def _run_background_scan(app, job: BackgroundScanJob):
    """Execute scan in background and update job status."""
    global _current_scan_job
    
    root = app.state.root_path.resolve()
    cache_manager = CacheManager(root)
    
    job.status = ScanStatus.RUNNING
    job.started_at = time.time()
    _current_scan_job = job.job_id
    
    # Notify via WebSocket that scan started
    try:
        await manager.broadcast(JupiterEvent(type=SCAN_STARTED, payload={
            "root": str(root), 
            "options": job.options.dict(),
            "job_id": job.job_id,
            "background": True
        }))
    except Exception as e:
        logger.warning("Failed to broadcast scan started: %s", e)
    emit_scan_started(str(root), job.options.dict())
    
    try:
        # Get connector
        if job.options.backend_name:
            connector = app.state.project_manager.get_connector(job.options.backend_name)
            if not connector:
                raise ValueError(f"Backend '{job.options.backend_name}' not found")
        else:
            connector = app.state.project_manager.get_default_connector()
        
        # Create progress callback that updates job status
        # Note: This callback runs in a thread, so we need to be careful with async
        def progress_callback(event_type: str, payload: Dict[str, Any]):
            if event_type == "SCAN_PROGRESS":
                job.files_total = payload.get("total_files", 0)
                job.files_processed = payload.get("processed", 0)
                job.progress = payload.get("percent", 0)
            elif event_type == "SCAN_FILE_COMPLETED":
                job.current_file = payload.get("file")
                job.files_processed = payload.get("processed", 0)
                job.files_total = payload.get("total", 0)
                job.progress = payload.get("percent", 0)
            
            # Schedule WebSocket broadcast in the event loop (thread-safe)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        manager.broadcast(JupiterEvent(
                            type="SCAN_PROGRESS",
                            payload={"job_id": job.job_id, **payload}
                        )),
                        loop
                    )
            except Exception:
                pass  # Ignore broadcast errors in callback
        
        if hasattr(connector, 'set_progress_callback'):
            connector.set_progress_callback(progress_callback)
        
        scan_options = {
            "show_hidden": job.options.show_hidden,
            "ignore_globs": job.options.ignore_globs,
            "incremental": job.options.incremental,
        }
        
        if not scan_options["ignore_globs"]:
            active_project = app.state.project_manager.get_active_project()
            if active_project:
                scan_options["ignore_globs"] = active_project.ignore_globs
        
        # Run the scan
        report_dict = await connector.scan(scan_options)
        
        # Process results
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
        
        # Build report for plugins
        report_for_plugins = {
            "report_schema_version": report_dict.get("report_schema_version", "1.0"),
            "root": report_dict["root"],
            "files": report_dict["files"],
            "dynamic": report_dict.get("dynamic"),
            "plugins": app.state.plugin_manager.get_plugins_info(),
            "quality": report_dict.get("quality"),
            "refactoring": report_dict.get("refactoring"),
            "project_path": str(root),
        }
        
        app.state.plugin_manager.hook_on_scan(report_for_plugins, project_root=root)
        
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
        
        # Get API info if available
        if hasattr(connector, "get_api_info"):
            try:
                api_info = await connector.get_api_info()
                if api_info:
                    report.api = api_info
            except Exception as e:
                logger.warning("Failed to fetch API info during background scan: %s", e)
        
        # Save to cache
        try:
            cache_manager.save_last_scan(report.dict())
        except Exception as exc:
            logger.warning("Failed to persist last scan cache: %s", exc)
        
        # Create snapshot if requested
        if job.options.capture_snapshot:
            try:
                metadata = SystemState(app).history_manager().create_snapshot(
                    report_dict,
                    label=job.options.snapshot_label,
                    backend_name=job.options.backend_name,
                )
                await manager.broadcast(f"Snapshot stored: {metadata.id}")
            except Exception as exc:
                logger.warning("Failed to store snapshot: %s", exc)
        
        # Update job status
        job.status = ScanStatus.COMPLETED
        job.finished_at = time.time()
        job.progress = 100
        job.result = report.dict()
        
        duration_ms = int((job.finished_at - job.started_at) * 1000)
        
        # Notify completion
        try:
            await manager.broadcast(JupiterEvent(type=SCAN_FINISHED, payload={
                "job_id": job.job_id,
                "file_count": len(report.files),
                "duration_ms": duration_ms,
                "background": True
            }))
            await manager.broadcast(f"Background scan completed. Found {len(file_models)} files in {duration_ms}ms.")
        except Exception as e:
            logger.warning("Failed to broadcast scan finished: %s", e)
        emit_scan_finished(str(root), len(report.files), duration_ms)
        
    except Exception as e:
        logger.error("Background scan failed: %s", e)
        job.status = ScanStatus.FAILED
        job.finished_at = time.time()
        job.error = str(e)
        emit_scan_error(str(root), str(e))
        try:
            await manager.broadcast(JupiterEvent(type="SCAN_ERROR", payload={
                "job_id": job.job_id,
                "error": str(e)
            }))
        except Exception:
            pass
    finally:
        _current_scan_job = None


@router.post("/scan/background", dependencies=[Depends(verify_token)])
async def post_scan_background(request: Request, options: ScanRequest) -> Dict[str, Any]:
    """
    Start a scan in the background and return immediately with a job ID.
    
    Use GET /scan/status/{job_id} to check progress.
    Progress updates are also broadcast via WebSocket.
    """
    global _scan_task
    
    # Check if a scan is already running
    current = get_current_scan()
    if current and current.status == ScanStatus.RUNNING:
        raise HTTPException(
            status_code=409, 
            detail=f"A scan is already running (job_id: {current.job_id}). Wait for it to complete or check its status."
        )
    
    # Create new job
    job_id = str(uuid.uuid4())[:8]  # Short ID for convenience
    job = BackgroundScanJob(job_id, options)
    _background_jobs[job_id] = job
    
    # Clean old completed jobs (keep last 10)
    completed_jobs = [j for j in _background_jobs.values() if j.status in (ScanStatus.COMPLETED, ScanStatus.FAILED)]
    if len(completed_jobs) > 10:
        for old_job in sorted(completed_jobs, key=lambda x: x.finished_at or 0)[:len(completed_jobs) - 10]:
            del _background_jobs[old_job.job_id]
    
    # Start background task using asyncio.create_task (runs in the same event loop)
    _scan_task = asyncio.create_task(_run_background_scan(request.app, job))
    
    logger.info("Started background scan job: %s", job_id)
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Scan started in background. Use /scan/status/{job_id} to check progress."
    }


@router.get("/scan/status/{job_id}", dependencies=[Depends(verify_token)])
async def get_scan_status(job_id: str) -> Dict[str, Any]:
    """Get the status of a background scan job."""
    job = get_background_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Scan job '{job_id}' not found")
    
    return job.to_dict()


@router.get("/scan/status", dependencies=[Depends(verify_token)])
async def get_current_scan_status() -> Dict[str, Any]:
    """Get the status of the currently running scan, if any."""
    current = get_current_scan()
    if current:
        return {
            "running": True,
            **current.to_dict()
        }
    return {
        "running": False,
        "message": "No scan currently running"
    }


@router.get("/scan/result/{job_id}", response_model=ScanReport, dependencies=[Depends(verify_token)])
async def get_scan_result(job_id: str) -> ScanReport:
    """Get the result of a completed background scan job."""
    job = get_background_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Scan job '{job_id}' not found")
    
    if job.status == ScanStatus.PENDING:
        raise HTTPException(status_code=202, detail="Scan job is pending")
    
    if job.status == ScanStatus.RUNNING:
        raise HTTPException(status_code=202, detail=f"Scan job is still running ({job.progress}% complete)")
    
    if job.status == ScanStatus.FAILED:
        raise HTTPException(status_code=500, detail=f"Scan job failed: {job.error}")
    
    if not job.result:
        raise HTTPException(status_code=500, detail="Scan completed but no result available")
    
    return ScanReport(**job.result)


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
