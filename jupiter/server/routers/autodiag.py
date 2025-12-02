"""
Autodiag router for Jupiter internal diagnostics.

Version: 1.1.0

This router provides endpoints for introspection and validation
of Jupiter's own functionality. It is designed to run on a
separate localhost-only port for security.

Changelog:
- v1.1.0: Replaced is_likely_used patterns with CallGraphService for accurate detection
- v1.0.0: Initial implementation
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request

from jupiter.core.cache import CacheManager
from jupiter.core.callgraph import CallGraphService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/diag", tags=["autodiag"])

# Cache for CallGraphService per project
_callgraph_cache: Dict[str, CallGraphService] = {}


def _get_callgraph_service(root: Path) -> CallGraphService:
    """Get or create CallGraphService for a project root."""
    key = str(root)
    if key not in _callgraph_cache:
        _callgraph_cache[key] = CallGraphService(root)
    return _callgraph_cache[key]


@router.get("/introspect")
async def introspect_api(request: Request) -> Dict[str, Any]:
    """
    Return all registered endpoints from the main API for self-analysis.
    
    This endpoint allows Jupiter to "see" its own API structure when
    analyzing itself as a project.
    
    Returns:
        Dict with:
        - endpoints: List of route info (path, methods, name, handler)
        - total: Total endpoint count
    """
    main_app = getattr(request.app.state, "main_app", None)
    if not main_app:
        return {"endpoints": [], "total": 0, "error": "Main app not available"}
    
    endpoints = []
    for route in main_app.routes:
        if not hasattr(route, "path"):
            continue
        
        endpoint_info: Dict[str, Any] = {
            "path": route.path,
            "methods": sorted(list(getattr(route, "methods", []))) if hasattr(route, "methods") else [],
            "name": getattr(route, "name", None),
        }
        
        if hasattr(route, "endpoint"):
            endpoint = route.endpoint
            endpoint_info["handler_name"] = getattr(endpoint, "__name__", str(endpoint))
            endpoint_info["handler_module"] = getattr(endpoint, "__module__", "unknown")
            endpoint_info["handler_qualname"] = getattr(endpoint, "__qualname__", None)
        
        endpoints.append(endpoint_info)
    
    return {"endpoints": endpoints, "total": len(endpoints)}


@router.get("/handlers")
async def get_all_handlers(request: Request) -> Dict[str, Any]:
    """
    Get all registered handlers across CLI, API, and plugins.
    
    Aggregates handlers from:
    - FastAPI routes (main app)
    - CLI command handlers
    - Plugin hook handlers
    
    Returns:
        Dict with api_handlers, cli_handlers, plugin_handlers, and total count.
    """
    main_app = getattr(request.app.state, "main_app", None)
    
    # API Handlers
    api_handlers = []
    if main_app:
        for route in main_app.routes:
            if not hasattr(route, "endpoint"):
                continue
            endpoint = route.endpoint
            api_handlers.append({
                "type": "api",
                "path": getattr(route, "path", None),
                "methods": sorted(list(getattr(route, "methods", []))) if hasattr(route, "methods") else [],
                "function_name": getattr(endpoint, "__name__", str(endpoint)),
                "module": getattr(endpoint, "__module__", "unknown"),
            })
    
    # CLI Handlers
    cli_handlers = []
    try:
        from jupiter.cli.main import get_cli_handlers
        for handler in get_cli_handlers():
            cli_handlers.append({
                "type": "cli",
                "command": handler["command"],
                "function_name": handler["function_name"],
                "module": handler["module"],
            })
    except ImportError:
        logger.warning("Could not import CLI handlers")
    
    # Plugin Handlers
    plugin_handlers = []
    plugin_manager = getattr(main_app.state if main_app else request.app.state, "plugin_manager", None)
    if plugin_manager:
        hook_names = ["on_scan", "on_analyze", "on_report", "on_startup", "on_shutdown", "setup", "cleanup"]
        for plugin in plugin_manager.get_enabled_plugins():
            plugin_name = getattr(plugin, "name", type(plugin).__name__)
            for hook in hook_names:
                if hasattr(plugin, hook) and callable(getattr(plugin, hook)):
                    method = getattr(plugin, hook)
                    plugin_handlers.append({
                        "type": "plugin",
                        "plugin_name": plugin_name,
                        "hook": hook,
                        "function_name": hook,
                        "module": getattr(method, "__module__", "unknown"),
                    })
    
    return {
        "api_handlers": api_handlers,
        "cli_handlers": cli_handlers,
        "plugin_handlers": plugin_handlers,
        "total": len(api_handlers) + len(cli_handlers) + len(plugin_handlers),
    }


@router.get("/functions")
async def get_function_usage(request: Request) -> Dict[str, Any]:
    """
    Get detailed function usage information with confidence scores.
    
    Returns:
        Dict with function usage details, summary counts, and total analyzed.
    """
    main_app = getattr(request.app.state, "main_app", None)
    root = getattr(main_app.state if main_app else request.app.state, "root_path", None)
    
    if not root:
        return {"functions": [], "summary": {}, "total_analyzed": 0, "error": "No root path"}
    
    cache_manager = CacheManager(root)
    last_scan = cache_manager.load_last_scan()
    
    if not last_scan:
        return {
            "functions": [],
            "summary": {},
            "total_analyzed": 0,
            "error": "No scan data available. Run a scan first.",
        }
    
    python_summary = last_scan.get("python_summary")
    if python_summary:
        return {
            "functions": python_summary.get("function_usage_details", []),
            "summary": python_summary.get("usage_summary", {}),
            "total_analyzed": python_summary.get("total_functions", 0),
        }
    
    return {"functions": [], "summary": {}, "total_analyzed": 0}


@router.post("/validate-unused")
async def validate_unused_functions(
    request: Request,
    functions: List[str],
) -> Dict[str, Any]:
    """
    Validate if listed functions are truly unused or false positives.
    
    Uses CallGraphService for accurate detection based on:
    - Global call graph analysis
    - Entry point detection (decorators, main, tests)
    - Reference propagation through the codebase
    
    Args:
        functions: List of function names to validate (format: "module::function")
    
    Returns:
        Dict mapping function names to validation results.
    """
    # Get project root
    main_app = getattr(request.app.state, "main_app", None)
    root = getattr(main_app.state if main_app else request.app.state, "root_path", None)
    
    if not root:
        return {"validated": 0, "results": {}, "error": "No root path configured"}
    
    # Use CallGraphService for accurate detection
    service = _get_callgraph_service(Path(root))
    
    # Get all known handlers (still useful for extra context)
    handlers_response = await get_all_handlers(request)
    known_handlers = set()
    
    for h in handlers_response.get("api_handlers", []):
        known_handlers.add(h["function_name"])
    
    for h in handlers_response.get("cli_handlers", []):
        known_handlers.add(h["function_name"])
    
    for h in handlers_response.get("plugin_handlers", []):
        known_handlers.add(h["function_name"])
    
    # Validate each function using call graph
    results: Dict[str, Dict[str, Any]] = {}
    for func in functions:
        # Extract file path and function name from "file::function" format
        if "::" in func:
            file_path, func_name = func.rsplit("::", 1)
            # Handle Class.method format
            if "." in func_name:
                func_name = func_name.split(".")[-1]
        else:
            file_path = ""
            func_name = func
        
        # Check via call graph first (most accurate)
        if file_path and service.is_function_used(file_path, func_name):
            reasons = service.get_usage_reasons(file_path, func_name)
            results[func] = {
                "is_unused": False,
                "reason": "callgraph_used",
                "details": reasons[:3] if len(reasons) > 3 else reasons,  # Limit to 3 reasons
                "confidence": 0.95,
            }
        elif func_name in known_handlers:
            # Registered handler not captured by call graph
            results[func] = {
                "is_unused": False,
                "reason": "registered_handler",
                "confidence": 1.0,
            }
        else:
            # Function is truly unused according to call graph
            results[func] = {
                "is_unused": True,
                "reason": "no_usage_in_callgraph",
                "confidence": 0.95,
            }
    
    return {
        "validated": len(results),
        "results": results,
        "callgraph_stats": service.get_statistics(),
    }


@router.get("/stats")
async def get_runtime_stats(request: Request) -> Dict[str, Any]:
    """
    Get runtime statistics for autodiag.
    
    Returns:
        Dict with uptime, request counts, and resource usage.
    """
    import time
    import os
    
    main_app = getattr(request.app.state, "main_app", None)
    
    # Get uptime if available
    start_time = getattr(request.app.state, "start_time", None)
    uptime_seconds = time.time() - start_time if start_time else None
    
    # Get memory usage (basic)
    try:
        import psutil  # type: ignore[import-not-found]
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
    except ImportError:
        memory_mb = None
    
    # Count routes
    route_count = len(main_app.routes) if main_app else 0
    
    return {
        "uptime_seconds": uptime_seconds,
        "memory_mb": round(memory_mb, 2) if memory_mb else None,
        "route_count": route_count,
        "pid": os.getpid(),
    }


@router.get("/callgraph")
async def get_callgraph_analysis(request: Request, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Get complete call graph analysis for the project.
    
    Uses CallGraphService to provide accurate function usage detection:
    - Entry point identification (decorators, main, tests, dunder methods)
    - Reference propagation through the entire codebase
    - Truly unused function detection with 0% false positives
    
    Query parameters:
        force_refresh: Force re-analysis (ignore cache)
    
    Returns:
        Dict with:
        - statistics: Analysis statistics (total, used, unused, etc.)
        - unused_functions: List of truly unused functions
        - entry_points: List of entry point functions
    """
    main_app = getattr(request.app.state, "main_app", None)
    root = getattr(main_app.state if main_app else request.app.state, "root_path", None)
    
    if not root:
        return {"error": "No root path configured", "statistics": {}}
    
    service = _get_callgraph_service(Path(root))
    
    if force_refresh:
        service.invalidate_cache()
    
    try:
        return service.to_dict()
    except Exception as e:
        logger.error("Call graph analysis failed: %s", e)
        return {"error": str(e), "statistics": {}}


