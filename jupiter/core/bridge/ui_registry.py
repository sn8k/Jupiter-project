"""UI Registry for Jupiter Plugin Bridge.

Version: 0.1.0

This module provides a registry for UI contributions from plugins.
It allows plugins to register panels, settings frames, and menu items
that are dynamically loaded by the web UI.

Features:
- Register and unregister UI contributions per plugin
- Panel registration with location control (sidebar, settings, both)
- Settings frame auto-generation from JSON Schema
- Menu item contributions
- i18n integration with prefixed keys
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from jupiter.core.bridge.interfaces import UIContribution, UILocation, Permission
from jupiter.core.bridge.exceptions import (
    PluginError,
    PermissionDeniedError,
    ValidationError,
)

logger = logging.getLogger(__name__)


@dataclass
class RegisteredPanel:
    """Represents a registered UI panel."""
    
    plugin_id: str
    panel_id: str
    location: UILocation
    route: str
    title_key: str
    icon: str = "🔌"
    order: int = 100
    description_key: Optional[str] = None
    component_path: Optional[str] = None  # Path to JS component
    lazy_load: bool = True
    visible: bool = True
    requires_auth: bool = False
    
    @property
    def full_route(self) -> str:
        """Get full route including plugin prefix."""
        if self.route.startswith("/"):
            return f"/plugins/{self.plugin_id}{self.route}"
        return f"/plugins/{self.plugin_id}/{self.route}"
    
    @property
    def i18n_title_key(self) -> str:
        """Get prefixed i18n key for title."""
        if self.title_key.startswith("plugin."):
            return self.title_key
        return f"plugin.{self.plugin_id}.{self.title_key}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "plugin_id": self.plugin_id,
            "panel_id": self.panel_id,
            "location": self.location.value,
            "route": self.route,
            "full_route": self.full_route,
            "title_key": self.title_key,
            "i18n_title_key": self.i18n_title_key,
            "icon": self.icon,
            "order": self.order,
            "description_key": self.description_key,
            "component_path": self.component_path,
            "lazy_load": self.lazy_load,
            "visible": self.visible,
            "requires_auth": self.requires_auth,
        }


@dataclass
class RegisteredMenuItem:
    """Represents a registered menu item."""
    
    plugin_id: str
    item_id: str
    label_key: str
    action: str  # Route or action ID
    icon: str = ""
    order: int = 100
    parent: Optional[str] = None  # Parent menu ID for submenus
    separator_before: bool = False
    separator_after: bool = False
    visible: bool = True
    
    @property
    def i18n_label_key(self) -> str:
        """Get prefixed i18n key for label."""
        if self.label_key.startswith("plugin."):
            return self.label_key
        return f"plugin.{self.plugin_id}.{self.label_key}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "plugin_id": self.plugin_id,
            "item_id": self.item_id,
            "label_key": self.label_key,
            "i18n_label_key": self.i18n_label_key,
            "action": self.action,
            "icon": self.icon,
            "order": self.order,
            "parent": self.parent,
            "separator_before": self.separator_before,
            "separator_after": self.separator_after,
            "visible": self.visible,
        }


@dataclass
class SettingsSchema:
    """Represents a plugin's settings schema for auto-UI generation."""
    
    plugin_id: str
    schema: Dict[str, Any]  # JSON Schema
    ui_schema: Optional[Dict[str, Any]] = None  # UI hints
    defaults: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "plugin_id": self.plugin_id,
            "schema": self.schema,
            "ui_schema": self.ui_schema,
            "defaults": self.defaults,
        }


