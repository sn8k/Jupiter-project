"""Plugin Configuration Manager for Jupiter Bridge.

Version: 0.1.0

This module handles plugin configuration with support for:
- Plugin defaults (from manifest)
- Global plugin config (from jupiter/plugins/<id>/config.yaml)
- Project-specific overrides (from <project>.jupiter.yaml)
- Per-project enabled/disabled state

Configuration Hierarchy (highest priority first):
1. Project overrides: <project>.jupiter.yaml → plugins.<id>.config_overrides
2. Global plugin config: jupiter/plugins/<id>/config.yaml
3. Manifest defaults: plugin.yaml → config_defaults

Usage:
    manager = PluginConfigManager(plugin_id)
    
    # Check if enabled for current project
    if manager.is_enabled_for_project():
        config = manager.get_merged_config()
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


class PluginConfigManager:
    """Manages configuration for a single plugin across projects.
    
    Handles the three-layer configuration:
    1. Defaults from manifest
    2. Global plugin config
    3. Project-specific overrides
    """
    
    def __init__(
        self,
        plugin_id: str,
        defaults: Optional[Dict[str, Any]] = None,
        plugins_dir: Optional[Path] = None,
    ):
        """Initialize the config manager.
        
        Args:
            plugin_id: Plugin identifier
            defaults: Default config from manifest (optional)
            plugins_dir: Path to plugins directory (optional, auto-detected)
        """
        self._plugin_id = plugin_id
        self._defaults = defaults or {}
        self._plugins_dir = plugins_dir or self._get_default_plugins_dir()
        
        # Cache
        self._global_config: Optional[Dict[str, Any]] = None
        self._global_config_loaded = False
    
    @property
    def plugin_id(self) -> str:
        return self._plugin_id
    
    @staticmethod
    def _get_default_plugins_dir() -> Path:
        """Get the default plugins directory."""
        return Path(__file__).parent.parent.parent / "plugins"
    
    # =========================================================================
    # Global Plugin Config
    # =========================================================================
    
    def get_global_config(self, reload: bool = False) -> Dict[str, Any]:
        """Load global configuration for this plugin.
        
        Looks for config.yaml in the plugin directory.
        
        Args:
            reload: Force reload from disk
            
        Returns:
            Dict with global config or empty dict
        """
        if self._global_config_loaded and not reload:
            return self._global_config or {}
        
        self._global_config = {}
        self._global_config_loaded = True
        
        config_file = self._plugins_dir / self._plugin_id / "config.yaml"
        
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    self._global_config = yaml.safe_load(f) or {}
                logger.debug(
                    "Loaded global config for plugin %s from %s",
                    self._plugin_id, config_file
                )
            except Exception as e:
                logger.warning(
                    "Failed to load global config for plugin %s: %s",
                    self._plugin_id, e
                )
        
        return self._global_config or {}
    
    def save_global_config(self, config: Dict[str, Any]) -> bool:
        """Save global configuration for this plugin.
        
        Args:
            config: Configuration dict to save
            
        Returns:
            True if saved successfully
        """
        plugin_dir = self._plugins_dir / self._plugin_id
        config_file = plugin_dir / "config.yaml"
        
        try:
            plugin_dir.mkdir(parents=True, exist_ok=True)
            with open(config_file, "w", encoding="utf-8") as f:
                yaml.safe_dump(config, f, default_flow_style=False)
            
            self._global_config = config
            logger.info("Saved global config for plugin %s", self._plugin_id)
            return True
        except Exception as e:
            logger.error(
                "Failed to save global config for plugin %s: %s",
                self._plugin_id, e
            )
            return False
    
    # =========================================================================
    # Project-Specific Config
    # =========================================================================
    
    def get_project_config(
        self, 
        project_root: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Get project-specific plugin configuration.
        
        Looks in <project>.jupiter.yaml → plugins.<plugin_id>
        
        Args:
            project_root: Project root path (auto-detected if None)
            
        Returns:
            Dict with project-specific config or empty dict
        """
        if project_root is None:
            project_root = self._get_current_project_root()
        
        if project_root is None:
            return {}
        
        try:
            from jupiter.config.config import load_config
            config = load_config(project_root)
            
            plugins_config = getattr(config, "plugins", None)
            if plugins_config is None:
                return {}
            
            # Handle both dict and PluginsConfig dataclass
            if hasattr(plugins_config, "settings"):
                # PluginsConfig dataclass
                settings = plugins_config.settings or {}
                return settings.get(self._plugin_id, {})
            elif isinstance(plugins_config, dict):
                # Dict format
                return plugins_config.get(self._plugin_id, {})
            
        except Exception as e:
            logger.debug(
                "No project config for plugin %s: %s",
                self._plugin_id, e
            )
        
        return {}
    
    def get_project_overrides(
        self, 
        project_root: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Get project-specific config overrides only.
        
        Args:
            project_root: Project root path (auto-detected if None)
            
        Returns:
            Dict with config_overrides or empty dict
        """
        project_config = self.get_project_config(project_root)
        return project_config.get("config_overrides", {})
    
    # =========================================================================
    # Enabled State
    # =========================================================================
    
    def is_enabled_for_project(
        self, 
        project_root: Optional[Path] = None
    ) -> bool:
        """Check if this plugin is enabled for a project.
        
        Checks in order:
        1. Project-specific plugins.<id>.enabled
        2. Project plugins.disabled list
        3. Project plugins.enabled list
        4. Default: True
        
        Args:
            project_root: Project root path (auto-detected if None)
            
        Returns:
            True if plugin should be enabled
        """
        if project_root is None:
            project_root = self._get_current_project_root()
        
        if project_root is None:
            return True  # Default enabled if no project
        
        try:
            from jupiter.config.config import load_config
            config = load_config(project_root)
            
            plugins_config = getattr(config, "plugins", None)
            if plugins_config is None:
                return True
            
            # Check per-plugin enabled setting
            plugin_specific = self.get_project_config(project_root)
            if "enabled" in plugin_specific:
                return bool(plugin_specific["enabled"])
            
            # Check disabled list
            disabled_list: List[str] = []
            if hasattr(plugins_config, "disabled"):
                disabled_list = plugins_config.disabled or []
            elif isinstance(plugins_config, dict):
                disabled_list = plugins_config.get("disabled", [])
            
            if self._plugin_id in disabled_list:
                return False
            
            # Check enabled list (if present, acts as whitelist)
            enabled_list: List[str] = []
            if hasattr(plugins_config, "enabled"):
                enabled_list = getattr(plugins_config, "enabled", None) or []
            elif isinstance(plugins_config, dict):
                enabled_list = plugins_config.get("enabled", [])
            
            if enabled_list:
                return self._plugin_id in enabled_list
            
            return True  # Default enabled
            
        except Exception as e:
            logger.debug(
                "Failed to check enabled state for plugin %s: %s",
                self._plugin_id, e
            )
            return True
    
    def set_enabled_for_project(
        self,
        enabled: bool,
        project_root: Optional[Path] = None
    ) -> bool:
        """Set enabled state for this plugin in a project.
        
        Updates <project>.jupiter.yaml with the enabled state.
        
        Args:
            enabled: New enabled state
            project_root: Project root path (auto-detected if None)
            
        Returns:
            True if saved successfully
        """
        if project_root is None:
            project_root = self._get_current_project_root()
        
        if project_root is None:
            logger.warning("Cannot set enabled state: no project root")
            return False
        
        try:
            from jupiter.config.config import get_project_config_path
            
            config_file = get_project_config_path(project_root)
            # get_project_config_path always returns a path (existing or default)
            
            # Load existing config
            existing: Dict[str, Any] = {}
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    existing = yaml.safe_load(f) or {}
            
            # Update plugins section
            if "plugins" not in existing:
                existing["plugins"] = {}
            
            if not isinstance(existing["plugins"], dict):
                existing["plugins"] = {}
            
            if self._plugin_id not in existing["plugins"]:
                existing["plugins"][self._plugin_id] = {}
            
            existing["plugins"][self._plugin_id]["enabled"] = enabled
            
            # Save
            with open(config_file, "w", encoding="utf-8") as f:
                yaml.safe_dump(existing, f, default_flow_style=False)
            
            logger.info(
                "Set plugin %s enabled=%s for project %s",
                self._plugin_id, enabled, project_root
            )
            return True
            
        except Exception as e:
            logger.error(
                "Failed to set enabled state for plugin %s: %s",
                self._plugin_id, e
            )
            return False
    
    # =========================================================================
    # Merged Configuration
    # =========================================================================
    
    def get_merged_config(
        self, 
        project_root: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Get fully merged configuration.
        
        Merges in order (later overrides earlier):
        1. Manifest defaults
        2. Global plugin config
        3. Project-specific overrides
        
        Args:
            project_root: Project root path (auto-detected if None)
            
        Returns:
            Merged configuration dict
        """
        merged = dict(self._defaults)
        
        # Layer 2: Global config
        global_config = self.get_global_config()
        merged = self._deep_merge(merged, global_config)
        
        # Layer 3: Project overrides
        project_overrides = self.get_project_overrides(project_root)
        merged = self._deep_merge(merged, project_overrides)
        
        return merged
    
    def get(
        self, 
        key: str, 
        default: Any = None,
        project_root: Optional[Path] = None
    ) -> Any:
        """Get a specific configuration value.
        
        Args:
            key: Configuration key (supports dot notation: "a.b.c")
            default: Default value if key not found
            project_root: Project root path (auto-detected if None)
            
        Returns:
            Configuration value or default
        """
        config = self.get_merged_config(project_root)
        return self._get_nested(config, key, default)
    
    # =========================================================================
    # Utilities
    # =========================================================================
    
    @staticmethod
    def _get_current_project_root() -> Optional[Path]:
        """Get the current project root from state."""
        try:
            from jupiter.core.state import load_last_root
            return load_last_root()
        except Exception:
            return None
    
    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries.
        
        Args:
            base: Base dictionary
            override: Override dictionary (takes precedence)
            
        Returns:
            Merged dictionary
        """
        result = dict(base)
        
        for key, value in override.items():
            if (
                key in result 
                and isinstance(result[key], dict) 
                and isinstance(value, dict)
            ):
                result[key] = PluginConfigManager._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    @staticmethod
    def _get_nested(data: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Get nested value using dot notation.
        
        Args:
            data: Dictionary to search
            key: Key with dot notation (e.g., "a.b.c")
            default: Default if not found
            
        Returns:
            Value or default
        """
        keys = key.split(".")
        current = data
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        
        return current


class ProjectPluginRegistry:
    """Registry for tracking plugin enabled state across projects.
    
    Provides a higher-level API for querying which plugins are
    enabled for the current project.
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the registry.
        
        Args:
            project_root: Project root (auto-detected if None)
        """
        self._project_root = project_root
        self._cache: Dict[str, bool] = {}
    
    @property
    def project_root(self) -> Optional[Path]:
        if self._project_root is None:
            self._project_root = PluginConfigManager._get_current_project_root()
        return self._project_root
    
    def is_enabled(self, plugin_id: str) -> bool:
        """Check if a plugin is enabled for this project.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if enabled
        """
        if plugin_id in self._cache:
            return self._cache[plugin_id]
        
        manager = PluginConfigManager(plugin_id)
        enabled = manager.is_enabled_for_project(self.project_root)
        self._cache[plugin_id] = enabled
        return enabled
    
    def get_enabled_plugins(self, all_plugin_ids: List[str]) -> List[str]:
        """Get list of enabled plugins from a list.
        
        Args:
            all_plugin_ids: All available plugin IDs
            
        Returns:
            List of enabled plugin IDs
        """
        return [pid for pid in all_plugin_ids if self.is_enabled(pid)]
    
    def get_disabled_plugins(self, all_plugin_ids: List[str]) -> List[str]:
        """Get list of disabled plugins from a list.
        
        Args:
            all_plugin_ids: All available plugin IDs
            
        Returns:
            List of disabled plugin IDs
        """
        return [pid for pid in all_plugin_ids if not self.is_enabled(pid)]
    
    def clear_cache(self) -> None:
        """Clear the enabled state cache."""
        self._cache.clear()
