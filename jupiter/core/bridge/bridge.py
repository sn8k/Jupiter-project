"""Jupiter Plugin Bridge - Core Singleton.

Version: 0.1.1

The Bridge is the central orchestrator for Jupiter's plugin system v2.
It manages:
- Plugin discovery and lifecycle
- Contribution registries (CLI, API, UI)
- Service locator for plugins
- Event bus for communication
- Legacy plugin adaptation

Usage:
    from jupiter.core.bridge import Bridge
    
    bridge = Bridge.get_instance()
    bridge.discover()
    bridge.initialize()
"""

from __future__ import annotations

import logging
import importlib
import sys
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type

from jupiter.core.bridge.interfaces import (
    IPlugin,
    IPluginManifest,
    IPluginHealth,
    IPluginMetrics,
    PluginState,
    PluginType,
    Permission,
    CLIContribution,
    APIContribution,
    UIContribution,
    HealthCheckResult,
    HealthStatus,
    PluginMetrics as PluginMetricsData,
    LegacyPlugin,
    ConfigurablePlugin,
)
from jupiter.core.bridge.manifest import (
    PluginManifest,
    generate_manifest_for_legacy,
)
from jupiter.core.bridge.exceptions import (
    BridgeError,
    PluginError,
    ManifestError,
    DependencyError,
    CircularDependencyError,
    LifecycleError,
    ServiceNotFoundError,
)

logger = logging.getLogger(__name__)

# Default plugins directory
DEFAULT_PLUGINS_DIR = Path(__file__).parent.parent.parent / "plugins"

# Core plugins that are always loaded (no manifest, hard-coded)
CORE_PLUGINS = {"bridge", "settings_update"}