@dataclass
class PluginUIManifest:
    """Complete UI manifest for a plugin."""
    
    plugin_id: str
    panels: List[RegisteredPanel] = field(default_factory=list)
    menu_items: List[RegisteredMenuItem] = field(default_factory=list)
    settings_schema: Optional[SettingsSchema] = None
    i18n_namespace: str = ""
    
    def __post_init__(self):
        if not self.i18n_namespace:
            self.i18n_namespace = f"plugin.{self.plugin_id}"
    
    @property
    def has_sidebar(self) -> bool:
        """Check if plugin has sidebar panels."""
        return any(
            p.location in (UILocation.SIDEBAR, UILocation.BOTH)
            for p in self.panels
        )
    
    @property
    def has_settings(self) -> bool:
        """Check if plugin has settings panels."""
        return any(
            p.location in (UILocation.SETTINGS, UILocation.BOTH)
            for p in self.panels
        ) or self.settings_schema is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "plugin_id": self.plugin_id,
            "panels": [p.to_dict() for p in self.panels],
            "menu_items": [m.to_dict() for m in self.menu_items],
            "settings_schema": self.settings_schema.to_dict() if self.settings_schema else None,
            "i18n_namespace": self.i18n_namespace,
            "has_sidebar": self.has_sidebar,
            "has_settings": self.has_settings,
        }


