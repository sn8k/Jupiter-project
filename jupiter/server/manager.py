from pathlib import Path
from typing import Dict, Optional
import logging
from jupiter.config.config import JupiterConfig, ProjectBackendConfig
from jupiter.core.connectors.base import BaseConnector
from jupiter.core.connectors.local import LocalConnector
from jupiter.core.connectors.remote import RemoteConnector

logger = logging.getLogger(__name__)

class ProjectManager:
    """
    Manages project backends (local or remote).
    """
    def __init__(self, config: JupiterConfig):
        self.config = config
        self.connectors: Dict[str, BaseConnector] = {}
        self._initialize_connectors()

    def _initialize_connectors(self) -> None:
        """Initialize connectors based on configuration."""
        self.connectors.clear()
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
        return [
            {
                "name": b.name,
                "type": b.type,
                "path": b.path,
                "api_url": b.api_url
            }
            for b in self.config.backends
        ]

