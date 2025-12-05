"""Live Map Plugin - API Routes.

Provides REST endpoints for the Live Map dependency graph visualization.

Version: 0.3.2

Note: This router is mounted by the Bridge at /plugins/livemap, so no prefix here.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

# No prefix - the Bridge mounts this at /plugins/livemap
router = APIRouter(tags=["livemap"])


@router.get("/graph")
async def get_graph(
    request: Request,
    simplify: bool = False,
    max_nodes: int = 1000
) -> Dict[str, Any]:
    """Generate a dependency graph for the Live Map visualization.
    
    Args:
        simplify: If True, group by directory instead of showing individual files.
        max_nodes: Maximum number of nodes before auto-simplification.
        
    Returns:
        Graph data with nodes and links for D3.js visualization.
    """
    from jupiter.core.cache import CacheManager
    from jupiter.plugins.livemap import build_graph
    
    # Get root path from app state
    root = getattr(request.app.state, "root_path", None)
    if not root:
        raise HTTPException(status_code=500, detail="No root path configured")
    
    # Try cached scan first
    cache_manager = CacheManager(root)
    last_scan = cache_manager.load_last_scan()
    
    if not last_scan or "files" not in last_scan:
        # Try scanning via connector if available
        project_manager = getattr(request.app.state, "project_manager", None)
        if project_manager:
            connector = project_manager.get_default_connector()
            if connector:
                try:
                    last_scan = await connector.scan({})
                except Exception as e:
                    logger.error("Failed to get scan data via connector: %s", e)
                    raise HTTPException(status_code=500, detail=f"Failed to get scan data: {str(e)}")
        
        if not last_scan or "files" not in last_scan:
            raise HTTPException(status_code=404, detail="No scan data available. Run a scan first.")
    
    try:
        graph = build_graph(last_scan["files"], simplify=simplify, max_nodes=max_nodes)
        return graph
    except Exception as e:
        logger.error("LiveMap graph generation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Graph generation failed: {str(e)}")


@router.get("/config")
async def get_config() -> Dict[str, Any]:
    """Get Live Map plugin configuration."""
    from jupiter.plugins.livemap import get_config as plugin_get_config
    
    try:
        return plugin_get_config()
    except Exception as e:
        logger.error("Failed to get livemap config: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config")
async def save_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Save Live Map plugin configuration."""
    from jupiter.plugins.livemap import configure
    
    try:
        configure(payload)
        return {"status": "ok", "message": "Configuration saved"}
    except Exception as e:
        logger.error("Failed to save livemap config: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


def register_api_contribution(app, bridge) -> None:
    """Register the livemap API routes.
    
    This function is called by the Bridge when initializing the plugin.
    
    Args:
        app: FastAPI application instance
        bridge: The Bridge instance
    """
    logger.info("Registering Live Map API routes at /livemap")
    app.include_router(router)
