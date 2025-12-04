"""Bridge v2 Core Plugins.

Version: 0.1.0

This module contains built-in plugins that are always loaded
with the Bridge. These plugins don't have external manifests
- they are hard-coded into Jupiter.

Core plugins include:
- settings_update: Self-update functionality

Usage:
    from jupiter.core.bridge.core_plugins import get_core_plugins
    
    for plugin in get_core_plugins():
        bridge.register_plugin(plugin.manifest, legacy=False)
"""

from __future__ import annotations

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from jupiter.core.bridge.interfaces import IPlugin

__version__ = "0.1.0"


def get_core_plugins() -> List["IPlugin"]:
    """Get all core plugin instances.
    
    Returns:
        List of core plugin instances ready for registration
    """
    from jupiter.core.bridge.core_plugins.settings_update_plugin import SettingsUpdatePlugin
    
    return [
        SettingsUpdatePlugin(),
    ]


def get_core_plugin_ids() -> List[str]:
    """Get IDs of all core plugins.
    
    Returns:
        List of plugin IDs
    """
    return ["settings_update"]


__all__ = ["get_core_plugins", "get_core_plugin_ids", "__version__"]