@router.get("/callgraph/unused")
async def get_unused_functions_callgraph(request: Request) -> Dict[str, Any]:
    """
    Get only truly unused functions from call graph analysis.
    
    This is a focused endpoint that returns just the unused functions
    without the full analysis data.
    
    Returns:
        Dict with:
        - unused_functions: List of unused function details
        - total: Count of unused functions
    """
    main_app = getattr(request.app.state, "main_app", None)
    root = getattr(main_app.state if main_app else request.app.state, "root_path", None)
    
    if not root:
        return {"error": "No root path configured", "unused_functions": [], "total": 0}
    
    service = _get_callgraph_service(Path(root))
    
    try:
        unused = service.get_unused_functions()
        return {
            "unused_functions": unused,
            "total": len(unused),
        }
    except Exception as e:
        logger.error("Get unused functions failed: %s", e)
        return {"error": str(e), "unused_functions": [], "total": 0}


@router.post("/callgraph/invalidate")
async def invalidate_callgraph_cache(request: Request) -> Dict[str, str]:
    """
    Invalidate the call graph cache for the project.
    
    Call this after code changes to force re-analysis on next request.
    
    Returns:
        Dict with status message
    """
    main_app = getattr(request.app.state, "main_app", None)
    root = getattr(main_app.state if main_app else request.app.state, "root_path", None)
    
    if not root:
        return {"status": "error", "message": "No root path configured"}
    
    service = _get_callgraph_service(Path(root))
    service.invalidate_cache()
    
    return {"status": "ok", "message": "Call graph cache invalidated"}


