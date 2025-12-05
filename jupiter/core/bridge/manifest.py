"""Plugin manifest parsing and validation.

Version: 0.1.3

This module handles loading, parsing, and validating plugin.yaml manifest files.
It provides:
- YAML parsing with error handling
- JSON Schema validation
- Conversion to PluginManifest class
- Version compatibility checking

Changes:
- 0.1.3: Added support for api.router format (FastAPI router entrypoint)
- 0.1.2: Fixed source_path to use plugin directory instead of manifest file path
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from jupiter.core.bridge.interfaces import (
    IPluginManifest,
    PluginType,
    Permission,
    UILocation,
    PluginCapabilities,
    CLIContribution,
    APIContribution,
    UIContribution,
)
from jupiter.core.bridge.exceptions import (
    ManifestError,
    ValidationError,
)

logger = logging.getLogger(__name__)

# Path to JSON schema for validation
SCHEMA_PATH = Path(__file__).parent / "schemas" / "plugin_manifest.json"

# Cache for loaded schema
_schema_cache: Optional[Dict[str, Any]] = None


def _load_schema() -> Dict[str, Any]:
    """Load the JSON schema for manifest validation.
    
    Returns:
        The parsed JSON schema dict (empty dict if not found).
        
    Raises:
        ValidationError: If schema file cannot be loaded.
    """
    global _schema_cache
    
    if _schema_cache is not None:
        return _schema_cache
    
    if not SCHEMA_PATH.exists():
        logger.warning("Plugin manifest schema not found at %s", SCHEMA_PATH)
        _schema_cache = {}  # Cache empty dict to avoid repeated warnings
        return {}
    
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema: Dict[str, Any] = json.load(f)
        _schema_cache = schema
        logger.debug("Loaded plugin manifest schema from %s", SCHEMA_PATH)
        return schema
    except json.JSONDecodeError as e:
        raise ValidationError(
            f"Invalid JSON in schema file: {e}",
            schema_path=str(SCHEMA_PATH)
        ) from e
    except OSError as e:
        raise ValidationError(
            f"Cannot read schema file: {e}",
            schema_path=str(SCHEMA_PATH)
        ) from e


def _validate_with_schema(data: Dict[str, Any], plugin_id: str) -> List[str]:
    """Validate manifest data against JSON Schema.
    
    Args:
        data: Parsed manifest data
        plugin_id: Plugin ID for error context
        
    Returns:
        List of validation error messages (empty if valid)
    """
    schema = _load_schema()
    if not schema:
        # No schema available, skip validation
        return []
    
    errors: List[str] = []
    
    # Basic required field checks (simplified schema validation)
    required_fields = schema.get("required", [])
    for field_name in required_fields:
        if field_name not in data:
            errors.append(f"Missing required field: '{field_name}'")
    
    # Validate field types and patterns
    properties = schema.get("properties", {})
    
    for field_name, value in data.items():
        if field_name not in properties:
            if schema.get("additionalProperties") is False:
                errors.append(f"Unknown field: '{field_name}'")
            continue
        
        field_schema = properties[field_name]
        
        # Type check
        expected_type = field_schema.get("type")
        if expected_type:
            if expected_type == "string" and not isinstance(value, str):
                errors.append(f"Field '{field_name}' must be a string")
            elif expected_type == "boolean" and not isinstance(value, bool):
                errors.append(f"Field '{field_name}' must be a boolean")
            elif expected_type == "integer" and not isinstance(value, int):
                errors.append(f"Field '{field_name}' must be an integer")
            elif expected_type == "array" and not isinstance(value, list):
                errors.append(f"Field '{field_name}' must be an array")
            elif expected_type == "object" and not isinstance(value, dict):
                errors.append(f"Field '{field_name}' must be an object")
        
        # Enum check
        allowed_values = field_schema.get("enum")
        if allowed_values and value not in allowed_values:
            errors.append(
                f"Field '{field_name}' must be one of: {allowed_values}, got '{value}'"
            )
        
        # Pattern check (simplified regex validation)
        pattern = field_schema.get("pattern")
        if pattern and isinstance(value, str):
            import re
            if not re.match(pattern, value):
                errors.append(
                    f"Field '{field_name}' does not match pattern: {pattern}"
                )
    
    return errors


class PluginManifest(IPluginManifest):
    """Concrete implementation of plugin manifest.
    
    Represents the parsed and validated content of a plugin.yaml file.
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        version: str,
        description: str,
        plugin_type: PluginType,
        jupiter_version: str,
        author: Optional[Dict[str, str]] = None,
        license: Optional[str] = None,
        homepage: Optional[str] = None,
        repository: Optional[str] = None,
        trust_level: str = "experimental",
        extends: bool = False,
        permissions: Optional[List[Permission]] = None,
        dependencies: Optional[Dict[str, str]] = None,
        python_dependencies: Optional[List[str]] = None,
        capabilities: Optional[PluginCapabilities] = None,
        entrypoints: Optional[Dict[str, str]] = None,
        cli_contributions: Optional[List[CLIContribution]] = None,
        api_contributions: Optional[List[APIContribution]] = None,
        ui_contributions: Optional[List[UIContribution]] = None,
        config_schema: Optional[Dict[str, Any]] = None,
        config_defaults: Optional[Dict[str, Any]] = None,
        source_path: Optional[Path] = None,
    ) -> None:
        """Initialize a PluginManifest.
        
        Args:
            id: Unique plugin identifier
            name: Human-readable name
            version: Semantic version string
            description: Plugin description
            plugin_type: Type of plugin (core, system, tool)
            jupiter_version: Minimum compatible Jupiter version
            author: Author information dict
            license: License identifier
            homepage: Homepage URL
            repository: Repository URL
            trust_level: Trust level (experimental, community, official)
            extends: Whether plugin extends another
            permissions: Required permissions
            dependencies: Plugin dependencies
            python_dependencies: Python package dependencies
            capabilities: Plugin capabilities
            entrypoints: Module entrypoints
            cli_contributions: CLI commands
            api_contributions: API routes
            ui_contributions: UI panels
            config_schema: Configuration schema
            config_defaults: Default configuration values
            source_path: Path to plugin.yaml
        """
        self._id = id
        self._name = name
        self._version = version
        self._description = description
        self._plugin_type = plugin_type
        self._jupiter_version = jupiter_version
        self._author = author
        self._license = license
        self._homepage = homepage
        self._repository = repository
        self._trust_level = trust_level
        self._extends = extends
        self._permissions = permissions if permissions is not None else []
        self._dependencies = dependencies if dependencies is not None else {}
        self._python_dependencies = python_dependencies if python_dependencies is not None else []
        self._capabilities = capabilities if capabilities is not None else PluginCapabilities()
        self._entrypoints = entrypoints if entrypoints is not None else {}
        self._cli_contributions = cli_contributions if cli_contributions is not None else []
        self._api_contributions = api_contributions if api_contributions is not None else []
        self._ui_contributions = ui_contributions if ui_contributions is not None else []
        self._config_schema = config_schema
        self._config_defaults = config_defaults if config_defaults is not None else {}
        self._source_path = source_path
    
    # IPluginManifest properties
    @property
    def id(self) -> str:
        return self._id
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def version(self) -> str:
        return self._version
    
    @property
    def description(self) -> str:
        return self._description
    
    @property
    def plugin_type(self) -> PluginType:
        return self._plugin_type
    
    @property
    def jupiter_version(self) -> str:
        return self._jupiter_version
    
    @property
    def permissions(self) -> List[Permission]:
        return self._permissions
    
    @property
    def dependencies(self) -> Dict[str, str]:
        return self._dependencies
    
    @property
    def capabilities(self) -> PluginCapabilities:
        return self._capabilities
    
    @property
    def cli_contributions(self) -> List[CLIContribution]:
        return self._cli_contributions
    
    @property
    def api_contributions(self) -> List[APIContribution]:
        return self._api_contributions
    
    @property
    def ui_contributions(self) -> List[UIContribution]:
        return self._ui_contributions
    
    @property
    def trust_level(self) -> str:
        return self._trust_level
    
    @property
    def source_path(self) -> Optional[Path]:
        return self._source_path
    
    @property
    def config_defaults(self) -> Dict[str, Any]:
        return self._config_defaults
    
    # Additional properties
    @property
    def author(self) -> Optional[Dict[str, str]]:
        return self._author
    
    @property
    def license(self) -> Optional[str]:
        return self._license
    
    @property
    def homepage(self) -> Optional[str]:
        return self._homepage
    
    @property
    def repository(self) -> Optional[str]:
        return self._repository
    
    @property
    def extends(self) -> bool:
        return self._extends
    
    @property
    def python_dependencies(self) -> List[str]:
        return self._python_dependencies
    
    @property
    def entrypoints(self) -> Dict[str, str]:
        return self._entrypoints
    
    @property
    def config_schema(self) -> Optional[Dict[str, Any]]:
        return self._config_schema
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize manifest to dict for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "type": self.plugin_type.value,
            "jupiter_version": self.jupiter_version,
            "author": self.author,
            "license": self.license,
            "trust_level": self.trust_level,
            "extends": self.extends,
            "permissions": [p.value for p in self.permissions],
            "dependencies": self.dependencies,
            "python_dependencies": self.python_dependencies,
            "capabilities": self.capabilities.to_dict(),
            "entrypoints": self.entrypoints,
            "cli": [c.to_dict() for c in self.cli_contributions],
            "api": [a.to_dict() for a in self.api_contributions],
            "ui": [u.to_dict() for u in self.ui_contributions],
            "config_schema": self.config_schema,
            "config_defaults": self.config_defaults,
        }
    
    @classmethod
    def from_dict(
        cls, 
        data: Dict[str, Any], 
        source_path: Optional[Path] = None,
        validate: bool = True
    ) -> "PluginManifest":
        """Create a PluginManifest from a dictionary.
        
        Args:
            data: Parsed manifest data
            source_path: Path to the manifest file (for error messages)
            validate: Whether to validate against schema
            
        Returns:
            PluginManifest instance
            
        Raises:
            ManifestError: If required fields are missing or invalid
            ValidationError: If schema validation fails
        """
        plugin_id = data.get("id", "unknown")
        
        # Validate against schema if requested
        if validate:
            errors = _validate_with_schema(data, plugin_id)
            if errors:
                raise ManifestError(
                    f"Manifest validation failed with {len(errors)} error(s)",
                    plugin_id=plugin_id,
                    details={"errors": errors}
                )
        
        # Extract required fields
        try:
            plugin_id = data["id"]
            name = data["name"]
            version = data["version"]
            description = data["description"]
            type_str = data["type"]
            jupiter_version = data["jupiter_version"]
        except KeyError as e:
            raise ManifestError(
                f"Missing required field: {e}",
                plugin_id=plugin_id,
                field=str(e)
            ) from e
        
        # Parse plugin type
        try:
            plugin_type = PluginType(type_str)
        except ValueError:
            raise ManifestError(
                f"Invalid plugin type: '{type_str}'",
                plugin_id=plugin_id,
                field="type"
            )
        
        # Parse permissions
        permissions: List[Permission] = []
        for perm_str in data.get("permissions", []):
            try:
                permissions.append(Permission(perm_str))
            except ValueError:
                logger.warning(
                    "Unknown permission '%s' in plugin %s, ignoring",
                    perm_str, plugin_id
                )
        
        # Parse capabilities
        caps_data = data.get("capabilities", {})
        metrics_data = caps_data.get("metrics", {})
        jobs_data = caps_data.get("jobs", {})
        health_data = caps_data.get("health_check", {})
        
        capabilities = PluginCapabilities(
            metrics_enabled=metrics_data.get("enabled", False),
            metrics_export_format=metrics_data.get("export_format", "json"),
            jobs_enabled=jobs_data.get("enabled", False),
            jobs_max_concurrent=jobs_data.get("max_concurrent", 1),
            health_check_enabled=health_data.get("enabled", True),
        )
        
        # Parse CLI contributions
        cli_contributions: List[CLIContribution] = []
        cli_data = data.get("cli", {})
        for cmd in cli_data.get("commands", []):
            cli_contributions.append(CLIContribution(
                name=cmd["name"],
                description=cmd.get("description", ""),
                entrypoint=cmd["entrypoint"],
                parent=cmd.get("parent"),
                aliases=cmd.get("aliases", []),
            ))
        
        # Parse API contributions
        api_contributions: List[APIContribution] = []
        api_data = data.get("api", {})
        
        # Support for api.router format (FastAPI router entrypoint)
        # Format: api.router: "server.api:router" with optional prefix and tags
        if "router" in api_data:
            api_contributions.append(APIContribution(
                plugin_id=plugin_id,
                entrypoint=api_data["router"],  # Store router entrypoint for later resolution
                prefix=api_data.get("prefix", f"/plugins/{plugin_id}"),
                tags=api_data.get("tags", [plugin_id]),
                router=None,  # Will be resolved by bridge after module load
            ))
        
        # Support for api.routes format (individual route definitions)
        for route in api_data.get("routes", []):
            api_contributions.append(APIContribution(
                path=route["path"],
                method=route["method"],
                entrypoint=route["entrypoint"],
                tags=route.get("tags", []),
                auth_required=route.get("auth_required", False),
            ))
        
        # Parse UI contributions
        ui_contributions: List[UIContribution] = []
        ui_data = data.get("ui", {})
        for panel in ui_data.get("panels", []):
            try:
                location = UILocation(panel["location"])
            except ValueError:
                location = UILocation.NONE
            
            ui_contributions.append(UIContribution(
                id=panel["id"],
                location=location,
                route=panel["route"],
                title_key=panel["title_key"],
                icon=panel.get("icon", "🔌"),
                order=panel.get("order", 100),
                settings_section=panel.get("settings_section"),
            ))
        
        # Parse config
        config_data = data.get("config", {})
        
        return cls(
            id=plugin_id,
            name=name,
            version=version,
            description=description,
            plugin_type=plugin_type,
            jupiter_version=jupiter_version,
            author=data.get("author"),
            license=data.get("license"),
            homepage=data.get("homepage"),
            repository=data.get("repository"),
            trust_level=data.get("trust_level", "experimental"),
            extends=data.get("extends", False),
            permissions=permissions,
            dependencies=data.get("dependencies", {}),
            python_dependencies=data.get("python_dependencies", []),
            capabilities=capabilities,
            entrypoints=data.get("entrypoints", {}),
            cli_contributions=cli_contributions,
            api_contributions=api_contributions,
            ui_contributions=ui_contributions,
            config_schema=config_data.get("schema"),
            config_defaults=config_data.get("defaults", {}),
            source_path=source_path,
        )
    
    @classmethod
    def from_yaml(cls, path: Union[str, Path], validate: bool = True) -> "PluginManifest":
        """Load a PluginManifest from a YAML file.
        
        Args:
            path: Path to plugin.yaml file
            validate: Whether to validate against schema
            
        Returns:
            PluginManifest instance
            
        Raises:
            ManifestError: If file cannot be read or parsed
        """
        path = Path(path)
        
        if not path.exists():
            raise ManifestError(
                f"Manifest file not found: {path}",
                plugin_id="unknown",
                details={"path": str(path)}
            )
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ManifestError(
                f"Invalid YAML syntax: {e}",
                plugin_id="unknown",
                details={"path": str(path)}
            ) from e
        except OSError as e:
            raise ManifestError(
                f"Cannot read manifest file: {e}",
                plugin_id="unknown",
                details={"path": str(path)}
            ) from e
        
        if not isinstance(data, dict):
            raise ManifestError(
                "Manifest must be a YAML mapping",
                plugin_id="unknown",
                details={"path": str(path)}
            )
        
        # Use parent directory as source_path (the plugin directory, not the yaml file)
        return cls.from_dict(data, source_path=path.parent, validate=validate)
    
    @classmethod
    def from_plugin_dir(cls, plugin_dir: Union[str, Path], validate: bool = True) -> "PluginManifest":
        """Load manifest from a plugin directory.
        
        Looks for plugin.yaml in the given directory.
        
        Args:
            plugin_dir: Path to plugin directory
            validate: Whether to validate against schema
            
        Returns:
            PluginManifest instance
        """
        plugin_dir = Path(plugin_dir)
        manifest_path = plugin_dir / "plugin.yaml"
        return cls.from_yaml(manifest_path, validate=validate)


