"""Plugin manager for Jupiter.

Version: 1.14.0 - Fix view_id collision (use plugin ID, not panel ID)

DEPRECATION WARNING:
The v1 PluginManager is deprecated and will be removed in Jupiter 2.0.0.
Please use the Bridge v2 architecture for plugin management.

The Bridge v2 provides:
- Better isolation and security (permissions, signatures)
- Hot reload support in developer mode
- Jobs system for long-running tasks
- Standardized CLI, API, and UI contributions
- Health checks and metrics
- Circuit breaker for fault tolerance

See: docs/PLUGIN_MIGRATION_GUIDE.md
See: docs/BRIDGE_V2_CHANGELOG.md
"""
from __future__ import annotations

import importlib
import logging
import pkgutil
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Type, Optional

from jupiter.plugins import Plugin, PluginUIType, PluginUIConfig
from jupiter.config.config import PluginsConfig

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages the lifecycle of Jupiter plugins.
    
    .. deprecated:: 1.8.53
        Use Bridge v2 architecture instead.
        See docs/PLUGIN_MIGRATION_GUIDE.md for migration guide.
    """

    def __init__(self, plugin_dir: Path | None = None, config: PluginsConfig | None = None) -> None:
        warnings.warn(
            "PluginManager is deprecated. Use Bridge v2 architecture. "
            "See docs/PLUGIN_MIGRATION_GUIDE.md",
            DeprecationWarning,
            stacklevel=2
        )
        self.plugins: List[Plugin] = []
        self.plugin_status: Dict[str, bool] = {}
        self.plugin_dir = plugin_dir
        self.config = config

    def discover_and_load(self) -> None:
        """Discover and load plugins from the plugins directory."""
        # Always load built-in plugins from jupiter.plugins package
        import jupiter.plugins
        self._load_from_package(jupiter.plugins)

        # If an external plugin dir is provided, load from there too (future use)
        if self.plugin_dir and self.plugin_dir.exists():
            # This part would require adding to sys.path or similar dynamic loading
            pass

    def _load_from_package(self, package: Any) -> None:
        """Load plugins from a python package."""
        path = package.__path__
        prefix = package.__name__ + "."

        for _, name, _ in pkgutil.iter_modules(path, prefix):
            try:
                module = importlib.import_module(name)
                self._register_plugins_from_module(module)
            except Exception as e:
                logger.error("Failed to load plugin module %s: %s", name, e)

    def _register_plugins_from_module(self, module: Any) -> None:
        """Find and instantiate Plugin classes in a module."""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and hasattr(attr, "name") and hasattr(attr, "version"):
                # Simple duck-typing check or inheritance check
                # We instantiate the plugin
                try:
                    plugin_instance = attr()
                    self.register(plugin_instance)
                except Exception as e:
                    logger.error("Failed to instantiate plugin %s: %s", attr_name, e)

    def register(self, plugin: Plugin) -> None:
        """Register a plugin instance."""
        # Avoid duplicates
        if any(p.name == plugin.name for p in self.plugins):
            return
        
        self.plugins.append(plugin)
        
        # Determine initial status based on config
        is_enabled = True
        if self.config:
            if plugin.name in self.config.disabled:
                is_enabled = False
            elif self.config.enabled and plugin.name not in self.config.enabled:
                is_enabled = False
            
            # Configure plugin if it supports it
            if hasattr(plugin, "configure"):
                plugin_settings = self.config.settings.get(plugin.name, {})
                try:
                    plugin.configure(plugin_settings)
                except Exception as e:
                    logger.error("Failed to configure plugin %s: %s", plugin.name, e)
        
        self.plugin_status[plugin.name] = is_enabled
        trust_level = getattr(plugin, "trust_level", "experimental")
        logger.info("Registered plugin: %s v%s [%s] (Enabled: %s)", plugin.name, plugin.version, trust_level, is_enabled)

    def is_enabled(self, plugin_name: str) -> bool:
        return self.plugin_status.get(plugin_name, False)

    def get_enabled_plugins(self) -> List["Plugin"]:
        """Return list of all enabled plugin instances.
        
        This method is used by system/autodiag routers to enumerate
        active plugins and their hooks for handler introspection.
        """
        return [p for p in self.plugins if self.is_enabled(p.name)]

    def enable_plugin(self, plugin_name: str) -> None:
        if any(p.name == plugin_name for p in self.plugins):
            self.plugin_status[plugin_name] = True
            logger.info("Plugin %s enabled", plugin_name)

    def disable_plugin(self, plugin_name: str) -> None:
        if any(p.name == plugin_name for p in self.plugins):
            self.plugin_status[plugin_name] = False
            logger.info("Plugin %s disabled", plugin_name)

    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """Return a plugin instance by name if it is registered."""
        for plugin in self.plugins:
            if plugin.name == plugin_name:
                return plugin
        return None

    def update_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> None:
        """Update configuration for a plugin."""
        for plugin in self.plugins:
            if plugin.name == plugin_name:
                if hasattr(plugin, "configure"):
                    plugin.configure(config)
                    if self.config:
                        self.config.settings[plugin_name] = config
                    logger.info("Updated config for plugin %s", plugin_name)
                return
        logger.warning("Plugin %s not found or not configurable", plugin_name)

    def reload_all_plugins(self) -> Dict[str, Any]:
        """Reload all plugins by clearing and re-discovering them.
        
        This is useful when plugin files have been modified on disk.
        Returns a dict with reload status and list of plugins.
        """
        old_status = self.plugin_status.copy()
        old_plugins = [p.name for p in self.plugins]
        
        # Clear current plugins
        self.plugins.clear()
        self.plugin_status.clear()
        
        # Force reimport of plugin modules
        import jupiter.plugins
        modules_to_reload = [
            name for name in sys.modules.keys()
            if name.startswith("jupiter.plugins.")
        ]
        for mod_name in modules_to_reload:
            try:
                module = sys.modules[mod_name]
                importlib.reload(module)
                logger.debug("Reloaded module: %s", mod_name)
            except Exception as e:
                logger.error("Failed to reload module %s: %s", mod_name, e)
        
        # Re-discover and load
        self.discover_and_load()
        
        # Restore previous enabled/disabled status
        for name, was_enabled in old_status.items():
            if name in self.plugin_status:
                self.plugin_status[name] = was_enabled
        
        new_plugins = [p.name for p in self.plugins]
        added = set(new_plugins) - set(old_plugins)
        removed = set(old_plugins) - set(new_plugins)
        
        logger.info("Plugins reloaded. Count: %d, Added: %s, Removed: %s", 
                    len(self.plugins), list(added), list(removed))
        
        return {
            "status": "ok",
            "count": len(self.plugins),
            "plugins": new_plugins,
            "added": list(added),
            "removed": list(removed),
        }

    def restart_plugin(self, plugin_name: str) -> Dict[str, Any]:
        """Restart a specific plugin by reloading its module.
        
        This is useful after updating a plugin file.
        Returns a dict with restart status.
        """
        # Find the plugin
        plugin = None
        for p in self.plugins:
            if p.name == plugin_name:
                plugin = p
                break
        
        if not plugin:
            return {"status": "error", "message": f"Plugin '{plugin_name}' not found"}
        
        # Get the module name for this plugin
        plugin_module = type(plugin).__module__
        was_enabled = self.plugin_status.get(plugin_name, False)
        old_config = getattr(plugin, "config", {}).copy() if hasattr(plugin, "config") else {}
        
        # Remove from our list
        self.plugins = [p for p in self.plugins if p.name != plugin_name]
        if plugin_name in self.plugin_status:
            del self.plugin_status[plugin_name]
        
        # Reload the module
        try:
            if plugin_module in sys.modules:
                module = sys.modules[plugin_module]
                importlib.reload(module)
                logger.info("Reloaded module: %s", plugin_module)
                
                # Re-register plugins from this module
                self._register_plugins_from_module(module)
                
                # Find the new instance and restore state
                for p in self.plugins:
                    if p.name == plugin_name:
                        self.plugin_status[plugin_name] = was_enabled
                        if old_config and hasattr(p, "configure"):
                            p.configure(old_config)
                        break
                
                return {
                    "status": "ok",
                    "message": f"Plugin '{plugin_name}' restarted successfully",
                    "enabled": self.is_enabled(plugin_name),
                }
            else:
                return {"status": "error", "message": f"Module '{plugin_module}' not found in sys.modules"}
        except Exception as e:
            logger.error("Failed to restart plugin %s: %s", plugin_name, e)
            return {"status": "error", "message": str(e)}

    def hook_on_scan(self, report: Dict[str, Any], project_root: Optional[Path] = None) -> None:
        """Dispatch on_scan hook."""
        for plugin in self.plugins:
            if self.is_enabled(plugin.name) and hasattr(plugin, "on_scan"):
                try:
                    # Set project root on plugin if it supports it
                    if project_root and hasattr(plugin, "_project_root"):
                        setattr(plugin, "_project_root", project_root)
                    plugin.on_scan(report)
                except Exception as e:
                    logger.error("Plugin %s failed on_scan: %s", plugin.name, e)

    def hook_on_analyze(self, summary: Dict[str, Any], project_root: Optional[Path] = None) -> None:
        """Dispatch on_analyze hook."""
        for plugin in self.plugins:
            if self.is_enabled(plugin.name) and hasattr(plugin, "on_analyze"):
                try:
                    # Set project root on plugin if it supports it
                    if project_root and hasattr(plugin, "_project_root"):
                        setattr(plugin, "_project_root", project_root)
                    plugin.on_analyze(summary)
                except Exception as e:
                    logger.error("Plugin %s failed on_analyze: %s", plugin.name, e)

    def get_plugins_info(self) -> List[Dict[str, Any]]:
        """Return info about loaded plugins.
        
        Includes both legacy plugins and v2 plugins from Bridge.
        V2 plugins take precedence over legacy plugins with the same name.
        Includes signature verification status if Bridge is available.
        """
        # Try to get signature verifier from Bridge
        signature_verifier = None
        try:
            from jupiter.core.bridge.signature import get_signature_verifier
            signature_verifier = get_signature_verifier()
        except Exception:
            pass
        
        result = []
        v2_plugin_ids: set[str] = set()
        
        # First, add v2 plugins from Bridge (they take precedence)
        try:
            from jupiter.core.bridge import get_bridge
            bridge = get_bridge()
            if bridge:
                for plugin_info in bridge.get_all_plugins():
                    # Skip legacy-wrapped plugins (already in self.plugins)
                    if plugin_info.legacy:
                        continue
                    
                    v2_plugin_ids.add(plugin_info.manifest.id)
                    
                    # Convert v2 plugin info to legacy format
                    info: Dict[str, Any] = {
                        "name": plugin_info.manifest.id,
                        "version": plugin_info.manifest.version,
                        "description": plugin_info.manifest.description,
                        "enabled": plugin_info.state.value == "ready",
                        "trust_level": plugin_info.manifest.trust_level,
                        "signature": None,  # TODO: Add signature verification for v2
                        "circuit_breaker": self._get_circuit_breaker_status(plugin_info.manifest.id),
                        "config": {},  # TODO: Add config from v2 manifest
                        "is_core": plugin_info.manifest.id in self.CORE_PLUGINS,
                        "restartable": True,
                        "ui_config": None,
                        "has_ui": bool(plugin_info.manifest.ui_contributions),
                        "has_settings_ui": False,
                        "v2": True,  # Flag to identify v2 plugins
                        "state": plugin_info.state.value,
                        "error": plugin_info.error,
                    }
                    result.append(info)
        except Exception as e:
            logger.debug("Could not get v2 plugins from Bridge: %s", e)
        
        # Then add legacy plugins (skip if v2 version exists)
        for p in self.plugins:
            # Skip if v2 version already added
            if p.name in v2_plugin_ids:
                continue
            trust_level = getattr(p, "trust_level", "experimental")
            signature_info = None
            
            # Try to get signature verification if available
            if signature_verifier:
                try:
                    plugin_path = self._get_plugin_path(p.name)
                    if plugin_path:
                        verification = signature_verifier.verify_plugin(plugin_path)
                        sig_info = verification.signature_info
                        signer_id = sig_info.signer_id if sig_info else None
                        signed_at = (
                            datetime.fromtimestamp(sig_info.timestamp, tz=timezone.utc).isoformat()
                            if sig_info else None
                        )
                        signature_info = {
                            "valid": verification.valid,
                            "trust_level": verification.trust_level.value if verification.trust_level else None,
                            "signer": signer_id,
                            "signed_at": signed_at,
                            "verified": verification.valid,
                        }
                        # Use verified trust level if signature is valid
                        if verification.valid and verification.trust_level:
                            trust_level = verification.trust_level.value
                except Exception as e:
                    logger.debug("Could not verify signature for %s: %s", p.name, e)
            
            # Get circuit breaker status from job manager
            circuit_breaker_info = self._get_circuit_breaker_status(p.name)
            
            info: Dict[str, Any] = {
                "name": p.name,
                "version": p.version,
                "description": getattr(p, "description", ""),
                "enabled": self.is_enabled(p.name),
                "trust_level": trust_level,
                "signature": signature_info,
                "circuit_breaker": circuit_breaker_info,
                "config": getattr(p, "config", {}),
                "is_core": p.name in self.CORE_PLUGINS,
                "restartable": getattr(p, "restartable", True),  # Default True, Bridge sets False
            }
            
            # Add UI config if present
            ui_config = getattr(p, "ui_config", None)
            if ui_config and hasattr(ui_config, "to_dict"):
                info["ui_config"] = ui_config.to_dict()
            else:
                info["ui_config"] = None
            
            # Check if plugin has UI methods
            info["has_ui"] = hasattr(p, "get_ui_html") and callable(getattr(p, "get_ui_html"))
            info["has_settings_ui"] = hasattr(p, "get_settings_html") and callable(getattr(p, "get_settings_html"))
            
            result.append(info)
        
        return result
    
    def _get_plugin_path(self, name: str) -> Optional[Path]:
        """Get the path to a plugin's directory.
        
        Args:
            name: Plugin name
            
        Returns:
            Path to plugin directory or None
        """
        try:
            import jupiter.plugins
            plugins_base = Path(jupiter.plugins.__file__).parent
            plugin_path = plugins_base / name
            if plugin_path.exists():
                return plugin_path
        except Exception:
            pass
        return None
    
    def _get_circuit_breaker_status(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get circuit breaker status for a plugin from the JobManager.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Circuit breaker info dict or None if not available
        """
        try:
            from jupiter.core.bridge.jobs import get_job_manager
            job_manager = get_job_manager()
            
            breaker = job_manager.get_circuit_breaker(plugin_id)
            if breaker is None:
                return None
            
            last_failure = (
                datetime.fromtimestamp(breaker.last_failure_time, tz=timezone.utc).isoformat()
                if breaker.last_failure_time is not None else None
            )
            opened_at = (
                datetime.fromtimestamp(breaker.opened_at, tz=timezone.utc).isoformat()
                if breaker.opened_at is not None else None
            )
            return {
                "state": breaker.state.value,
                "failure_count": breaker.failure_count,
                "last_failure": last_failure,
                "opened_at": opened_at,
                "is_open": breaker.state.value == "open",
            }
        except Exception:
            return None

    def get_sidebar_plugins(self) -> List[Dict[str, Any]]:
        """Return plugins that should appear in the sidebar menu.
        
        Includes both legacy plugins with ui_config and v2 plugins with UI contributions.
        """
        sidebar_plugins = []
        v2_plugin_ids: set[str] = set()
        
        # First, add v2 plugins from Bridge
        try:
            from jupiter.core.bridge import get_bridge
            bridge = get_bridge()
            if bridge:
                for plugin_info in bridge.get_all_plugins():
                    # Skip legacy-wrapped plugins
                    if plugin_info.legacy:
                        continue
                    
                    # Check for UI contributions with sidebar location
                    for ui_contrib in plugin_info.manifest.ui_contributions:
                        loc = ui_contrib.location.value if ui_contrib.location else "sidebar"
                        if loc in ("sidebar", "both"):
                            v2_plugin_ids.add(plugin_info.manifest.id)
                            sidebar_plugins.append({
                                "name": plugin_info.manifest.id,
                                "menu_icon": ui_contrib.icon or "🔌",
                                "menu_label_key": ui_contrib.title_key or plugin_info.manifest.id,
                                "menu_order": ui_contrib.order or 100,
                                # Always use plugin ID as view_id to avoid collisions
                                # (panel id 'main' is common across plugins)
                                "view_id": plugin_info.manifest.id,
                                "v2": True,
                                "route": ui_contrib.route,
                            })
        except Exception as e:
            logger.debug("Could not get v2 sidebar plugins from Bridge: %s", e)
        
        # Then add legacy plugins
        for p in self.plugins:
            if p.name in v2_plugin_ids:
                continue
            if not self.is_enabled(p.name):
                continue
            
            ui_config = getattr(p, "ui_config", None)
            if not ui_config:
                continue
            
            ui_type = getattr(ui_config, "ui_type", PluginUIType.NONE)
            if ui_type in (PluginUIType.SIDEBAR, PluginUIType.BOTH):
                sidebar_plugins.append({
                    "name": p.name,
                    "menu_icon": getattr(ui_config, "menu_icon", "🔌"),
                    "menu_label_key": getattr(ui_config, "menu_label_key", p.name),
                    "menu_order": getattr(ui_config, "menu_order", 100),
                    "view_id": getattr(ui_config, "view_id", p.name),
                })
        
        # Sort by menu_order
        sidebar_plugins.sort(key=lambda x: x["menu_order"])
        return sidebar_plugins

    def get_settings_plugins(self) -> List[Dict[str, Any]]:
        """Return plugins that should appear in the settings page.
        
        Includes both legacy plugins with settings UI and v2 plugins with config schema.
        """
        settings_plugins = []
        v2_plugin_ids: set[str] = set()
        
        # First, add v2 plugins from Bridge (any v2 plugin with config schema gets settings)
        try:
            from jupiter.core.bridge import get_bridge
            bridge = get_bridge()
            if bridge:
                for plugin_info in bridge.get_all_plugins():
                    # Skip legacy-wrapped plugins
                    if plugin_info.legacy:
                        continue
                    
                    # Check for UI contributions with settings location
                    has_settings_ui = False
                    for ui_contrib in plugin_info.manifest.ui_contributions:
                        loc = ui_contrib.location.value if ui_contrib.location else "sidebar"
                        if loc in ("settings", "both"):
                            has_settings_ui = True
                            break
                    
                    # Also add if plugin has config schema (auto-generate settings form)
                    has_config = bool(getattr(plugin_info.manifest, 'config_schema', None))
                    
                    if has_settings_ui or has_config:
                        v2_plugin_ids.add(plugin_info.manifest.id)
                        settings_plugins.append({
                            "name": plugin_info.manifest.id,
                            "settings_section": plugin_info.manifest.name,
                            "v2": True,
                            "has_config_schema": has_config,
                        })
        except Exception as e:
            logger.debug("Could not get v2 settings plugins from Bridge: %s", e)
        
        # Then add legacy plugins
        for p in self.plugins:
            if p.name in v2_plugin_ids:
                continue
            if not self.is_enabled(p.name):
                continue
            
            ui_config = getattr(p, "ui_config", None)
            if not ui_config:
                continue
            
            ui_type = getattr(ui_config, "ui_type", PluginUIType.NONE)
            if ui_type in (PluginUIType.SETTINGS, PluginUIType.BOTH):
                settings_plugins.append({
                    "name": p.name,
                    "settings_section": getattr(ui_config, "settings_section", p.name),
                })
        
        return settings_plugins

    def get_plugin_ui_html(self, plugin_name: str) -> Optional[str]:
        """Get the UI HTML for a plugin.
        
        For v2 plugins:
        1. Try importing web.ui module and calling get_ui_html()
        2. Fallback to empty container div
        For legacy plugins, returns the result of get_ui_html() method.
        """
        # Check v2 plugins first
        try:
            from jupiter.core.bridge.bridge import Bridge
            import importlib
            bridge = Bridge.get_instance()
            if bridge:
                plugin_info = bridge.get_plugin(plugin_name)
                if plugin_info and not plugin_info.legacy:
                    # V2 plugins: try importing web.ui module first
                    try:
                        ui_module = importlib.import_module(f"jupiter.plugins.{plugin_name}.web.ui")
                        get_html = getattr(ui_module, "get_ui_html", None)
                        if get_html and callable(get_html):
                            result = get_html()
                            if result:
                                return str(result)
                    except ImportError:
                        pass
                    # Fallback: V2 plugins get a mount container - JS will populate it
                    return f'<div id="plugin-{plugin_name}-container" class="plugin-v2-container"></div>'
        except Exception:
            pass
        
        # Legacy plugins
        for p in self.plugins:
            if p.name == plugin_name and self.is_enabled(p.name):
                method = getattr(p, "get_ui_html", None)
                if method is not None and callable(method):
                    result = method()
                    return str(result) if result is not None else None
        return None

    def get_plugin_ui_js(self, plugin_name: str) -> Optional[str]:
        """Get the UI JavaScript for a plugin.
        
        For v2 plugins:
        1. Try reading web/panels/main.js
        2. Try importing web.ui module and calling get_ui_js()
        For legacy plugins, returns the result of get_ui_js() method.
        """
        # Check v2 plugins first
        try:
            from jupiter.core.bridge.bridge import Bridge
            from pathlib import Path
            import importlib
            bridge = Bridge.get_instance()
            if bridge:
                plugin_info = bridge.get_plugin(plugin_name)
                if plugin_info and not plugin_info.legacy:
                    source_path = plugin_info.manifest.source_path
                    if source_path:
                        # V2 plugins: first try web/panels/main.js
                        js_path = source_path / "web" / "panels" / "main.js"
                        if js_path.exists():
                            return js_path.read_text(encoding="utf-8")
                    
                    # Fallback: try importing web.ui module
                    try:
                        ui_module = importlib.import_module(f"jupiter.plugins.{plugin_name}.web.ui")
                        get_js = getattr(ui_module, "get_ui_js", None)
                        if get_js and callable(get_js):
                            result = get_js()
                            if result:
                                return str(result)
                    except ImportError:
                        pass
        except Exception as e:
            logger.debug("Could not get v2 plugin JS for %s: %s", plugin_name, e)
        
        # Legacy plugins
        for p in self.plugins:
            if p.name == plugin_name and self.is_enabled(p.name):
                method = getattr(p, "get_ui_js", None)
                if method is not None and callable(method):
                    result = method()
                    return str(result) if result is not None else None
        return None

    def get_plugin_settings_html(self, plugin_name: str) -> Optional[str]:
        """Get the settings HTML for a plugin.
        
        For v2 plugins with config_schema, returns a container for auto-form generation.
        For legacy plugins, returns the result of get_settings_html() method.
        """
        # Check v2 plugins first
        try:
            from jupiter.core.bridge import get_bridge
            bridge = get_bridge()
            if bridge:
                plugin_info = bridge.get_plugin(plugin_name)
                if plugin_info and not plugin_info.legacy:
                    # V2 plugins get a settings container
                    manifest = plugin_info.manifest
                    config_schema = getattr(manifest, 'config_schema', None)
                    if config_schema:
                        # Return container for auto-form - JS will generate form from schema
                        return f'''
                        <div id="plugin-{plugin_name}-settings" class="plugin-v2-settings" 
                             data-plugin="{plugin_name}"
                             data-schema='{__import__("json").dumps(config_schema)}'>
                            <h4>{manifest.name} Settings</h4>
                            <div class="auto-form-container"></div>
                        </div>
                        '''
        except Exception as e:
            logger.debug("Could not get v2 plugin settings HTML for %s: %s", plugin_name, e)
        
        # Legacy plugins
        for p in self.plugins:
            if p.name == plugin_name and self.is_enabled(p.name):
                method = getattr(p, "get_settings_html", None)
                if method is not None and callable(method):
                    result = method()
                    return str(result) if result is not None else None
        return None

    def get_plugin_settings_js(self, plugin_name: str) -> Optional[str]:
        """Get the settings JavaScript for a plugin."""
        for p in self.plugins:
            if p.name == plugin_name and self.is_enabled(p.name):
                method = getattr(p, "get_settings_js", None)
                if method is not None and callable(method):
                    result = method()
                    return str(result) if result is not None else None
        return None

    def get_plugin_translations(self, plugin_name: str, lang_code: str) -> Dict[str, Any]:
        """Get translations for a plugin in the specified language.
        
        Loads translations from the plugin's web/lang/{lang_code}.json file.
        Falls back to 'en' if the requested language is not available.
        
        Args:
            plugin_name: Plugin name/id
            lang_code: Language code (e.g., 'en', 'fr')
            
        Returns:
            Dict with translation key-value pairs, or empty dict if not found
        """
        import json
        
        # Check v2 plugins first
        try:
            from jupiter.core.bridge.bridge import Bridge
            bridge = Bridge.get_instance()
            if bridge:
                plugin_info = bridge.get_plugin(plugin_name)
                if plugin_info and not plugin_info.legacy:
                    source_path = plugin_info.manifest.source_path
                    if source_path:
                        # Try requested language
                        lang_path = source_path / "web" / "lang" / f"{lang_code}.json"
                        if lang_path.exists():
                            try:
                                return json.loads(lang_path.read_text(encoding="utf-8"))
                            except json.JSONDecodeError as e:
                                logger.warning("Invalid JSON in %s: %s", lang_path, e)
                        
                        # Fallback to English
                        if lang_code != "en":
                            en_path = source_path / "web" / "lang" / "en.json"
                            if en_path.exists():
                                try:
                                    return json.loads(en_path.read_text(encoding="utf-8"))
                                except json.JSONDecodeError as e:
                                    logger.warning("Invalid JSON in %s: %s", en_path, e)
        except Exception as e:
            logger.debug("Could not get v2 plugin translations for %s: %s", plugin_name, e)
        
        # Legacy plugins - try web/lang directory in plugin path
        plugins_dir = self._get_plugins_directory()
        plugin_dir = plugins_dir / plugin_name
        if plugin_dir.exists():
            lang_path = plugin_dir / "web" / "lang" / f"{lang_code}.json"
            if lang_path.exists():
                try:
                    return json.loads(lang_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as e:
                    logger.warning("Invalid JSON in %s: %s", lang_path, e)
            
            # Fallback to English
            if lang_code != "en":
                en_path = plugin_dir / "web" / "lang" / "en.json"
                if en_path.exists():
                    try:
                        return json.loads(en_path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError as e:
                        logger.warning("Invalid JSON in %s: %s", en_path, e)
        
        return {}

    # --- Plugin Installation / Uninstallation ---

    # Core plugins that cannot be uninstalled
    CORE_PLUGINS = frozenset({
        "code_quality",
        "ai_helper", 
        "notifications_webhook",
        "pylance_analyzer",
        "settings_update",
    })

    def _get_plugins_directory(self) -> Path:
        """Get the plugins directory path."""
        import jupiter.plugins
        return Path(jupiter.plugins.__path__[0])

    def install_plugin_from_url(self, url: str) -> Dict[str, Any]:
        """Install a plugin from a URL (ZIP file or Git repo).
        
        Args:
            url: URL to ZIP file or Git repository (git+https://...)
            
        Returns:
            Dict with status and plugin_name if successful
        """
        import tempfile
        import shutil
        import urllib.request
        import zipfile
        
        plugins_dir = self._get_plugins_directory()
        
        try:
            if url.startswith("git+"):
                # Git repository - would need git installed
                # For now, just return an error
                return {
                    "status": "error",
                    "message": "Git repository installation not yet supported. Please download the ZIP and upload it.",
                }
            
            # Download ZIP file
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)
                zip_path = tmp_path / "plugin.zip"
                
                # Download the file
                logger.info("Downloading plugin from %s", url)
                urllib.request.urlretrieve(url, zip_path)
                
                # Extract and install
                return self._install_from_zip(zip_path, plugins_dir)
                
        except Exception as e:
            logger.error("Failed to install plugin from URL %s: %s", url, e)
            return {"status": "error", "message": str(e)}

    def install_plugin_from_bytes(self, content: bytes, filename: str) -> Dict[str, Any]:
        """Install a plugin from uploaded file bytes.
        
        Args:
            content: File content as bytes
            filename: Original filename
            
        Returns:
            Dict with status and plugin_name if successful
        """
        import tempfile
        import shutil
        import zipfile
        
        plugins_dir = self._get_plugins_directory()
        
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)
                
                if filename.endswith(".zip"):
                    zip_path = tmp_path / filename
                    zip_path.write_bytes(content)
                    return self._install_from_zip(zip_path, plugins_dir)
                    
                elif filename.endswith(".py"):
                    # Single Python file - install directly
                    plugin_name = filename[:-3]  # Remove .py extension
                    
                    # Check if plugin already exists
                    target_path = plugins_dir / filename
                    if target_path.exists():
                        return {
                            "status": "error",
                            "message": f"Plugin file '{filename}' already exists. Delete it first or choose a different name.",
                        }
                    
                    # Write the file
                    target_path.write_bytes(content)
                    logger.info("Installed plugin file: %s", filename)
                    
                    # Reload plugins to pick up the new one
                    self.reload_all_plugins()
                    
                    return {
                        "status": "ok",
                        "plugin_name": plugin_name,
                        "message": f"Plugin '{plugin_name}' installed successfully",
                    }
                else:
                    return {"status": "error", "message": f"Unsupported file type: {filename}"}
                    
        except Exception as e:
            logger.error("Failed to install plugin from file %s: %s", filename, e)
            return {"status": "error", "message": str(e)}

    def _install_from_zip(self, zip_path: Path, plugins_dir: Path) -> Dict[str, Any]:
        """Install a plugin from a ZIP file.
        
        Args:
            zip_path: Path to the ZIP file
            plugins_dir: Target plugins directory
            
        Returns:
            Dict with status and plugin_name if successful
        """
        import zipfile
        import shutil
        import tempfile
        
        try:
            with tempfile.TemporaryDirectory() as extract_dir:
                extract_path = Path(extract_dir)
                
                # Extract ZIP
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(extract_path)
                
                # Find the plugin content
                # Could be a single folder or files directly
                contents = list(extract_path.iterdir())
                
                if len(contents) == 1 and contents[0].is_dir():
                    # Single directory - use its contents
                    source_dir = contents[0]
                    plugin_name = source_dir.name
                else:
                    # Files directly in the ZIP
                    source_dir = extract_path
                    plugin_name = zip_path.stem
                
                # Check for Python files
                py_files = list(source_dir.glob("*.py"))
                if not py_files:
                    return {"status": "error", "message": "No Python files found in the archive"}
                
                # If there's an __init__.py, this is a package
                if (source_dir / "__init__.py").exists():
                    # Copy as a package
                    target_dir = plugins_dir / plugin_name
                    if target_dir.exists():
                        return {
                            "status": "error",
                            "message": f"Plugin directory '{plugin_name}' already exists",
                        }
                    shutil.copytree(source_dir, target_dir)
                    logger.info("Installed plugin package: %s", plugin_name)
                else:
                    # Copy individual .py files
                    for py_file in py_files:
                        target_file = plugins_dir / py_file.name
                        if target_file.exists():
                            logger.warning("Skipping existing file: %s", py_file.name)
                            continue
                        shutil.copy2(py_file, target_file)
                        logger.info("Installed plugin file: %s", py_file.name)
                    
                    # Use first .py file name as plugin name
                    plugin_name = py_files[0].stem
                
                # Reload plugins
                self.reload_all_plugins()
                
                return {
                    "status": "ok",
                    "plugin_name": plugin_name,
                    "message": f"Plugin '{plugin_name}' installed successfully",
                }
                
        except zipfile.BadZipFile:
            return {"status": "error", "message": "Invalid ZIP file"}
        except Exception as e:
            logger.error("Failed to install plugin from ZIP: %s", e)
            return {"status": "error", "message": str(e)}

    def uninstall_plugin(self, plugin_name: str) -> Dict[str, Any]:
        """Uninstall a plugin by name.
        
        Removes the plugin files from the plugins directory.
        
        Args:
            plugin_name: Name of the plugin to uninstall
            
        Returns:
            Dict with status
            
        Raises:
            ValueError: If the plugin is a core plugin or doesn't exist
        """
        import shutil
        
        # Check if it's a core plugin
        if plugin_name in self.CORE_PLUGINS:
            raise ValueError(f"Cannot uninstall core plugin '{plugin_name}'")
        
        # Find the plugin
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            raise ValueError(f"Plugin '{plugin_name}' not found")
        
        plugins_dir = self._get_plugins_directory()
        
        # Find the plugin files/directory
        plugin_module = type(plugin).__module__
        
        # Try to find the file/directory to delete
        plugin_path = None
        
        # Check for single file plugin
        single_file = plugins_dir / f"{plugin_name}.py"
        if single_file.exists():
            plugin_path = single_file
        
        # Check for package plugin
        package_dir = plugins_dir / plugin_name
        if package_dir.is_dir():
            plugin_path = package_dir
        
        if not plugin_path:
            return {
                "status": "error",
                "message": f"Cannot find plugin files for '{plugin_name}'",
            }
        
        try:
            # Disable the plugin first
            self.disable_plugin(plugin_name)
            
            # Remove from our list
            self.plugins = [p for p in self.plugins if p.name != plugin_name]
            if plugin_name in self.plugin_status:
                del self.plugin_status[plugin_name]
            
            # Remove from sys.modules
            modules_to_remove = [
                name for name in sys.modules.keys()
                if name == plugin_module or name.startswith(f"{plugin_module}.")
            ]
            for mod_name in modules_to_remove:
                del sys.modules[mod_name]
            
            # Delete the files
            if plugin_path.is_dir():
                shutil.rmtree(plugin_path)
                logger.info("Removed plugin directory: %s", plugin_path)
            else:
                plugin_path.unlink()
                logger.info("Removed plugin file: %s", plugin_path)
            
            return {
                "status": "ok",
                "message": f"Plugin '{plugin_name}' uninstalled successfully",
            }
            
        except Exception as e:
            logger.error("Failed to uninstall plugin %s: %s", plugin_name, e)
            return {"status": "error", "message": str(e)}
