"""Plugin system bootstrap module.

Version: 0.1.1

This module provides the initialization logic for the plugin system v2.
It should be called during application startup to:
1. Initialize all registries (CLI, API, UI)
2. Initialize the Bridge
3. Discover and load plugins
4. Register plugin contributions

Usage:
    from jupiter.core.bridge.bootstrap import init_plugin_system, shutdown_plugin_system
    
    # At startup
    bridge = await init_plugin_system(app, config)
    
    # At shutdown
    await shutdown_plugin_system()
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from fastapi import FastAPI
    from jupiter.config import JupiterConfig

logger = logging.getLogger(__name__)

# Module-level state
_initialized = False
_bridge = None


async def init_plugin_system(
    app: "FastAPI",
    config: Optional["JupiterConfig"] = None,
    plugins_dir: Optional[Path] = None,
) -> Any:
    """Initialize the plugin system.
    
    This function:
    1. Resets all registries (for clean state)
    2. Creates the Bridge singleton
    3. Discovers plugins from the plugins directory
    4. Initializes plugins in dependency order
    5. Registers plugin contributions (CLI, API, UI)
    6. Attaches registries to FastAPI app state
    
    Args:
        app: FastAPI application instance
        config: Jupiter configuration (optional)
        plugins_dir: Path to plugins directory (defaults to jupiter/plugins)
        
    Returns:
        The Bridge instance
        
    Raises:
        RuntimeError: If initialization fails
    """
    global _initialized, _bridge
    
    if _initialized:
        logger.warning("Plugin system already initialized, skipping")
        return _bridge
    
    logger.info("Initializing plugin system v2...")
    
    try:
        # Import registries and Bridge
        from jupiter.core.bridge import (
            Bridge,
            get_cli_registry,
            get_api_registry,
            get_ui_registry,
            get_event_bus,
            reset_cli_registry,
            reset_api_registry,
            reset_ui_registry,
            reset_event_bus,
        )
        
        # Reset all registries for clean state
        reset_cli_registry()
        reset_api_registry()
        reset_ui_registry()
        reset_event_bus()
        logger.debug("Registries reset")
        
        # Create Bridge
        bridge = Bridge()
        _bridge = bridge
        
        # Determine plugins directory
        if plugins_dir is None:
            # Default to jupiter/plugins relative to the jupiter package
            plugins_dir = Path(__file__).parent.parent.parent / "plugins"
        
        # Set plugins directory on bridge
        if plugins_dir:
            bridge.plugins_dir = plugins_dir
        
        # Discover plugins
        if plugins_dir and plugins_dir.exists():
            logger.info("Discovering plugins in %s", plugins_dir)
            bridge.discover()
            logger.info("Discovered %d plugins", len(bridge.get_all_plugins()))
        else:
            logger.warning("Plugins directory not found: %s", plugins_dir)
        
        # Initialize plugins
        logger.info("Initializing plugins...")
        bridge.initialize()
        
        # Count ready plugins (get_all_plugins returns a list)
        all_plugins = bridge.get_all_plugins()
        ready = sum(1 for p in all_plugins if p.state.value == "ready")
        errors = sum(1 for p in all_plugins if p.state.value == "error")
        
        logger.info(
            "Plugin initialization complete: %d ready, %d errors, %d total",
            ready, errors, len(all_plugins)
        )
        
        # Get registries
        cli_registry = get_cli_registry()
        api_registry = get_api_registry()
        ui_registry = get_ui_registry()
        event_bus = get_event_bus()
        
        # Attach to FastAPI app state
        app.state.bridge = bridge
        app.state.cli_registry = cli_registry
        app.state.api_registry = api_registry
        app.state.ui_registry = ui_registry
        app.state.event_bus = event_bus
        
        logger.debug("Registries attached to app.state")
        
        # Log contribution counts
        cli_count = len(cli_registry.get_all_commands())
        api_count = len(api_registry.get_all_routes())
        ui_count = len(ui_registry.get_sidebar_panels()) + len(ui_registry.get_settings_panels())
        
        logger.info(
            "Registered contributions: %d CLI commands, %d API routes, %d UI panels",
            cli_count, api_count, ui_count
        )
        
        _initialized = True
        return bridge
        
    except Exception as e:
        logger.error("Failed to initialize plugin system: %s", e, exc_info=True)
        raise RuntimeError(f"Plugin system initialization failed: {e}") from e


async def shutdown_plugin_system() -> None:
    """Shutdown the plugin system.
    
    This function:
    1. Disables all plugins
    2. Resets all registries
    3. Clears module-level state
    """
    global _initialized, _bridge
    
    if not _initialized:
        logger.debug("Plugin system not initialized, nothing to shutdown")
        return
    
    logger.info("Shutting down plugin system...")
    
    try:
        from jupiter.core.bridge import (
            reset_cli_registry,
            reset_api_registry,
            reset_ui_registry,
            reset_event_bus,
        )
        
        # Disable all plugins (get_all_plugins returns a List[PluginInfo])
        if _bridge:
            all_plugins = _bridge.get_all_plugins()
            for plugin_info in all_plugins:
                try:
                    # disable_plugin may not be implemented yet
                    if hasattr(_bridge, 'disable_plugin'):
                        getattr(_bridge, 'disable_plugin')(plugin_info.manifest.id)
                except Exception as e:
                    logger.warning("Error disabling plugin %s: %s", plugin_info.manifest.id, e)
        
        # Reset registries
        reset_cli_registry()
        reset_api_registry()
        reset_ui_registry()
        reset_event_bus()
        
        _initialized = False
        _bridge = None
        
        logger.info("Plugin system shutdown complete")
        
    except Exception as e:
        logger.error("Error during plugin system shutdown: %s", e)


def is_initialized() -> bool:
    """Check if the plugin system is initialized."""
    return _initialized


def get_bridge() -> Any:
    """Get the Bridge instance.
    
    Returns:
        Bridge instance or None if not initialized
    """
    return _bridge


def get_plugin_stats() -> Dict[str, Any]:
    """Get plugin system statistics.
    
    Returns:
        Dictionary with plugin counts and status
    """
    if not _initialized or not _bridge:
        return {
            "initialized": False,
            "plugins_loaded": 0,
            "plugins_ready": 0,
            "plugins_error": 0,
            "cli_commands": 0,
            "api_routes": 0,
            "ui_panels": 0,
        }
    
    try:
        from jupiter.core.bridge import (
            get_cli_registry,
            get_api_registry,
            get_ui_registry,
        )
        
        all_plugins = _bridge.get_all_plugins()
        
        cli_registry = get_cli_registry()
        api_registry = get_api_registry()
        ui_registry = get_ui_registry()
        
        return {
            "initialized": True,
            "plugins_loaded": len(all_plugins),
            "plugins_ready": sum(1 for p in all_plugins if p.state.value == "ready"),
            "plugins_error": sum(1 for p in all_plugins if p.state.value == "error"),
            "cli_commands": len(cli_registry.get_all_commands()) if cli_registry else 0,
            "api_routes": len(api_registry.get_all_routes()) if api_registry else 0,
            "ui_panels": (
                len(ui_registry.get_sidebar_panels()) + 
                len(ui_registry.get_settings_panels())
            ) if ui_registry else 0,
        }
        
    except Exception as e:
        logger.warning("Error getting plugin stats: %s", e)
        return {
            "initialized": True,
            "error": str(e),
        }
