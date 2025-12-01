from typing import Any, Dict, Optional
from jupiter.core.connectors.base import BaseConnector
from jupiter.core.connectors.project_api import OpenApiConnector

class GenericApiConnector(BaseConnector):
    """Connector for a generic remote API (OpenAPI)."""

    def __init__(self, base_url: str, openapi_url: str = "/openapi.json"):
        self.base_url = base_url.rstrip("/")
        self.openapi_url = openapi_url
        self.api_connector = OpenApiConnector(self.base_url, openapi_url)

    async def scan(self, options: Dict[str, Any]) -> Dict[str, Any]:
        # For a generic API, "scan" means fetching the schema and listing endpoints
        endpoints = await self.api_connector.get_endpoints()
        
        # We represent endpoints as "files" for the UI to display something
        files = []
        for ep in endpoints:
            files.append({
                "path": f"{ep.method} {ep.path}",
                "size_bytes": 0,
                "modified_timestamp": 0,
                "file_type": "endpoint",
                "language_analysis": {"language": "API"},
            })

        return {
            "report_schema_version": "1.0",
            "root": self.base_url,
            "files": files,
            "dynamic": None,
            "plugins": {},
            "quality": {},
            "refactoring": [],
        }

    async def analyze(self, options: Dict[str, Any]) -> Dict[str, Any]:
        endpoints = await self.api_connector.get_endpoints()
        return {
            "api": {
                "endpoints": [e.to_dict() for e in endpoints],
                "config": {
                    "base_url": self.base_url,
                    "openapi_url": self.openapi_url
                }
            },
            "summary": {
                "file_count": len(endpoints),
                "total_size_bytes": 0,
                "languages": {"API": len(endpoints)}
            }
        }

    async def run_command(self, command: list[str], with_dynamic: bool = False, cwd: Optional[str] = None) -> Dict[str, Any]:
        return {
            "stdout": "",
            "stderr": "Running commands is not supported on generic API projects.",
            "returncode": 1,
            "dynamic_data": None
        }

    def get_api_base_url(self) -> Optional[str]:
        return self.base_url
