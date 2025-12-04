"""Jupiter Plugin Bridge - Developer Mode.

Version: 0.1.1

Provides developer mode features for easier plugin development:
- Relaxed security (allow unsigned plugins without prompts)
- Auto-reload on file changes (watch mode)
- Verbose logging
- Skip rate limiting
- Test console integration

Usage:
    from jupiter.core.bridge.dev_mode import (
        get_dev_mode,
        enable_dev_mode,
        disable_dev_mode,
        is_dev_mode,
    )
    
    # Enable developer mode
    enable_dev_mode()
    
    # Check if dev mode is active
    if is_dev_mode():
        print("Developer mode is active")
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Set
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer as WatchdogObserver

logger = logging.getLogger(__name__)

__version__ = "0.1.1"


# =============================================================================
# DEVELOPER MODE CONFIG
# =============================================================================

@dataclass
class DevModeConfig:
    """Configuration for developer mode."""
    
    # Whether dev mode is enabled
    enabled: bool = False
    
    # Security settings in dev mode
    allow_unsigned_plugins: bool = True
    skip_signature_verification: bool = True
    allow_all_permissions: bool = False  # Still require explicit opt-in
    
    # Logging
    verbose_logging: bool = True
    log_level: str = "DEBUG"
    
    # Rate limiting
    disable_rate_limiting: bool = True
    
    # Hot reload
    enable_hot_reload: bool = True
    auto_reload_on_change: bool = True
    watch_dirs: List[str] = field(default_factory=list)
    
    # Debug features
    enable_test_console: bool = True
    enable_debug_endpoints: bool = True
    
    # Profiling
    enable_profiling: bool = False
    profile_plugin_loads: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "enabled": self.enabled,
            "allow_unsigned_plugins": self.allow_unsigned_plugins,
            "skip_signature_verification": self.skip_signature_verification,
            "allow_all_permissions": self.allow_all_permissions,
            "verbose_logging": self.verbose_logging,
            "log_level": self.log_level,
            "disable_rate_limiting": self.disable_rate_limiting,
            "enable_hot_reload": self.enable_hot_reload,
            "auto_reload_on_change": self.auto_reload_on_change,
            "watch_dirs": self.watch_dirs,
            "enable_test_console": self.enable_test_console,
            "enable_debug_endpoints": self.enable_debug_endpoints,
            "enable_profiling": self.enable_profiling,
            "profile_plugin_loads": self.profile_plugin_loads,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DevModeConfig":
        """Create from dictionary."""
        return cls(
            enabled=data.get("enabled", False),
            allow_unsigned_plugins=data.get("allow_unsigned_plugins", True),
            skip_signature_verification=data.get("skip_signature_verification", True),
            allow_all_permissions=data.get("allow_all_permissions", False),
            verbose_logging=data.get("verbose_logging", True),
            log_level=data.get("log_level", "DEBUG"),
            disable_rate_limiting=data.get("disable_rate_limiting", True),
            enable_hot_reload=data.get("enable_hot_reload", True),
            auto_reload_on_change=data.get("auto_reload_on_change", True),
            watch_dirs=data.get("watch_dirs", []),
            enable_test_console=data.get("enable_test_console", True),
            enable_debug_endpoints=data.get("enable_debug_endpoints", True),
            enable_profiling=data.get("enable_profiling", False),
            profile_plugin_loads=data.get("profile_plugin_loads", False),
        )


# =============================================================================
# FILE WATCHER
# =============================================================================

class PluginFileHandler(FileSystemEventHandler):
    """Handle file changes for auto-reload."""
    
    def __init__(
        self,
        dev_mode: "DeveloperMode",
        debounce_seconds: float = 1.0,
    ):
        """Initialize the handler.
        
        Args:
            dev_mode: DeveloperMode instance
            debounce_seconds: Debounce time between reloads
        """
        super().__init__()
        self._dev_mode = dev_mode
        self._debounce_seconds = debounce_seconds
        self._pending_reloads: Dict[str, float] = {}
        self._lock = Lock()
    
    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification."""
        if event.is_directory:
            return
        
        # Only watch Python files - convert src_path to str
        src_path: str = str(event.src_path)
        
        if not src_path.endswith(".py"):
            return
        
        # Find which plugin this file belongs to
        plugin_id = self._find_plugin_for_file(src_path)
        if not plugin_id:
            return
        
        # Schedule reload with debounce
        import time
        now = time.time()
        
        with self._lock:
            last_time = self._pending_reloads.get(plugin_id, 0)
            if now - last_time < self._debounce_seconds:
                return
            self._pending_reloads[plugin_id] = now
        
        # Schedule async reload
        logger.info("File changed: %s (plugin: %s)", event.src_path, plugin_id)
        self._dev_mode.schedule_reload(plugin_id)
    
    def _find_plugin_for_file(self, filepath: str) -> Optional[str]:
        """Find which plugin a file belongs to."""
        path = Path(filepath)
        
        # Check registered watch mappings
        for plugin_id, watched_paths in self._dev_mode._watched_plugins.items():
            for watched_path in watched_paths:
                try:
                    path.relative_to(watched_path)
                    return plugin_id
                except ValueError:
                    continue
        
        return None