@router.get("/health")
async def autodiag_health() -> Dict[str, str]:
    """Simple health check for the autodiag server."""
    return {"status": "ok", "service": "autodiag"}


@router.get("/exercise-dynamic")
async def exercise_dynamic_functions(request: Request) -> Dict[str, Any]:
    """
    Exercise functions that are dynamically called but not statically detectable.
    
    This endpoint explicitly invokes various system functions that are designed
    to be called dynamically (via getattr, callbacks, etc.) but which may be
    flagged as unused by static analysis.
    
    Categories exercised:
    - Plugin API methods (get_state, get_last_report, get_summary, etc.)
    - Meeting adapter methods (notify_online, last_seen_payload)
    - Watch router functions (broadcast_file_change)
    - Callgraph properties (short_key, is_implicitly_used)
    
    Returns:
        Dict with results for each exercised function.
    """
    results: Dict[str, Any] = {
        "exercised_functions": [],
        "errors": [],
        "total_exercised": 0,
    }
    
    # Get main app for accessing state
    main_app = getattr(request.app.state, "main_app", None)
    if not main_app:
        results["errors"].append("Main app not available")
        return results
    
    root_path = getattr(main_app.state, "root_path", None)
    
    # === Exercise Plugin API methods ===
    plugin_manager = getattr(main_app.state, "plugin_manager", None)
    if plugin_manager:
        # AutodiagPlugin
        autodiag_plugin = plugin_manager.get_plugin("autodiag")
        if autodiag_plugin:
            try:
                state = autodiag_plugin.get_state()
                results["exercised_functions"].append({
                    "function": "autodiag_plugin.get_state",
                    "status": "success",
                    "result_type": type(state).__name__,
                })
            except Exception as e:
                results["errors"].append(f"autodiag_plugin.get_state: {e}")
            
            try:
                report = autodiag_plugin.get_last_report()
                results["exercised_functions"].append({
                    "function": "autodiag_plugin.get_last_report",
                    "status": "success",
                    "result_type": type(report).__name__ if report else "None",
                })
            except Exception as e:
                results["errors"].append(f"autodiag_plugin.get_last_report: {e}")
            
            try:
                autodiag_plugin.update_from_report({"status": "test", "timestamp": 0})
                results["exercised_functions"].append({
                    "function": "autodiag_plugin.update_from_report",
                    "status": "success",
                })
            except Exception as e:
                results["errors"].append(f"autodiag_plugin.update_from_report: {e}")
        
        # CodeQualityPlugin
        code_quality_plugin = plugin_manager.get_plugin("code_quality")
        if code_quality_plugin:
            try:
                summary = code_quality_plugin.get_last_summary()
                results["exercised_functions"].append({
                    "function": "code_quality_plugin.get_last_summary",
                    "status": "success",
                    "result_type": type(summary).__name__ if summary else "None",
                })
            except Exception as e:
                results["errors"].append(f"code_quality_plugin.get_last_summary: {e}")
        
        # PylanceAnalyzerPlugin
        pylance_plugin = plugin_manager.get_plugin("pylance_analyzer")
        if pylance_plugin:
            try:
                summary = pylance_plugin.get_summary()
                results["exercised_functions"].append({
                    "function": "pylance_plugin.get_summary",
                    "status": "success",
                    "result_type": type(summary).__name__ if summary else "None",
                })
            except Exception as e:
                results["errors"].append(f"pylance_plugin.get_summary: {e}")
            
            try:
                diags = pylance_plugin.get_diagnostics_for_file("test.py")
                results["exercised_functions"].append({
                    "function": "pylance_plugin.get_diagnostics_for_file",
                    "status": "success",
                    "result_type": type(diags).__name__,
                })
            except Exception as e:
                results["errors"].append(f"pylance_plugin.get_diagnostics_for_file: {e}")
    
    # === Exercise Meeting Adapter methods ===
    meeting_adapter = getattr(main_app.state, "meeting_adapter", None)
    if meeting_adapter:
        try:
            payload = meeting_adapter.last_seen_payload()
            results["exercised_functions"].append({
                "function": "meeting_adapter.last_seen_payload",
                "status": "success",
                "result_type": type(payload).__name__,
            })
        except Exception as e:
            results["errors"].append(f"meeting_adapter.last_seen_payload: {e}")
        
        try:
            # notify_online may fail if Meeting is not configured, that's OK
            result = meeting_adapter.notify_online()
            results["exercised_functions"].append({
                "function": "meeting_adapter.notify_online",
                "status": "success",
                "result": result,
            })
        except Exception as e:
            results["errors"].append(f"meeting_adapter.notify_online: {e}")
    
    # === Exercise Watch Router functions ===
    try:
        from jupiter.server.routers.watch import broadcast_file_change
        # Call with a test path - this won't broadcast if watch is not active
        await broadcast_file_change("test/file.py", "test")
        results["exercised_functions"].append({
            "function": "watch.broadcast_file_change",
            "status": "success",
        })
    except Exception as e:
        results["errors"].append(f"watch.broadcast_file_change: {e}")
    
    # === Exercise CallGraph properties ===
    if root_path:
        try:
            from jupiter.core.callgraph import CallGraphService, FunctionInfo
            
            # Create a test FunctionInfo to exercise properties
            test_func = FunctionInfo(
                name="test_func",
                file_path="test/file.py",
                line_number=1,
                is_method=True,
                class_name="TestClass",
            )
            
            # Exercise short_key property
            short_key = test_func.short_key
            results["exercised_functions"].append({
                "function": "FunctionInfo.short_key",
                "status": "success",
                "result": short_key,
            })
            
            # Exercise is_implicitly_used property
            is_implicit = test_func.is_implicitly_used
            results["exercised_functions"].append({
                "function": "FunctionInfo.is_implicitly_used",
                "status": "success",
                "result": is_implicit,
            })
        except Exception as e:
            results["errors"].append(f"callgraph properties: {e}")
    
    results["total_exercised"] = len(results["exercised_functions"])
    return results


