"""Bridge Config Plugin - API Routes

Provides REST API endpoints for Bridge configuration management.

Version: 1.0.1
"""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


class ConfigUpdateRequest(BaseModel):
    """Request body for configuration update."""
    config: Dict[str, Any]


@router.get("/status")
async def get_status(request: Request) -> Dict[str, Any]:
    """Get Bridge status and current configuration."""
    from jupiter.plugins.bridge_config import get_bridge_status
    return get_bridge_status()


@router.get("/config")
async def get_config(request: Request) -> Dict[str, Any]:
    """Get current Bridge configuration."""
    from jupiter.plugins.bridge_config import get_config
    return {"config": get_config()}


@router.put("/config")
async def update_config(request: Request, body: ConfigUpdateRequest) -> Dict[str, Any]:
    """Update Bridge configuration."""
    from jupiter.plugins.bridge_config import update_config
    result = update_config(body.config)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Update failed"))
    
    return result


@router.get("/dev-mode")
async def get_dev_mode_status(request: Request) -> Dict[str, Any]:
    """Get developer mode status and configuration."""
    try:
        from jupiter.core.bridge.dev_mode import get_dev_mode, is_dev_mode
        
        dev_mode = get_dev_mode()
        if dev_mode:
            return {
                "active": is_dev_mode(),
                "config": dev_mode.config.to_dict() if hasattr(dev_mode.config, 'to_dict') else {},
            }
        return {"active": False, "config": {}}
    except ImportError:
        return {"active": False, "config": {}, "error": "Dev mode module not available"}


@router.post("/dev-mode/enable")
async def enable_dev_mode(request: Request) -> Dict[str, Any]:
    """Enable developer mode."""
    try:
        from jupiter.core.bridge.dev_mode import enable_dev_mode
        enable_dev_mode()
        return {"success": True, "message": "Developer mode enabled"}
    except ImportError:
        raise HTTPException(status_code=503, detail="Dev mode module not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dev-mode/disable")
async def disable_dev_mode(request: Request) -> Dict[str, Any]:
    """Disable developer mode."""
    try:
        from jupiter.core.bridge.dev_mode import disable_dev_mode
        disable_dev_mode()
        return {"success": True, "message": "Developer mode disabled"}
    except ImportError:
        raise HTTPException(status_code=503, detail="Dev mode module not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/governance")
async def get_governance_status(request: Request) -> Dict[str, Any]:
    """Get governance status and configuration."""
    try:
        from jupiter.core.bridge.governance import get_governance
        
        gov = get_governance()
        if gov:
            # Get per-plugin feature flags from plugin_policies
            feature_flags = {}
            for plugin_id, policy in gov.config.plugin_policies.items():
                if policy.feature_flags:
                    feature_flags[plugin_id] = {
                        flag.name: flag.to_dict()
                        for flag in policy.feature_flags.values()
                    }
            return {
                "mode": gov.config.mode.value,
                "whitelist": list(gov.config.whitelist),
                "blacklist": list(gov.config.blacklist),
                "global_feature_flags": gov.config.global_feature_flags,
                "feature_flags": feature_flags,
            }
        return {"mode": "disabled", "whitelist": [], "blacklist": [], "feature_flags": {}}
    except ImportError:
        return {"mode": "disabled", "error": "Governance module not available"}


@router.get("/plugins-summary")
async def get_plugins_summary(request: Request) -> Dict[str, Any]:
    """Get summary of all loaded plugins."""
    try:
        from jupiter.core.bridge import get_bridge
        
        bridge = get_bridge()
        if not bridge:
            return {"total": 0, "plugins": []}
        
        all_plugins = bridge.get_all_plugins()
        
        plugins = []
        for p in all_plugins:
            plugins.append({
                "id": p.manifest.id,
                "name": p.manifest.name,
                "version": p.manifest.version,
                "type": p.manifest.plugin_type.value if hasattr(p.manifest.plugin_type, 'value') else str(p.manifest.plugin_type),
                "state": p.state.value if hasattr(p.state, 'value') else str(p.state),
                "legacy": p.legacy,
            })
        
        return {
            "total": len(plugins),
            "ready": sum(1 for p in plugins if p["state"] == "ready"),
            "error": sum(1 for p in plugins if p["state"] == "error"),
            "plugins": plugins
        }
    except Exception as e:
        return {"total": 0, "plugins": [], "error": str(e)}


@router.get("/health")
async def health_check(request: Request) -> Dict[str, Any]:
    """Health check endpoint."""
    from jupiter.plugins.bridge_config import health
    return health()


@router.get("/metrics")
async def get_metrics(request: Request) -> Dict[str, Any]:
    """Get plugin metrics."""
    from jupiter.plugins.bridge_config import metrics
    return metrics()