@dataclass
class PluginInfo:
    """Runtime information about a loaded plugin."""
    
    manifest: IPluginManifest
    instance: Optional[Any] = None  # Plugin instance
    module: Optional[Any] = None    # Loaded module
    state: PluginState = PluginState.DISCOVERED
    error: Optional[str] = None
    legacy: bool = False            # True if wrapped v1 plugin
    load_order: int = 0             # Order in which plugin was loaded
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize plugin info for API responses."""
        return {
            "id": self.manifest.id,
            "name": self.manifest.name,
            "version": self.manifest.version,
            "description": self.manifest.description,
            "type": self.manifest.plugin_type.value,
            "state": self.state.value,
            "error": self.error,
            "legacy": self.legacy,
            "trust_level": self.manifest.trust_level,
            "permissions": [p.value for p in self.manifest.permissions],
        }


class Bridge:
    """Singleton Bridge that orchestrates the plugin system.
    
    The Bridge is responsible for:
    - Discovering plugins in the plugins directory
    - Managing plugin lifecycle (load, init, shutdown)
    - Registering and resolving contributions
    - Providing services to plugins
    - Event bus for plugin communication
    
    Thread Safety:
        The Bridge uses locks to ensure thread-safe operations.
        Plugin loading and state changes are protected.
    """
    
    _instance: Optional["Bridge"] = None
    _lock: Lock = Lock()
    
    def __new__(cls) -> "Bridge":
        """Ensure only one Bridge instance exists (singleton)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> "Bridge":
        """Get the Bridge singleton instance."""
        return cls()
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton (for testing only)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance._shutdown_all()
            cls._instance = None
    
    def __init__(self) -> None:
        """Initialize the Bridge (only runs once due to singleton)."""
        if getattr(self, "_initialized", False):
            return
        
        # Plugin registries
        self._plugins: Dict[str, PluginInfo] = {}
        self._load_order_counter: int = 0
        
        # Contribution registries
        self._cli_contributions: Dict[str, CLIContribution] = {}
        self._api_contributions: Dict[str, APIContribution] = {}
        self._ui_contributions: Dict[str, UIContribution] = {}
        
        # Remote actions registry (for Meeting integration)
        self._remote_actions: Dict[str, Dict[str, Any]] = {}
        
        # Event subscribers
        self._event_subscribers: Dict[str, List[Callable[[str, Dict[str, Any]], None]]] = {}
        
        # Service references (lazy-loaded)
        self._services: Dict[str, Any] = {}
        
        # Configuration
        self._plugins_dir: Path = DEFAULT_PLUGINS_DIR
        self._developer_mode: bool = False
        
        # State
        self._ready: bool = False
        
        self._initialized = True
        logger.info("Bridge initialized")
    
    # =========================================================================
    # PROPERTIES
    # =========================================================================
    
    @property
    def plugins_dir(self) -> Path:
        """Get the plugins directory."""
        return self._plugins_dir
    
    @plugins_dir.setter
    def plugins_dir(self, path: Path) -> None:
        """Set the plugins directory."""
        self._plugins_dir = Path(path)
    
    @property
    def developer_mode(self) -> bool:
        """Check if developer mode is enabled."""
        return self._developer_mode
    
    @developer_mode.setter
    def developer_mode(self, value: bool) -> None:
        """Set developer mode."""
        self._developer_mode = value
    
    @property
    def is_ready(self) -> bool:
        """Check if the Bridge is fully initialized."""
        return self._ready
    
    # =========================================================================
    # PLUGIN LIFECYCLE
    # =========================================================================
    
    def discover(self) -> List[str]:
        """Discover plugins in the plugins directory.
        
        Scans for:
        1. v2 plugins with plugin.yaml manifest
        2. v1 plugins (Python files/classes matching LegacyPlugin protocol)
        
        Returns:
            List of discovered plugin IDs
        """
        discovered: List[str] = []
        
        if not self._plugins_dir.exists():
            logger.warning("Plugins directory does not exist: %s", self._plugins_dir)
            return discovered
        
        logger.info("Discovering plugins in %s", self._plugins_dir)
        
        # Scan for v2 plugins (directories with plugin.yaml)
        for item in self._plugins_dir.iterdir():
            if item.is_dir() and (item / "plugin.yaml").exists():
                try:
                    manifest = PluginManifest.from_plugin_dir(item, validate=True)
                    self._register_plugin(manifest, legacy=False)
                    discovered.append(manifest.id)
                    logger.debug("Discovered v2 plugin: %s", manifest.id)
                except ManifestError as e:
                    logger.error("Failed to load manifest for %s: %s", item.name, e)
        
        # Scan for v1 plugins (Python files)
        for item in self._plugins_dir.iterdir():
            if item.is_file() and item.suffix == ".py" and not item.name.startswith("_"):
                try:
                    plugin_id = item.stem
                    if plugin_id not in self._plugins:
                        self._discover_legacy_plugin(item)
                        if plugin_id in self._plugins:
                            discovered.append(plugin_id)
                except Exception as e:
                    logger.error("Failed to discover legacy plugin %s: %s", item.name, e)
        
        logger.info("Discovered %d plugins", len(discovered))
        return discovered
    
    def _discover_legacy_plugin(self, path: Path) -> None:
        """Discover and register a legacy v1 plugin.
        
        Args:
            path: Path to the Python file
        """
        module_name = f"jupiter.plugins.{path.stem}"
        
        try:
            # Import the module
            if module_name in sys.modules:
                module = sys.modules[module_name]
            else:
                module = importlib.import_module(module_name)
            
            # Find plugin classes
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if self._is_legacy_plugin_class(attr):
                    # Create manifest for legacy plugin
                    plugin_id = getattr(attr, "name", path.stem)
                    version = getattr(attr, "version", "0.0.0")
                    description = getattr(attr, "description", "")
                    
                    # Check for UI config
                    has_ui = hasattr(attr, "ui_config")
                    ui_type = "none"
                    if has_ui:
                        ui_config = getattr(attr, "ui_config", None)
                        if ui_config and hasattr(ui_config, "ui_type"):
                            ui_type = ui_config.ui_type.value if hasattr(ui_config.ui_type, "value") else str(ui_config.ui_type)
                    
                    manifest = generate_manifest_for_legacy(
                        plugin_id=plugin_id,
                        name=getattr(attr, "name", attr_name),
                        version=version,
                        description=description,
                        has_ui=has_ui,
                        ui_type=ui_type,
                    )
                    
                    info = PluginInfo(
                        manifest=manifest,
                        module=module,
                        state=PluginState.DISCOVERED,
                        legacy=True,
                    )
                    
                    # Store the class for later instantiation
                    info.instance = attr  # Store class, not instance yet
                    
                    self._plugins[plugin_id] = info
                    logger.debug("Discovered legacy plugin: %s", plugin_id)
                    return
                    
        except ImportError as e:
            logger.error("Failed to import legacy plugin %s: %s", path.stem, e)
        except Exception as e:
            logger.error("Error discovering legacy plugin %s: %s", path.stem, e)
    
    def _is_legacy_plugin_class(self, obj: Any) -> bool:
        """Check if an object is a legacy plugin class."""
        if not isinstance(obj, type):
            return False
        
        # Must have name and version attributes
        if not (hasattr(obj, "name") and hasattr(obj, "version")):
            return False
        
        # Must have at least one hook method
        has_hook = (
            hasattr(obj, "on_scan") or 
            hasattr(obj, "on_analyze") or
            hasattr(obj, "configure")
        )
        
        return has_hook
    
    def _register_plugin(self, manifest: IPluginManifest, legacy: bool = False) -> None:
        """Register a plugin with its manifest.
        
        Args:
            manifest: The plugin manifest
            legacy: Whether this is a legacy v1 plugin
        """
        with self._lock:
            if manifest.id in self._plugins:
                logger.warning("Plugin %s already registered, skipping", manifest.id)
                return
            
            self._plugins[manifest.id] = PluginInfo(
                manifest=manifest,
                state=PluginState.DISCOVERED,
                legacy=legacy,
            )
    
    def initialize(self, plugin_ids: Optional[List[str]] = None) -> Dict[str, bool]:
        """Initialize discovered plugins.
        
        Loads plugins in dependency order:
        1. Core plugins (always first)
        2. System plugins
        3. Tool plugins
        
        Args:
            plugin_ids: Specific plugins to initialize, or None for all
            
        Returns:
            Dict of plugin_id -> success status
        """
        results: Dict[str, bool] = {}
        
        # Determine which plugins to load
        if plugin_ids is None:
            to_load = list(self._plugins.keys())
        else:
            to_load = plugin_ids
        
        # Sort by type priority and then resolve dependencies
        sorted_plugins = self._sort_by_load_order(to_load)
        
        logger.info("Initializing %d plugins", len(sorted_plugins))
        
        for plugin_id in sorted_plugins:
            try:
                self._initialize_plugin(plugin_id)
                results[plugin_id] = True
            except Exception as e:
                logger.error("Failed to initialize plugin %s: %s", plugin_id, e)
                results[plugin_id] = False
                
                if plugin_id in self._plugins:
                    self._plugins[plugin_id].state = PluginState.ERROR
                    self._plugins[plugin_id].error = str(e)
        
        self._ready = True
        self._emit_event("BRIDGE_READY", {"plugins": list(results.keys())})
        
        return results
    
    def _sort_by_load_order(self, plugin_ids: List[str]) -> List[str]:
        """Sort plugins by type priority and dependencies.
        
        Order:
        1. Core plugins
        2. System plugins  
        3. Tool plugins
        
        Within each category, dependencies are resolved.
        """
        core: List[str] = []
        system: List[str] = []
        tool: List[str] = []
        
        for pid in plugin_ids:
            if pid not in self._plugins:
                continue
            
            manifest = self._plugins[pid].manifest
            
            if manifest.plugin_type == PluginType.CORE or pid in CORE_PLUGINS:
                core.append(pid)
            elif manifest.plugin_type == PluginType.SYSTEM:
                system.append(pid)
            else:
                tool.append(pid)
        
        # Resolve dependencies within each category
        def resolve_deps(pids: List[str]) -> List[str]:
            # Topological sort
            result: List[str] = []
            visited: Set[str] = set()
            temp_mark: Set[str] = set()
            
            def visit(pid: str, path: List[str]) -> None:
                if pid in temp_mark:
                    raise CircularDependencyError(
                        plugin_id=pid,
                        cycle=path + [pid]
                    )
                if pid in visited:
                    return
                
                temp_mark.add(pid)
                
                if pid in self._plugins:
                    deps = self._plugins[pid].manifest.dependencies
                    for dep_id in deps:
                        if dep_id in pids:
                            visit(dep_id, path + [pid])
                
                temp_mark.remove(pid)
                visited.add(pid)
                result.append(pid)
            
            for pid in pids:
                if pid not in visited:
                    visit(pid, [])
            
            return result
        
        return resolve_deps(core) + resolve_deps(system) + resolve_deps(tool)
    
    def _initialize_plugin(self, plugin_id: str) -> None:
        """Initialize a single plugin.
        
        Args:
            plugin_id: The plugin to initialize
            
        Raises:
            PluginError: If initialization fails
        """
        if plugin_id not in self._plugins:
            raise PluginError(f"Plugin not found", plugin_id=plugin_id)
        
        info = self._plugins[plugin_id]
        
        if info.state == PluginState.READY:
            return  # Already initialized
        
        info.state = PluginState.LOADING
        self._load_order_counter += 1
        info.load_order = self._load_order_counter
        
        logger.debug("Initializing plugin: %s", plugin_id)
        
        try:
            if info.legacy:
                self._initialize_legacy_plugin(info)
            else:
                self._initialize_v2_plugin(info)
            
            # Register contributions
            self._register_contributions(info)
            
            info.state = PluginState.READY
            self._emit_event("PLUGIN_LOADED", {
                "plugin_id": plugin_id,
                "version": info.manifest.version,
            })
            
            logger.info("Plugin %s v%s initialized", plugin_id, info.manifest.version)
            
        except Exception as e:
            info.state = PluginState.ERROR
            info.error = str(e)
            self._emit_event("PLUGIN_ERROR", {
                "plugin_id": plugin_id,
                "error": str(e),
            })
            raise PluginError(str(e), plugin_id=plugin_id) from e
    
    def _initialize_legacy_plugin(self, info: PluginInfo) -> None:
        """Initialize a legacy v1 plugin."""
        # The 'instance' field holds the class, instantiate it
        plugin_class = info.instance
        if plugin_class is None:
            raise PluginError(
                "Legacy plugin has no class instance",
                plugin_id=info.manifest.id
            )
        info.instance = plugin_class()
        
        # Configure if possible
        if isinstance(info.instance, ConfigurablePlugin):
            config = self._get_plugin_config(info.manifest.id)
            info.instance.configure(config)
    
    def _initialize_v2_plugin(self, info: PluginInfo) -> None:
        """Initialize a v2 plugin with manifest."""
        manifest = info.manifest
        
        # Load the module if not already loaded
        if info.module is None and manifest.source_path:
            plugin_dir = manifest.source_path.parent
            module_name = f"jupiter.plugins.{manifest.id}"
            
            # Add to path if needed
            if str(plugin_dir) not in sys.path:
                sys.path.insert(0, str(plugin_dir.parent))
            
            info.module = importlib.import_module(module_name)
        
        # Find and instantiate the plugin class
        if info.module:
            for attr_name in dir(info.module):
                attr = getattr(info.module, attr_name)
                if isinstance(attr, type) and issubclass(attr, IPlugin) and attr is not IPlugin:
                    info.instance = attr()
                    break
        
        # Call init if plugin implements IPlugin
        if info.instance and hasattr(info.instance, "init"):
            # Create a service locator for this plugin
            services = self._create_service_locator(info.manifest.id)
            info.instance.init(services)
    
    def _register_contributions(self, info: PluginInfo) -> None:
        """Register CLI/API/UI contributions from a plugin."""
        manifest = info.manifest
        plugin_id = manifest.id
        
        # Register CLI contributions
        for cli in manifest.cli_contributions:
            key = f"{plugin_id}.{cli.name}"
            self._cli_contributions[key] = cli
            logger.debug("Registered CLI: %s", key)
        
        # Register API contributions
        for api in manifest.api_contributions:
            key = f"{plugin_id}.{api.path}"
            self._api_contributions[key] = api
            logger.debug("Registered API: %s", key)
        
        # Register UI contributions
        for ui in manifest.ui_contributions:
            key = f"{plugin_id}.{ui.id}"
            self._ui_contributions[key] = ui
            logger.debug("Registered UI: %s", key)
    
    def shutdown(self, plugin_id: str) -> None:
        """Shutdown a single plugin.
        
        Args:
            plugin_id: The plugin to shutdown
        """
        if plugin_id not in self._plugins:
            return
        
        info = self._plugins[plugin_id]
        
        if info.state != PluginState.READY:
            return
        
        info.state = PluginState.UNLOADING
        
        try:
            if info.instance and hasattr(info.instance, "shutdown"):
                info.instance.shutdown()
            
            info.state = PluginState.DISABLED
            self._emit_event("PLUGIN_DISABLED", {"plugin_id": plugin_id})
            
            logger.info("Plugin %s shutdown", plugin_id)
            
        except Exception as e:
            logger.error("Error shutting down plugin %s: %s", plugin_id, e)
            info.state = PluginState.ERROR
            info.error = str(e)
    
    def _shutdown_all(self) -> None:
        """Shutdown all plugins (for Bridge reset)."""
        for plugin_id in list(self._plugins.keys()):
            self.shutdown(plugin_id)
        
        self._plugins.clear()
        self._cli_contributions.clear()
        self._api_contributions.clear()
        self._ui_contributions.clear()
        self._ready = False
    
    # =========================================================================
    # PLUGIN QUERIES
    # =========================================================================
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginInfo]:
        """Get info for a specific plugin."""
        return self._plugins.get(plugin_id)
    
    def get_all_plugins(self) -> List[PluginInfo]:
        """Get all registered plugins."""
        return list(self._plugins.values())
    
    def get_plugins_by_state(self, state: PluginState) -> List[PluginInfo]:
        """Get plugins in a specific state."""
        return [p for p in self._plugins.values() if p.state == state]
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[PluginInfo]:
        """Get plugins of a specific type."""
        return [
            p for p in self._plugins.values() 
            if p.manifest.plugin_type == plugin_type
        ]
    
    def is_plugin_enabled(self, plugin_id: str) -> bool:
        """Check if a plugin is enabled and ready."""
        info = self._plugins.get(plugin_id)
        return info is not None and info.state == PluginState.READY
    
    # =========================================================================
    # CONTRIBUTION QUERIES
    # =========================================================================
    
    def get_cli_contributions(self) -> Dict[str, CLIContribution]:
        """Get all CLI contributions."""
        return self._cli_contributions.copy()
    
    def get_api_contributions(self) -> Dict[str, APIContribution]:
        """Get all API contributions."""
        return self._api_contributions.copy()
    
    def get_ui_contributions(self) -> Dict[str, UIContribution]:
        """Get all UI contributions."""
        return self._ui_contributions.copy()
    
    # =========================================================================
    # EVENTS
    # =========================================================================
    
    def subscribe(self, topic: str, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Subscribe to an event topic.
        
        Args:
            topic: Event topic name
            callback: Function to call when event is emitted
        """
        if topic not in self._event_subscribers:
            self._event_subscribers[topic] = []
        self._event_subscribers[topic].append(callback)
    
    def unsubscribe(self, topic: str, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Unsubscribe from an event topic."""
        if topic in self._event_subscribers:
            try:
                self._event_subscribers[topic].remove(callback)
            except ValueError:
                pass
    
    def emit(self, topic: str, payload: Dict[str, Any]) -> None:
        """Emit an event to all subscribers.
        
        Args:
            topic: Event topic name
            payload: Event data
        """
        self._emit_event(topic, payload)
    
    def _emit_event(self, topic: str, payload: Dict[str, Any]) -> None:
        """Internal event emission."""
        callbacks = self._event_subscribers.get(topic, [])
        
        for callback in callbacks:
            try:
                callback(topic, payload)
            except Exception as e:
                logger.error("Error in event callback for %s: %s", topic, e)
    
    # =========================================================================
    # SERVICES
    # =========================================================================
    
    def _create_service_locator(self, plugin_id: str) -> "ServiceLocator":
        """Create a service locator for a plugin."""
        return ServiceLocator(self, plugin_id)
    
    def _get_plugin_config(self, plugin_id: str) -> Dict[str, Any]:
        """Get configuration for a plugin.
        
        Merges:
        1. Plugin default config
        2. Global config overrides
        3. Project config overrides
        """
        config: Dict[str, Any] = {}
        
        # Get manifest defaults
        if plugin_id in self._plugins:
            manifest = self._plugins[plugin_id].manifest
            config.update(manifest.config_defaults)
        
        # TODO: Merge with global and project config
        # This will be implemented in services.py
        
        return config
    
    def register_service(self, name: str, service: Any) -> None:
        """Register a service for plugins to access.
        
        Args:
            name: Service name
            service: Service instance
        """
        self._services[name] = service
        logger.debug("Registered service: %s", name)
    
    def get_service(self, name: str) -> Any:
        """Get a registered service.
        
        Args:
            name: Service name
            
        Returns:
            Service instance
            
        Raises:
            ServiceNotFoundError: If service not found
        """
        if name not in self._services:
            raise ServiceNotFoundError(name)
        return self._services[name]
    
    # =========================================================================
    # HEALTH & METRICS
    # =========================================================================
    
    def health_check(self, plugin_id: str) -> HealthCheckResult:
        """Run health check for a plugin.
        
        Args:
            plugin_id: Plugin to check
            
        Returns:
            Health check result
        """
        if plugin_id not in self._plugins:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                message=f"Plugin {plugin_id} not found"
            )
        
        info = self._plugins[plugin_id]
        
        if info.state != PluginState.READY:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Plugin state: {info.state.value}",
                details={"error": info.error}
            )
        
        # Check if plugin implements health check
        if info.instance and isinstance(info.instance, IPluginHealth):
            try:
                return info.instance.health()
            except Exception as e:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed: {e}"
                )
        
        # Default to healthy if no health check implemented
        return HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="Plugin is ready"
        )
    
    def get_metrics(self, plugin_id: str) -> Optional[PluginMetricsData]:
        """Get metrics for a plugin.
        
        Args:
            plugin_id: Plugin to get metrics for
            
        Returns:
            Plugin metrics or None if not available
        """
        if plugin_id not in self._plugins:
            return None
        
        info = self._plugins[plugin_id]
        
        if info.instance and isinstance(info.instance, IPluginMetrics):
            try:
                return info.instance.metrics()
            except Exception as e:
                logger.error("Error getting metrics for %s: %s", plugin_id, e)
        
        return None
    
    # =========================================================================
    # REMOTE ACTIONS (Meeting integration)
    # =========================================================================
    
    def register_remote_action(
        self, 
        action_id: str, 
        plugin_id: str,
        handler: Callable[[Dict[str, Any]], Any],
        requires_confirmation: bool = True
    ) -> None:
        """Register a remote action callable from Meeting.
        
        Args:
            action_id: Unique action identifier
            plugin_id: Plugin providing the action
            handler: Function to call when action is invoked
            requires_confirmation: Whether user confirmation is required
        """
        self._remote_actions[action_id] = {
            "plugin_id": plugin_id,
            "handler": handler,
            "requires_confirmation": requires_confirmation,
        }
    
    def get_remote_actions(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered remote actions."""
        return {
            action_id: {
                "plugin_id": info["plugin_id"],
                "requires_confirmation": info["requires_confirmation"],
            }
            for action_id, info in self._remote_actions.items()
        }


class ServiceLocator:
    """Provides access to Bridge services for a specific plugin.
    
    Each plugin gets its own ServiceLocator instance that:
    - Provides access to core services
    - Enforces permission checks
    - Provides a logger prefixed with the plugin ID
    """
    
    def __init__(self, bridge: Bridge, plugin_id: str) -> None:
        self._bridge = bridge
        self._plugin_id = plugin_id
        self._logger: Optional[logging.Logger] = None
    
    def get_logger(self) -> logging.Logger:
        """Get a logger prefixed with the plugin ID."""
        if self._logger is None:
            self._logger = logging.getLogger(f"jupiter.plugins.{self._plugin_id}")
        return self._logger
    
    def get_config(self) -> Dict[str, Any]:
        """Get configuration for this plugin."""
        return self._bridge._get_plugin_config(self._plugin_id)
    
    def get_event_bus(self) -> "EventBusProxy":
        """Get an event bus proxy for this plugin."""
        return EventBusProxy(self._bridge, self._plugin_id)
    
    def get_service(self, name: str) -> Any:
        """Get a registered service."""
        return self._bridge.get_service(name)


class EventBusProxy:
    """Proxy for event bus operations scoped to a plugin."""
    
    def __init__(self, bridge: Bridge, plugin_id: str) -> None:
        self._bridge = bridge
        self._plugin_id = plugin_id
    
    def subscribe(self, topic: str, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Subscribe to events."""
        self._bridge.subscribe(topic, callback)
    
    def unsubscribe(self, topic: str, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Unsubscribe from events."""
        self._bridge.unsubscribe(topic, callback)
    
    def emit(self, topic: str, payload: Dict[str, Any]) -> None:
        """Emit an event with plugin context."""
        payload["_source_plugin"] = self._plugin_id
        self._bridge.emit(topic, payload)