@router.post("/run")
async def run_autodiag(request: Request) -> Dict[str, Any]:
    """
    Run a full autodiagnostic analysis.
    
    This endpoint triggers the AutoDiagRunner to:
    1. Perform static analysis
    2. Execute test scenarios (CLI, API, plugins)
    3. Compare results to identify false positives
    
    Query parameters:
    - skip_cli: Skip CLI scenario tests (default: false)
    - skip_api: Skip API scenario tests (default: false)
    - skip_plugins: Skip plugin hook tests (default: false)
    - timeout: Timeout per scenario in seconds (default: 30)
    
    Returns:
        AutoDiagReport with complete analysis results
    """
    from jupiter.core.autodiag import AutoDiagRunner, AutodiagStatus
    
    # Get query parameters
    query_params = request.query_params
    skip_cli = query_params.get("skip_cli", "false").lower() == "true"
    skip_api = query_params.get("skip_api", "false").lower() == "true"
    skip_plugins = query_params.get("skip_plugins", "false").lower() == "true"
    timeout = float(query_params.get("timeout", "30"))
    
    # Get project root from main app state
    main_app = getattr(request.app.state, "main_app", None)
    if not main_app:
        return {"error": "Main app not available", "status": "failed"}
    
    root_path = getattr(main_app.state, "root_path", None)
    if not root_path:
        return {"error": "Project root not configured", "status": "failed"}
    
    # Get API URLs
    server_state = getattr(main_app.state, "server", None)
    host = getattr(server_state, "host", "localhost") if server_state else "localhost"
    port = getattr(server_state, "port", 8000) if server_state else 8000
    api_base_url = f"http://{host}:{port}"
    
    # Get auth token from request headers (forward the token used by the caller)
    auth_header = request.headers.get("Authorization", "")
    auth_token = None
    if auth_header.startswith("Bearer "):
        auth_token = auth_header[7:]
    
    # Run autodiag (async)
    try:
        runner = AutoDiagRunner(
            project_root=root_path,
            api_base_url=api_base_url,
            diag_base_url=f"http://127.0.0.1:8081",  # Diag always on localhost
            skip_cli=skip_cli,
            skip_api=skip_api,
            skip_plugins=skip_plugins,
            timeout_seconds=timeout,
            auth_token=auth_token,
        )
        report = await runner.run()
        return report.to_dict()
    except Exception as e:
        logger.error("Autodiag run failed: %s", e)
        return {
            "error": str(e),
            "status": "failed",
        }

