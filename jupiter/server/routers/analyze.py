"""Analysis and CI router for Jupiter API.

Version: 1.0.1
"""

import logging
from typing import Optional, List, Dict, Any, cast
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
    CIRequest,
    CIResponse,
    CIMetrics,
    CIThresholds,
)
from jupiter.server.routers.auth import verify_token
from jupiter.core.cache import CacheManager
from jupiter.core.simulator import ProjectSimulator
from jupiter.core.graph import GraphBuilder
from jupiter.server.system_services import SystemState

logger = logging.getLogger(__name__)
router = APIRouter()

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
    if not analyze_options["ignore_globs"]:
        active_project = app.state.project_manager.get_active_project()
        if active_project:
            analyze_options["ignore_globs"] = active_project.ignore_globs
    
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
            severity=r["severity"],
            locations=r.get("locations"),
            code_excerpt=r.get("code_excerpt")
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
    app.state.plugin_manager.hook_on_analyze(response_dict, project_root=root)
    
    return AnalyzeResponse(**response_dict)


@router.post("/ci", response_model=CIResponse, dependencies=[Depends(verify_token)])
async def run_ci_check(request: Request, ci_req: Optional[CIRequest] = None) -> CIResponse:
    """Run CI quality gates analysis.
    
    Analyzes the project and checks against configured thresholds for:
    - Maximum cyclomatic complexity
    - Number of duplication clusters
    - Number of potentially unused functions
    
    Returns pass/fail status with detailed metrics.
    """
    if ci_req is None:
        ci_req = CIRequest(
            fail_on_complexity=None,
            fail_on_duplication=None,
            fail_on_unused=None,
            backend_name=None
        )
    
    app = request.app
    root = app.state.root_path
    logger.info("Running CI analysis on %s", root)
    
    # Get connector
    if ci_req.backend_name:
        connector = app.state.project_manager.get_connector(ci_req.backend_name)
        if not connector:
            raise HTTPException(status_code=404, detail=f"Backend '{ci_req.backend_name}' not found")
    else:
        connector = app.state.project_manager.get_default_connector()
    
    # Run analysis
    try:
        summary_dict = await connector.analyze({"top": 10, "show_hidden": False})
    except Exception as e:
        logger.error("CI analysis failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
    # Run plugin hooks to enrich with quality data
    app.state.plugin_manager.hook_on_analyze(summary_dict, project_root=root)
    
    # Get thresholds from config
    config = app.state.project_manager.config
    base_thresholds: Dict[str, Optional[int]] = {}
    if config and config.ci:
        base_thresholds = config.ci.fail_on.copy()
    
    # Apply overrides from request
    if ci_req.fail_on_complexity is not None:
        base_thresholds["max_complexity"] = ci_req.fail_on_complexity
    if ci_req.fail_on_duplication is not None:
        base_thresholds["max_duplication_clusters"] = ci_req.fail_on_duplication
    if ci_req.fail_on_unused is not None:
        base_thresholds["max_unused_functions"] = ci_req.fail_on_unused
    
    # Calculate metrics
    max_complexity = 0
    quality = summary_dict.get("quality") or {}
    complexity_per_file = quality.get("complexity_per_file", [])
    for item in complexity_per_file:
        score = item.get("score", 0)
        if score > max_complexity:
            max_complexity = score
    
    duplication_clusters = quality.get("duplication_clusters", [])
    duplication_count = len(duplication_clusters)
    
    python_summary = summary_dict.get("python_summary") or {}
    unused_count = python_summary.get("total_potentially_unused_functions", 0)
    
    # Evaluate thresholds
    failures: List[str] = []
    
    limit_complexity = base_thresholds.get("max_complexity")
    if limit_complexity is not None and max_complexity > limit_complexity:
        failures.append(f"Max complexity {max_complexity} exceeds limit {limit_complexity}")
    
    limit_duplication = base_thresholds.get("max_duplication_clusters")
    if limit_duplication is not None and duplication_count > limit_duplication:
        failures.append(f"Duplication clusters {duplication_count} exceeds limit {limit_duplication}")
    
    limit_unused = base_thresholds.get("max_unused_functions")
    if limit_unused is not None and unused_count > limit_unused:
        failures.append(f"Unused functions {unused_count} exceeds limit {limit_unused}")
    
    return CIResponse(
        status="failed" if failures else "passed",
        failures=failures,
        metrics=CIMetrics(
            max_complexity=max_complexity,
            duplication_clusters=duplication_count,
            unused_functions=unused_count,
        ),
        thresholds=CIThresholds(
            max_complexity=base_thresholds.get("max_complexity"),
            max_duplication_clusters=base_thresholds.get("max_duplication_clusters"),
            max_unused_functions=base_thresholds.get("max_unused_functions"),
        ),
        summary=summary_dict,
    )


@router.get("/snapshots", response_model=SnapshotListResponse, dependencies=[Depends(verify_token)])
async def get_snapshots(request: Request) -> SnapshotListResponse:
    history = SystemState(request.app).history_manager()
    entries = [SnapshotMetadataModel(**asdict(meta)) for meta in history.list_snapshots()]
    return SnapshotListResponse(snapshots=entries)


@router.get("/snapshots/diff", response_model=SnapshotDiffResponse, dependencies=[Depends(verify_token)])
async def diff_snapshots(request: Request, id_a: str, id_b: str) -> SnapshotDiffResponse:
    try:
        diff = SystemState(request.app).history_manager().compare_snapshots(id_a, id_b).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return SnapshotDiffResponse(**diff)


@router.get("/snapshots/{snapshot_id}", response_model=SnapshotResponse, dependencies=[Depends(verify_token)])
async def get_snapshot(request: Request, snapshot_id: str) -> SnapshotResponse:
    snapshot = SystemState(request.app).history_manager().get_snapshot(snapshot_id)
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


@router.get("/graph", dependencies=[Depends(verify_token)], deprecated=True)
async def get_graph(
    request: Request,
    backend_name: Optional[str] = None,
    simplify: bool = False,
    max_nodes: int = 1000
) -> Dict[str, Any]:
    """Generate a dependency graph for the project.
    
    DEPRECATED: Use /plugins/livemap/graph instead.
    This endpoint will be removed in a future version.
    """
    import warnings
    warnings.warn(
        "GET /graph is deprecated. Use /plugins/livemap/graph instead.",
        DeprecationWarning,
        stacklevel=2
    )
    logger.warning("Deprecated /graph endpoint called. Use /plugins/livemap/graph instead.")
    
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
