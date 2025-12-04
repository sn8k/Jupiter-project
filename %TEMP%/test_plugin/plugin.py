"""
Jupiter Plugin: test_plugin

Version: 0.1.0
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from jupiter.core.bridge.interfaces import (
    IPlugin,
    IPluginManifest,
    PluginType,
    Permission,
    CLIContribution,
    APIContribution,
    UIContribution,
)

logger = logging.getLogger(__name__)


class TestPluginPlugin(IPlugin):
    """Main plugin class."""
    
    def __init__(self, manifest: IPluginManifest):
        self._manifest = manifest
        self._enabled = True
        self._logger = logging.getLogger(f"jupiter.plugins.{manifest.id}")
    
    @property
    def manifest(self) -> IPluginManifest:
        return self._manifest
    
    def initialize(self) -> None:
        """Called when the plugin is loaded."""
        self._logger.info("[%s] Initializing", self._manifest.id)
    
    def shutdown(self) -> None:
        """Called when the plugin is unloaded."""
        self._logger.info("[%s] Shutting down", self._manifest.id)
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Apply configuration."""
        self._enabled = config.get("enabled", True)
        self._logger.info("[%s] Configured: enabled=%s", self._manifest.id, self._enabled)
    
    def get_cli_contribution(self) -> Optional[CLIContribution]:
        """Return CLI contribution (optional)."""
        return None
    
    def get_api_contribution(self) -> Optional[APIContribution]:
        """Return API contribution (optional)."""
        return None
    
    def get_ui_contribution(self) -> Optional[UIContribution]:
        """Return UI contribution (optional)."""
        return None
    
    # Plugin hooks
    def on_scan(self, report: Dict[str, Any], **kwargs) -> None:
        """Called after a scan completes."""
        pass
    
    def on_analyze(self, report: Dict[str, Any], **kwargs) -> None:
        """Called after an analysis completes."""
        pass
