"""Plugin system for Jupiter."""

from __future__ import annotations

from typing import Protocol, Any, runtime_checkable, Optional, TYPE_CHECKING
from dataclasses import dataclass, field, asdict
from enum import Enum

# Type checking imports to avoid circular dependencies
if TYPE_CHECKING:
    from jupiter.plugins.bridge_plugin import BridgeContext


class PluginUIType(str, Enum):
    """Where the plugin UI should be displayed."""
    
    NONE = "none"              # No UI (background plugin)
    SIDEBAR = "sidebar"        # Shows as a menu item in the sidebar
    SETTINGS = "settings"      # Shows as a section in Settings page
    BOTH = "both"              # Shows in both sidebar and settings


@dataclass
class PluginUIConfig:
    """Configuration for plugin UI integration.
    
    Attributes:
        ui_type: Where to display the plugin (sidebar, settings, both, or none)
        menu_icon: Icon for sidebar menu (emoji or icon class)
        menu_label_key: i18n key for menu label (e.g., "pylance_view")
        menu_order: Sort order in menu (lower = higher in list)
        settings_section: Section name in settings (if ui_type includes settings)
        view_id: Unique ID for the view (used in routing)
    """
    
    ui_type: PluginUIType = PluginUIType.NONE
    menu_icon: str = "🔌"
    menu_label_key: str = ""
    menu_order: int = 100
    settings_section: Optional[str] = None
    view_id: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "ui_type": self.ui_type.value,
            "menu_icon": self.menu_icon,
            "menu_label_key": self.menu_label_key,
            "menu_order": self.menu_order,
            "settings_section": self.settings_section,
            "view_id": self.view_id,
        }


@runtime_checkable
class Plugin(Protocol):
    """Base interface for Jupiter plugins."""

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


class UIPlugin(Protocol):
    """Extended interface for plugins with UI components.
    
    Plugins can implement this protocol to provide custom views
    in the Jupiter web interface.
    """
    
    name: str
    version: str
    description: str
    ui_config: PluginUIConfig
    
    def get_ui_html(self) -> str:
        """Return HTML content for the plugin's view.
        
        This HTML will be injected into the main content area
        when the plugin's view is selected.
        """
        ...
    
    def get_ui_js(self) -> str:
        """Return JavaScript code for the plugin's view.
        
        This code will be executed when the view is loaded.
        It should define an init function and event handlers.
        """
        ...
    
    def get_settings_html(self) -> str:
        """Return HTML for the settings section (if ui_type includes settings)."""
        ...
    
    def get_settings_js(self) -> str:
        """Return JavaScript for the settings section."""
        ...


# =============================================================================
# BRIDGE ACCESS FUNCTIONS
# =============================================================================

def get_bridge() -> Optional["BridgeContext"]:
    """Get the Bridge context for plugin use.
    
    The Bridge provides stable, versioned access to Jupiter's core
    functionality without plugins needing to import core modules directly.
    
    Returns:
        The BridgeContext if the Bridge is initialized, None otherwise.
        
    Example:
        from jupiter.plugins import get_bridge
        
        bridge = get_bridge()
        if bridge:
            # Access services
            scanner = bridge.get_service("scanner")
            config = bridge.get_service("config")
            
            # Use capabilities
            if bridge.has_capability("scan_directory"):
                result = bridge.invoke("scan_directory", path)
    """
    try:
        from jupiter.plugins.bridge_plugin import get_bridge as _get_bridge
        return _get_bridge()
    except ImportError:
        return None


def has_bridge() -> bool:
    """Check if the Bridge is available and initialized."""
    bridge = get_bridge()
    return bridge is not None


