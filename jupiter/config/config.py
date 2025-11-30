"""Configuration loading and models for Jupiter."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import logging
import os
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
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenConfig:
    """Configuration for a single access token."""
    token: str
    role: str = "viewer"  # "admin" or "viewer"


@dataclass
class UserConfig:
    """Configuration for a Jupiter user."""
    name: str
    token: str
    role: str = "viewer"  # "admin", "editor", "viewer"


@dataclass
class SecurityConfig:
    """Configuration for security."""

    token: Optional[str] = None
    tokens: list[TokenConfig] = field(default_factory=list)
    allow_run: bool = True
    allowed_commands: list[str] = field(default_factory=list)


@dataclass
class CiConfig:
    """Configuration for CI/CD quality gates."""

    fail_on: dict[str, int] = field(default_factory=dict)


@dataclass
class PerformanceConfig:
    """Configuration for performance tuning."""

    parallel_scan: bool = True
    max_workers: Optional[int] = None  # None = CPU count
    scan_timeout: int = 300
    graph_simplification: bool = False
    max_graph_nodes: int = 1000
    large_file_threshold: int = 1024 * 1024  # 1MB
    excluded_dirs: list[str] = field(default_factory=lambda: ["node_modules", "venv", ".venv", "dist", "build"])


@dataclass
class ProjectBackendConfig:
    """Configuration for a project backend."""
    name: str
    type: str = "local_fs"  # local_fs, remote_jupiter_api
    path: Optional[str] = None
    api_url: Optional[str] = None
    api_key: Optional[str] = None


@dataclass
class ProjectApiConfig:
    """Configuration for the project's own API (for inspection)."""
    type: str = "openapi"
    base_url: Optional[str] = None
    openapi_url: str = "/openapi.json"
    # Static analysis / Dynamic import config
    connector: Optional[str] = None  # e.g. "fastapi", "flask"
    app_var: Optional[str] = None
    path: Optional[str] = None


