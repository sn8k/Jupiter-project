from pathlib import Path
from typing import Dict, Optional
import logging
import uuid
from jupiter.config.config import (
    JupiterConfig,
    ProjectBackendConfig,
    default_project_config_file_name,
    load_global_config,
    save_global_config,
    ProjectDefinition,
    load_config,
)
from jupiter.core.state import save_last_root
from jupiter.core.connectors.base import BaseConnector
from jupiter.core.connectors.local import LocalConnector
from jupiter.core.connectors.remote import RemoteConnector

logger = logging.getLogger(__name__)

class ProjectManager:
    """
    Manages project backends (local or remote) and multiple projects.
    """
    def __init__(self, config: Optional[JupiterConfig] = None):
        self.global_config = load_global_config()
        self.config = config
        self.connectors: Dict[str, BaseConnector] = {}
        
        if self.config:
            self._initialize_connectors()
        elif self.global_config.default_project_id:
            self.set_active_project(self.global_config.default_project_id)

    def create_project(self, path: str, name: str) -> ProjectDefinition:
        """Register a new project."""
        project_id = str(uuid.uuid4())
        project_def = ProjectDefinition(
            id=project_id,
            name=name,
            path=path,
            config_file=default_project_config_file_name(name),
            ignore_globs=[],
        )
        self.global_config.projects.append(project_def)
        self.global_config.default_project_id = project_id
        save_global_config(self.global_config)
        
        # Load it immediately
        self.set_active_project(project_id)
        return project_def

    def set_active_project(self, project_id: str) -> bool:
        """Switch to another project."""
        project = next((p for p in self.global_config.projects if p.id == project_id), None)
        if not project:
            return False
            
        try:
            # Load config from project path
            project_path = Path(project.path)
            new_config = load_config(project_path, config_file=project.config_file)
            new_config.project_root = project_path # Ensure root is set
            
            self.refresh_for_root(new_config)
            
            # Update global default
            self.global_config.default_project_id = project_id
            save_global_config(self.global_config)
            save_last_root(project_path)
            return True
        except Exception as e:
            logger.error(f"Failed to load project {project.name}: {e}")
            return False

    def get_projects(self) -> list[ProjectDefinition]:
        return self.global_config.projects

    def get_active_project(self) -> Optional[ProjectDefinition]:
        """Return the active project definition, if any."""
        if not self.global_config.default_project_id:
            return None
        return next((p for p in self.global_config.projects if p.id == self.global_config.default_project_id), None)

    def delete_project(self, project_id: str) -> bool:
        """Remove a project from the registry."""
        project = next((p for p in self.global_config.projects if p.id == project_id), None)
        if not project:
            return False
            
        self.global_config.projects.remove(project)
        
        # If we deleted the active project, unset default
        if self.global_config.default_project_id == project_id:
            self.global_config.default_project_id = None
            # If there are other projects, pick the first one
            if self.global_config.projects:
                self.global_config.default_project_id = self.global_config.projects[0].id
                # Try to activate it
                self.set_active_project(self.global_config.default_project_id)
            else:
                # No projects left, we are in setup mode effectively
                self.config = None
                self.connectors.clear()
        
        save_global_config(self.global_config)
        return True

    def _initialize_connectors(self) -> None:
        """Initialize connectors based on configuration."""
        self.connectors.clear()
        if not self.config:
            return

        if not self.config.backends:
            default_backend = ProjectBackendConfig(
                name="local",
                type="local_fs",
                path="."
            )
            self.config.backends.append(default_backend)

        for backend_conf in self.config.backends:
            if backend_conf.type == "local_fs":
                backend_path = self._resolve_local_path(backend_conf.path)
                
                # Handle "local" API connector
                project_api = self.config.project_api
                if project_api:
                    logger.info(f"Project API config found: connector={project_api.connector}")
                    if project_api.connector == "local":
                        # Inject local server details
                        project_api.base_url = f"http://{self.config.server.host}:{self.config.server.port}"
                        project_api.openapi_url = "/openapi.json"
                        project_api.type = "openapi"
                        logger.info(f"Configured local API connector: {project_api.base_url}")
                else:
                    logger.info("No Project API config found")

                self.connectors[backend_conf.name] = LocalConnector(
                    str(backend_path),
                    project_api_config=project_api
                )
            elif backend_conf.type == "remote_jupiter_api":
                if backend_conf.api_url:
                    self.connectors[backend_conf.name] = RemoteConnector(
                        base_url=backend_conf.api_url, 
                        api_key=backend_conf.api_key
                    )

    def get_connector(self, name: str = "local") -> Optional[BaseConnector]:
        """Get a connector by name."""
        return self.connectors.get(name)

    def get_default_connector(self) -> BaseConnector:
        """Get the first available connector or local."""
        if not self.connectors:
             # Fallback if something went wrong, though init should handle it
             return LocalConnector(".")
        
        # Return the first one
        return list(self.connectors.values())[0]

    def refresh_for_root(self, config: JupiterConfig) -> None:
        """Reload connectors against a new project root configuration."""
        self.config = config
        self.config.project_root = config.project_root or Path.cwd()
        self._initialize_connectors()

    def _resolve_local_path(self, backend_path: Optional[str]) -> Path:
        base_path = Path(backend_path or ".")
        if base_path.is_absolute():
            return base_path.resolve()
        return (self.config.project_root / base_path).resolve()

    def list_backends(self) -> list[dict]:
        """List available backends."""
        if not self.config:
            return []
        return [
            {
                "name": b.name,
                "type": b.type,
                "path": b.path,
                "api_url": b.api_url
            }
            for b in self.config.backends
        ]

