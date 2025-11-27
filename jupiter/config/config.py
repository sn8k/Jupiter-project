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
class JupiterConfig:
    """Root configuration object for Jupiter."""

    project_root: Optional[Path] = None
    server: ServerConfig = field(default_factory=ServerConfig)
    gui: GuiConfig = field(default_factory=GuiConfig)
    meeting: MeetingConfig = field(default_factory=MeetingConfig)
    ui: UIConfig = field(default_factory=UIConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JupiterConfig":
        """Create a config object from a dictionary."""
        server_cfg = ServerConfig(**data.get("server", {}))
        gui_cfg = GuiConfig(**data.get("gui", {}))
        meeting_cfg = MeetingConfig(**data.get("meeting", {}))
        ui_cfg = UIConfig(**data.get("ui", {}))
        return cls(
            project_root=data.get("project_root"),
            server=server_cfg,
            gui=gui_cfg,
            meeting=meeting_cfg,
            ui=ui_cfg,
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
            config_data = yaml.safe_load(f) or {}
    except (IOError, yaml.YAMLError) as e:
        logger.error("Failed to load or parse config file %s: %s", config_file, e)
        # Fallback to default config on error
        return JupiterConfig(project_root=root_path)

    # Create config from dict, which handles defaults for missing sections
    config = JupiterConfig.from_dict(config_data)
    config.project_root = root_path
    return config