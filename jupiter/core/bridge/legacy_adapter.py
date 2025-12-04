"""Legacy Plugin Adapter for Jupiter Bridge.

Version: 0.1.0

This module provides backward compatibility for legacy plugins that use the
old Plugin protocol (on_scan, on_analyze, configure) rather than the new
Bridge-based manifest system.

The adapter:
- Detects legacy plugins (classes implementing Plugin protocol)
- Generates minimal manifests automatically
- Wraps legacy methods as Bridge-compatible handlers
- Registers legacy plugins with restrictive default permissions

This allows gradual migration without breaking existing functionality.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type, Protocol, runtime_checkable

from jupiter.core.bridge.interfaces import (
    PluginType,
    Permission,
)
from jupiter.core.bridge.exceptions import BridgeError

logger = logging.getLogger(__name__)

__version__ = "0.1.0"


class LegacyPluginError(BridgeError):
    """Error specific to legacy plugin operations."""
    
    def __init__(self, message: str, plugin_id: str = "", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.plugin_id = plugin_id


# =============================================================================
# LEGACY CAPABILITIES (simplified version for legacy plugins)
# =============================================================================

@dataclass
class LegacyCapabilities:
    """Simplified capabilities for legacy plugins.
    
    Legacy plugins have limited capabilities compared to Bridge plugins.
    """
    
    health: bool = False
    metrics: bool = False
    cli: bool = False
    api: bool = False
    ui: bool = False
    jobs: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return asdict(self)


# =============================================================================
# LEGACY PLUGIN DETECTION
# =============================================================================

@runtime_checkable
class LegacyPlugin(Protocol):
    """Protocol for detecting legacy Jupiter plugins.
    
    Legacy plugins have:
    - name, version, description attributes
    - on_scan(report: dict) method
    - on_analyze(summary: dict) method
    - configure(config: dict) method
    """
    
    name: str
    version: str
    description: str
    
    def on_scan(self, report: dict[str, Any]) -> None:
        """Hook called after a scan is completed."""
        ...
    
    def on_analyze(self, summary: dict[str, Any]) -> None:
        """Hook called after an analysis is completed."""
        ...
    
    def configure(self, config: dict[str, Any]) -> None:
        """Configure the plugin with the given settings."""
        ...


@runtime_checkable
class LegacyUIPlugin(Protocol):
    """Protocol for detecting legacy plugins with UI components."""
    
    name: str
    version: str
    description: str
    ui_config: Any  # PluginUIConfig
    
    def get_ui_html(self) -> str:
        ...
    
    def get_ui_js(self) -> str:
        ...


def is_legacy_plugin(cls: Type[Any]) -> bool:
    """Check if a class is a legacy plugin.
    
    Args:
        cls: The class to check.
        
    Returns:
        True if the class implements the legacy Plugin protocol.
    """
    if not inspect.isclass(cls):
        return False
    
    # Check for required attributes
    required_attrs = ["name", "version", "description"]
    for attr in required_attrs:
        if not hasattr(cls, attr):
            return False
    
    # Check for required methods
    required_methods = ["on_scan", "on_analyze", "configure"]
    for method in required_methods:
        if not hasattr(cls, method) or not callable(getattr(cls, method, None)):
            return False
    
    return True


def is_legacy_ui_plugin(cls: Type[Any]) -> bool:
    """Check if a class is a legacy UI plugin.
    
    Args:
        cls: The class to check.
        
    Returns:
        True if the class implements the legacy UIPlugin protocol.
    """
    if not is_legacy_plugin(cls):
        return False
    
    # Additional check for UI components
    if not hasattr(cls, "ui_config"):
        return False
    
    if not hasattr(cls, "get_ui_html") or not hasattr(cls, "get_ui_js"):
        return False
    
    return True


# =============================================================================
# LEGACY MANIFEST WRAPPER
# =============================================================================

@dataclass
class LegacyManifest:
    """Auto-generated manifest for legacy plugins.
    
    This manifest is created automatically when a legacy plugin is detected.
    It provides minimal metadata and restrictive permissions by default.
    
    Note: This is a simplified manifest that doesn't implement the full
    IPluginManifest interface since legacy plugins have limited capabilities.
    """
    
    id: str
    name: str
    version: str
    description: str
    author: str = "unknown"
    homepage: str = ""
    license: str = "unknown"
    type: PluginType = PluginType.TOOL
    capabilities: LegacyCapabilities = field(default_factory=LegacyCapabilities)
    permissions: List[Permission] = field(default_factory=list)
    dependencies: Dict[str, str] = field(default_factory=dict)
    entrypoints: Dict[str, str] = field(default_factory=dict)
    config_schema: Optional[Dict[str, Any]] = None
    extends: bool = False
    legacy: bool = True
    legacy_class: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize manifest to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "homepage": self.homepage,
            "license": self.license,
            "type": self.type.value,
            "capabilities": self.capabilities.to_dict(),
            "permissions": [p.value for p in self.permissions],
            "dependencies": self.dependencies,
            "entrypoints": self.entrypoints,
            "config_schema": self.config_schema,
            "extends": self.extends,
            "legacy": self.legacy,
            "legacy_class": self.legacy_class,
        }
    
    @classmethod
    def from_legacy_class(cls, legacy_cls: Type[Any], module_path: str) -> "LegacyManifest":
        """Create a manifest from a legacy plugin class.
        
        Args:
            legacy_cls: The legacy plugin class.
            module_path: Path to the module containing the class.
            
        Returns:
            A LegacyManifest instance with auto-generated values.
        """
        # Get basic info from class attributes
        name = getattr(legacy_cls, "name", legacy_cls.__name__)
        version = getattr(legacy_cls, "version", "0.0.0")
        description = getattr(legacy_cls, "description", "Legacy plugin")
        
        # Generate plugin ID from class name
        plugin_id = name.lower().replace(" ", "_").replace("-", "_")
        
        # Detect capabilities
        capabilities = LegacyCapabilities(
            health=False,  # Legacy plugins don't have health checks
            metrics=False,  # Legacy plugins don't expose metrics
            cli=False,  # Legacy plugins don't register CLI commands
            api=False,  # Legacy plugins don't register API routes
            ui=is_legacy_ui_plugin(legacy_cls),
            jobs=False,
        )
        
        # Restrictive default permissions for legacy plugins
        permissions: List[Permission] = []
        
        return cls(
            id=plugin_id,
            name=name,
            version=version,
            description=description,
            capabilities=capabilities,
            permissions=permissions,
            legacy=True,
            legacy_class=f"{module_path}:{legacy_cls.__name__}",
        )


# =============================================================================
# LEGACY PLUGIN WRAPPER
# =============================================================================

class LegacyPluginWrapper:
    """Wrapper that adapts a legacy plugin to a Bridge-compatible interface.
    
    This wrapper:
    - Holds a reference to the legacy plugin instance
    - Translates Bridge events to legacy hook calls
    - Provides default implementations for new interface methods
    
    Note: This doesn't inherit from IPlugin since legacy plugins have
    limited capabilities. The Bridge handles them specially.
    """
    
    def __init__(
        self,
        manifest: LegacyManifest,
        legacy_instance: Any,
    ):
        """Initialize the wrapper.
        
        Args:
            manifest: The auto-generated manifest.
            legacy_instance: Instance of the legacy plugin class.
        """
        self._manifest = manifest
        self._legacy = legacy_instance
        self._config: Dict[str, Any] = {}
        self._initialized = False
        self._error: Optional[str] = None
        
        logger.debug(
            "LegacyPluginWrapper created for %s (class: %s)",
            manifest.id,
            manifest.legacy_class,
        )
    
    @property
    def manifest(self) -> LegacyManifest:
        """Get the plugin manifest."""
        return self._manifest
    
    @property
    def legacy_instance(self) -> Any:
        """Get the wrapped legacy plugin instance."""
        return self._legacy
    
    def init(self, config: Dict[str, Any]) -> None:
        """Initialize the plugin with configuration.
        
        Calls the legacy configure() method.
        
        Args:
            config: Plugin configuration.
        """
        self._config = config
        try:
            if hasattr(self._legacy, "configure") and callable(self._legacy.configure):
                self._legacy.configure(config)
            self._initialized = True
            self._error = None
            logger.info("Legacy plugin %s initialized", self._manifest.id)
        except Exception as e:
            self._error = str(e)
            logger.error("Failed to initialize legacy plugin %s: %s", self._manifest.id, e)
            raise LegacyPluginError(
                f"Legacy plugin init failed: {e}",
                plugin_id=self._manifest.id
            ) from e
    
    def shutdown(self) -> None:
        """Shutdown the plugin.
        
        Legacy plugins don't have a shutdown hook, so this is a no-op.
        """
        logger.debug("Legacy plugin %s shutdown (no-op)", self._manifest.id)
        self._initialized = False
    
    def health(self) -> Dict[str, Any]:
        """Health check for the plugin.
        
        Legacy plugins don't have health checks, returns basic status.
        
        Returns:
            Health status dictionary.
        """
        return {
            "status": "healthy" if self._initialized and not self._error else "unhealthy",
            "legacy": True,
            "error": self._error,
            "initialized": self._initialized,
        }
    
    def metrics(self) -> Dict[str, Any]:
        """Get plugin metrics.
        
        Legacy plugins don't expose metrics, returns empty dict.
        
        Returns:
            Empty metrics dictionary.
        """
        return {
            "legacy": True,
            "metrics_supported": False,
        }
    
    def on_scan(self, report: Dict[str, Any]) -> None:
        """Handle scan completed event.
        
        Delegates to the legacy on_scan hook.
        
        Args:
            report: The scan report.
        """
        if not self._initialized:
            logger.warning("Legacy plugin %s not initialized, skipping on_scan", self._manifest.id)
            return
        
        try:
            if hasattr(self._legacy, "on_scan") and callable(self._legacy.on_scan):
                self._legacy.on_scan(report)
        except Exception as e:
            logger.error("Legacy plugin %s on_scan failed: %s", self._manifest.id, e)
            self._error = str(e)
    
    def on_analyze(self, summary: Dict[str, Any]) -> None:
        """Handle analyze completed event.
        
        Delegates to the legacy on_analyze hook.
        
        Args:
            summary: The analysis summary.
        """
        if not self._initialized:
            logger.warning("Legacy plugin %s not initialized, skipping on_analyze", self._manifest.id)
            return
        
        try:
            if hasattr(self._legacy, "on_analyze") and callable(self._legacy.on_analyze):
                self._legacy.on_analyze(summary)
        except Exception as e:
            logger.error("Legacy plugin %s on_analyze failed: %s", self._manifest.id, e)
            self._error = str(e)
    
    def get_ui_html(self) -> Optional[str]:
        """Get UI HTML if available.
        
        Returns:
            HTML string or None.
        """
        if not self._manifest.capabilities.ui:
            return None
        
        if hasattr(self._legacy, "get_ui_html") and callable(self._legacy.get_ui_html):
            try:
                result = self._legacy.get_ui_html()
                return str(result) if result is not None else None
            except Exception as e:
                logger.error("Legacy plugin %s get_ui_html failed: %s", self._manifest.id, e)
        
        return None
    
    def get_ui_js(self) -> Optional[str]:
        """Get UI JavaScript if available.
        
        Returns:
            JavaScript string or None.
        """
        if not self._manifest.capabilities.ui:
            return None
        
        if hasattr(self._legacy, "get_ui_js") and callable(self._legacy.get_ui_js):
            try:
                result = self._legacy.get_ui_js()
                return str(result) if result is not None else None
            except Exception as e:
                logger.error("Legacy plugin %s get_ui_js failed: %s", self._manifest.id, e)
        
        return None


# =============================================================================
# LEGACY ADAPTER
# =============================================================================

class LegacyAdapter:
    """Adapter for detecting and loading legacy plugins.
    
    The LegacyAdapter scans the legacy plugins directory, detects plugins
    using the old protocol, wraps them with auto-generated manifests,
    and provides them to the Bridge for registration.
    
    Usage:
        adapter = LegacyAdapter()
        legacy_plugins = adapter.discover("jupiter/plugins")
        
        for wrapper in legacy_plugins:
            bridge.register_legacy_plugin(wrapper)
    """
    
    def __init__(self):
        """Initialize the legacy adapter."""
        self._discovered: Dict[str, LegacyPluginWrapper] = {}
        self._errors: Dict[str, str] = {}
        self._scan_count = 0
        
        logger.debug("LegacyAdapter initialized")
    
    @property
    def discovered_plugins(self) -> Dict[str, LegacyPluginWrapper]:
        """Get discovered legacy plugins."""
        return self._discovered.copy()
    
    @property
    def discovery_errors(self) -> Dict[str, str]:
        """Get discovery errors by module path."""
        return self._errors.copy()
    
    def discover(
        self,
        plugins_dir: Path,
        exclude: Optional[Set[str]] = None,
    ) -> List[LegacyPluginWrapper]:
        """Discover legacy plugins in a directory.
        
        Scans Python files for classes implementing the legacy Plugin protocol.
        
        Args:
            plugins_dir: Path to the plugins directory.
            exclude: Set of plugin IDs to exclude (e.g., already migrated).
            
        Returns:
            List of LegacyPluginWrapper instances.
        """
        exclude = exclude or set()
        self._scan_count += 1
        
        logger.info("Discovering legacy plugins in %s", plugins_dir)
        
        if not plugins_dir.exists():
            logger.warning("Plugins directory does not exist: %s", plugins_dir)
            return []
        
        discovered: List[LegacyPluginWrapper] = []
        
        # Scan Python files
        for py_file in plugins_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            
            if py_file.name == "bridge_plugin.py":
                # Skip the bridge plugin itself
                continue
            
            try:
                wrapper = self._load_legacy_module(py_file, exclude)
                if wrapper:
                    discovered.append(wrapper)
                    self._discovered[wrapper.manifest.id] = wrapper
            except Exception as e:
                module_path = str(py_file)
                self._errors[module_path] = str(e)
                logger.warning("Failed to load legacy module %s: %s", py_file.name, e)
        
        logger.info(
            "Discovered %d legacy plugins (%d errors)",
            len(discovered),
            len(self._errors),
        )
        
        return discovered
    
    def _load_legacy_module(
        self,
        module_path: Path,
        exclude: Set[str],
    ) -> Optional[LegacyPluginWrapper]:
        """Load a legacy plugin from a module file.
        
        Args:
            module_path: Path to the Python module.
            exclude: Set of plugin IDs to exclude.
            
        Returns:
            LegacyPluginWrapper or None if not a valid legacy plugin.
        """
        module_name = module_path.stem
        
        # Build the import path
        # Assuming structure: jupiter/plugins/<name>.py
        import_path = f"jupiter.plugins.{module_name}"
        
        logger.debug("Attempting to load legacy module: %s", import_path)
        
        try:
            # Import the module
            if import_path in sys.modules:
                module = sys.modules[import_path]
            else:
                module = importlib.import_module(import_path)
        except ImportError as e:
            logger.debug("Could not import %s: %s", import_path, e)
            return None
        
        # Find legacy plugin classes in the module
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Skip imported classes (not defined in this module)
            if obj.__module__ != import_path:
                continue
            
            # Check if it's a legacy plugin
            if not is_legacy_plugin(obj):
                continue
            
            logger.debug("Found legacy plugin class: %s.%s", import_path, name)
            
            # Create manifest
            manifest = LegacyManifest.from_legacy_class(obj, import_path)
            
            # Check exclusion
            if manifest.id in exclude:
                logger.debug("Skipping excluded legacy plugin: %s", manifest.id)
                continue
            
            # Instantiate the legacy plugin
            try:
                instance = obj()
            except Exception as e:
                logger.warning("Failed to instantiate legacy plugin %s: %s", name, e)
                continue
            
            # Create wrapper
            wrapper = LegacyPluginWrapper(manifest, instance)
            
            logger.info(
                "Loaded legacy plugin: %s v%s (%s)",
                manifest.name,
                manifest.version,
                manifest.legacy_class,
            )
            
            return wrapper
        
        return None
    
    def get_plugin(self, plugin_id: str) -> Optional[LegacyPluginWrapper]:
        """Get a discovered legacy plugin by ID.
        
        Args:
            plugin_id: The plugin ID.
            
        Returns:
            LegacyPluginWrapper or None.
        """
        return self._discovered.get(plugin_id)
    
    def clear(self) -> None:
        """Clear all discovered plugins."""
        self._discovered.clear()
        self._errors.clear()
        logger.debug("LegacyAdapter cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics.
        
        Returns:
            Dictionary with discovery statistics.
        """
        return {
            "discovered_count": len(self._discovered),
            "error_count": len(self._errors),
            "scan_count": self._scan_count,
            "plugins": [
                {
                    "id": w.manifest.id,
                    "name": w.manifest.name,
                    "version": w.manifest.version,
                    "has_ui": w.manifest.capabilities.ui,
                }
                for w in self._discovered.values()
            ],
            "errors": self._errors,
        }


