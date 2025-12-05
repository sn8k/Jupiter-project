"""
Watchdog Plugin v2 - Jupiter Bridge Architecture

This system plugin monitors plugin files for changes and automatically
reloads them without requiring a full Jupiter restart. Essential for
plugin development and debugging.

Conforme à plugins_architecture.md v0.6.0

@version 1.0.0
@module jupiter.plugins.watchdog
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

__version__ = "1.0.0"

# =============================================================================
# BRIDGE REFERENCES (injected during init)
# =============================================================================

_bridge = None
_logger: Optional[logging.Logger] = None


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class WatchedFile:
    """Represents a watched plugin file."""
    path: Path
    mtime: float
    plugin_name: str
    module_name: str


@dataclass
class PluginState:
    """Internal state of the Watchdog plugin."""
    enabled: bool = False  # Disabled by default (opt-in for development)
    check_interval: float = 2.0
    auto_reload: bool = True
    watch_external: bool = False
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Runtime state
    watched_files: Dict[str, WatchedFile] = field(default_factory=dict)
    monitor_thread: Optional[threading.Thread] = None
    stop_event: threading.Event = field(default_factory=threading.Event)
    plugin_manager: Optional[Any] = None
    reload_callback: Optional[Callable[[str], Dict[str, Any]]] = None
    plugins_dir: Optional[Path] = None
    
    # Metrics
    last_check: float = 0.0
    reload_count: int = 0
    last_reload: Optional[str] = None


_state: Optional[PluginState] = None


def _get_state() -> PluginState:
    """Get or create plugin state."""
    global _state
    if _state is None:
        _state = PluginState()
    return _state


# =============================================================================
# CORE PLUGINS LIST
# =============================================================================

CORE_PLUGINS = {"watchdog", "notifications", "code_quality", "livemap"}


# =============================================================================
# PLUGIN LIFECYCLE (Bridge v2 API)
# =============================================================================

def init(bridge) -> None:
    """
    Initialize the Watchdog plugin.
    
    Args:
        bridge: Instance du Bridge fournissant les registres et services.
    """
    global _bridge, _logger
    _bridge = bridge
    
    # Get dedicated logger via bridge.services (§3.3.1)
    _logger = bridge.services.get_logger("watchdog")
    
    # Load plugin config
    config = bridge.services.get_config("watchdog") or {}
    
    state = _get_state()
    state.config = config
    state.enabled = config.get("enabled", False)
    state.check_interval = max(0.5, config.get("check_interval", 2.0))
    state.auto_reload = config.get("auto_reload", True)
    state.watch_external = config.get("watch_external", False)
    
    # Start monitoring if enabled
    if state.enabled:
        _start_monitoring()
    
    if _logger:
        _logger.info(
            "Watchdog initialized: enabled=%s, interval=%.1fs, auto_reload=%s",
            state.enabled,
            state.check_interval,
            state.auto_reload,
        )


def shutdown() -> None:
    """Shutdown the plugin and stop monitoring."""
    _stop_monitoring()
    if _logger:
        _logger.info("Watchdog shut down")


def health() -> Dict[str, Any]:
    """
    Return health status of the plugin.
    
    Returns:
        Dict with status, message, and details.
    """
    state = _get_state()
    
    if not state.enabled:
        return {
            "status": "disabled",
            "message": "Plugin is disabled",
            "details": {"enabled": False},
        }
    
    monitoring = state.monitor_thread is not None and state.monitor_thread.is_alive()
    
    return {
        "status": "healthy" if monitoring else "degraded",
        "message": "Watchdog monitoring active" if monitoring else "Monitor thread not running",
        "details": {
            "enabled": True,
            "monitoring": monitoring,
            "watched_files": len(state.watched_files),
            "check_interval": state.check_interval,
        },
    }


def metrics() -> Dict[str, Any]:
    """
    Return plugin metrics.
    
    Returns:
        Dict with monitoring statistics.
    """
    state = _get_state()
    return {
        "reload_count": state.reload_count,
        "watched_files": len(state.watched_files),
        "last_check": state.last_check,
        "last_reload": state.last_reload,
    }


def reset_settings() -> bool:
    """Reset plugin settings to defaults."""
    global _state
    _stop_monitoring()
    _state = PluginState()
    if _logger:
        _logger.info("Watchdog settings reset to defaults")
    return True


# =============================================================================
# FILE MONITORING
# =============================================================================

def _discover_plugin_files() -> None:
    """Discover and catalog all plugin files to watch."""
    state = _get_state()
    
    if _logger:
        _logger.debug("Discovering plugin files to watch...")
    
    # Find the jupiter/plugins directory
    import jupiter.plugins
    plugins_path = Path(jupiter.plugins.__path__[0])
    state.plugins_dir = plugins_path
    
    if _logger:
        _logger.debug("Plugins directory: %s", plugins_path)
    
    # Clear existing watches
    state.watched_files.clear()
    
    # Find all .py files in the plugins directory
    for py_file in plugins_path.glob("*.py"):
        if py_file.name.startswith("_"):
            continue  # Skip __init__.py etc.
        
        module_name = f"jupiter.plugins.{py_file.stem}"
        plugin_name = py_file.stem
        
        try:
            import sys
            if module_name in sys.modules:
                module = sys.modules[module_name]
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and hasattr(attr, "name"):
                        name_attr = getattr(attr, "name", None)
                        if isinstance(name_attr, str):
                            plugin_name = name_attr
                            break
        except Exception as e:
            if _logger:
                _logger.debug("Could not determine plugin name for %s: %s", py_file, e)
        
        watched = WatchedFile(
            path=py_file,
            mtime=py_file.stat().st_mtime,
            plugin_name=plugin_name,
            module_name=module_name,
        )
        state.watched_files[str(py_file)] = watched
        
        if _logger:
            _logger.debug("Watching: %s (plugin: %s)", py_file.name, plugin_name)
    
    if _logger:
        _logger.info("Watchdog monitoring %d plugin files", len(state.watched_files))


def _start_monitoring() -> None:
    """Start the file monitoring thread."""
    state = _get_state()
    
    if state.monitor_thread is not None and state.monitor_thread.is_alive():
        if _logger:
            _logger.debug("Monitor thread already running")
        return
    
    _discover_plugin_files()
    
    state.stop_event.clear()
    state.monitor_thread = threading.Thread(
        target=_monitor_loop,
        name="PluginWatchdog",
        daemon=True,
    )
    state.monitor_thread.start()
    
    if _logger:
        _logger.info("Watchdog monitoring started (interval: %.1fs)", state.check_interval)


def _stop_monitoring() -> None:
    """Stop the file monitoring thread."""
    state = _get_state()
    
    if state.monitor_thread is None:
        return
    
    if _logger:
        _logger.info("Stopping Watchdog monitoring...")
    
    state.stop_event.set()
    state.monitor_thread.join(timeout=5.0)
    state.monitor_thread = None
    
    if _logger:
        _logger.info("Watchdog monitoring stopped")


def _monitor_loop() -> None:
    """Main monitoring loop running in a separate thread."""
    state = _get_state()
    
    if _logger:
        _logger.debug("Monitor loop started")
    
    while not state.stop_event.is_set():
        try:
            _check_for_changes()
        except Exception as e:
            if _logger:
                _logger.error("Error in watchdog monitor loop: %s", e, exc_info=True)
        
        state.stop_event.wait(timeout=state.check_interval)
    
    if _logger:
        _logger.debug("Monitor loop exited")


def _check_for_changes() -> None:
    """Check all watched files for modifications."""
    state = _get_state()
    state.last_check = time.time()
    
    for file_path, watched in list(state.watched_files.items()):
        try:
            if not watched.path.exists():
                if _logger:
                    _logger.warning("Watched file no longer exists: %s", watched.path)
                continue
            
            current_mtime = watched.path.stat().st_mtime
            
            if current_mtime > watched.mtime:
                if _logger:
                    _logger.info(
                        "Change detected: %s (plugin: %s, mtime: %.2f -> %.2f)",
                        watched.path.name, watched.plugin_name, watched.mtime, current_mtime
                    )
                
                watched.mtime = current_mtime
                
                if state.auto_reload:
                    _trigger_reload(watched)
                else:
                    if _logger:
                        _logger.info(
                            "Auto-reload disabled. Manual reload required for plugin: %s",
                            watched.plugin_name
                        )
                        
        except Exception as e:
            if _logger:
                _logger.error("Error checking file %s: %s", file_path, e)


def _trigger_reload(watched: WatchedFile) -> None:
    """Trigger a reload of the modified plugin."""
    state = _get_state()
    
    if _logger:
        _logger.info("Triggering reload for plugin: %s", watched.plugin_name)
    
    # Skip reloading ourselves
    if watched.plugin_name == "watchdog":
        if _logger:
            _logger.info("Skipping self-reload for watchdog plugin")
        return
    
    result = None
    
    # Try using the callback if available
    if state.reload_callback:
        try:
            result = state.reload_callback(watched.plugin_name)
            if _logger:
                _logger.info("Reload via callback: %s", result)
        except Exception as e:
            if _logger:
                _logger.error("Reload callback failed: %s", e, exc_info=True)
    
    # Try using plugin_manager directly
    elif state.plugin_manager:
        try:
            result = state.plugin_manager.restart_plugin(watched.plugin_name)
            if _logger:
                _logger.info("Reload via plugin_manager: %s", result)
        except Exception as e:
            if _logger:
                _logger.error("Plugin manager reload failed: %s", e, exc_info=True)
    
    else:
        if _logger:
            _logger.warning(
                "Cannot reload plugin %s: no plugin_manager or reload_callback configured",
                watched.plugin_name
            )
        return
    
    if result and result.get("status") == "ok":
        state.reload_count += 1
        state.last_reload = f"{watched.plugin_name} @ {time.strftime('%H:%M:%S')}"
        if _logger:
            _logger.info(
                "Plugin %s reloaded successfully (total reloads: %d)",
                watched.plugin_name, state.reload_count
            )
    else:
        if _logger:
            _logger.error("Failed to reload plugin %s: %s", watched.plugin_name, result)


# =============================================================================
# PUBLIC API
# =============================================================================

def force_check() -> Dict[str, Any]:
    """Force an immediate check for changes."""
    state = _get_state()
    
    if _logger:
        _logger.info("Force check requested")
    
    if not state.enabled:
        return {"status": "error", "message": "Watchdog is disabled"}
    
    # Re-discover files in case new plugins were added
    _discover_plugin_files()
    
    # Check for changes
    changes_before = state.reload_count
    _check_for_changes()
    changes_after = state.reload_count
    
    return {
        "status": "ok",
        "checked": len(state.watched_files),
        "reloaded": changes_after - changes_before,
    }


def get_status() -> Dict[str, Any]:
    """Return current watchdog status."""
    state = _get_state()
    return {
        "enabled": state.enabled,
        "monitoring": state.monitor_thread is not None and state.monitor_thread.is_alive(),
        "watched_files": len(state.watched_files),
        "check_interval": state.check_interval,
        "auto_reload": state.auto_reload,
        "reload_count": state.reload_count,
        "last_reload": state.last_reload,
        "last_check": state.last_check,
        "files": [
            {
                "path": str(wf.path.name),
                "plugin": wf.plugin_name,
                "mtime": wf.mtime,
            }
            for wf in state.watched_files.values()
        ],
    }


def get_config() -> Dict[str, Any]:
    """Return current configuration."""
    state = _get_state()
    return {
        "enabled": state.enabled,
        "check_interval": state.check_interval,
        "auto_reload": state.auto_reload,
        "watch_external": state.watch_external,
    }


def configure(config: Dict[str, Any]) -> None:
    """
    Configure the plugin.
    
    Args:
        config: Configuration dictionary.
    """
    state = _get_state()
    old_enabled = state.enabled
    
    state.config = config
    state.enabled = config.get("enabled", False)
    state.check_interval = max(0.5, config.get("check_interval", 2.0))
    state.auto_reload = config.get("auto_reload", True)
    state.watch_external = config.get("watch_external", False)
    
    # Store plugin manager reference if provided
    if "plugin_manager" in config:
        state.plugin_manager = config["plugin_manager"]
        if _logger:
            _logger.debug("Watchdog received plugin_manager reference")
    
    # Store reload callback if provided
    if "reload_callback" in config:
        state.reload_callback = config["reload_callback"]
        if _logger:
            _logger.debug("Watchdog received reload_callback")
    
    # Start/stop monitoring based on enabled state
    if state.enabled and not old_enabled:
        _start_monitoring()
    elif not state.enabled and old_enabled:
        _stop_monitoring()
    
    if _logger:
        _logger.info(
            "Watchdog configured: enabled=%s, interval=%.1fs, auto_reload=%s",
            state.enabled, state.check_interval, state.auto_reload
        )


# =============================================================================
# HOOKS (no-op for this plugin)
# =============================================================================

def on_scan(report: Dict[str, Any]) -> None:
    """Hook called after scan - no action needed."""
    pass


def on_analyze(summary: Dict[str, Any]) -> None:
    """Hook called after analysis - no action needed."""
    pass


# =============================================================================
# LEGACY COMPATIBILITY - Class-based plugin interface
# =============================================================================

class PluginWatchdog:
    """
    Legacy class-based plugin interface for backward compatibility.
    """
    
    name = "watchdog"
    version = __version__
    description = "Auto-reload plugins when their files are modified (development tool)."
    trust_level = "stable"
    
    # UI Configuration
    from jupiter.plugins import PluginUIConfig, PluginUIType
    ui_config = PluginUIConfig(
        ui_type=PluginUIType.SETTINGS,
        menu_icon="👁️",
        menu_label_key="watchdog_view",
        menu_order=999,
        settings_section="Plugin Watchdog",
        view_id=None,
    )
    
    # Core plugins
    CORE_PLUGINS = CORE_PLUGINS
    
    def __init__(self) -> None:
        self._state = _get_state()
    
    def configure(self, config: Dict[str, Any]) -> None:
        configure(config)
    
    def get_config(self) -> Dict[str, Any]:
        return get_config()
    
    def get_status(self) -> Dict[str, Any]:
        return get_status()
    
    def force_check(self) -> Dict[str, Any]:
        return force_check()
    
    def on_scan(self, report: Dict[str, Any]) -> None:
        on_scan(report)
    
    def on_analyze(self, summary: Dict[str, Any]) -> None:
        on_analyze(summary)
    
    def get_ui_html(self) -> str:
        """No sidebar view - return empty."""
        return ""
    
    def get_ui_js(self) -> str:
        """No sidebar view - return empty."""
        return ""
    
    def get_settings_html(self) -> str:
        """Return HTML for the settings section."""
        from .web.ui import get_settings_html
        return get_settings_html()
    
    def get_settings_js(self) -> str:
        """Return JavaScript for the settings section."""
        from .web.ui import get_settings_js
        return get_settings_js()
