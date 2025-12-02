"""Plugin Watchdog for Jupiter.

This system plugin monitors plugin files for changes and automatically
reloads them without requiring a full Jupiter restart. Essential for
plugin development and debugging.

Features:
- Monitors all plugin files in jupiter/plugins/
- Detects file modifications (mtime changes)
- Auto-reloads modified plugins
- Preserves plugin enabled/disabled state
- Configurable check interval
- Detailed logging for debugging

Version: 1.0.0
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from jupiter.plugins import PluginUIConfig, PluginUIType

logger = logging.getLogger(__name__)

PLUGIN_VERSION = "1.0.2"


@dataclass
class WatchedFile:
    """Represents a watched plugin file."""
    path: Path
    mtime: float
    plugin_name: str
    module_name: str


class PluginWatchdog:
    """System plugin that monitors and auto-reloads modified plugins.
    
    This plugin is SETTINGS-only (no sidebar view) and provides:
    - File monitoring for plugin changes
    - Automatic reload on modification
    - Manual reload triggers
    - Status reporting
    """

    name = "watchdog"
    version = PLUGIN_VERSION
    description = "Auto-reload plugins when their files are modified (development tool)."
    trust_level = "stable"
    
    # UI Configuration - SETTINGS ONLY (no sidebar)
    ui_config = PluginUIConfig(
        ui_type=PluginUIType.SETTINGS,
        menu_icon="👁️",
        menu_label_key="watchdog_view",
        menu_order=999,  # Last in list (system plugin)
        settings_section="Plugin Watchdog",
        view_id=None,  # No sidebar view
    )

    # Core plugins that should not trigger full reload warnings
    CORE_PLUGINS = {"watchdog", "notifications", "code_quality", "livemap"}

    def __init__(self) -> None:
        logger.debug("PluginWatchdog.__init__() called")
        
        self.enabled = False  # Disabled by default (opt-in for development)
        self.check_interval = 2.0  # Seconds between checks
        self.auto_reload = True  # Auto-reload or just notify
        self.watch_external = False  # Watch external plugin dirs too
        
        self._watched_files: Dict[str, WatchedFile] = {}
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._plugin_manager: Optional[Any] = None  # Set by configure()
        self._reload_callback: Optional[Callable[[str], Dict[str, Any]]] = None
        self._last_check: float = 0.0
        self._reload_count: int = 0
        self._last_reload: Optional[str] = None
        self._plugins_dir: Optional[Path] = None
        
        logger.info("PluginWatchdog v%s initialized (enabled=%s)", PLUGIN_VERSION, self.enabled)

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the watchdog plugin."""
        logger.debug("PluginWatchdog.configure() called with: %s", config)
        
        old_enabled = self.enabled
        
        self.enabled = config.get("enabled", False)
        self.check_interval = max(0.5, config.get("check_interval", 2.0))
        self.auto_reload = config.get("auto_reload", True)
        self.watch_external = config.get("watch_external", False)
        
        # Store plugin manager reference if provided
        if "plugin_manager" in config:
            self._plugin_manager = config["plugin_manager"]
            logger.debug("PluginWatchdog received plugin_manager reference")
        
        # Store reload callback if provided
        if "reload_callback" in config:
            self._reload_callback = config["reload_callback"]
            logger.debug("PluginWatchdog received reload_callback")
        
        # Start/stop monitoring based on enabled state
        if self.enabled and not old_enabled:
            self._start_monitoring()
        elif not self.enabled and old_enabled:
            self._stop_monitoring()
        
        logger.info(
            "PluginWatchdog configured: enabled=%s, interval=%.1fs, auto_reload=%s",
            self.enabled, self.check_interval, self.auto_reload
        )

    def get_config(self) -> Dict[str, Any]:
        """Return current configuration."""
        return {
            "enabled": self.enabled,
            "check_interval": self.check_interval,
            "auto_reload": self.auto_reload,
            "watch_external": self.watch_external,
        }

    def get_status(self) -> Dict[str, Any]:
        """Return current watchdog status."""
        return {
            "enabled": self.enabled,
            "monitoring": self._monitor_thread is not None and self._monitor_thread.is_alive(),
            "watched_files": len(self._watched_files),
            "check_interval": self.check_interval,
            "auto_reload": self.auto_reload,
            "reload_count": self._reload_count,
            "last_reload": self._last_reload,
            "last_check": self._last_check,
            "files": [
                {
                    "path": str(wf.path.name),
                    "plugin": wf.plugin_name,
                    "mtime": wf.mtime,
                }
                for wf in self._watched_files.values()
            ],
        }

    def _discover_plugin_files(self) -> None:
        """Discover and catalog all plugin files to watch."""
        logger.debug("Discovering plugin files to watch...")
        
        # Find the jupiter/plugins directory
        import jupiter.plugins
        plugins_path = Path(jupiter.plugins.__path__[0])
        self._plugins_dir = plugins_path
        
        logger.debug("Plugins directory: %s", plugins_path)
        
        # Clear existing watches
        self._watched_files.clear()
        
        # Find all .py files in the plugins directory
        for py_file in plugins_path.glob("*.py"):
            if py_file.name.startswith("_"):
                continue  # Skip __init__.py etc.
            
            # Determine plugin name from file
            module_name = f"jupiter.plugins.{py_file.stem}"
            
            # Try to get the actual plugin name from the module
            plugin_name = py_file.stem
            try:
                import sys
                if module_name in sys.modules:
                    module = sys.modules[module_name]
                    # Look for plugin class
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        # Check if it's a class with a 'name' attribute that's a string
                        if isinstance(attr, type) and hasattr(attr, "name"):
                            name_attr = getattr(attr, "name", None)
                            # Only use if it's an actual string value, not a property or descriptor
                            if isinstance(name_attr, str):
                                plugin_name = name_attr
                                break
            except Exception as e:
                logger.debug("Could not determine plugin name for %s: %s", py_file, e)
            
            watched = WatchedFile(
                path=py_file,
                mtime=py_file.stat().st_mtime,
                plugin_name=plugin_name,
                module_name=module_name,
            )
            self._watched_files[str(py_file)] = watched
            logger.debug("Watching: %s (plugin: %s)", py_file.name, plugin_name)
        
        logger.info("Watchdog monitoring %d plugin files", len(self._watched_files))

    def _start_monitoring(self) -> None:
        """Start the file monitoring thread."""
        if self._monitor_thread is not None and self._monitor_thread.is_alive():
            logger.debug("Monitor thread already running")
            return
        
        self._discover_plugin_files()
        
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="PluginWatchdog",
            daemon=True,
        )
        self._monitor_thread.start()
        logger.info("PluginWatchdog monitoring started (interval: %.1fs)", self.check_interval)

    def _stop_monitoring(self) -> None:
        """Stop the file monitoring thread."""
        if self._monitor_thread is None:
            return
        
        logger.info("Stopping PluginWatchdog monitoring...")
        self._stop_event.set()
        self._monitor_thread.join(timeout=5.0)
        self._monitor_thread = None
        logger.info("PluginWatchdog monitoring stopped")

    def _monitor_loop(self) -> None:
        """Main monitoring loop running in a separate thread."""
        logger.debug("Monitor loop started")
        
        while not self._stop_event.is_set():
            try:
                self._check_for_changes()
            except Exception as e:
                logger.error("Error in watchdog monitor loop: %s", e, exc_info=True)
            
            # Wait for the interval or until stopped
            self._stop_event.wait(timeout=self.check_interval)
        
        logger.debug("Monitor loop exited")

    def _check_for_changes(self) -> None:
        """Check all watched files for modifications."""
        self._last_check = time.time()
        
        for file_path, watched in list(self._watched_files.items()):
            try:
                if not watched.path.exists():
                    logger.warning("Watched file no longer exists: %s", watched.path)
                    continue
                
                current_mtime = watched.path.stat().st_mtime
                
                if current_mtime > watched.mtime:
                    logger.info(
                        "Change detected: %s (plugin: %s, mtime: %.2f -> %.2f)",
                        watched.path.name, watched.plugin_name, watched.mtime, current_mtime
                    )
                    
                    # Update stored mtime
                    watched.mtime = current_mtime
                    
                    if self.auto_reload:
                        self._trigger_reload(watched)
                    else:
                        logger.info(
                            "Auto-reload disabled. Manual reload required for plugin: %s",
                            watched.plugin_name
                        )
                        
            except Exception as e:
                logger.error("Error checking file %s: %s", file_path, e)

    def _trigger_reload(self, watched: WatchedFile) -> None:
        """Trigger a reload of the modified plugin."""
        logger.info("Triggering reload for plugin: %s", watched.plugin_name)
        
        # Skip reloading ourselves to avoid issues
        if watched.plugin_name == "watchdog":
            logger.info("Skipping self-reload for watchdog plugin")
            return
        
        result = None
        
        # Try using the callback if available
        if self._reload_callback:
            try:
                result = self._reload_callback(watched.plugin_name)
                logger.info("Reload via callback: %s", result)
            except Exception as e:
                logger.error("Reload callback failed: %s", e, exc_info=True)
        
        # Try using plugin_manager directly
        elif self._plugin_manager:
            try:
                result = self._plugin_manager.restart_plugin(watched.plugin_name)
                logger.info("Reload via plugin_manager: %s", result)
            except Exception as e:
                logger.error("Plugin manager reload failed: %s", e, exc_info=True)
        
        else:
            logger.warning(
                "Cannot reload plugin %s: no plugin_manager or reload_callback configured",
                watched.plugin_name
            )
            return
        
        if result and result.get("status") == "ok":
            self._reload_count += 1
            self._last_reload = f"{watched.plugin_name} @ {time.strftime('%H:%M:%S')}"
            logger.info(
                "Plugin %s reloaded successfully (total reloads: %d)",
                watched.plugin_name, self._reload_count
            )
        else:
            logger.error("Failed to reload plugin %s: %s", watched.plugin_name, result)

    def force_check(self) -> Dict[str, Any]:
        """Force an immediate check for changes."""
        logger.info("Force check requested")
        
        if not self.enabled:
            return {"status": "error", "message": "Watchdog is disabled"}
        
        # Re-discover files in case new plugins were added
        self._discover_plugin_files()
        
        # Check for changes
        changes_before = self._reload_count
        self._check_for_changes()
        changes_after = self._reload_count
        
        return {
            "status": "ok",
            "checked": len(self._watched_files),
            "reloaded": changes_after - changes_before,
        }

    def on_scan(self, report: Dict[str, Any]) -> None:
        """Hook called after scan - no action needed."""
        pass

    def on_analyze(self, summary: Dict[str, Any]) -> None:
        """Hook called after analysis - no action needed."""
        pass

    # === UI Methods (Settings only) ===

    def get_ui_html(self) -> str:
        """No sidebar view - return empty."""
        return ""

    def get_ui_js(self) -> str:
        """No sidebar view - return empty."""
        return ""

    def get_settings_html(self) -> str:
        """Return HTML for the settings section."""
        return """
<div class="watchdog-settings">
    <header class="settings-header">
        <div>
            <p class="eyebrow" data-i18n="watchdog_eyebrow">Development</p>
            <h3 data-i18n="watchdog_title">Plugin Watchdog</h3>
            <p class="muted small" data-i18n="watchdog_description">
                Automatically reload plugins when their source files are modified.
                Useful during plugin development to avoid restarting Jupiter.
            </p>
        </div>
    </header>
    
    <div class="settings-content">
        <!-- Status Panel -->
        <div class="watchdog-status panel-inset" id="watchdog-status-panel">
            <div class="status-grid">
                <div class="status-item">
                    <span class="status-label" data-i18n="watchdog_status_monitoring">Monitoring</span>
                    <span class="status-value" id="watchdog-status-monitoring">--</span>
                </div>
                <div class="status-item">
                    <span class="status-label" data-i18n="watchdog_status_files">Watched Files</span>
                    <span class="status-value" id="watchdog-status-files">--</span>
                </div>
                <div class="status-item">
                    <span class="status-label" data-i18n="watchdog_status_reloads">Reloads</span>
                    <span class="status-value" id="watchdog-status-reloads">--</span>
                </div>
                <div class="status-item">
                    <span class="status-label" data-i18n="watchdog_status_last">Last Reload</span>
                    <span class="status-value" id="watchdog-status-last">--</span>
                </div>
            </div>
        </div>
        
        <!-- Settings Form -->
        <div class="settings-form">
            <div class="form-group">
                <label class="checkbox-label">
                    <input type="checkbox" id="watchdog-enabled">
                    <span data-i18n="watchdog_enabled">Enable Plugin Watchdog</span>
                </label>
                <p class="hint" data-i18n="watchdog_enabled_hint">
                    Start monitoring plugin files for changes.
                </p>
            </div>
            
            <div class="form-group">
                <label class="checkbox-label">
                    <input type="checkbox" id="watchdog-auto-reload" checked>
                    <span data-i18n="watchdog_auto_reload">Auto-reload on change</span>
                </label>
                <p class="hint" data-i18n="watchdog_auto_reload_hint">
                    Automatically reload plugins when changes are detected.
                </p>
            </div>
            
            <div class="form-group">
                <label for="watchdog-interval" data-i18n="watchdog_interval">Check Interval (seconds)</label>
                <input type="range" id="watchdog-interval" min="0.5" max="10" step="0.5" value="2">
                <span class="range-value" id="watchdog-interval-value">2.0s</span>
                <p class="hint" data-i18n="watchdog_interval_hint">
                    How often to check for file changes.
                </p>
            </div>
        </div>
        
        <!-- Actions -->
        <div class="settings-actions">
            <button class="btn btn-secondary" id="watchdog-force-check" data-i18n="watchdog_force_check">
                🔍 Force Check Now
            </button>
            <button class="btn btn-secondary" id="watchdog-refresh-status" data-i18n="watchdog_refresh_status">
                🔄 Refresh Status
            </button>
            <button class="btn btn-primary" id="watchdog-save-settings" data-i18n="watchdog_save">
                💾 Save Watchdog Settings
            </button>
        </div>
        
        <!-- Watched Files List -->
        <details class="watchdog-files-details">
            <summary data-i18n="watchdog_watched_files">Watched Files</summary>
            <ul class="watchdog-files-list" id="watchdog-files-list">
                <li class="muted" data-i18n="watchdog_no_files">No files being watched</li>
            </ul>
        </details>
    </div>
</div>

<style>
.watchdog-settings {
    padding: 1rem 0;
}

.watchdog-status {
    background: var(--panel-bg, #1e1e1e);
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1.5rem;
}

.status-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 1rem;
}

.status-item {
    text-align: center;
}

.status-label {
    display: block;
    font-size: 0.75rem;
    color: var(--muted);
    margin-bottom: 0.25rem;
}

.status-value {
    display: block;
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--accent, #4fc3f7);
}

.status-value.active {
    color: var(--success, #66bb6a);
}

.status-value.inactive {
    color: var(--muted);
}

.settings-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-bottom: 1.5rem;
}

.settings-actions {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-bottom: 1.5rem;
}

.watchdog-files-details {
    margin-top: 1rem;
}

.watchdog-files-details summary {
    cursor: pointer;
    font-weight: 500;
    padding: 0.5rem 0;
}

.watchdog-files-list {
    list-style: none;
    padding: 0;
    margin: 0.5rem 0;
    font-size: 0.85rem;
    font-family: monospace;
}

.watchdog-files-list li {
    padding: 0.25rem 0.5rem;
    border-bottom: 1px solid var(--border);
}

.watchdog-files-list li:last-child {
    border-bottom: none;
}

.range-value {
    display: inline-block;
    min-width: 3rem;
    text-align: center;
    font-weight: 500;
}
</style>
"""

    def get_settings_js(self) -> str:
        """Return JavaScript for the settings section."""
        return """
(function() {
    // Get API base URL from global state
    function getApiBase() {
        if (typeof state !== 'undefined' && state.apiBaseUrl) {
            return state.apiBaseUrl;
        }
        return window.location.protocol + '//' + window.location.hostname + ':8000';
    }
    
    // Get auth headers
    function getAuthHeaders() {
        const token = localStorage.getItem('jupiter-token') || sessionStorage.getItem('jupiter-token');
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = 'Bearer ' + token;
        return headers;
    }
    
    // Elements
    const enabledCheckbox = document.getElementById('watchdog-enabled');
    const autoReloadCheckbox = document.getElementById('watchdog-auto-reload');
    const intervalSlider = document.getElementById('watchdog-interval');
    const intervalValue = document.getElementById('watchdog-interval-value');
    const saveBtn = document.getElementById('watchdog-save-settings');
    const forceCheckBtn = document.getElementById('watchdog-force-check');
    const refreshStatusBtn = document.getElementById('watchdog-refresh-status');
    const filesList = document.getElementById('watchdog-files-list');
    
    // Status elements
    const statusMonitoring = document.getElementById('watchdog-status-monitoring');
    const statusFiles = document.getElementById('watchdog-status-files');
    const statusReloads = document.getElementById('watchdog-status-reloads');
    const statusLast = document.getElementById('watchdog-status-last');
    
    // Notification helper
    function notify(message, type = 'info') {
        if (window.showNotification) {
            window.showNotification(message, type);
        } else {
            console.log(`[${type}] ${message}`);
        }
    }
    
    // Load config
    async function loadConfig() {
        try {
            const resp = await fetch(`${getApiBase()}/plugins/watchdog/config`, {
                headers: getAuthHeaders()
            });
            if (resp.ok) {
                const config = await resp.json();
                enabledCheckbox.checked = config.enabled || false;
                autoReloadCheckbox.checked = config.auto_reload !== false;
                intervalSlider.value = config.check_interval || 2;
                intervalValue.textContent = `${intervalSlider.value}s`;
            }
        } catch (e) {
            console.error('Failed to load watchdog config:', e);
        }
    }
    
    // Load status
    async function loadStatus() {
        try {
            const resp = await fetch(`${getApiBase()}/plugins/watchdog/status`, {
                headers: getAuthHeaders()
            });
            if (resp.ok) {
                const status = await resp.json();
                
                statusMonitoring.textContent = status.monitoring ? '✅ Active' : '⏸️ Stopped';
                statusMonitoring.className = 'status-value ' + (status.monitoring ? 'active' : 'inactive');
                
                statusFiles.textContent = status.watched_files || 0;
                statusReloads.textContent = status.reload_count || 0;
                statusLast.textContent = status.last_reload || '--';
                
                // Update files list
                if (status.files && status.files.length > 0) {
                    filesList.innerHTML = status.files.map(f => 
                        `<li>📄 ${f.path} <span class="muted">(${f.plugin})</span></li>`
                    ).join('');
                } else {
                    filesList.innerHTML = '<li class="muted">No files being watched</li>';
                }
            }
        } catch (e) {
            console.error('Failed to load watchdog status:', e);
        }
    }
    
    // Save config
    async function saveConfig() {
        const config = {
            enabled: enabledCheckbox.checked,
            auto_reload: autoReloadCheckbox.checked,
            check_interval: parseFloat(intervalSlider.value),
        };
        
        try {
            const resp = await fetch(`${getApiBase()}/plugins/watchdog/config`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify(config),
            });
            
            if (resp.ok) {
                notify(window.t ? window.t('watchdog_saved') : 'Watchdog settings saved', 'success');
                // Reload status after save
                setTimeout(loadStatus, 500);
            } else {
                notify(window.t ? window.t('watchdog_save_error') : 'Error saving settings', 'error');
            }
        } catch (e) {
            console.error('Failed to save watchdog config:', e);
            notify('Error: ' + e.message, 'error');
        }
    }
    
    // Force check
    async function forceCheck() {
        try {
            const resp = await fetch(`${getApiBase()}/plugins/watchdog/check`, {
                method: 'POST',
                headers: getAuthHeaders()
            });
            if (resp.ok) {
                const result = await resp.json();
                notify(`Checked ${result.checked} files, reloaded ${result.reloaded}`, 'info');
                loadStatus();
            }
        } catch (e) {
            console.error('Force check failed:', e);
            notify('Force check failed: ' + e.message, 'error');
        }
    }
    
    // Event listeners
    intervalSlider.addEventListener('input', () => {
        intervalValue.textContent = `${intervalSlider.value}s`;
    });
    
    saveBtn.addEventListener('click', saveConfig);
    forceCheckBtn.addEventListener('click', forceCheck);
    refreshStatusBtn.addEventListener('click', loadStatus);
    
    // Initial load
    loadConfig();
    loadStatus();
    
    // Auto-refresh status every 5 seconds if enabled
    setInterval(() => {
        if (enabledCheckbox.checked) {
            loadStatus();
        }
    }, 5000);
})();
"""
