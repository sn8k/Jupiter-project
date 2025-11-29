"""Configuration loading and models for Jupiter."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import logging
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

CONFIG_FILE_NAME = "jupiter.yaml"


@dataclass
class ServerConfig:
    """Configuration for the API server."""

    host: str = "127.0.0.1"
    port: int = 8000


@dataclass
class GuiConfig:
    """Configuration for the GUI server."""

    host: str = "127.0.0.1"
    port: int = 8050


@dataclass
class MeetingConfig:
    """Configuration for the Meeting feature."""

    enabled: bool = False
    deviceKey: Optional[str] = None


@dataclass
class UIConfig:
    """Configuration for the web UI."""

    theme: str = "dark"
    language: str = "en"


@dataclass
class PluginsConfig:
    """Configuration for plugins."""

    enabled: list[str] = field(default_factory=list)
    disabled: list[str] = field(default_factory=list)


@dataclass
class SecurityConfig:
    """Configuration for security."""

    token: Optional[str] = None


@dataclass
class ProjectBackendConfig:
    """Configuration for a project backend."""
    name: str
    type: str = "local_fs"  # local_fs, remote_jupiter_api
    path: Optional[str] = None
    api_url: Optional[str] = None
    api_key: Optional[str] = None


@dataclass
class JupiterConfig:
    """Global configuration."""

    server: ServerConfig = field(default_factory=ServerConfig)
    gui: GuiConfig = field(default_factory=GuiConfig)
    meeting: MeetingConfig = field(default_factory=MeetingConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    plugins: PluginsConfig = field(default_factory=PluginsConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    backends: list[ProjectBackendConfig] = field(default_factory=list)
    project_root: Path = field(default_factory=Path.cwd)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JupiterConfig:
        """Create a config object from a dictionary."""
        server_data = data.get("server", {})
        gui_data = data.get("gui", {})
        meeting_data = data.get("meeting", {})
        ui_data = data.get("ui", {})
        plugins_data = data.get("plugins", {})
        security_data = data.get("security", {})
        backends_data = data.get("backends", [])

        backends = [ProjectBackendConfig(**b) for b in backends_data]

        return cls(
            server=ServerConfig(**server_data),
            gui=GuiConfig(**gui_data),
            meeting=MeetingConfig(**meeting_data),
            ui=UIConfig(**ui_data),
            plugins=PluginsConfig(**plugins_data),
            security=SecurityConfig(**security_data),
            backends=backends,
        )



def load_config(root_path: Path) -> JupiterConfig:
    """Load configuration from a YAML file.

    Looks for ``jupiter.yaml`` in the given ``root_path``. If not found,
    returns a default configuration. If found, loads it and merges it with
    the defaults.
    """
    config_file = root_path / CONFIG_FILE_NAME

    if not config_file.is_file():
        logger.debug("No config file found at %s, using defaults.", config_file)
        return JupiterConfig(project_root=root_path)

    logger.info("Loading config from %s", config_file)
    try:
        with config_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        
        config = JupiterConfig.from_dict(data)
        config.project_root = root_path
        return config
    except Exception as e:
        logger.error("Failed to load config file: %s", e)
        return JupiterConfig(project_root=root_path)


def save_config(config: JupiterConfig, root_path: Path) -> None:
    """Save configuration to a YAML file."""
    config_file = root_path / CONFIG_FILE_NAME
    
    data = {
        "server": {
            "host": config.server.host,
            "port": config.server.port,
        },
        "gui": {
            "host": config.gui.host,
            "port": config.gui.port,
        },
        "meeting": {
            "enabled": config.meeting.enabled,
            "deviceKey": config.meeting.deviceKey,
        },
        "ui": {
            "theme": config.ui.theme,
            "language": config.ui.language,
        },
        "plugins": {
            "enabled": config.plugins.enabled,
            "disabled": config.plugins.disabled,
        },
        "backends": [
            {
                "name": b.name,
                "type": b.type,
                "path": b.path,
                "api_url": b.api_url,
            }
            for b in config.backends
        ],
    }
    
    try:
        with config_file.open("w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False)
        logger.info("Saved config to %s", config_file)
    except Exception as e:
        logger.error("Failed to save config file: %s", e)
        raise