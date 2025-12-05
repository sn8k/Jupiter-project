"""Jupiter Plugin Bridge - Hot Reload System.

Version: 0.2.0

Provides dynamic plugin reloading without restarting Jupiter.
Allows developers to iterate quickly during plugin development.

Features:
- Unload a running plugin gracefully
- Reload module code from disk
- Re-initialize plugin with fresh state
- Preserve registered services and event subscriptions
- Emit reload events for UI notification
- Developer mode guard (reload only allowed when dev mode is enabled)

Usage:
    from jupiter.core.bridge.hot_reload import reload_plugin, get_hot_reloader
    
    # Reload a single plugin
    result = reload_plugin("my_plugin")
    
    # Or use the reloader instance
    reloader = get_hot_reloader()
    result = reloader.reload("my_plugin")
"""

from __future__ import annotations

import importlib
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from jupiter.core.bridge.bridge import Bridge, PluginInfo

from jupiter.core.bridge.exceptions import (
    BridgeError,
    PluginError,
    LifecycleError,
)
from jupiter.core.bridge.interfaces import PluginState

logger = logging.getLogger(__name__)


class HotReloadError(BridgeError):
    """Error during hot reload operation."""
    
    def __init__(
        self, 
        message: str, 
        plugin_id: str,
        phase: str = "unknown",
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.plugin_id = plugin_id
        self.phase = phase
        self.original_error = original_error
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for API responses."""
        return {
            "error": "HotReloadError",
            "message": str(self),
            "plugin_id": self.plugin_id,
            "phase": self.phase,
            "original_error": str(self.original_error) if self.original_error else None,
        }


@dataclass
class ReloadResult:
    """Result of a hot reload operation."""
    
    success: bool
    plugin_id: str
    duration_ms: float = 0.0
    phase: str = "completed"
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    # State tracking
    old_version: Optional[str] = None
    new_version: Optional[str] = None
    contributions_reloaded: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for API responses."""
        return {
            "success": self.success,
            "plugin_id": self.plugin_id,
            "duration_ms": self.duration_ms,
            "phase": self.phase,
            "error": self.error,
            "warnings": self.warnings,
            "old_version": self.old_version,
            "new_version": self.new_version,
            "contributions_reloaded": self.contributions_reloaded,
        }


@dataclass
class ReloadHistoryEntry:
    """Entry in the reload history."""
    
    plugin_id: str
    timestamp: float
    success: bool
    duration_ms: float
    old_version: Optional[str] = None
    new_version: Optional[str] = None
    error: Optional[str] = None


class HotReloader:
    """Manages hot reloading of plugins.
    
    Provides safe plugin reloading with:
    - Graceful shutdown of existing instance
    - Module cache invalidation
    - Fresh import and initialization
    - Contribution re-registration
    - Event notification
    
    Thread Safety:
        Uses locks to prevent concurrent reloads of the same plugin.
    """
    
    def __init__(self) -> None:
        self._bridge: Optional[Bridge] = None
        self._reload_locks: Dict[str, Lock] = {}
        self._global_lock = Lock()
        self._history: List[ReloadHistoryEntry] = []
        self._max_history = 100
        self._reload_count = 0
        self._callbacks: List[Callable[[ReloadResult], None]] = []
        
        # Plugins that cannot be reloaded
        self._blacklist: Set[str] = {"bridge", "settings_update"}
    
    def set_bridge(self, bridge: Bridge) -> None:
        """Set the Bridge instance.
        
        Args:
            bridge: The Bridge singleton
        """
        self._bridge = bridge
    
    def get_bridge(self) -> Bridge:
        """Get the Bridge instance.
        
        Returns:
            Bridge instance
            
        Raises:
            BridgeError: If Bridge not set
        """
        if self._bridge is None:
            # Try to import it
            from jupiter.core.bridge.bridge import Bridge
            self._bridge = Bridge.get_instance()
        return self._bridge
    
    def _get_plugin_lock(self, plugin_id: str) -> Lock:
        """Get or create a lock for a specific plugin."""
        with self._global_lock:
            if plugin_id not in self._reload_locks:
                self._reload_locks[plugin_id] = Lock()
            return self._reload_locks[plugin_id]
    
    def can_reload(self, plugin_id: str) -> tuple[bool, str]:
        """Check if a plugin can be reloaded.
        
        Args:
            plugin_id: Plugin to check
            
        Returns:
            Tuple of (can_reload, reason)
        """
        # Check developer mode first
        from jupiter.core.bridge.dev_mode import is_dev_mode
        if not is_dev_mode():
            return False, "Hot reload requires developer mode to be enabled"
        
        # Check blacklist
        if plugin_id in self._blacklist:
            return False, f"Plugin '{plugin_id}' is a core plugin and cannot be reloaded"
        
        bridge = self.get_bridge()
        
        # Check if plugin exists
        info = bridge.get_plugin(plugin_id)
        if info is None:
            return False, f"Plugin '{plugin_id}' not found"
        
        # Check state
        if info.state == PluginState.LOADING:
            return False, f"Plugin '{plugin_id}' is currently loading"
        
        if info.state == PluginState.UNLOADING:
            return False, f"Plugin '{plugin_id}' is currently unloading"
        
        # Check if legacy plugin without module
        if info.legacy and info.module is None:
            return False, f"Legacy plugin '{plugin_id}' has no module to reload"
        
        return True, "Plugin can be reloaded"
    
    def reload(
        self, 
        plugin_id: str,
        force: bool = False,
        preserve_config: bool = True,
        skip_dev_mode_check: bool = False
    ) -> ReloadResult:
        """Reload a plugin.
        
        Performs:
        1. Developer mode validation (unless bypassed)
        2. Plugin-specific validation checks
        3. Shutdown existing instance
        4. Unload module from sys.modules
        5. Re-import module
        6. Re-initialize plugin
        7. Re-register contributions
        
        Args:
            plugin_id: Plugin to reload
            force: If True, skip some validation checks (not dev mode)
            preserve_config: If True, preserve plugin config across reload
            skip_dev_mode_check: If True, allow reload even without dev mode
                               (for internal/testing use only)
            
        Returns:
            ReloadResult with operation status
        """
        start_time = time.perf_counter()
        warnings: List[str] = []
        old_version: Optional[str] = None
        
        # Always check developer mode unless explicitly bypassed
        if not skip_dev_mode_check:
            from jupiter.core.bridge.dev_mode import is_dev_mode
            if not is_dev_mode():
                return ReloadResult(
                    success=False,
                    plugin_id=plugin_id,
                    phase="dev_mode_check",
                    error="Hot reload requires developer mode to be enabled. "
                          "Set developer_mode: true in your jupiter config.",
                )
        
        # Check if reload is allowed (plugin-specific checks)
        if not force:
            can_reload, reason = self.can_reload(plugin_id)
            if not can_reload:
                return ReloadResult(
                    success=False,
                    plugin_id=plugin_id,
                    phase="validation",
                    error=reason,
                )
        
        plugin_lock = self._get_plugin_lock(plugin_id)
        
        # Acquire lock with timeout
        if not plugin_lock.acquire(timeout=10):
            return ReloadResult(
                success=False,
                plugin_id=plugin_id,
                phase="lock_acquisition",
                error=f"Could not acquire lock for '{plugin_id}' (timeout)",
            )
        
        try:
            bridge = self.get_bridge()
            info = bridge.get_plugin(plugin_id)
            
            if info is None:
                return ReloadResult(
                    success=False,
                    plugin_id=plugin_id,
                    phase="validation",
                    error=f"Plugin '{plugin_id}' not found",
                )
            
            old_version = info.manifest.version
            saved_config: Optional[Dict[str, Any]] = None
            
            # Phase 1: Save config if needed
            if preserve_config:
                try:
                    saved_config = bridge._get_plugin_config(plugin_id)
                except Exception as e:
                    warnings.append(f"Could not preserve config: {e}")
            
            # Phase 2: Shutdown existing instance
            try:
                self._shutdown_plugin(bridge, plugin_id)
            except Exception as e:
                logger.warning("Error during shutdown of %s: %s", plugin_id, e)
                warnings.append(f"Shutdown warning: {e}")
            
            # Phase 3: Unload module
            try:
                modules_unloaded = self._unload_module(plugin_id, info)
                if modules_unloaded:
                    logger.debug("Unloaded %d modules for %s", len(modules_unloaded), plugin_id)
            except Exception as e:
                return ReloadResult(
                    success=False,
                    plugin_id=plugin_id,
                    phase="module_unload",
                    error=str(e),
                    old_version=old_version,
                    warnings=warnings,
                )
            
            # Phase 4: Clear contributions
            try:
                self._clear_contributions(bridge, plugin_id)
            except Exception as e:
                warnings.append(f"Error clearing contributions: {e}")
            
            # Phase 5: Re-discover plugin
            try:
                self._rediscover_plugin(bridge, plugin_id)
            except Exception as e:
                return ReloadResult(
                    success=False,
                    plugin_id=plugin_id,
                    phase="rediscovery",
                    error=str(e),
                    old_version=old_version,
                    warnings=warnings,
                )
            
            # Phase 6: Re-initialize plugin
            try:
                bridge.initialize([plugin_id])
            except Exception as e:
                return ReloadResult(
                    success=False,
                    plugin_id=plugin_id,
                    phase="initialization",
                    error=str(e),
                    old_version=old_version,
                    warnings=warnings,
                )
            
            # Get new version
            new_info = bridge.get_plugin(plugin_id)
            new_version = new_info.manifest.version if new_info else None
            
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Record history
            self._record_history(ReloadHistoryEntry(
                plugin_id=plugin_id,
                timestamp=time.time(),
                success=True,
                duration_ms=duration_ms,
                old_version=old_version,
                new_version=new_version,
            ))
            
            # Emit event
            self._emit_reload_event(plugin_id, True, old_version, new_version)
            
            # Create result
            result = ReloadResult(
                success=True,
                plugin_id=plugin_id,
                duration_ms=duration_ms,
                phase="completed",
                old_version=old_version,
                new_version=new_version,
                contributions_reloaded=True,
                warnings=warnings,
            )
            
            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(result)
                except Exception as e:
                    logger.error("Error in reload callback: %s", e)
            
            logger.info(
                "Hot-reloaded plugin %s: v%s -> v%s (%.1fms)",
                plugin_id, old_version, new_version, duration_ms
            )
            
            return result
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Record failure
            self._record_history(ReloadHistoryEntry(
                plugin_id=plugin_id,
                timestamp=time.time(),
                success=False,
                duration_ms=duration_ms,
                old_version=old_version,
                error=str(e),
            ))
            
            # Emit failure event
            self._emit_reload_event(plugin_id, False, old_version, None, str(e))
            
            raise HotReloadError(
                f"Failed to reload plugin '{plugin_id}': {e}",
                plugin_id=plugin_id,
                phase="unknown",
                original_error=e,
            )
            
        finally:
            plugin_lock.release()
            self._reload_count += 1
    
    def _shutdown_plugin(self, bridge: Bridge, plugin_id: str) -> None:
        """Shutdown a plugin gracefully."""
        info = bridge.get_plugin(plugin_id)
        if info is None:
            return
        
        # Call shutdown on instance
        if info.instance and hasattr(info.instance, "shutdown"):
            try:
                info.instance.shutdown()
            except Exception as e:
                logger.warning("Error in plugin %s shutdown: %s", plugin_id, e)
        
        # Update state
        info.state = PluginState.DISABLED
        info.instance = None
    
    def _unload_module(self, plugin_id: str, info: "PluginInfo") -> List[str]:
        """Unload plugin module from sys.modules.
        
        Returns:
            List of module names that were unloaded
        """
        unloaded: List[str] = []
        
        # Build list of modules to unload
        module_patterns = [
            f"jupiter.plugins.{plugin_id}",
            f"plugins.{plugin_id}",
        ]
        
        # Also unload submodules
        modules_to_remove = []
        for mod_name in list(sys.modules.keys()):
            for pattern in module_patterns:
                if mod_name == pattern or mod_name.startswith(f"{pattern}."):
                    modules_to_remove.append(mod_name)
                    break
        
        # Remove modules
        for mod_name in modules_to_remove:
            if mod_name in sys.modules:
                del sys.modules[mod_name]
                unloaded.append(mod_name)
                logger.debug("Unloaded module: %s", mod_name)
        
        # Clear module reference in info
        info.module = None
        
        return unloaded
    
    def _clear_contributions(self, bridge: Bridge, plugin_id: str) -> None:
        """Clear all contributions from a plugin."""
        # Clear CLI contributions
        cli_to_remove = [
            key for key in bridge._cli_contributions 
            if key.startswith(f"{plugin_id}.")
        ]
        for key in cli_to_remove:
            del bridge._cli_contributions[key]
        
        # Clear API contributions
        api_to_remove = [
            key for key in bridge._api_contributions 
            if key.startswith(f"{plugin_id}.")
        ]
        for key in api_to_remove:
            del bridge._api_contributions[key]
        
        # Clear UI contributions
        ui_to_remove = [
            key for key in bridge._ui_contributions 
            if key.startswith(f"{plugin_id}.")
        ]
        for key in ui_to_remove:
            del bridge._ui_contributions[key]
        
        logger.debug(
            "Cleared contributions for %s: %d CLI, %d API, %d UI",
            plugin_id, len(cli_to_remove), len(api_to_remove), len(ui_to_remove)
        )
    
    def _rediscover_plugin(self, bridge: Bridge, plugin_id: str) -> None:
        """Re-discover a plugin after module unload."""
        plugins_dir = bridge.plugins_dir
        
        # Try v2 plugin directory
        plugin_dir = plugins_dir / plugin_id
        if plugin_dir.is_dir() and (plugin_dir / "plugin.yaml").exists():
            from jupiter.core.bridge.manifest import PluginManifest
            
            manifest = PluginManifest.from_plugin_dir(plugin_dir, validate=True)
            
            # Update registry
            bridge._plugins[plugin_id].manifest = manifest
            bridge._plugins[plugin_id].state = PluginState.DISCOVERED
            bridge._plugins[plugin_id].error = None
            
            logger.debug("Re-discovered v2 plugin: %s", plugin_id)
            return
        
        # Try legacy plugin file
        plugin_file = plugins_dir / f"{plugin_id}.py"
        if plugin_file.is_file():
            bridge._discover_legacy_plugin(plugin_file)
            logger.debug("Re-discovered legacy plugin: %s", plugin_id)
            return
        
        raise HotReloadError(
            f"Could not find plugin '{plugin_id}' in {plugins_dir}",
            plugin_id=plugin_id,
            phase="rediscovery",
        )
    
    def _emit_reload_event(
        self,
        plugin_id: str,
        success: bool,
        old_version: Optional[str],
        new_version: Optional[str],
        error: Optional[str] = None,
    ) -> None:
        """Emit a reload event to the Bridge event bus."""
        try:
            bridge = self.get_bridge()
            
            if success:
                bridge.emit("PLUGIN_RELOADED", {
                    "plugin_id": plugin_id,
                    "old_version": old_version,
                    "new_version": new_version,
                })
            else:
                bridge.emit("PLUGIN_RELOAD_FAILED", {
                    "plugin_id": plugin_id,
                    "error": error,
                })
        except Exception as e:
            logger.warning("Failed to emit reload event: %s", e)
    
    def _record_history(self, entry: ReloadHistoryEntry) -> None:
        """Record a reload in history."""
        self._history.append(entry)
        
        # Trim history if needed
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
    
    def get_history(
        self, 
        plugin_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get reload history.
        
        Args:
            plugin_id: Filter by plugin ID, or None for all
            limit: Maximum entries to return
            
        Returns:
            List of history entries as dicts
        """
        entries = self._history
        
        if plugin_id:
            entries = [e for e in entries if e.plugin_id == plugin_id]
        
        # Return most recent first
        entries = list(reversed(entries[-limit:]))
        
        return [
            {
                "plugin_id": e.plugin_id,
                "timestamp": e.timestamp,
                "success": e.success,
                "duration_ms": e.duration_ms,
                "old_version": e.old_version,
                "new_version": e.new_version,
                "error": e.error,
            }
            for e in entries
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get reload statistics.
        
        Returns:
            Statistics dict
        """
        successful = sum(1 for e in self._history if e.success)
        failed = sum(1 for e in self._history if not e.success)
        
        avg_duration = 0.0
        if successful > 0:
            durations = [e.duration_ms for e in self._history if e.success]
            avg_duration = sum(durations) / len(durations)
        
        return {
            "total_reloads": self._reload_count,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / max(1, successful + failed),
            "average_duration_ms": avg_duration,
            "blacklisted_plugins": list(self._blacklist),
        }
    
    def add_to_blacklist(self, plugin_id: str) -> None:
        """Add a plugin to the reload blacklist."""
        self._blacklist.add(plugin_id)
    
    def remove_from_blacklist(self, plugin_id: str) -> None:
        """Remove a plugin from the reload blacklist."""
        self._blacklist.discard(plugin_id)
    
    def register_callback(self, callback: Callable[[ReloadResult], None]) -> None:
        """Register a callback for reload events.
        
        Args:
            callback: Function called with ReloadResult after each reload
        """
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[ReloadResult], None]) -> None:
        """Unregister a reload callback."""
        try:
            self._callbacks.remove(callback)
        except ValueError:
            pass
    
    def clear_history(self) -> None:
        """Clear reload history."""
        self._history.clear()


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_hot_reloader: Optional[HotReloader] = None
_lock = Lock()


