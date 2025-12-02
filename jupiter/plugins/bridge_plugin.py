"""Jupiter Plugin Bridge - Core Services Gateway for Plugins.

Version: 1.0.2

The Bridge is a system plugin that provides a stable, versioned API layer
between plugins and Jupiter's core functionality. It acts as a mediator
to prevent plugins from directly importing core modules, enabling:

1. **Decoupling**: Plugins don't need to know Jupiter's internal structure
2. **Versioning**: APIs can evolve without breaking existing plugins
3. **Discovery**: Plugins can query available capabilities at runtime
4. **Lazy Loading**: Services are instantiated only when needed
5. **Future-proofing**: New services can be added without modifying plugins

Architecture:
------------
- ServiceRegistry: Central registry of available services
- CapabilityProvider: Interface for services to declare their capabilities
- BridgeContext: The main interface plugins receive to access services
- Service Adapters: Thin wrappers around core modules with stable APIs

Design Principles:
-----------------
1. Services are LAZY: Only loaded when first accessed
2. Capabilities are DECLARATIVE: Services declare what they can do
3. APIs are VERSIONED: Breaking changes require version bumps
4. Errors are GRACEFUL: Missing services return None or raise BridgeError
5. State is MINIMAL: Bridge holds references, not data
"""

from __future__ import annotations

import logging
import importlib
import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import (
    Any, Callable, Dict, Generic, List, Optional, Protocol, 
    Set, Type, TypeVar, Union, cast, runtime_checkable
)
from weakref import WeakValueDictionary

from jupiter.plugins import PluginUIConfig, PluginUIType

logger = logging.getLogger(__name__)

PLUGIN_VERSION = "1.0.2"
BRIDGE_API_VERSION = "1.0"  # Semantic version for the Bridge API


# =============================================================================
# EXCEPTIONS
# =============================================================================

class BridgeError(Exception):
    """Base exception for Bridge-related errors."""
    
    def __init__(self, message: str, service: Optional[str] = None):
        super().__init__(message)
        self.service = service


class ServiceNotFoundError(BridgeError):
    """Raised when a requested service is not registered."""
    pass


class ServiceLoadError(BridgeError):
    """Raised when a service fails to load."""
    pass


class CapabilityNotFoundError(BridgeError):
    """Raised when a requested capability is not available."""
    pass


# =============================================================================
# SERVICE CAPABILITY SYSTEM
# =============================================================================

class ServiceCategory(str, Enum):
    """Categories of services available through the Bridge."""
    
    CORE = "core"           # Core functionality (scanner, analyzer, etc.)
    IO = "io"               # Input/Output (file system, network)
    EVENTS = "events"       # Event system and notifications
    CONFIG = "config"       # Configuration management
    DATA = "data"           # Data access (cache, history, state)
    UI = "ui"               # UI-related services
    SECURITY = "security"   # Security and permissions
    EXTERNAL = "external"   # External service integrations


@dataclass
class Capability:
    """Describes a single capability provided by a service."""
    
    name: str
    description: str
    method: str                    # The method name that provides this capability
    parameters: List[str] = field(default_factory=list)
    returns: str = "Any"
    since_version: str = "1.0"     # Bridge API version when added
    deprecated: bool = False
    deprecated_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ServiceDescriptor:
    """Describes a service available through the Bridge."""
    
    name: str
    category: ServiceCategory
    description: str
    version: str
    capabilities: List[Capability] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # Other services needed
    lazy: bool = True              # If True, only loaded when first accessed
    system: bool = False           # If True, cannot be disabled
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "version": self.version,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "dependencies": self.dependencies,
            "lazy": self.lazy,
            "system": self.system,
        }


# =============================================================================
# SERVICE INTERFACE
# =============================================================================

T = TypeVar("T")


@runtime_checkable
class ServiceProvider(Protocol):
    """Protocol that all Bridge services must implement."""
    
    @classmethod
    def get_descriptor(cls) -> ServiceDescriptor:
        """Return the service descriptor."""
        ...
    
    def initialize(self, bridge: "BridgeContext") -> None:
        """Initialize the service with access to the bridge."""
        ...
    
    def shutdown(self) -> None:
        """Clean up resources when the service is stopped."""
        ...


