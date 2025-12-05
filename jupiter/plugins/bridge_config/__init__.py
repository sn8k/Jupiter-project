"""Bridge Configuration Plugin v2 - Jupiter Bridge Architecture

This system plugin provides a configuration panel for the Jupiter Plugin Bridge,
exposing settings for developer mode, governance, hot reload, and monitoring.

Conforme à plugins_architecture.md v0.4.0

@version 1.0.1
@module jupiter.plugins.bridge_config
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

__version__ = "1.0.1"

# =============================================================================
# BRIDGE REFERENCES (injected during init)
# =============================================================================

_bridge = None
_logger = None


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class BridgeConfigState:
    """Internal state of the Bridge Config plugin."""
    config: Dict[str, Any] = field(default_factory=dict)
    last_update: Optional[datetime] = None
    update_count: int = 0
    error_count: int = 0


# =============================================================================
# PLUGIN SINGLETON
# =============================================================================

_state: Optional[BridgeConfigState] = None


def _get_state() -> BridgeConfigState:
    """Get or create plugin state."""
    global _state
    if _state is None:
        _state = BridgeConfigState()
    return _state


# =============================================================================
# PLUGIN LIFECYCLE (Bridge v2 API)
# =============================================================================

def init(bridge) -> None:
    """
    Initialize the Bridge Config plugin.
    
    Called by Bridge during plugin initialization phase.
    
    Args:
        bridge: Instance du Bridge fournissant les registres et services.
    """
    global _bridge, _logger
    _bridge = bridge
    
    # Get dedicated logger via bridge.services
    _logger = bridge.services.get_logger("bridge_config")
    
    # Load plugin config
    config = bridge.services.get_config("bridge_config") or {}
    
    state = _get_state()
    state.config = config
    
    # Apply initial settings to Bridge if needed
    _apply_bridge_settings(config)
    
    _logger.info("Bridge Config plugin initialized")


def shutdown() -> None:
    """Shutdown the Bridge Config plugin."""
    global _bridge, _logger
    
    if _logger:
        _logger.info("Bridge Config plugin shutting down")
    
    _bridge = None
    _logger = None


def health() -> Dict[str, Any]:
    """
    Health check for the plugin.
    
    Returns:
        Health status dictionary with status, message, and details.
    """
    state = _get_state()
    
    # Check if Bridge is accessible
    bridge_ok = _bridge is not None
    
    return {
        "status": "healthy" if bridge_ok else "unhealthy",
        "message": "Bridge Config operational" if bridge_ok else "Bridge not available",
        "details": {
            "last_update": state.last_update.isoformat() if state.last_update else None,
            "update_count": state.update_count,
            "error_count": state.error_count,
        }
    }


def metrics() -> Dict[str, Any]:
    """
    Metrics for the plugin.
    
    Returns:
        Metrics dictionary.
    """
    state = _get_state()
    
    # Gather Bridge-level metrics
    bridge_metrics = {}
    if _bridge:
        try:
            # Get plugin counts
            all_plugins = _bridge.get_all_plugins()
            ready_count = sum(1 for p in all_plugins if p.state.value == "ready")
            error_count = sum(1 for p in all_plugins if p.state.value == "error")
            
            bridge_metrics = {
                "total_plugins": len(all_plugins),
                "ready_plugins": ready_count,
                "error_plugins": error_count,
            }
        except Exception:
            pass
    
    return {
        "bridge_config_updates_total": state.update_count,
        "bridge_config_errors_total": state.error_count,
        "bridge_config_last_update": state.last_update.isoformat() if state.last_update else None,
        **bridge_metrics
    }


# =============================================================================
# CONFIGURATION HELPERS
# =============================================================================

def _apply_bridge_settings(config: Dict[str, Any]) -> None:
    """Apply configuration to Bridge subsystems."""
    if not _bridge:
        return
    
    try:
        # Apply developer mode
        if config.get("developer_mode", False):
            _apply_dev_mode(config)
        
        # Apply governance settings
        governance_mode = config.get("governance_mode", "disabled")
        _apply_governance_mode(governance_mode)
        
        if _logger:
            _logger.debug("Bridge settings applied: %s", list(config.keys()))
            
    except Exception as e:
        if _logger:
            _logger.warning("Failed to apply some Bridge settings: %s", e)


def _apply_dev_mode(config: Dict[str, Any]) -> None:
    """Apply developer mode settings."""
    try:
        from jupiter.core.bridge.dev_mode import get_dev_mode, enable_dev_mode
        
        dev_mode = get_dev_mode()
        if dev_mode:
            dev_mode.config.enabled = True
            dev_mode.config.allow_unsigned_plugins = config.get("allow_unsigned_plugins", False)
            dev_mode.config.verbose_logging = config.get("verbose_logging", False)
            dev_mode.config.enable_hot_reload = config.get("hot_reload_enabled", False)
            
            if _logger:
                _logger.info("Developer mode enabled with settings")
    except ImportError:
        if _logger:
            _logger.warning("Dev mode module not available")


def _apply_governance_mode(mode: str) -> None:
    """Apply governance mode."""
    try:
        from jupiter.core.bridge.governance import get_governance, ListMode
        
        governance = get_governance()
        if governance:
            mode_map = {
                "disabled": ListMode.DISABLED,
                "whitelist": ListMode.WHITELIST,
                "blacklist": ListMode.BLACKLIST,
            }
            governance.config.mode = mode_map.get(mode, ListMode.DISABLED)
            
            if _logger:
                _logger.debug("Governance mode set to: %s", mode)
    except ImportError:
        if _logger:
            _logger.warning("Governance module not available")


# =============================================================================
# PUBLIC API FOR OTHER MODULES
# =============================================================================

def get_bridge_status() -> Dict[str, Any]:
    """Get current Bridge status and configuration."""
    state = _get_state()
    
    result = {
        "version": __version__,
        "config": state.config,
        "bridge_available": _bridge is not None,
    }
    
    if _bridge:
        try:
            # Get dev mode status
            from jupiter.core.bridge.dev_mode import is_dev_mode
            result["developer_mode_active"] = is_dev_mode()
        except ImportError:
            result["developer_mode_active"] = False
        
        try:
            # Get governance status
            from jupiter.core.bridge.governance import get_governance
            gov = get_governance()
            if gov:
                result["governance"] = {
                    "mode": gov.config.mode.value,
                    "whitelist_count": len(gov.config.whitelist),
                    "blacklist_count": len(gov.config.blacklist),
                }
        except ImportError:
            result["governance"] = {"mode": "disabled"}
        
        try:
            # Get plugin summary
            all_plugins = _bridge.get_all_plugins()
            result["plugins_summary"] = {
                "total": len(all_plugins),
                "ready": sum(1 for p in all_plugins if p.state.value == "ready"),
                "error": sum(1 for p in all_plugins if p.state.value == "error"),
                "legacy": sum(1 for p in all_plugins if p.legacy),
            }
        except Exception:
            pass
    
    return result


def update_config(new_config: Dict[str, Any]) -> Dict[str, Any]:
    """Update Bridge configuration."""
    state = _get_state()
    
    try:
        # Merge with existing config
        state.config.update(new_config)
        state.last_update = datetime.now()
        state.update_count += 1
        
        # Apply to Bridge
        _apply_bridge_settings(state.config)
        
        # Persist to project config if Bridge supports it
        if _bridge:
            try:
                config_service = _bridge.services.get_config("bridge_config")
                if hasattr(config_service, "save"):
                    config_service.save(state.config)
            except Exception:
                pass
        
        if _logger:
            _logger.info("Bridge configuration updated")
        
        return {"success": True, "config": state.config}
        
    except Exception as e:
        state.error_count += 1
        if _logger:
            _logger.error("Failed to update config: %s", e)
        return {"success": False, "error": str(e)}


def get_config() -> Dict[str, Any]:
    """Get current configuration."""
    return _get_state().config.copy()
