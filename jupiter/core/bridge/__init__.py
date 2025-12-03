"""Jupiter Plugin Bridge - Core Infrastructure.

Version: 0.7.0

The Bridge is the central component of Jupiter's plugin architecture v2.
It provides:
- Plugin discovery and lifecycle management
- Service locator for plugins to access core functionality
- Event bus for plugin communication
- Registry for CLI/API/UI contributions

This package contains:
- interfaces.py: ABC interfaces for plugin contracts
- exceptions.py: Dedicated exception classes
- manifest.py: Plugin manifest parsing and validation
- bridge.py: Main Bridge singleton and plugin registry
- services.py: Service locator implementation
- events.py: Event bus for pub/sub
- cli_registry.py: CLI contribution registry
- api_registry.py: API contribution registry  
- ui_registry.py: UI contribution registry
- legacy_adapter.py: Compatibility layer for v1 plugins
"""

__version__ = "0.7.0"

from jupiter.core.bridge.exceptions import (
    BridgeError,
    PluginError,
    ManifestError,
    DependencyError,
    CircularDependencyError,
    ServiceNotFoundError,
    PermissionDeniedError,
    LifecycleError,
    ValidationError,
    SignatureError,
)

from jupiter.core.bridge.interfaces import (
    IPlugin,
    IPluginManifest,
    IPluginContribution,
    IPluginHealth,
    IPluginMetrics,
    PluginState,
    PluginType,
    Permission,
    UILocation,
    HealthStatus,
    PluginCapabilities,
    CLIContribution,
    APIContribution,
    UIContribution,
    HealthCheckResult,
    PluginMetrics,
    LegacyPlugin,
    ConfigurablePlugin,
)

from jupiter.core.bridge.manifest import (
    PluginManifest,
    generate_manifest_for_legacy,
)

from jupiter.core.bridge.bridge import (
    Bridge,
    PluginInfo,
    ServiceLocator as BridgeServiceLocator,  # Legacy alias
    EventBusProxy,
)

from jupiter.core.bridge.services import (
    PluginLogger,
    SecureRunner,
    ConfigProxy,
    ServiceLocator,
    create_service_locator,
)

from jupiter.core.bridge.events import (
    EventBus,
    EventTopic,
    Event,
    Subscription,
    get_event_bus,
    reset_event_bus,
    emit_plugin_loaded,
    emit_plugin_error,
    emit_scan_started,
    emit_scan_progress,
    emit_scan_finished,
    emit_scan_error,
    emit_config_changed,
    emit_job_started,
    emit_job_progress,
    emit_job_completed,
    emit_job_failed,
)

from jupiter.core.bridge.cli_registry import (
    CLIRegistry,
    RegisteredCommand,
    CommandGroup,
    get_cli_registry,
    reset_cli_registry,
)

from jupiter.core.bridge.api_registry import (
    APIRegistry,
    HTTPMethod,
    RegisteredRoute,
    PluginRouter,
    get_api_registry,
    reset_api_registry,
)

__all__ = [
    # Version
    "__version__",
    # Bridge
    "Bridge",
    "PluginInfo",
    "ServiceLocator",
    "BridgeServiceLocator",  # Legacy alias
    "EventBusProxy",
    # Services
    "PluginLogger",
    "SecureRunner",
    "ConfigProxy",
    "create_service_locator",
    # Exceptions
    "BridgeError",
    "PluginError", 
    "ManifestError",
    "DependencyError",
    "CircularDependencyError",
    "ServiceNotFoundError",
    "PermissionDeniedError",
    "LifecycleError",
    "ValidationError",
    "SignatureError",
    # Interfaces
    "IPlugin",
    "IPluginManifest",
    "IPluginContribution",
    "IPluginHealth",
    "IPluginMetrics",
    "PluginState",
    "PluginType",
    "Permission",
    "UILocation",
    "HealthStatus",
    # Data classes
    "PluginCapabilities",
    "CLIContribution",
    "APIContribution",
    "UIContribution",
    "HealthCheckResult",
    "PluginMetrics",
    # Protocols
    "LegacyPlugin",
    "ConfigurablePlugin",
    # Manifest
    "PluginManifest",
    "generate_manifest_for_legacy",
    # Events
    "EventBus",
    "EventTopic",
    "Event",
    "Subscription",
    "get_event_bus",
    "reset_event_bus",
    "emit_plugin_loaded",
    "emit_plugin_error",
    "emit_scan_started",
    "emit_scan_progress",
    "emit_scan_finished",
    "emit_scan_error",
    "emit_config_changed",
    "emit_job_started",
    "emit_job_progress",
    "emit_job_completed",
    "emit_job_failed",
    # CLI Registry
    "CLIRegistry",
    "RegisteredCommand",
    "CommandGroup",
    "get_cli_registry",
    "reset_cli_registry",
    # API Registry
    "APIRegistry",
    "HTTPMethod",
    "RegisteredRoute",
    "PluginRouter",
    "get_api_registry",
    "reset_api_registry",
]