def get_hot_reloader() -> HotReloader:
    """Get the HotReloader singleton.
    
    Returns:
        HotReloader instance
    """
    global _hot_reloader
    if _hot_reloader is None:
        with _lock:
            if _hot_reloader is None:
                _hot_reloader = HotReloader()
    return _hot_reloader


def init_hot_reloader(bridge: "Bridge") -> HotReloader:
    """Initialize the HotReloader with a Bridge instance.
    
    Args:
        bridge: Bridge instance to use
        
    Returns:
        Initialized HotReloader
    """
    reloader = get_hot_reloader()
    reloader.set_bridge(bridge)
    return reloader


def reset_hot_reloader() -> None:
    """Reset the HotReloader singleton (for testing)."""
    global _hot_reloader
    with _lock:
        _hot_reloader = None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def reload_plugin(
    plugin_id: str,
    force: bool = False,
    preserve_config: bool = True,
    skip_dev_mode_check: bool = False
) -> ReloadResult:
    """Reload a plugin.
    
    Convenience function that uses the singleton HotReloader.
    
    Note: Hot reload requires developer mode to be enabled unless
    skip_dev_mode_check is True (for internal/testing use only).
    
    Args:
        plugin_id: Plugin to reload
        force: Skip plugin-specific validation checks
        preserve_config: Preserve plugin config across reload
        skip_dev_mode_check: Skip developer mode verification (testing only)
        
    Returns:
        ReloadResult with operation status
    """
    return get_hot_reloader().reload(
        plugin_id, force, preserve_config, skip_dev_mode_check
    )


def can_reload_plugin(plugin_id: str) -> tuple[bool, str]:
    """Check if a plugin can be reloaded.
    
    Args:
        plugin_id: Plugin to check
        
    Returns:
        Tuple of (can_reload, reason)
    """
    return get_hot_reloader().can_reload(plugin_id)


def get_reload_history(
    plugin_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get reload history.
    
    Args:
        plugin_id: Filter by plugin ID, or None for all
        limit: Maximum entries to return
        
    Returns:
        List of history entries
    """
    return get_hot_reloader().get_history(plugin_id, limit)


def get_reload_stats() -> Dict[str, Any]:
    """Get reload statistics.
    
    Returns:
        Statistics dict
    """
    return get_hot_reloader().get_stats()
