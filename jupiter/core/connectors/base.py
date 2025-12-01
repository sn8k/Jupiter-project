from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseConnector(ABC):
    """Abstract base class for project backends."""

    @abstractmethod
    async def scan(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a scan on the project."""
        pass

    @abstractmethod
    async def run_command(self, command: list[str], with_dynamic: bool = False, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Run a command in the project context.
        
        Args:
            command: The command to execute as a list of strings.
            with_dynamic: Enable dynamic analysis (tracing) for this run.
            cwd: Optional working directory. If None, uses project root.
        """
        pass

    @abstractmethod
    async def analyze(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the project."""
        pass

    @abstractmethod
    def get_api_base_url(self) -> Optional[str]:
        """Return the API base URL if applicable (for UI direct access)."""
        pass