def generate_manifest_for_legacy(
    plugin_id: str,
    name: str,
    version: str,
    description: str,
    has_ui: bool = False,
    ui_type: str = "none",
) -> PluginManifest:
    """Generate a minimal manifest for a legacy v1 plugin.
    
    Used by the legacy adapter to wrap v1 plugins.
    
    Args:
        plugin_id: Plugin identifier
        name: Display name
        version: Version string
        description: Plugin description
        has_ui: Whether plugin has UI
        ui_type: UI location type
        
    Returns:
        PluginManifest with minimal settings and restricted permissions
    """
    ui_contributions: List[UIContribution] = []
    
    if has_ui and ui_type != "none":
        try:
            location = UILocation(ui_type)
        except ValueError:
            location = UILocation.NONE
        
        if location != UILocation.NONE:
            ui_contributions.append(UIContribution(
                id="main",
                location=location,
                route=f"/plugins/{plugin_id}",
                title_key=f"plugin.{plugin_id}.title",
            ))
    
    return PluginManifest(
        id=plugin_id,
        name=name,
        version=version,
        description=description,
        plugin_type=PluginType.TOOL,
        jupiter_version=">=1.0.0",
        trust_level="experimental",
        permissions=[],  # No permissions by default for legacy
        ui_contributions=ui_contributions,
    )