# =============================================================================
# MODULE-LEVEL SINGLETON
# =============================================================================

_adapter: Optional[LegacyAdapter] = None


def get_legacy_adapter() -> LegacyAdapter:
    """Get the global LegacyAdapter instance.
    
    Returns:
        The singleton LegacyAdapter.
    """
    global _adapter
    if _adapter is None:
        _adapter = LegacyAdapter()
    return _adapter


def init_legacy_adapter() -> LegacyAdapter:
    """Initialize and return the global LegacyAdapter.
    
    Returns:
        The initialized LegacyAdapter.
    """
    global _adapter
    _adapter = LegacyAdapter()
    logger.info("LegacyAdapter initialized")
    return _adapter


def shutdown_legacy_adapter() -> None:
    """Shutdown and clear the global LegacyAdapter."""
    global _adapter
    if _adapter:
        _adapter.clear()
        _adapter = None
        logger.info("LegacyAdapter shutdown")


def discover_legacy_plugins(
    plugins_dir: Path,
    exclude: Optional[Set[str]] = None,
) -> List[LegacyPluginWrapper]:
    """Discover legacy plugins using the global adapter.
    
    Convenience function that uses the singleton adapter.
    
    Args:
        plugins_dir: Path to the plugins directory.
        exclude: Set of plugin IDs to exclude.
        
    Returns:
        List of discovered LegacyPluginWrapper instances.
    """
    adapter = get_legacy_adapter()
    return adapter.discover(plugins_dir, exclude)
