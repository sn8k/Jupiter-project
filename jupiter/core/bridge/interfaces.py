"""Interface definitions for the Jupiter Plugin Bridge.

Version: 0.1.1

This module defines the Abstract Base Classes (ABCs) and Protocols
that plugins must implement to integrate with Jupiter's Bridge system.

Key interfaces:
- IPlugin: Base plugin interface (required)
- IPluginManifest: Manifest data structure
- IPluginContribution: CLI/API/UI contribution descriptors
- IPluginHealth: Health check interface (optional)
- IPluginMetrics: Metrics exposure interface (optional)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable


# =============================================================================
# ENUMERATIONS
# =============================================================================

class PluginState(str, Enum):
    """Lifecycle states of a plugin."""
    
    DISCOVERED = "discovered"   # Found but not loaded
    LOADING = "loading"         # Being loaded/initialized
    READY = "ready"             # Fully operational
    ERROR = "error"             # Failed to load or runtime error
    DISABLED = "disabled"       # Explicitly disabled by user/config
    UNLOADING = "unloading"     # Being unloaded (for hot reload)


class PluginType(str, Enum):
    """Classification of plugin types."""
    
    CORE = "core"       # Internal, non-disableable (bridge, settings_update)
    SYSTEM = "system"   # Infrastructure, disableable via config
    TOOL = "tool"       # Optional feature plugins


class Permission(str, Enum):
    """Granular permissions that plugins can request."""
    
    FS_READ = "fs_read"                 # Read filesystem
    FS_WRITE = "fs_write"               # Write filesystem
    RUN_COMMANDS = "run_commands"       # Execute shell commands
    NETWORK_OUTBOUND = "network_outbound"  # Make HTTP requests
    ACCESS_MEETING = "access_meeting"   # Access Meeting adapter
    ACCESS_CONFIG = "access_config"     # Read/write config
    EMIT_EVENTS = "emit_events"         # Emit events on the bus
    REGISTER_API = "register_api"       # Register API routes
    REGISTER_CLI = "register_cli"       # Register CLI commands
    REGISTER_UI = "register_ui"         # Register UI components


class UILocation(str, Enum):
    """Where a plugin's UI should appear."""
    
    NONE = "none"           # No UI
    SIDEBAR = "sidebar"     # Sidebar menu item
    SETTINGS = "settings"   # Settings page section
    BOTH = "both"           # Both sidebar and settings


class HealthStatus(str, Enum):
    """Health check result status."""
    
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PluginCapabilities:
    """Declares what capabilities a plugin supports.
    
    These are used for auto-generation of UI cards and metrics collection.
    """
    
    metrics_enabled: bool = False
    metrics_export_format: str = "json"  # "json" or "prometheus"
    jobs_enabled: bool = False
    jobs_max_concurrent: int = 1
    health_check_enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CLIContribution:
    """Describes a CLI command contributed by a plugin."""
    
    name: str                           # Command name (e.g., "quality")
    description: str                    # Help text
    entrypoint: str                     # Module:function path
    parent: Optional[str] = None        # Parent command (for subcommands)
    aliases: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class APIContribution:
    """Describes an API route contributed by a plugin."""
    
    path: str                           # Route path (e.g., "/quality/analyze")
    method: str                         # HTTP method
    entrypoint: str                     # Module:function path
    tags: List[str] = field(default_factory=list)
    auth_required: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UIContribution:
    """Describes a UI panel/section contributed by a plugin."""
    
    id: str                             # Unique panel ID
    location: UILocation                # Where to show (sidebar, settings, both)
    route: str                          # URL route
    title_key: str                      # i18n key for title
    icon: str = "🔌"                    # Icon (emoji or class)
    order: int = 100                    # Sort order
    settings_section: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "location": self.location.value,
        }


@dataclass 
class HealthCheckResult:
    """Result of a plugin health check."""
    
    status: HealthStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }


@dataclass
class PluginMetrics:
    """Metrics exposed by a plugin."""
    
    execution_count: int = 0
    error_count: int = 0
    last_execution: Optional[float] = None
    average_duration_ms: float = 0.0
    custom: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# ABSTRACT BASE CLASSES
# =============================================================================