@dataclass
class JupiterConfig:
    """Global configuration."""

    server: ServerConfig = field(default_factory=ServerConfig)
    gui: GuiConfig = field(default_factory=GuiConfig)
    meeting: MeetingConfig = field(default_factory=MeetingConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    plugins: PluginsConfig = field(default_factory=PluginsConfig)
    users: list[UserConfig] = field(default_factory=list)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    ci: CiConfig = field(default_factory=CiConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    backends: list[ProjectBackendConfig] = field(default_factory=list)
    project_api: Optional[ProjectApiConfig] = None
    project_root: Path = field(default_factory=Path.cwd)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JupiterConfig:
        """Create a config object from a dictionary."""
        server_data = data.get("server", {})
        gui_data = data.get("gui", {})
        meeting_data = data.get("meeting", {})
        
        # Robustness: handle device_key vs deviceKey
        if "device_key" in meeting_data and "deviceKey" not in meeting_data:
            meeting_data["deviceKey"] = meeting_data.pop("device_key")

        ui_data = data.get("ui", {})
        plugins_data = data.get("plugins", {})
        
        # Handle PluginsConfig manually to support extra settings
        plugins_enabled = plugins_data.get("enabled", [])
        plugins_disabled = plugins_data.get("disabled", [])
        plugins_settings = {k: v for k, v in plugins_data.items() if k not in ("enabled", "disabled")}
        plugins_config = PluginsConfig(enabled=plugins_enabled, disabled=plugins_disabled, settings=plugins_settings)

        users_data = data.get("users", [])
        users_config = [UserConfig(**u) for u in users_data]

        security_data = data.get("security", {})
        # Parse tokens if present
        if "tokens" in security_data and isinstance(security_data["tokens"], list):
            security_data["tokens"] = [TokenConfig(**t) for t in security_data["tokens"]]

        ci_data = data.get("ci", {})
        performance_data = data.get("performance", {})
        backends_data = data.get("backends", [])
        project_api_data = data.get("api") or data.get("project_api")

        backends = [ProjectBackendConfig(**b) for b in backends_data]
        project_api = ProjectApiConfig(**project_api_data) if project_api_data else None

        return cls(
            server=ServerConfig(**server_data),
            gui=GuiConfig(**gui_data),
            meeting=MeetingConfig(**meeting_data),
            ui=UIConfig(**ui_data),
            plugins=plugins_config,
            users=users_config,
            security=SecurityConfig(**security_data),
            ci=CiConfig(**ci_data),
            performance=PerformanceConfig(**performance_data),
            backends=backends,
            project_api=project_api,
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


def load_merged_config(install_path: Path, project_path: Path) -> JupiterConfig:
    """Load configuration merging global (install) and project settings."""
    # 1. Load global config
    global_config = load_config(install_path)

    # Check LocalAppData override
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        app_data_path = Path(local_app_data) / "Jupiter"
        if (app_data_path / CONFIG_FILE_NAME).exists():
             logger.info("Loading global config from LocalAppData: %s", app_data_path)
             global_config = load_config(app_data_path)
    
    # If paths are same, just return it
    if install_path.resolve() == project_path.resolve() and not (local_app_data and (Path(local_app_data) / "Jupiter" / CONFIG_FILE_NAME).exists()):
        return global_config

    # 2. Load project config
    project_config = load_config(project_path)

    # 3. Merge: Global settings override defaults, Project settings override Global (for some)
    # Actually, for "Global" settings (Meeting, Server, UI), we want the Global config to prevail 
    # if the project config doesn't explicitly define them (or maybe always?).
    # But here, we want the "Effective Configuration".
    
    # Strategy: Start with Global, overlay Project specific parts.
    # However, load_config returns a full object with defaults.
    
    # We want:
    # - Meeting/Server/GUI/UI -> From Global (unless we want per-project overrides?)
    #   Let's say Global prevails for these to ensure license/port consistency.
    # - Performance/CI/Backends/API -> From Project (or Global if Project is empty/default)
    
    # Since we can't easily know if a field is "default" or "explicitly set to default value",
    # we assume the Global config holds the "System" settings.
    
    merged = project_config
    
    # Force Global Settings
    merged.server = global_config.server
    merged.gui = global_config.gui
    merged.meeting = global_config.meeting
    merged.ui = global_config.ui
    # Plugins? Maybe merge lists? For now, let's stick to Global for plugins to avoid security issues.
    merged.plugins = global_config.plugins
    
    return merged


def _update_yaml_section(file_path: Path, updates: dict[str, Any]) -> None:
    """Helper to update specific sections of a YAML file without destroying others."""
    data = {}
    if file_path.exists():
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning("Failed to read %s for update: %s", file_path, e)
    
    # Deep merge or top-level replace?
    # For top-level sections (e.g. "meeting"), we replace the whole dict.
    for key, value in updates.items():
        data[key] = value
        
    try:
        with file_path.open("w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False)
    except Exception as e:
        logger.error("Failed to write %s: %s", file_path, e)
        raise


def save_global_settings(config: JupiterConfig, install_path: Path) -> None:
    """Save only global settings (Server, GUI, Meeting, UI, Plugins) to the install path."""
    updates = {
        "server": {"host": config.server.host, "port": config.server.port},
        "gui": {"host": config.gui.host, "port": config.gui.port},
        "meeting": {"enabled": config.meeting.enabled, "deviceKey": config.meeting.deviceKey},
        "ui": {"theme": config.ui.theme, "language": config.ui.language},
        "plugins": {"enabled": config.plugins.enabled, "disabled": config.plugins.disabled},
        "users": [{"name": u.name, "token": u.token, "role": u.role} for u in config.users],
    }
    _update_yaml_section(install_path / CONFIG_FILE_NAME, updates)


def save_project_settings(config: JupiterConfig, project_path: Path) -> None:
    """Save only project settings (Performance, CI, Backends, API) to the project path."""
    updates = {
        "performance": {
            "parallel_scan": config.performance.parallel_scan,
            "max_workers": config.performance.max_workers,
            "scan_timeout": config.performance.scan_timeout,
            "graph_simplification": config.performance.graph_simplification,
            "max_graph_nodes": config.performance.max_graph_nodes,
            "large_file_threshold": config.performance.large_file_threshold,
            "excluded_dirs": config.performance.excluded_dirs,
        },
        "ci": {"fail_on": config.ci.fail_on},
        "backends": [
            {"name": b.name, "type": b.type, "path": b.path, "api_url": b.api_url}
            for b in config.backends
        ],
        "security": { # Security is usually project specific (allowed commands)
             "allow_run": config.security.allow_run,
             "allowed_commands": config.security.allowed_commands
        }
    }
    
    if config.project_api:
        updates["api"] = {
            "type": config.project_api.type,
            "base_url": config.project_api.base_url,
            "openapi_url": config.project_api.openapi_url,
            "connector": config.project_api.connector,
            "app_var": config.project_api.app_var,
            "path": config.project_api.path,
        }

    _update_yaml_section(project_path / CONFIG_FILE_NAME, updates)


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
        "ci": {
            "fail_on": config.ci.fail_on,
        },
        "plugins": {
            "enabled": config.plugins.enabled,
            "disabled": config.plugins.disabled,
        },
        "performance": {
            "parallel_scan": config.performance.parallel_scan,
            "max_workers": config.performance.max_workers,
            "scan_timeout": config.performance.scan_timeout,
            "graph_simplification": config.performance.graph_simplification,
            "max_graph_nodes": config.performance.max_graph_nodes,
            "large_file_threshold": config.performance.large_file_threshold,
            "excluded_dirs": config.performance.excluded_dirs,
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

    if config.project_api:
        data["api"] = {
            "type": config.project_api.type,
            "base_url": config.project_api.base_url,
            "openapi_url": config.project_api.openapi_url,
            "connector": config.project_api.connector,
            "app_var": config.project_api.app_var,
            "path": config.project_api.path,
        }
    
    try:
        with config_file.open("w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False)
        logger.info("Saved config to %s", config_file)
    except Exception as e:
        logger.error("Failed to save config file: %s", e)
        raise