class BaseService(ABC):
    """Base class for Bridge services with common functionality."""
    
    _bridge: Optional["BridgeContext"] = None
    
    @classmethod
    @abstractmethod
    def get_descriptor(cls) -> ServiceDescriptor:
        """Return the service descriptor."""
        pass
    
    def initialize(self, bridge: "BridgeContext") -> None:
        """Initialize the service with access to the bridge."""
        self._bridge = bridge
        logger.debug("[Bridge] Service %s initialized", self.__class__.__name__)
    
    def shutdown(self) -> None:
        """Clean up resources when the service is stopped."""
        self._bridge = None
        logger.debug("[Bridge] Service %s shut down", self.__class__.__name__)
    
    def _require_capability(self, capability: str) -> None:
        """Raise an error if the capability is not available."""
        descriptor = self.get_descriptor()
        if not any(c.name == capability for c in descriptor.capabilities):
            raise CapabilityNotFoundError(
                f"Capability '{capability}' not found in service '{descriptor.name}'"
            )


# =============================================================================
# SERVICE REGISTRY
# =============================================================================

class ServiceRegistry:
    """Registry for managing Bridge services.
    
    The registry handles:
    - Service registration and discovery
    - Lazy instantiation of services
    - Dependency resolution
    - Service lifecycle management
    """
    
    def __init__(self) -> None:
        self._service_classes: Dict[str, Type[ServiceProvider]] = {}
        self._instances: Dict[str, ServiceProvider] = {}
        self._descriptors: Dict[str, ServiceDescriptor] = {}
        self._load_order: List[str] = []  # For proper shutdown
        
    def register(self, service_class: Type[ServiceProvider]) -> None:
        """Register a service class."""
        descriptor = service_class.get_descriptor()
        name = descriptor.name
        
        if name in self._service_classes:
            logger.warning("[Bridge] Service '%s' already registered, replacing", name)
        
        self._service_classes[name] = service_class
        self._descriptors[name] = descriptor
        logger.info(
            "[Bridge] Registered service: %s v%s (%s)",
            name, descriptor.version, descriptor.category.value
        )
    
    def unregister(self, name: str) -> bool:
        """Unregister a service."""
        if name not in self._service_classes:
            return False
        
        # Shutdown instance if loaded
        if name in self._instances:
            try:
                self._instances[name].shutdown()
            except Exception as e:
                logger.error("[Bridge] Error shutting down service '%s': %s", name, e)
            del self._instances[name]
            self._load_order.remove(name)
        
        del self._service_classes[name]
        del self._descriptors[name]
        logger.info("[Bridge] Unregistered service: %s", name)
        return True
    
    def get(self, name: str, bridge: "BridgeContext") -> Optional[ServiceProvider]:
        """Get a service instance, instantiating if necessary."""
        if name not in self._service_classes:
            logger.warning("[Bridge] Service '%s' not found", name)
            return None
        
        # Lazy instantiation
        if name not in self._instances:
            service_class = self._service_classes[name]
            descriptor = self._descriptors[name]
            
            # Check dependencies
            for dep in descriptor.dependencies:
                if dep not in self._service_classes:
                    raise ServiceLoadError(
                        f"Service '{name}' requires '{dep}' which is not registered",
                        service=name
                    )
                # Ensure dependency is loaded
                self.get(dep, bridge)
            
            try:
                instance = service_class()
                instance.initialize(bridge)
                self._instances[name] = instance
                self._load_order.append(name)
                logger.debug("[Bridge] Instantiated service: %s", name)
            except Exception as e:
                raise ServiceLoadError(
                    f"Failed to instantiate service '{name}': {e}",
                    service=name
                ) from e
        
        return self._instances[name]
    
    def has_service(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._service_classes
    
    def is_loaded(self, name: str) -> bool:
        """Check if a service instance exists."""
        return name in self._instances
    
    def list_services(self) -> List[ServiceDescriptor]:
        """List all registered services."""
        return list(self._descriptors.values())
    
    def list_by_category(self, category: ServiceCategory) -> List[ServiceDescriptor]:
        """List services in a specific category."""
        return [d for d in self._descriptors.values() if d.category == category]
    
    def find_by_capability(self, capability: str) -> List[str]:
        """Find services that provide a specific capability."""
        result = []
        for name, descriptor in self._descriptors.items():
            if any(c.name == capability for c in descriptor.capabilities):
                result.append(name)
        return result
    
    def shutdown_all(self) -> None:
        """Shutdown all loaded services in reverse order."""
        for name in reversed(self._load_order):
            if name in self._instances:
                try:
                    self._instances[name].shutdown()
                    logger.debug("[Bridge] Shut down service: %s", name)
                except Exception as e:
                    logger.error("[Bridge] Error shutting down '%s': %s", name, e)
        
        self._instances.clear()
        self._load_order.clear()


# =============================================================================
# BRIDGE CONTEXT
# =============================================================================

class BridgeContext:
    """The main interface plugins use to access Bridge services.
    
    This is the object plugins receive when they request the Bridge.
    It provides a clean, stable API for accessing core functionality.
    
    Usage in plugins:
        from jupiter.plugins import get_bridge
        
        bridge = get_bridge()
        scanner = bridge.get_service("scanner")
        if scanner:
            files = scanner.scan_directory(path)
    """
    
    def __init__(self, registry: ServiceRegistry) -> None:
        self._registry = registry
        self._plugin_manager: Any = None  # Set by PluginBridge
        self._app_state: Any = None       # FastAPI app.state reference
    
    @property
    def api_version(self) -> str:
        """Get the Bridge API version."""
        return BRIDGE_API_VERSION
    
    def get_service(self, name: str) -> Optional[ServiceProvider]:
        """Get a service by name.
        
        Args:
            name: The service name (e.g., "scanner", "events", "config")
            
        Returns:
            The service instance, or None if not found.
            
        Example:
            scanner = bridge.get_service("scanner")
            if scanner:
                result = scanner.scan(path)
        """
        return self._registry.get(name, self)
    
    def require_service(self, name: str) -> ServiceProvider:
        """Get a service, raising an error if not found.
        
        Args:
            name: The service name
            
        Returns:
            The service instance
            
        Raises:
            ServiceNotFoundError: If the service is not registered
        """
        service = self.get_service(name)
        if service is None:
            raise ServiceNotFoundError(f"Required service '{name}' not found", service=name)
        return service
    
    def has_service(self, name: str) -> bool:
        """Check if a service is available."""
        return self._registry.has_service(name)
    
    def has_capability(self, capability: str) -> bool:
        """Check if any service provides a capability."""
        return len(self._registry.find_by_capability(capability)) > 0
    
    def list_services(self) -> List[Dict[str, Any]]:
        """List all available services with their descriptors."""
        return [d.to_dict() for d in self._registry.list_services()]
    
    def list_capabilities(self) -> List[str]:
        """List all available capabilities across all services."""
        capabilities: Set[str] = set()
        for descriptor in self._registry.list_services():
            for cap in descriptor.capabilities:
                capabilities.add(cap.name)
        return sorted(capabilities)
    
    def find_service_for(self, capability: str) -> Optional[str]:
        """Find the first service that provides a capability."""
        services = self._registry.find_by_capability(capability)
        return services[0] if services else None
    
    def invoke(self, capability: str, *args: Any, **kwargs: Any) -> Any:
        """Invoke a capability on the first service that provides it.
        
        This is a convenience method for when you don't care which
        service provides the capability, just that it exists.
        
        Args:
            capability: The capability name
            *args, **kwargs: Arguments to pass to the capability method
            
        Returns:
            The result of the capability method
            
        Raises:
            CapabilityNotFoundError: If no service provides the capability
        """
        service_name = self.find_service_for(capability)
        if not service_name:
            raise CapabilityNotFoundError(f"No service provides capability '{capability}'")
        
        service = self.require_service(service_name)
        
        # Find the method that provides this capability
        descriptor = self._registry._descriptors[service_name]
        cap = next((c for c in descriptor.capabilities if c.name == capability), None)
        if not cap:
            raise CapabilityNotFoundError(f"Capability '{capability}' not found")
        
        method = getattr(service, cap.method, None)
        if not method or not callable(method):
            raise CapabilityNotFoundError(
                f"Method '{cap.method}' not found for capability '{capability}'"
            )
        
        return method(*args, **kwargs)


# =============================================================================
# BUILT-IN SERVICES
# =============================================================================

class EventsService(BaseService):
    """Service for emitting and listening to Jupiter events."""
    
    @classmethod
    def get_descriptor(cls) -> ServiceDescriptor:
        return ServiceDescriptor(
            name="events",
            category=ServiceCategory.EVENTS,
            description="Event system for broadcasting and receiving notifications",
            version="1.0.0",
            capabilities=[
                Capability(
                    name="emit_event",
                    description="Broadcast an event to all listeners",
                    method="emit",
                    parameters=["event_type", "payload"],
                    returns="None"
                ),
                Capability(
                    name="create_event",
                    description="Create a JupiterEvent object",
                    method="create_event",
                    parameters=["event_type", "payload"],
                    returns="JupiterEvent"
                ),
            ],
            system=True
        )
    
    def __init__(self) -> None:
        self._ws_manager: Any = None
        self._event_class: Any = None
    
    def initialize(self, bridge: BridgeContext) -> None:
        super().initialize(bridge)
        # Lazy import to avoid circular dependencies
        from jupiter.core.events import JupiterEvent
        from jupiter.server.ws import manager
        self._event_class = JupiterEvent
        self._ws_manager = manager
    
    def create_event(self, event_type: str, payload: Dict[str, Any]) -> Any:
        """Create a JupiterEvent object."""
        return self._event_class(type=event_type, payload=payload)
    
    async def emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Emit an event to all WebSocket clients."""
        if self._ws_manager:
            event = self.create_event(event_type, payload)
            await self._ws_manager.broadcast(event)
            logger.debug("[Bridge.Events] Emitted %s", event_type)


class ConfigService(BaseService):
    """Service for reading and writing configuration."""
    
    @classmethod
    def get_descriptor(cls) -> ServiceDescriptor:
        return ServiceDescriptor(
            name="config",
            category=ServiceCategory.CONFIG,
            description="Configuration management service",
            version="1.0.0",
            capabilities=[
                Capability(
                    name="get_config",
                    description="Get the current configuration",
                    method="get_config",
                    returns="JupiterConfig"
                ),
                Capability(
                    name="get_project_root",
                    description="Get the current project root path",
                    method="get_project_root",
                    returns="Path"
                ),
                Capability(
                    name="get_plugin_config",
                    description="Get configuration for a specific plugin",
                    method="get_plugin_config",
                    parameters=["plugin_name"],
                    returns="Dict[str, Any]"
                ),
            ],
            system=True
        )
    
    def get_config(self) -> Any:
        """Get the current Jupiter configuration."""
        if self._bridge and self._bridge._app_state:
            return getattr(self._bridge._app_state, "config", None)
        return None
    
    def get_project_root(self) -> Optional[Path]:
        """Get the current project root."""
        if self._bridge and self._bridge._app_state:
            root = getattr(self._bridge._app_state, "project_root", None)
            return Path(root) if root else None
        return None
    
    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Get configuration for a specific plugin."""
        config = self.get_config()
        if config and hasattr(config, "plugins") and config.plugins:
            return config.plugins.settings.get(plugin_name, {})
        return {}


class ScannerService(BaseService):
    """Service for filesystem scanning operations."""
    
    @classmethod
    def get_descriptor(cls) -> ServiceDescriptor:
        return ServiceDescriptor(
            name="scanner",
            category=ServiceCategory.CORE,
            description="Filesystem scanning and analysis",
            version="1.0.0",
            capabilities=[
                Capability(
                    name="scan_directory",
                    description="Scan a directory and return file information",
                    method="scan",
                    parameters=["path", "options"],
                    returns="Dict[str, Any]"
                ),
                Capability(
                    name="list_files",
                    description="List all files in a directory",
                    method="list_files",
                    parameters=["path", "extensions"],
                    returns="List[Path]"
                ),
            ],
            dependencies=["config"]
        )
    
    def __init__(self) -> None:
        self._scanner_module: Any = None
    
    def initialize(self, bridge: BridgeContext) -> None:
        super().initialize(bridge)
        from jupiter.core import scanner
        self._scanner_module = scanner
    
    def scan(
        self, 
        path: Optional[Path] = None, 
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run a scan on the specified path."""
        if path is None:
            config_service = cast(Any, self._bridge.get_service("config")) if self._bridge else None
            if config_service:
                path = config_service.get_project_root()
        
        if path is None:
            return {"error": "No path specified and no project root configured"}
        
        options = options or {}
        return self._scanner_module.scan_project(
            root=path,
            show_hidden=options.get("show_hidden", False),
            ignore_globs=options.get("ignore_globs", [])
        )
    
    def list_files(
        self, 
        path: Path, 
        extensions: Optional[List[str]] = None
    ) -> List[Path]:
        """List files in a directory, optionally filtered by extension."""
        if not path.exists():
            return []
        
        files = []
        for item in path.rglob("*"):
            if item.is_file():
                if extensions is None or item.suffix.lower() in extensions:
                    files.append(item)
        return files


class CacheService(BaseService):
    """Service for caching scan results and other data."""
    
    @classmethod
    def get_descriptor(cls) -> ServiceDescriptor:
        return ServiceDescriptor(
            name="cache",
            category=ServiceCategory.DATA,
            description="Caching service for scan results and metadata",
            version="1.0.0",
            capabilities=[
                Capability(
                    name="get_cached_report",
                    description="Get the last cached scan report",
                    method="get_last_report",
                    returns="Optional[Dict[str, Any]]"
                ),
                Capability(
                    name="save_report",
                    description="Save a scan report to cache",
                    method="save_report",
                    parameters=["report"],
                    returns="bool"
                ),
                Capability(
                    name="clear_cache",
                    description="Clear all cached data",
                    method="clear",
                    returns="bool"
                ),
            ],
            dependencies=["config"]
        )
    
    def __init__(self) -> None:
        self._cache_module: Any = None
    
    def initialize(self, bridge: BridgeContext) -> None:
        super().initialize(bridge)
        from jupiter.core import cache
        self._cache_module = cache
    
    def get_last_report(self) -> Optional[Dict[str, Any]]:
        """Get the last cached scan report."""
        config_service = cast(Any, self._bridge.get_service("config")) if self._bridge else None
        if not config_service:
            return None
        
        root = config_service.get_project_root()
        if not root:
            return None
        
        return self._cache_module.load_cached_report(root)
    
    def save_report(self, report: Dict[str, Any]) -> bool:
        """Save a report to cache."""
        config_service = cast(Any, self._bridge.get_service("config")) if self._bridge else None
        if not config_service:
            return False
        
        root = config_service.get_project_root()
        if not root:
            return False
        
        try:
            self._cache_module.save_cached_report(root, report)
            return True
        except Exception as e:
            logger.error("[Bridge.Cache] Failed to save report: %s", e)
            return False
    
    def clear(self) -> bool:
        """Clear all cached data."""
        config_service = cast(Any, self._bridge.get_service("config")) if self._bridge else None
        if not config_service:
            return False
        
        root = config_service.get_project_root()
        if not root:
            return False
        
        try:
            self._cache_module.clear_cache(root)
            return True
        except Exception as e:
            logger.error("[Bridge.Cache] Failed to clear cache: %s", e)
            return False


class HistoryService(BaseService):
    """Service for snapshot history management."""
    
    @classmethod
    def get_descriptor(cls) -> ServiceDescriptor:
        return ServiceDescriptor(
            name="history",
            category=ServiceCategory.DATA,
            description="Snapshot history and diff functionality",
            version="1.0.0",
            capabilities=[
                Capability(
                    name="list_snapshots",
                    description="List all available snapshots",
                    method="list_snapshots",
                    returns="List[Dict[str, Any]]"
                ),
                Capability(
                    name="get_snapshot",
                    description="Get a specific snapshot by ID",
                    method="get_snapshot",
                    parameters=["snapshot_id"],
                    returns="Optional[Dict[str, Any]]"
                ),
                Capability(
                    name="create_snapshot",
                    description="Create a new snapshot from a report",
                    method="create_snapshot",
                    parameters=["report", "label"],
                    returns="str"
                ),
                Capability(
                    name="diff_snapshots",
                    description="Compare two snapshots",
                    method="diff_snapshots",
                    parameters=["id1", "id2"],
                    returns="Dict[str, Any]"
                ),
            ],
            dependencies=["config"]
        )
    
    def __init__(self) -> None:
        self._history_module: Any = None
    
    def initialize(self, bridge: BridgeContext) -> None:
        super().initialize(bridge)
        from jupiter.core import history
        self._history_module = history
    
    def _get_root(self) -> Optional[Path]:
        config_service = cast(Any, self._bridge.get_service("config")) if self._bridge else None
        return config_service.get_project_root() if config_service else None
    
    def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all snapshots."""
        root = self._get_root()
        if not root:
            return []
        return self._history_module.list_snapshots(root)
    
    def get_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Get a snapshot by ID."""
        root = self._get_root()
        if not root:
            return None
        return self._history_module.get_snapshot(root, snapshot_id)
    
    def create_snapshot(
        self, 
        report: Dict[str, Any], 
        label: Optional[str] = None
    ) -> str:
        """Create a snapshot from a report."""
        root = self._get_root()
        if not root:
            raise BridgeError("No project root configured")
        return self._history_module.save_snapshot(root, report, label)
    
    def diff_snapshots(self, id1: str, id2: str) -> Dict[str, Any]:
        """Compare two snapshots."""
        root = self._get_root()
        if not root:
            return {"error": "No project root configured"}
        return self._history_module.diff_snapshots(root, id1, id2)


class LoggingService(BaseService):
    """Service for structured logging."""
    
    @classmethod
    def get_descriptor(cls) -> ServiceDescriptor:
        return ServiceDescriptor(
            name="logging",
            category=ServiceCategory.IO,
            description="Structured logging service for plugins",
            version="1.0.0",
            capabilities=[
                Capability(
                    name="get_logger",
                    description="Get a logger instance for a plugin",
                    method="get_logger",
                    parameters=["name"],
                    returns="logging.Logger"
                ),
                Capability(
                    name="set_level",
                    description="Set the global log level",
                    method="set_level",
                    parameters=["level"],
                    returns="None"
                ),
            ],
            system=True
        )
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger for a plugin."""
        return logging.getLogger(f"jupiter.plugins.{name}")
    
    def set_level(self, level: Union[int, str]) -> None:
        """Set the global log level."""
        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.INFO)
        logging.getLogger("jupiter").setLevel(level)


# =============================================================================
# PLUGIN BRIDGE (Main Plugin Class)
# =============================================================================

class PluginBridge:
    """System plugin that provides the Bridge interface to other plugins.
    
    This is the main plugin class that manages the Bridge lifecycle
    and provides the BridgeContext to requesting plugins.
    """
    
    name = "bridge"
    version = PLUGIN_VERSION
    description = "Core services gateway for plugins - provides stable API access to Jupiter functionality"
    trust_level = "system"
    restartable = False  # Cannot be restarted by user (only by watchdog or system)
    
    # Settings-only UI for bridge status and service inspection
    ui_config = PluginUIConfig(
        ui_type=PluginUIType.SETTINGS,
        menu_icon="🌉",
        menu_label_key="bridge_settings",
        menu_order=5,  # High priority (low number = top)
        view_id="bridge",
        settings_section="bridge"
    )
    
    def __init__(self) -> None:
        self._registry = ServiceRegistry()
        self._context: Optional[BridgeContext] = None
        self._initialized = False
        self._app_state: Any = None
        self._plugin_manager: Any = None
        
        # Register built-in services
        self._register_builtin_services()
    
    def _register_builtin_services(self) -> None:
        """Register all built-in services."""
        builtin_services = [
            EventsService,
            ConfigService,
            ScannerService,
            CacheService,
            HistoryService,
            LoggingService,
        ]
        
        for service_class in builtin_services:
            self._registry.register(service_class)
        
        logger.info(
            "[Bridge] Registered %d built-in services",
            len(builtin_services)
        )
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the Bridge plugin."""
        # Bridge has minimal configuration
        pass
    
    def initialize(
        self, 
        app_state: Any = None, 
        plugin_manager: Any = None
    ) -> BridgeContext:
        """Initialize the Bridge and return the context.
        
        This should be called once during Jupiter startup, typically
        by the PluginManager after all plugins are loaded.
        """
        if self._initialized and self._context:
            return self._context
        
        self._app_state = app_state
        self._plugin_manager = plugin_manager
        
        # Create the context
        self._context = BridgeContext(self._registry)
        self._context._app_state = app_state
        self._context._plugin_manager = plugin_manager
        
        self._initialized = True
        logger.info(
            "[Bridge] Initialized (API v%s, %d services available)",
            BRIDGE_API_VERSION,
            len(self._registry.list_services())
        )
        
        return self._context
    
    def get_context(self) -> Optional[BridgeContext]:
        """Get the Bridge context for plugin use."""
        return self._context
    
    def register_service(self, service_class: Type[ServiceProvider]) -> None:
        """Register a custom service (for advanced plugins)."""
        self._registry.register(service_class)
    
    def unregister_service(self, name: str) -> bool:
        """Unregister a service."""
        return self._registry.unregister(name)
    
    def shutdown(self) -> None:
        """Shutdown the Bridge and all services."""
        self._registry.shutdown_all()
        self._initialized = False
        self._context = None
        logger.info("[Bridge] Shutdown complete")
    
    # === Plugin hooks (no-op for system plugin) ===
    
    def on_scan(self, report: Dict[str, Any]) -> None:
        """No action on scan."""
        pass
    
    def on_analyze(self, summary: Dict[str, Any]) -> None:
        """No action on analyze."""
        pass
    
    # === UI Methods ===
    
    def get_ui_html(self) -> str:
        """No sidebar view."""
        return ""
    
    def get_ui_js(self) -> str:
        """No sidebar view."""
        return ""
    
    def get_settings_html(self) -> str:
        """Return HTML for the Bridge settings panel."""
        return """
        <div class="bridge-settings">
            <div class="bridge-header">
                <h4 data-i18n="bridge_title">🌉 Plugin Bridge</h4>
                <p class="bridge-description" data-i18n="bridge_description">
                    Core services gateway providing stable API access for plugins.
                </p>
            </div>
            
            <div class="bridge-status-card">
                <div class="status-row">
                    <span data-i18n="bridge_api_version">API Version:</span>
                    <span class="status-value" id="bridge-api-version">-</span>
                </div>
                <div class="status-row">
                    <span data-i18n="bridge_services_count">Services Available:</span>
                    <span class="status-value" id="bridge-services-count">-</span>
                </div>
                <div class="status-row">
                    <span data-i18n="bridge_services_loaded">Services Loaded:</span>
                    <span class="status-value" id="bridge-services-loaded">-</span>
                </div>
            </div>
            
            <div class="bridge-actions">
                <button class="btn btn-secondary" id="btn-bridge-refresh" data-i18n="bridge_refresh">
                    🔄 Refresh Status
                </button>
            </div>
            
            <h5 data-i18n="bridge_services_title" style="margin-top: 1.5rem;">Available Services</h5>
            <div id="bridge-services-list" class="bridge-services-list">
                <p class="loading" data-i18n="loading">Loading...</p>
            </div>
            
            <h5 data-i18n="bridge_capabilities_title" style="margin-top: 1.5rem;">All Capabilities</h5>
            <div id="bridge-capabilities-list" class="bridge-capabilities-list">
                <p class="loading" data-i18n="loading">Loading...</p>
            </div>
        </div>
        
        <style>
            .bridge-settings {
                padding: 1rem;
            }
            .bridge-header {
                margin-bottom: 1.5rem;
            }
            .bridge-description {
                color: var(--text-muted);
                font-size: 0.9rem;
            }
            .bridge-status-card {
                background: var(--card-bg, #2d2d2d);
                border-radius: 8px;
                padding: 1rem;
                margin-bottom: 1rem;
            }
            .status-row {
                display: flex;
                justify-content: space-between;
                padding: 0.5rem 0;
                border-bottom: 1px solid var(--border-color, #444);
            }
            .status-row:last-child {
                border-bottom: none;
            }
            .status-value {
                font-weight: 600;
                color: var(--accent, #4fc3f7);
            }
            .bridge-actions {
                margin: 1rem 0;
            }
            .bridge-services-list, .bridge-capabilities-list {
                background: var(--card-bg, #2d2d2d);
                border-radius: 8px;
                padding: 1rem;
                max-height: 300px;
                overflow-y: auto;
            }
            .service-item {
                padding: 0.75rem;
                border-bottom: 1px solid var(--border-color, #444);
            }
            .service-item:last-child {
                border-bottom: none;
            }
            .service-name {
                font-weight: 600;
                color: var(--accent, #4fc3f7);
            }
            .service-category {
                font-size: 0.8rem;
                color: var(--text-muted);
                margin-left: 0.5rem;
            }
            .service-description {
                font-size: 0.85rem;
                color: var(--text-muted);
                margin-top: 0.25rem;
            }
            .capability-tag {
                display: inline-block;
                background: var(--accent-dim, #1a3a4a);
                color: var(--accent, #4fc3f7);
                padding: 0.25rem 0.5rem;
                border-radius: 4px;
                font-size: 0.8rem;
                margin: 0.25rem;
            }
        </style>
        """
    
    def get_settings_js(self) -> str:
        """Return JavaScript for the Bridge settings panel."""
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
                const headers = {};
                if (token) headers['Authorization'] = 'Bearer ' + token;
                return headers;
            }
            
            async function loadBridgeStatus() {
                try {
                    const response = await fetch(getApiBase() + '/plugins/bridge/status', {
                        headers: getAuthHeaders()
                    });
                    if (!response.ok) throw new Error('Failed to fetch bridge status');
                    const data = await response.json();
                    
                    document.getElementById('bridge-api-version').textContent = data.api_version || '-';
                    document.getElementById('bridge-services-count').textContent = data.services_count || 0;
                    document.getElementById('bridge-services-loaded').textContent = data.services_loaded || 0;
                    
                    // Render services
                    const servicesList = document.getElementById('bridge-services-list');
                    if (data.services && data.services.length > 0) {
                        servicesList.innerHTML = data.services.map(s => `
                            <div class="service-item">
                                <div>
                                    <span class="service-name">${s.name}</span>
                                    <span class="service-category">[${s.category}]</span>
                                    <span style="font-size:0.8rem; color:var(--text-muted);">v${s.version}</span>
                                </div>
                                <div class="service-description">${s.description}</div>
                                <div style="margin-top:0.5rem;">
                                    ${s.capabilities.map(c => `<span class="capability-tag">${c.name}</span>`).join('')}
                                </div>
                            </div>
                        `).join('');
                    } else {
                        servicesList.innerHTML = '<p>No services available</p>';
                    }
                    
                    // Render capabilities
                    const capsList = document.getElementById('bridge-capabilities-list');
                    if (data.capabilities && data.capabilities.length > 0) {
                        capsList.innerHTML = data.capabilities.map(c => 
                            `<span class="capability-tag">${c}</span>`
                        ).join('');
                    } else {
                        capsList.innerHTML = '<p>No capabilities available</p>';
                    }
                    
                } catch (err) {
                    console.error('[Bridge] Failed to load status:', err);
                    document.getElementById('bridge-services-list').innerHTML = 
                        '<p style="color:var(--error);">Failed to load services</p>';
                }
            }
            
            // Refresh button
            const refreshBtn = document.getElementById('btn-bridge-refresh');
            if (refreshBtn) {
                refreshBtn.addEventListener('click', loadBridgeStatus);
            }
            
            // Initial load
            loadBridgeStatus();
        })();
        """
    
    # === Status methods for API ===
    
    def get_status(self) -> Dict[str, Any]:
        """Get Bridge status for API."""
        services = self._registry.list_services()
        loaded_count = sum(1 for s in services if self._registry.is_loaded(s.name))
        
        return {
            "api_version": BRIDGE_API_VERSION,
            "plugin_version": PLUGIN_VERSION,
            "initialized": self._initialized,
            "services_count": len(services),
            "services_loaded": loaded_count,
            "services": [s.to_dict() for s in services],
            "capabilities": self._context.list_capabilities() if self._context else [],
        }


# =============================================================================
# MODULE-LEVEL BRIDGE ACCESS
# =============================================================================

# Singleton instance for global access
_bridge_instance: Optional[PluginBridge] = None


def get_bridge() -> Optional[BridgeContext]:
    """Get the Bridge context for plugin use.
    
    This is the main entry point for plugins to access the Bridge.
    
    Returns:
        The BridgeContext if the Bridge is initialized, None otherwise.
        
    Example:
        from jupiter.plugins.bridge_plugin import get_bridge
        
        bridge = get_bridge()
        if bridge:
            scanner = bridge.get_service("scanner")
            if scanner:
                files = scanner.list_files(path, [".py"])
    """
    global _bridge_instance
    if _bridge_instance:
        return _bridge_instance.get_context()
    return None


def get_bridge_plugin() -> Optional[PluginBridge]:
    """Get the Bridge plugin instance (for internal use)."""
    global _bridge_instance
    return _bridge_instance


def _set_bridge_instance(instance: PluginBridge) -> None:
    """Set the global Bridge instance (called by PluginManager)."""
    global _bridge_instance
    _bridge_instance = instance
