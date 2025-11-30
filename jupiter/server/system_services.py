"""Helpers for managing runtime system state (root, config, plugins)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from jupiter.config.config import (
    JupiterConfig,
    load_merged_config,
    save_global_settings,
    save_project_settings,
)
from jupiter.core.logging_utils import configure_logging
from jupiter.core.history import HistoryManager
from jupiter.core.plugin_manager import PluginManager
from jupiter.server.manager import ProjectManager


class SystemState:
    """Wrapper around ``app.state`` to centralize config/root helpers."""

    def __init__(self, app: FastAPI):
        self.app = app

    @property
    def root_path(self) -> Path:
        return self.app.state.root_path

    @property
    def install_path(self) -> Path:
        return getattr(self.app.state, "install_path", self.root_path)

    def history_manager(self) -> HistoryManager:
        manager = getattr(self.app.state, "history_manager", None)
        if manager is None or getattr(manager, "project_root", None) != self.root_path:
            manager = HistoryManager(self.root_path)
            self.app.state.history_manager = manager
        return manager

    def load_effective_config(self) -> JupiterConfig:
        """Return merged install/project config for the current root."""
        config = load_merged_config(self.install_path, self.root_path)
        config.project_root = self.root_path
        return config

    def save_effective_config(self, config: JupiterConfig) -> None:
        save_global_settings(config, self.install_path)
        save_project_settings(config, self.root_path)

    def rebuild_runtime(self, config: JupiterConfig, new_root: Path | None = None, reset_history: bool = False) -> None:
        """Rebuild managers/plugins when the root or config changes."""
        target_root = new_root or self.root_path
        self.app.state.root_path = target_root

        adapter = getattr(self.app.state, "meeting_adapter", None)
        if adapter:
            adapter.project_root = target_root
            adapter.device_key = config.meeting.deviceKey

        project_manager = getattr(self.app.state, "project_manager", None)
        if project_manager:
            project_manager.refresh_for_root(config)
        else:
            self.app.state.project_manager = ProjectManager(config)

        configure_logging(config.logging.level, log_file=config.logging.path)

        plugin_manager = PluginManager(config=config.plugins)
        plugin_manager.discover_and_load()
        self.app.state.plugin_manager = plugin_manager

        if reset_history or new_root is not None:
            self.app.state.history_manager = HistoryManager(target_root)


def preserve_meeting_config(previous: JupiterConfig | None, target: JupiterConfig) -> None:
    """Carry over Meeting device key when switching roots."""
    if not previous:
        return

    if previous.meeting.deviceKey and not target.meeting.deviceKey:
        target.meeting.deviceKey = previous.meeting.deviceKey
        target.meeting.enabled = previous.meeting.enabled