# =============================================================================
# DEVELOPER MODE
# =============================================================================

class DeveloperMode:
    """Central manager for developer mode features.
    
    Controls all development-time conveniences:
    - Relaxed security
    - Auto-reload
    - Verbose logging
    - Debug features
    """
    
    def __init__(self, config: Optional[DevModeConfig] = None):
        """Initialize developer mode.
        
        Args:
            config: Configuration options
        """
        self._config = config or DevModeConfig()
        self._lock = Lock()
        
        # File watching - use Any for type since Observer is a runtime-only import
        self._observer: Optional[Any] = None
        self._watched_plugins: Dict[str, List[Path]] = {}
        self._file_handler: Optional["PluginFileHandler"] = None
        
        # Reload scheduling
        self._pending_reloads: Set[str] = set()
        self._reload_callbacks: List[Callable[[str], None]] = []
        
        # Original logging levels
        self._original_log_levels: Dict[str, int] = {}
        
        # Stats
        self._auto_reloads: int = 0
        self._files_watched: int = 0
    
    @property
    def config(self) -> DevModeConfig:
        """Get current configuration."""
        return self._config
    
    @property
    def enabled(self) -> bool:
        """Check if dev mode is enabled."""
        return self._config.enabled
    
    def enable(self, config: Optional[DevModeConfig] = None) -> None:
        """Enable developer mode.
        
        Args:
            config: Optional configuration override
        """
        with self._lock:
            if config:
                self._config = config
            self._config.enabled = True
        
        # Apply settings
        self._apply_logging_settings()
        self._apply_security_settings()
        
        # Start file watching if configured
        if self._config.auto_reload_on_change:
            self._start_file_watching()
        
        logger.warning(
            "Developer mode ENABLED - security features relaxed! "
            "Do not use in production."
        )
    
    def disable(self) -> None:
        """Disable developer mode."""
        with self._lock:
            self._config.enabled = False
        
        # Restore settings
        self._restore_logging_settings()
        
        # Stop file watching
        self._stop_file_watching()
        
        logger.info("Developer mode disabled")
    
    # -------------------------------------------------------------------------
    # LOGGING
    # -------------------------------------------------------------------------
    
    def _apply_logging_settings(self) -> None:
        """Apply verbose logging settings."""
        if not self._config.verbose_logging:
            return
        
        # Save current levels
        root_logger = logging.getLogger()
        self._original_log_levels["root"] = root_logger.level
        
        # Set verbose logging for Jupiter
        jupiter_logger = logging.getLogger("jupiter")
        self._original_log_levels["jupiter"] = jupiter_logger.level
        
        # Apply new levels
        level = getattr(logging, self._config.log_level, logging.DEBUG)
        root_logger.setLevel(min(root_logger.level, level))
        jupiter_logger.setLevel(level)
        
        logger.debug("Verbose logging enabled (level: %s)", self._config.log_level)
    
    def _restore_logging_settings(self) -> None:
        """Restore original logging settings."""
        for name, level in self._original_log_levels.items():
            if name == "root":
                logging.getLogger().setLevel(level)
            else:
                logging.getLogger(name).setLevel(level)
        
        self._original_log_levels.clear()
    
    # -------------------------------------------------------------------------
    # SECURITY
    # -------------------------------------------------------------------------
    
    def _apply_security_settings(self) -> None:
        """Apply relaxed security settings."""
        # Settings are checked dynamically via is_* methods
        logger.debug(
            "Security settings relaxed: unsigned=%s, skip_verify=%s",
            self._config.allow_unsigned_plugins,
            self._config.skip_signature_verification,
        )
    
    def should_allow_unsigned(self) -> bool:
        """Check if unsigned plugins should be allowed."""
        return self._config.enabled and self._config.allow_unsigned_plugins
    
    def should_skip_signature_verification(self) -> bool:
        """Check if signature verification should be skipped."""
        return self._config.enabled and self._config.skip_signature_verification
    
    def should_allow_all_permissions(self) -> bool:
        """Check if all permissions should be auto-granted."""
        return self._config.enabled and self._config.allow_all_permissions
    
    def should_disable_rate_limiting(self) -> bool:
        """Check if rate limiting should be disabled."""
        return self._config.enabled and self._config.disable_rate_limiting
    
    # -------------------------------------------------------------------------
    # FILE WATCHING
    # -------------------------------------------------------------------------
    
    def _start_file_watching(self) -> None:
        """Start file system observer."""
        if self._observer is not None:
            return
        
        self._file_handler = PluginFileHandler(self)
        self._observer = WatchdogObserver()
        
        # Watch configured directories
        for watch_dir in self._config.watch_dirs:
            path = Path(watch_dir)
            if path.exists() and self._observer is not None:
                self._observer.schedule(
                    self._file_handler,
                    str(path),
                    recursive=True,
                )
                logger.debug("Watching directory: %s", path)
        
        if self._observer is not None:
            self._observer.start()
        logger.info("File watcher started")
    
    def _stop_file_watching(self) -> None:
        """Stop file system observer."""
        if self._observer is None:
            return
        
        self._observer.stop()
        self._observer.join()
        self._observer = None
        self._file_handler = None
        logger.info("File watcher stopped")
    
    def watch_plugin(self, plugin_id: str, paths: List[Path]) -> None:
        """Register paths to watch for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            paths: Paths to watch for changes
        """
        with self._lock:
            self._watched_plugins[plugin_id] = paths
            self._files_watched = sum(
                len(p) for p in self._watched_plugins.values()
            )
        
        # Add to observer if running
        if self._observer and self._file_handler:
            for path in paths:
                if path.exists():
                    self._observer.schedule(
                        self._file_handler,
                        str(path),
                        recursive=True,
                    )
        
        logger.debug("Watching plugin %s: %s", plugin_id, paths)
    
    def unwatch_plugin(self, plugin_id: str) -> None:
        """Stop watching a plugin.
        
        Args:
            plugin_id: Plugin identifier
        """
        with self._lock:
            self._watched_plugins.pop(plugin_id, None)
            self._files_watched = sum(
                len(p) for p in self._watched_plugins.values()
            )
    
    # -------------------------------------------------------------------------
    # AUTO-RELOAD
    # -------------------------------------------------------------------------
    
    def schedule_reload(self, plugin_id: str) -> None:
        """Schedule a plugin for reload.
        
        Args:
            plugin_id: Plugin to reload
        """
        if not self._config.enabled or not self._config.enable_hot_reload:
            return
        
        with self._lock:
            self._pending_reloads.add(plugin_id)
        
        # Notify callbacks
        for callback in self._reload_callbacks:
            try:
                callback(plugin_id)
            except Exception as e:
                logger.error("Reload callback failed: %s", e)
        
        self._auto_reloads += 1
        logger.info("Scheduled reload for plugin: %s", plugin_id)
    
    def add_reload_callback(
        self,
        callback: Callable[[str], None],
    ) -> None:
        """Add a callback for reload events.
        
        Args:
            callback: Function called with plugin_id when reload is scheduled
        """
        self._reload_callbacks.append(callback)
    
    def remove_reload_callback(
        self,
        callback: Callable[[str], None],
    ) -> bool:
        """Remove a reload callback.
        
        Returns:
            True if removed
        """
        try:
            self._reload_callbacks.remove(callback)
            return True
        except ValueError:
            return False
    
    def get_pending_reloads(self) -> List[str]:
        """Get list of plugins pending reload."""
        with self._lock:
            return list(self._pending_reloads)
    
    def clear_pending_reload(self, plugin_id: str) -> None:
        """Clear a pending reload after it's been processed."""
        with self._lock:
            self._pending_reloads.discard(plugin_id)
    
    # -------------------------------------------------------------------------
    # DEBUG FEATURES
    # -------------------------------------------------------------------------
    
    def is_test_console_enabled(self) -> bool:
        """Check if test console is enabled."""
        return self._config.enabled and self._config.enable_test_console
    
    def is_debug_endpoints_enabled(self) -> bool:
        """Check if debug API endpoints are enabled."""
        return self._config.enabled and self._config.enable_debug_endpoints
    
    def is_profiling_enabled(self) -> bool:
        """Check if profiling is enabled."""
        return self._config.enabled and self._config.enable_profiling
    
    # -------------------------------------------------------------------------
    # STATS & INFO
    # -------------------------------------------------------------------------
    
    def get_stats(self) -> Dict[str, Any]:
        """Get developer mode statistics."""
        return {
            "enabled": self._config.enabled,
            "auto_reloads": self._auto_reloads,
            "files_watched": self._files_watched,
            "watched_plugins": list(self._watched_plugins.keys()),
            "pending_reloads": self.get_pending_reloads(),
            "config": self._config.to_dict(),
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status."""
        return {
            "enabled": self._config.enabled,
            "features": {
                "unsigned_plugins": self.should_allow_unsigned(),
                "skip_verification": self.should_skip_signature_verification(),
                "auto_permissions": self.should_allow_all_permissions(),
                "no_rate_limit": self.should_disable_rate_limiting(),
                "hot_reload": self._config.enable_hot_reload,
                "auto_reload": self._config.auto_reload_on_change,
                "test_console": self.is_test_console_enabled(),
                "debug_endpoints": self.is_debug_endpoints_enabled(),
                "profiling": self.is_profiling_enabled(),
            },
        }


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_dev_mode: Optional[DeveloperMode] = None
_dev_mode_lock = Lock()


def get_dev_mode() -> DeveloperMode:
    """Get the global developer mode instance.
    
    Returns:
        The global DeveloperMode instance
    """
    global _dev_mode
    
    with _dev_mode_lock:
        if _dev_mode is None:
            _dev_mode = DeveloperMode()
    
    return _dev_mode


def init_dev_mode(config: Optional[DevModeConfig] = None) -> DeveloperMode:
    """Initialize or reinitialize the global developer mode.
    
    Args:
        config: Configuration options
        
    Returns:
        The initialized DeveloperMode
    """
    global _dev_mode
    
    with _dev_mode_lock:
        _dev_mode = DeveloperMode(config)
    
    logger.info("Global developer mode initialized")
    return _dev_mode


def reset_dev_mode() -> None:
    """Reset the global developer mode."""
    global _dev_mode
    
    with _dev_mode_lock:
        if _dev_mode:
            _dev_mode.disable()
        _dev_mode = None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def is_dev_mode() -> bool:
    """Check if developer mode is enabled.
    
    Returns:
        True if dev mode is enabled
    """
    return get_dev_mode().enabled


def enable_dev_mode(config: Optional[DevModeConfig] = None) -> None:
    """Enable developer mode.
    
    Args:
        config: Optional configuration
    """
    get_dev_mode().enable(config)


def disable_dev_mode() -> None:
    """Disable developer mode."""
    get_dev_mode().disable()


def get_dev_mode_status() -> Dict[str, Any]:
    """Get developer mode status.
    
    Returns:
        Status dictionary
    """
    return get_dev_mode().get_status()
