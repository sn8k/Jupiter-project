import logging
from typing import Optional, List, Dict, Any
from dataclasses import asdict
from fastapi import APIRouter, Depends, HTTPException, Request
from jupiter.server.models import (
    AnalyzeResponse, 
    Hotspot, 
    PythonProjectSummary, 
    RefactoringRecommendation,
    SnapshotListResponse,
    SnapshotResponse,
    SnapshotDiffResponse,
    SnapshotMetadataModel,
    SimulateRequest,
    SimulateResponse,
    ImpactModel,
)
from jupiter.server.routers.auth import verify_token
from jupiter.core.history import HistoryManager
from jupiter.core.cache import CacheManager
from jupiter.core.simulator import ProjectSimulator
from jupiter.core.graph import GraphBuilder

logger = logging.getLogger(__name__)
router = APIRouter()

def _history_manager(app) -> HistoryManager:
    manager = getattr(app.state, "history_manager", None)
    if manager is None:
        manager = HistoryManager(app.state.root_path)
        app.state.history_manager = manager
    return manager

@router.get("/analyze", response_model=AnalyzeResponse, dependencies=[Depends(verify_token)])
async def get_analyze(
    request: Request,
    top: int = 5, 
    show_hidden: bool = False, 
    ignore_globs: Optional[List[str]] = None,
    backend_name: Optional[str] = None
) -> AnalyzeResponse:
    """Scan and analyze a project, returning a summary."""
    app = request.app
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

@router.get("/snapshots", response_model=SnapshotListResponse, dependencies=[Depends(verify_token)])
async def get_snapshots(request: Request) -> SnapshotListResponse:
    history = _history_manager(request.app)
    entries = [SnapshotMetadataModel(**asdict(meta)) for meta in history.list_snapshots()]
    return SnapshotListResponse(snapshots=entries)


@router.get("/snapshots/diff", response_model=SnapshotDiffResponse, dependencies=[Depends(verify_token)])
async def diff_snapshots(request: Request, id_a: str, id_b: str) -> SnapshotDiffResponse:
    try:
        diff = _history_manager(request.app).compare_snapshots(id_a, id_b).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return SnapshotDiffResponse(**diff)


@router.get("/snapshots/{snapshot_id}", response_model=SnapshotResponse, dependencies=[Depends(verify_token)])
async def get_snapshot(request: Request, snapshot_id: str) -> SnapshotResponse:
    snapshot = _history_manager(request.app).get_snapshot(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    metadata = SnapshotMetadataModel(**snapshot["metadata"])
    return SnapshotResponse(metadata=metadata, report=snapshot["report"])


@router.post("/simulate/remove", response_model=SimulateResponse)
async def simulate_remove(request: Request, sim_req: SimulateRequest) -> SimulateResponse:
    """Simulate the removal of a file or function."""
    # We need the current scan state. We can load it from cache.
    root = request.app.state.root_path
    cache_manager = CacheManager(root)
    last_scan = cache_manager.load_last_scan()
    
    if not last_scan or "files" not in last_scan:
        raise HTTPException(status_code=400, detail="No scan data available. Please run a scan first.")
        
    simulator = ProjectSimulator(last_scan["files"])
    
    if sim_req.target_type == "file":
        result = simulator.simulate_remove_file(sim_req.path)
    elif sim_req.target_type == "function":
        if not sim_req.function_name:
            raise HTTPException(status_code=400, detail="function_name is required for function target")
        result = simulator.simulate_remove_function(sim_req.path, sim_req.function_name)
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


@router.get("/graph", dependencies=[Depends(verify_token)])
async def get_graph(
    request: Request,
    backend_name: Optional[str] = None,
    simplify: bool = False,
    max_nodes: int = 1000
) -> Dict[str, Any]:
    """Generate a dependency graph for the project."""
    # We try to use the cached scan first for speed
    app = request.app
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
