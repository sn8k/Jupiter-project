"""Plugin manager for Jupiter."""

from __future__ import annotations

import importlib
import logging
import pkgutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Type

from jupiter.plugins import Plugin
from jupiter.config.config import PluginsConfig

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages the lifecycle of Jupiter plugins."""

    def __init__(self, plugin_dir: Path | None = None, config: PluginsConfig | None = None) -> None:
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
        
        self.plugin_status[plugin.name] = is_enabled
        logger.info("Registered plugin: %s v%s (Enabled: %s)", plugin.name, plugin.version, is_enabled)

    def is_enabled(self, plugin_name: str) -> bool:
        return self.plugin_status.get(plugin_name, False)

    def enable_plugin(self, plugin_name: str) -> None:
        if any(p.name == plugin_name for p in self.plugins):
            self.plugin_status[plugin_name] = True
            logger.info("Plugin %s enabled", plugin_name)

    def disable_plugin(self, plugin_name: str) -> None:
        if any(p.name == plugin_name for p in self.plugins):
            self.plugin_status[plugin_name] = False
            logger.info("Plugin %s disabled", plugin_name)

    def hook_on_scan(self, report: Dict[str, Any]) -> None:
        """Dispatch on_scan hook."""
        for plugin in self.plugins:
            if self.is_enabled(plugin.name) and hasattr(plugin, "on_scan"):
                try:
                    plugin.on_scan(report)
                except Exception as e:
                    logger.error("Plugin %s failed on_scan: %s", plugin.name, e)

    def hook_on_analyze(self, summary: Dict[str, Any]) -> None:
        """Dispatch on_analyze hook."""
        for plugin in self.plugins:
            if self.is_enabled(plugin.name) and hasattr(plugin, "on_analyze"):
                try:
                    plugin.on_analyze(summary)
                except Exception as e:
                    logger.error("Plugin %s failed on_analyze: %s", plugin.name, e)

    def get_plugins_info(self) -> List[Dict[str, Any]]:
        """Return info about loaded plugins."""
        return [
            {
                "name": p.name,
                "version": p.version,
                "description": getattr(p, "description", ""),
                "enabled": self.is_enabled(p.name)
            }
            for p in self.plugins
        ]