class IPluginManifest(ABC):
    """Interface for plugin manifest data.
    
    A manifest describes the plugin's metadata, requirements,
    permissions, and contributions.
    """
    
    @property
    @abstractmethod
    def id(self) -> str:
        """Unique plugin identifier (e.g., 'ai_helper')."""
        ...
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable plugin name."""
        ...
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Semantic version string (e.g., '1.0.0')."""
        ...
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Brief description of the plugin."""
        ...
    
    @property
    @abstractmethod
    def plugin_type(self) -> PluginType:
        """Plugin type (core, system, tool)."""
        ...
    
    @property
    @abstractmethod
    def jupiter_version(self) -> str:
        """Minimum compatible Jupiter version."""
        ...
    
    @property
    @abstractmethod
    def permissions(self) -> List[Permission]:
        """List of permissions the plugin requires."""
        ...
    
    @property
    @abstractmethod
    def dependencies(self) -> Dict[str, str]:
        """Dependencies on other plugins {plugin_id: version_spec}."""
        ...
    
    @property
    @abstractmethod
    def capabilities(self) -> PluginCapabilities:
        """Plugin capabilities declaration."""
        ...
    
    @property
    @abstractmethod
    def cli_contributions(self) -> List[CLIContribution]:
        """CLI commands contributed by the plugin."""
        ...
    
    @property
    @abstractmethod
    def api_contributions(self) -> List[APIContribution]:
        """API routes contributed by the plugin."""
        ...
    
    @property
    @abstractmethod
    def ui_contributions(self) -> List[UIContribution]:
        """UI panels/sections contributed by the plugin."""
        ...
    
    @property
    @abstractmethod
    def trust_level(self) -> str:
        """Trust level of the plugin (experimental, community, official)."""
        ...
    
    @property
    @abstractmethod
    def source_path(self) -> Optional[Path]:
        """Path to the plugin source (plugin.yaml location)."""
        ...
    
    @property
    @abstractmethod
    def config_defaults(self) -> Dict[str, Any]:
        """Default configuration values for the plugin."""
        ...
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize manifest to dict."""
        ...


class IPlugin(ABC):
    """Base interface that all plugins must implement.
    
    This interface defines the minimal contract for a Jupiter plugin.
    Plugins can optionally implement additional interfaces for
    health checks, metrics, etc.
    """
    
    @property
    @abstractmethod
    def manifest(self) -> IPluginManifest:
        """Return the plugin's manifest."""
        ...
    
    @abstractmethod
    def init(self, services: Any) -> None:
        """Initialize the plugin with access to Bridge services.
        
        Called once when the plugin is first loaded.
        The services object provides access to core functionality.
        
        Args:
            services: ServiceLocator instance for accessing core services
        """
        ...
    
    @abstractmethod
    def shutdown(self) -> None:
        """Clean up resources when the plugin is unloaded.
        
        Called when:
        - Jupiter is shutting down
        - Plugin is being disabled
        - Plugin is being hot-reloaded
        """
        ...


class IPluginContribution(ABC):
    """Interface for plugins that contribute CLI/API/UI components.
    
    This is the extension point for plugins to register their
    contributions to Jupiter's surfaces.
    """
    
    @abstractmethod
    def register_contributions(self, registry: Any) -> None:
        """Register all contributions with the Bridge registry.
        
        Args:
            registry: The Bridge's contribution registry
        """
        ...


class IPluginHealth(ABC):
    """Interface for plugins that support health checks.
    
    Plugins implementing this interface can report their health
    status, which is used by the system for monitoring and
    automatic recovery.
    """
    
    @abstractmethod
    def health(self) -> HealthCheckResult:
        """Perform a health check and return the result.
        
        Should be fast (< 1 second) and not have side effects.
        """
        ...


class IPluginMetrics(ABC):
    """Interface for plugins that expose metrics.
    
    Plugins implementing this interface can report metrics
    which are collected by the Bridge and exposed via API.
    """
    
    @abstractmethod
    def metrics(self) -> PluginMetrics:
        """Return current metrics for this plugin."""
        ...


# =============================================================================
# PROTOCOLS (for duck-typing compatibility)
# =============================================================================

@runtime_checkable
class LegacyPlugin(Protocol):
    """Protocol matching the v1 plugin interface.
    
    Used by the legacy adapter to detect and wrap v1 plugins.
    """
    
    name: str
    version: str
    description: str
    
    def on_scan(self, report: Dict[str, Any]) -> None:
        """Hook called after a scan is completed."""
        ...
    
    def on_analyze(self, summary: Dict[str, Any]) -> None:
        """Hook called after an analysis is completed."""
        ...


@runtime_checkable
class ConfigurablePlugin(Protocol):
    """Protocol for plugins that accept configuration."""
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the plugin with settings."""
        ...


@runtime_checkable
class UICapablePlugin(Protocol):
    """Protocol for plugins with UI capabilities."""
    
    ui_config: Any  # PluginUIConfig from v1
    
    def get_ui_html(self) -> str:
        """Return HTML content for the plugin view."""
        ...
    
    def get_ui_js(self) -> str:
        """Return JavaScript for the plugin view."""
        ...


# =============================================================================
# TYPE ALIASES
# =============================================================================

# Callback types for event handlers
EventCallback = Callable[[str, Dict[str, Any]], None]

# Hook function types
ScanHook = Callable[[Dict[str, Any]], None]
AnalyzeHook = Callable[[Dict[str, Any]], None]
