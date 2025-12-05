"""
Configuration loading and models for Jupiter.

Version: 1.4.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
import os
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

PROJECT_CONFIG_SUFFIX = ".jupiter.yaml"
LEGACY_CONFIG_FILE_NAME = "jupiter.yaml"
GLOBAL_INSTALL_CONFIG_FILE_NAME = "global_config.yaml"
GLOBAL_REGISTRY_FILE_NAME = "global_config.yaml"
LEGACY_GLOBAL_REGISTRY_FILE_NAME = "global.yaml"


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
    """Configuration for the Meeting feature.
    
    Attributes:
        deviceKey: The Jupiter device key for license verification.
        base_url: The Meeting API base URL.
        device_type: The expected device type (default: "Jupiter").
        timeout_seconds: HTTP request timeout for Meeting API calls.
        auth_token: Optional authentication token for Meeting API.
        heartbeat_interval_seconds: Interval between heartbeat signals to Meeting (default: 60).
    """

    deviceKey: Optional[str] = None
    base_url: str = "https://meeting.ygsoft.fr/api"
    device_type: str = "Jupiter"
    timeout_seconds: float = 5.0
    auth_token: Optional[str] = None
    heartbeat_interval_seconds: int = 60


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
class LoggingConfig:
    """Configuration for logging.
    
    Attributes:
        level: Log verbosity level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        path: Log file destination path.
        reset_on_start: If True, delete log file on startup. If False, add separator.
    """

    level: str = "INFO"
    path: Optional[str] = "logs/jupiter.log"  # Default log file path
    reset_on_start: bool = True  # Clear log file on each startup


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

    fail_on: dict[str, int | None] = field(default_factory=dict)


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
class ProjectDefinition:
    """Definition of a registered project."""
    id: str
    name: str
    path: str
    config_file: str | None = None
    ignore_globs: list[str] = field(default_factory=list)


@dataclass
class GlobalConfig:
    """Global application configuration."""
    projects: list[ProjectDefinition] = field(default_factory=list)
    default_project_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GlobalConfig:
        projects_data = data.get("projects", [])
        projects = []
        for p in projects_data:
            ignore_globs = p.get("ignore_globs") or []
            projects.append(ProjectDefinition(
                id=p["id"],
                name=p["name"],
                path=p["path"],
                config_file=p.get("config_file"),
                ignore_globs=ignore_globs if isinstance(ignore_globs, list) else [],
            ))
        return cls(
            projects=projects,
            default_project_id=data.get("default_project_id")
        )


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
class AutodiagConfig:
    """Configuration for the autodiag dual-port architecture (Phase 3).
    
    Attributes:
        enabled: Whether autodiag server is enabled.
        port: Port for autodiag API (localhost only).
        introspect_api: Enable API introspection endpoint.
        validate_handlers: Enable handler validation endpoint.
        collect_runtime_stats: Enable runtime statistics collection.
    """
    enabled: bool = True  # Enabled by default for self-diagnosis
    port: int = 8081
    introspect_api: bool = True
    validate_handlers: bool = True
    collect_runtime_stats: bool = False


@dataclass
class JupiterConfig:
    """Global configuration."""

    server: ServerConfig = field(default_factory=ServerConfig)
    gui: GuiConfig = field(default_factory=GuiConfig)
    meeting: MeetingConfig = field(default_factory=MeetingConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    plugins: PluginsConfig = field(default_factory=PluginsConfig)
    users: list[UserConfig] = field(default_factory=list)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    ci: CiConfig = field(default_factory=CiConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    backends: list[ProjectBackendConfig] = field(default_factory=list)
    project_api: Optional[ProjectApiConfig] = None
    autodiag: AutodiagConfig = field(default_factory=AutodiagConfig)
    project_root: Path = field(default_factory=Path.cwd)
    developer_mode: bool = False  # Enable developer mode features (hot reload, etc.)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JupiterConfig:
        """Create a config object from a dictionary."""
        server_data = data.get("server", {})
        gui_data = data.get("gui", {})
        meeting_data = data.get("meeting", {})
        
        # Robustness: handle device_key vs deviceKey
        if "device_key" in meeting_data and "deviceKey" not in meeting_data:
            meeting_data["deviceKey"] = meeting_data.pop("device_key")
        
        # Filter only known MeetingConfig fields to avoid TypeError
        meeting_known_fields = {"enabled", "deviceKey", "base_url", "device_type", "timeout_seconds", "auth_token"}
        meeting_data = {k: v for k, v in meeting_data.items() if k in meeting_known_fields}

        ui_data = data.get("ui", {})
        plugins_data = data.get("plugins", {})
        logging_data = data.get("logging", {})
        
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
        autodiag_data = data.get("autodiag", {})

        backends = [ProjectBackendConfig(**b) for b in backends_data]
        project_api = ProjectApiConfig(**project_api_data) if project_api_data else None
        autodiag = AutodiagConfig(**autodiag_data) if autodiag_data else AutodiagConfig()

        return cls(
            server=ServerConfig(**server_data),
            gui=GuiConfig(**gui_data),
            meeting=MeetingConfig(**meeting_data),
            ui=UIConfig(**ui_data),
            logging=LoggingConfig(**logging_data),
            plugins=plugins_config,
            users=users_config,
            security=SecurityConfig(**security_data),
            ci=CiConfig(**ci_data),
            performance=PerformanceConfig(**performance_data),
            backends=backends,
            project_api=project_api,
            autodiag=autodiag,
            developer_mode=data.get("developer_mode", False),
        )


def _sanitize_project_name_for_filename(name: str) -> str:
    """Normalize a project name so it is safe for filenames."""
    normalized = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name.strip())
    normalized = normalized.strip("._") or "project"
    return normalized.lower()


def default_project_config_file_name(project_name: str) -> str:
    """Return the canonical config file name for a project."""
    return f"{_sanitize_project_name_for_filename(project_name)}{PROJECT_CONFIG_SUFFIX}"


def get_project_config_path(root_path: Path, config_file: str | None = None) -> Path:
    """Locate the project configuration file, preferring the new naming scheme."""
    preferred_name = config_file or default_project_config_file_name(root_path.name)
    candidates = [
        root_path / preferred_name,
        *sorted(root_path.glob(f"*{PROJECT_CONFIG_SUFFIX}")),
        root_path / LEGACY_CONFIG_FILE_NAME,
    ]

    seen: set[Path] = set()
    ordered_candidates: list[Path] = []
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        ordered_candidates.append(candidate)

    for candidate in ordered_candidates:
        if candidate.is_file():
            return candidate

    # Default to the preferred path even if it does not exist yet
    return ordered_candidates[0]


def resolve_install_config_path(install_path: Path) -> Path:
    """Return the global install config path, honoring legacy filenames."""
    modern = install_path / GLOBAL_INSTALL_CONFIG_FILE_NAME
    legacy = install_path / LEGACY_CONFIG_FILE_NAME
    if modern.exists():
        return modern
    if legacy.exists():
        return legacy
    return modern


def load_install_config(install_path: Path) -> JupiterConfig:
    """Load configuration from the install directory using the global filename."""
    config_path = resolve_install_config_path(install_path)

    if not config_path.is_file():
        logger.debug("No global config file found at %s, using defaults.", config_path)
        return JupiterConfig(project_root=install_path)

    logger.info("Loading global config from %s", config_path)
    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        config = JupiterConfig.from_dict(data)
        config.project_root = install_path
        return config
    except Exception as e:
        logger.error("Failed to load global config file: %s", e)
        return JupiterConfig(project_root=install_path)



def load_config(root_path: Path, config_file: str | None = None) -> JupiterConfig:
    """Load configuration from a YAML file.

    Project configs follow the ``<project>.jupiter.yaml`` naming convention.
    Legacy ``jupiter.yaml`` files are still supported as a fallback.
    """
    config_path = get_project_config_path(root_path, config_file=config_file)

    if not config_path.is_file():
        logger.debug("No config file found at %s, using defaults.", config_path)
        return JupiterConfig(project_root=root_path)

    logger.info("Loading config from %s", config_path)
    try:
        with config_path.open("r", encoding="utf-8") as f:
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
    global_config = load_install_config(install_path)

    # Check LocalAppData override
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        app_data_path = Path(local_app_data) / "Jupiter"
        if resolve_install_config_path(app_data_path).exists():
             logger.info("Loading global config from LocalAppData: %s", app_data_path)
             global_config = load_install_config(app_data_path)
    
    # 2. Always load project config (even if paths are same)
    # Project-specific settings (API, backends, performance) should come from project config
    project_config = load_config(project_path)

    # 3. Merge: Global settings for system-level, Project settings for project-level
    
    # We want:
    # - Meeting/Server/GUI/UI/Plugins -> From Global (to ensure license/port consistency)
    # - Performance/CI/Backends/API/project_api -> From Project
    
    merged = project_config
    
    # Force Global Settings (system-level)
    merged.server = global_config.server
    merged.gui = global_config.gui
    merged.meeting = global_config.meeting
    merged.ui = global_config.ui
    merged.plugins = global_config.plugins
    merged.users = global_config.users
    merged.security = global_config.security
    merged.logging = global_config.logging
    
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


def _serialize_performance(performance: PerformanceConfig) -> dict[str, Any]:
    """Convert performance config to a serializable dict."""
    return {
        "parallel_scan": performance.parallel_scan,
        "max_workers": performance.max_workers,
        "scan_timeout": performance.scan_timeout,
        "graph_simplification": performance.graph_simplification,
        "max_graph_nodes": performance.max_graph_nodes,
        "large_file_threshold": performance.large_file_threshold,
        "excluded_dirs": performance.excluded_dirs,
    }


def _serialize_backends(backends: list[ProjectBackendConfig]) -> list[dict[str, Any]]:
    """Convert backend configs to a serializable list."""
    return [
        {
            "name": backend.name,
            "type": backend.type,
            "path": backend.path,
            "api_url": backend.api_url,
        }
        for backend in backends
    ]


def _serialize_project_api(project_api: ProjectApiConfig | None) -> dict[str, Any] | None:
    """Convert optional project API config to a dict if present."""
    if not project_api:
        return None
    return {
        "type": project_api.type,
        "base_url": project_api.base_url,
        "openapi_url": project_api.openapi_url,
        "connector": project_api.connector,
        "app_var": project_api.app_var,
        "path": project_api.path,
    }


def save_global_settings(config: JupiterConfig, install_path: Path) -> None:
    """Save global settings (Server, GUI, Meeting, UI, Security, Plugins, Users, Logging) to the install path."""
    meeting_data = {
        "deviceKey": config.meeting.deviceKey,
        "heartbeat_interval_seconds": config.meeting.heartbeat_interval_seconds,
    }
    # Only include auth_token if it has a value (avoid saving null/empty)
    if config.meeting.auth_token:
        meeting_data["auth_token"] = config.meeting.auth_token
    
    plugin_settings: dict[str, Any] = {}
    if getattr(config.plugins, "settings", None):
        plugin_settings = {k: v for k, v in config.plugins.settings.items()}

    updates = {
        "server": {"host": config.server.host, "port": config.server.port},
        "gui": {"host": config.gui.host, "port": config.gui.port},
        "meeting": meeting_data,
        "ui": {"theme": config.ui.theme, "language": config.ui.language},
        "security": {
            "allow_run": config.security.allow_run,
            "allowed_commands": config.security.allowed_commands,
            "token": config.security.token,
        },
        "logging": {"level": config.logging.level, "path": config.logging.path},
        "plugins": {
            "enabled": config.plugins.enabled,
            "disabled": config.plugins.disabled,
            **plugin_settings,
        },
        "users": [{"name": u.name, "token": u.token, "role": u.role} for u in config.users],
    }
    _update_yaml_section(resolve_install_config_path(install_path), updates)


def save_project_settings(config: JupiterConfig, project_path: Path) -> None:
    """Save only project-specific settings (Performance, CI, Backends, API) to the project path.
    
    Global settings (server, gui, meeting, ui, users, plugins, security, logging)
    should be saved via save_global_settings() to global_config.yaml instead.
    """
    updates = {
        "performance": _serialize_performance(config.performance),
        "ci": {"fail_on": config.ci.fail_on},
        "backends": _serialize_backends(config.backends),
    }
    
    project_api_serialized = _serialize_project_api(config.project_api)
    if project_api_serialized:
        updates["api"] = project_api_serialized

    _update_yaml_section(get_project_config_path(project_path), updates)


def save_config(config: JupiterConfig, root_path: Path) -> None:
    """Save project-specific configuration to the project YAML file.
    
    This only saves project-specific settings (performance, ci, backends, api).
    Global settings should be saved via save_global_settings() instead.
    """
    config_file = get_project_config_path(root_path)
    
    data = {
        "performance": _serialize_performance(config.performance),
        "ci": {"fail_on": config.ci.fail_on},
        "backends": _serialize_backends(config.backends),
    }

    project_api_serialized = _serialize_project_api(config.project_api)
    if project_api_serialized:
        data["api"] = project_api_serialized
    
    try:
        with config_file.open("w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False)
        logger.info("Saved project config to %s", config_file)
    except Exception as e:
        logger.error("Failed to save project config file: %s", e)
        raise


def get_global_config_path() -> Path:
    """Get the path to the global configuration file."""
    home_root = Path.home() / ".jupiter"
    modern = home_root / GLOBAL_REGISTRY_FILE_NAME
    legacy = home_root / LEGACY_GLOBAL_REGISTRY_FILE_NAME
    if modern.exists():
        return modern
    if legacy.exists():
        return legacy
    return modern


def load_global_config() -> GlobalConfig:
    """Load the global configuration."""
    path = get_global_config_path()
    if not path.exists():
        return GlobalConfig()

    def _normalize_projects(cfg: GlobalConfig) -> bool:
        """Ensure project entries use modern config filenames and absolute paths."""
        changed = False
        for project in cfg.projects:
            expected_cfg = default_project_config_file_name(project.name)
            if not project.config_file or project.config_file in (LEGACY_CONFIG_FILE_NAME, "jupiter.yaml"):
                project.config_file = expected_cfg
                changed = True

            try:
                resolved = Path(project.path).expanduser().resolve()
                if str(resolved) != project.path:
                    project.path = str(resolved)
                    changed = True
            except OSError:
                # If the path cannot be resolved, keep the stored value.
                continue
        return changed

    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            cfg = GlobalConfig.from_dict(data)

        if _normalize_projects(cfg):
            try:
                save_global_config(cfg)
                logger.info("Normalized global registry entries to modern config naming.")
            except Exception as e:
                logger.warning("Failed to persist normalized global registry: %s", e)

        return cfg
    except Exception as e:
        logger.error("Failed to load global config: %s", e)
        return GlobalConfig()


def save_global_config(config: GlobalConfig) -> None:
    """Save the global configuration."""
    storage_root = Path.home() / ".jupiter"
    storage_root.mkdir(parents=True, exist_ok=True)
    path = storage_root / GLOBAL_REGISTRY_FILE_NAME
    
    data = {
        "projects": [
            {
                "id": p.id,
                "name": p.name,
                "path": p.path,
                "config_file": p.config_file or default_project_config_file_name(p.name),
                "ignore_globs": p.ignore_globs,
            }
            for p in config.projects
        ],
        "default_project_id": config.default_project_id
    }
    
    try:
        with path.open("w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False)
    except Exception as e:
        logger.error("Failed to save global config: %s", e)
        raise