class UIRegistry:
    """Registry for UI contributions from plugins.
    
    The UI Registry manages all UI elements contributed by plugins.
    It handles:
    - Panel registration (sidebar, settings, both)
    - Menu item registration
    - Settings schema for auto-UI generation
    - i18n key prefixing
    
    Usage:
        registry = UIRegistry()
        
        # Register a panel
        registry.register_panel(
            plugin_id="my_plugin",
            panel_id="main",
            location=UILocation.SIDEBAR,
            route="/",
            title_key="panel_title",
            icon="📊",
        )
        
        # Get UI manifest for web UI
        manifest = registry.get_ui_manifest()
    """
    
    def __init__(self):
        """Initialize the UI registry."""
        # plugin_id -> PluginUIManifest
        self._manifests: Dict[str, PluginUIManifest] = {}
        # Permission tracking: plugin_id -> set of permissions
        self._permissions: Dict[str, Set[Permission]] = {}
    
    def set_plugin_permissions(
        self,
        plugin_id: str,
        permissions: Set[Permission],
    ) -> None:
        """Set permissions for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            permissions: Set of granted permissions
        """
        self._permissions[plugin_id] = permissions.copy()
    
    def _check_permission(self, plugin_id: str) -> None:
        """Check if plugin has permission to register UI components.
        
        Args:
            plugin_id: Plugin identifier
            
        Raises:
            PermissionDeniedError: If plugin lacks permission
        """
        perms = self._permissions.get(plugin_id, set())
        if Permission.REGISTER_UI not in perms:
            raise PermissionDeniedError(
                f"Plugin '{plugin_id}' does not have permission to register UI components",
                plugin_id=plugin_id,
                permission=Permission.REGISTER_UI,
            )
    
    def _ensure_manifest(self, plugin_id: str) -> PluginUIManifest:
        """Ensure a UI manifest exists for the plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            PluginUIManifest for the plugin
        """
        if plugin_id not in self._manifests:
            self._manifests[plugin_id] = PluginUIManifest(plugin_id=plugin_id)
        return self._manifests[plugin_id]
    
    def register_panel(
        self,
        plugin_id: str,
        panel_id: str,
        location: UILocation,
        route: str,
        title_key: str,
        icon: str = "🔌",
        order: int = 100,
        description_key: Optional[str] = None,
        component_path: Optional[str] = None,
        lazy_load: bool = True,
        visible: bool = True,
        requires_auth: bool = False,
        check_permissions: bool = True,
    ) -> RegisteredPanel:
        """Register a UI panel for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            panel_id: Unique panel ID within the plugin
            location: Where to show (sidebar, settings, both)
            route: Panel route
            title_key: i18n key for panel title
            icon: Panel icon (emoji or CSS class)
            order: Sort order (lower = earlier)
            description_key: i18n key for description
            component_path: Path to JS component file
            lazy_load: Whether to lazy load the component
            visible: Whether panel is visible
            requires_auth: Whether authentication is required
            check_permissions: Whether to check plugin permissions
            
        Returns:
            RegisteredPanel object
            
        Raises:
            PermissionDeniedError: If plugin lacks permission
            ValidationError: If panel_id is invalid or duplicate
        """
        if check_permissions:
            self._check_permission(plugin_id)
        
        # Validate panel_id
        self._validate_panel_id(panel_id, plugin_id)
        
        panel = RegisteredPanel(
            plugin_id=plugin_id,
            panel_id=panel_id,
            location=location,
            route=route,
            title_key=title_key,
            icon=icon,
            order=order,
            description_key=description_key,
            component_path=component_path,
            lazy_load=lazy_load,
            visible=visible,
            requires_auth=requires_auth,
        )
        
        manifest = self._ensure_manifest(plugin_id)
        manifest.panels.append(panel)
        
        logger.debug(
            "Registered UI panel '%s' for plugin '%s' at %s",
            panel_id,
            plugin_id,
            location.value
        )
        
        return panel
    
    def register_from_contribution(
        self,
        plugin_id: str,
        contribution: UIContribution,
        check_permissions: bool = True,
    ) -> RegisteredPanel:
        """Register a panel from a UIContribution.
        
        Args:
            plugin_id: Plugin identifier
            contribution: UI contribution from manifest
            check_permissions: Whether to check plugin permissions
            
        Returns:
            RegisteredPanel object
        """
        # Ensure location is not None (use default if needed)
        location = contribution.location if contribution.location is not None else UILocation.SIDEBAR
        return self.register_panel(
            plugin_id=plugin_id,
            panel_id=contribution.id,
            location=location,
            route=contribution.route,
            title_key=contribution.title_key,
            icon=contribution.icon,
            order=contribution.order,
            description_key=contribution.settings_section,
            check_permissions=check_permissions,
        )
    
    def register_menu_item(
        self,
        plugin_id: str,
        item_id: str,
        label_key: str,
        action: str,
        icon: str = "",
        order: int = 100,
        parent: Optional[str] = None,
        separator_before: bool = False,
        separator_after: bool = False,
        visible: bool = True,
        check_permissions: bool = True,
    ) -> RegisteredMenuItem:
        """Register a menu item for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            item_id: Unique item ID within the plugin
            label_key: i18n key for label
            action: Route or action ID
            icon: Menu item icon
            order: Sort order
            parent: Parent menu ID for submenus
            separator_before: Add separator before item
            separator_after: Add separator after item
            visible: Whether item is visible
            check_permissions: Whether to check plugin permissions
            
        Returns:
            RegisteredMenuItem object
        """
        if check_permissions:
            self._check_permission(plugin_id)
        
        menu_item = RegisteredMenuItem(
            plugin_id=plugin_id,
            item_id=item_id,
            label_key=label_key,
            action=action,
            icon=icon,
            order=order,
            parent=parent,
            separator_before=separator_before,
            separator_after=separator_after,
            visible=visible,
        )
        
        manifest = self._ensure_manifest(plugin_id)
        manifest.menu_items.append(menu_item)
        
        logger.debug(
            "Registered menu item '%s' for plugin '%s'",
            item_id,
            plugin_id
        )
        
        return menu_item
    
    def register_settings_schema(
        self,
        plugin_id: str,
        schema: Dict[str, Any],
        ui_schema: Optional[Dict[str, Any]] = None,
        defaults: Optional[Dict[str, Any]] = None,
        check_permissions: bool = True,
    ) -> SettingsSchema:
        """Register a settings schema for auto-UI generation.
        
        Args:
            plugin_id: Plugin identifier
            schema: JSON Schema for settings
            ui_schema: Optional UI hints (widget types, etc.)
            defaults: Default values
            check_permissions: Whether to check plugin permissions
            
        Returns:
            SettingsSchema object
        """
        if check_permissions:
            self._check_permission(plugin_id)
        
        settings_schema = SettingsSchema(
            plugin_id=plugin_id,
            schema=schema,
            ui_schema=ui_schema,
            defaults=defaults or {},
        )
        
        manifest = self._ensure_manifest(plugin_id)
        manifest.settings_schema = settings_schema
        
        logger.debug(
            "Registered settings schema for plugin '%s'",
            plugin_id
        )
        
        return settings_schema
    
    def unregister_panel(
        self,
        plugin_id: str,
        panel_id: str,
    ) -> bool:
        """Unregister a UI panel.
        
        Args:
            plugin_id: Plugin identifier
            panel_id: Panel ID
            
        Returns:
            True if panel was removed
        """
        if plugin_id not in self._manifests:
            return False
        
        manifest = self._manifests[plugin_id]
        for i, panel in enumerate(manifest.panels):
            if panel.panel_id == panel_id:
                manifest.panels.pop(i)
                logger.debug(
                    "Unregistered UI panel '%s' for plugin '%s'",
                    panel_id,
                    plugin_id
                )
                return True
        
        return False
    
    def unregister_menu_item(
        self,
        plugin_id: str,
        item_id: str,
    ) -> bool:
        """Unregister a menu item.
        
        Args:
            plugin_id: Plugin identifier
            item_id: Menu item ID
            
        Returns:
            True if item was removed
        """
        if plugin_id not in self._manifests:
            return False
        
        manifest = self._manifests[plugin_id]
        for i, item in enumerate(manifest.menu_items):
            if item.item_id == item_id:
                manifest.menu_items.pop(i)
                logger.debug(
                    "Unregistered menu item '%s' for plugin '%s'",
                    item_id,
                    plugin_id
                )
                return True
        
        return False
    
    def unregister_plugin(self, plugin_id: str) -> int:
        """Unregister all UI contributions for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Number of contributions removed
        """
        if plugin_id not in self._manifests:
            return 0
        
        manifest = self._manifests[plugin_id]
        count = len(manifest.panels) + len(manifest.menu_items)
        if manifest.settings_schema:
            count += 1
        
        del self._manifests[plugin_id]
        self._permissions.pop(plugin_id, None)
        
        if count > 0:
            logger.debug(
                "Unregistered %d UI contributions for plugin '%s'",
                count,
                plugin_id
            )
        
        return count
    
    def get_panel(
        self,
        plugin_id: str,
        panel_id: str,
    ) -> Optional[RegisteredPanel]:
        """Get a registered panel.
        
        Args:
            plugin_id: Plugin identifier
            panel_id: Panel ID
            
        Returns:
            RegisteredPanel or None if not found
        """
        if plugin_id not in self._manifests:
            return None
        
        for panel in self._manifests[plugin_id].panels:
            if panel.panel_id == panel_id:
                return panel
        
        return None
    
    def get_plugin_panels(self, plugin_id: str) -> List[RegisteredPanel]:
        """Get all panels for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            List of panels
        """
        if plugin_id not in self._manifests:
            return []
        return self._manifests[plugin_id].panels.copy()
    
    def get_sidebar_panels(self) -> List[RegisteredPanel]:
        """Get all sidebar panels (sorted by order).
        
        Returns:
            List of panels for sidebar
        """
        result = []
        for manifest in self._manifests.values():
            for panel in manifest.panels:
                if panel.location in (UILocation.SIDEBAR, UILocation.BOTH):
                    if panel.visible:
                        result.append(panel)
        
        return sorted(result, key=lambda p: (p.order, p.plugin_id))
    
    def get_settings_panels(self) -> List[RegisteredPanel]:
        """Get all settings panels (sorted by order).
        
        Returns:
            List of panels for settings
        """
        result = []
        for manifest in self._manifests.values():
            for panel in manifest.panels:
                if panel.location in (UILocation.SETTINGS, UILocation.BOTH):
                    if panel.visible:
                        result.append(panel)
        
        return sorted(result, key=lambda p: (p.order, p.plugin_id))
    
    def get_all_panels(self) -> List[RegisteredPanel]:
        """Get all registered panels.
        
        Returns:
            List of all panels
        """
        result = []
        for manifest in self._manifests.values():
            result.extend(manifest.panels)
        return result
    
    def get_menu_items(self, parent: Optional[str] = None) -> List[RegisteredMenuItem]:
        """Get menu items (optionally filtered by parent).
        
        Args:
            parent: Parent menu ID to filter (None for root items)
            
        Returns:
            List of menu items
        """
        result = []
        for manifest in self._manifests.values():
            for item in manifest.menu_items:
                if item.parent == parent and item.visible:
                    result.append(item)
        
        return sorted(result, key=lambda m: (m.order, m.plugin_id))
    
    def get_all_menu_items(self) -> List[RegisteredMenuItem]:
        """Get all registered menu items.
        
        Returns:
            List of all menu items
        """
        result = []
        for manifest in self._manifests.values():
            result.extend(manifest.menu_items)
        return result
    
    def get_settings_schema(self, plugin_id: str) -> Optional[SettingsSchema]:
        """Get settings schema for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            SettingsSchema or None
        """
        if plugin_id not in self._manifests:
            return None
        return self._manifests[plugin_id].settings_schema
    
    def get_all_settings_schemas(self) -> List[SettingsSchema]:
        """Get all settings schemas.
        
        Returns:
            List of settings schemas
        """
        result = []
        for manifest in self._manifests.values():
            if manifest.settings_schema:
                result.append(manifest.settings_schema)
        return result
    
    def get_plugin_manifest(self, plugin_id: str) -> Optional[PluginUIManifest]:
        """Get complete UI manifest for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            PluginUIManifest or None
        """
        return self._manifests.get(plugin_id)
    
    def get_plugins_with_ui(self) -> List[str]:
        """Get list of plugin IDs that have registered UI.
        
        Returns:
            List of plugin IDs
        """
        return list(self._manifests.keys())
    
    def get_ui_manifest(self) -> Dict[str, Any]:
        """Get complete UI manifest for web UI consumption.
        
        Returns:
            Dictionary with all UI contributions
        """
        return {
            "plugins": {
                plugin_id: manifest.to_dict()
                for plugin_id, manifest in self._manifests.items()
            },
            "sidebar_panels": [p.to_dict() for p in self.get_sidebar_panels()],
            "settings_panels": [p.to_dict() for p in self.get_settings_panels()],
            "menu_items": [m.to_dict() for m in self.get_menu_items()],
            "plugin_count": len(self._manifests),
        }
    
    def _validate_panel_id(self, panel_id: str, plugin_id: str) -> None:
        """Validate a panel ID.
        
        Args:
            panel_id: Panel ID
            plugin_id: Plugin identifier
            
        Raises:
            ValidationError: If panel_id is invalid
        """
        if not panel_id:
            raise ValidationError(
                "Panel ID cannot be empty",
                validation_errors=["panel_id is required"],
            )
        
        if not panel_id.replace("-", "").replace("_", "").isalnum():
            raise ValidationError(
                f"Panel ID '{panel_id}' contains invalid characters",
                validation_errors=["panel_id must contain only alphanumeric, hyphens, underscores"],
            )
        
        # Check for duplicates within the same plugin
        if plugin_id in self._manifests:
            for panel in self._manifests[plugin_id].panels:
                if panel.panel_id == panel_id:
                    raise ValidationError(
                        f"Panel '{panel_id}' is already registered for plugin '{plugin_id}'",
                        validation_errors=["duplicate panel_id"],
                    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize registry state to dictionary.
        
        Returns:
            Dictionary with manifests
        """
        return {
            "manifests": {
                plugin_id: manifest.to_dict()
                for plugin_id, manifest in self._manifests.items()
            },
            "total_panels": sum(len(m.panels) for m in self._manifests.values()),
            "total_menu_items": sum(len(m.menu_items) for m in self._manifests.values()),
            "plugins_with_settings": sum(
                1 for m in self._manifests.values() if m.settings_schema
            ),
        }


# Global UI registry instance
_ui_registry: Optional[UIRegistry] = None


def get_ui_registry() -> UIRegistry:
    """Get the global UI registry instance.
    
    Returns:
        UIRegistry singleton
    """
    global _ui_registry
    if _ui_registry is None:
        _ui_registry = UIRegistry()
    return _ui_registry


def reset_ui_registry() -> None:
    """Reset the global UI registry (for testing)."""
    global _ui_registry
    _ui_registry = None
