"""Connectors for inspecting the project's own API."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import httpx
import logging

logger = logging.getLogger(__name__)

@dataclass
class EndpointInfo:
    path: str
    method: str
    summary: Optional[str] = None
    tags: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class BaseProjectApiConnector(ABC):
    @abstractmethod
    async def get_endpoints(self) -> List[EndpointInfo]:
        pass

class OpenApiConnector(BaseProjectApiConnector):
    def __init__(self, base_url: str, openapi_url: str):
        self.base_url = base_url.rstrip("/")
        self.openapi_url = openapi_url
        
    async def get_endpoints(self) -> List[EndpointInfo]:
        url = f"{self.base_url}{self.openapi_url}"
        logger.info(f"Fetching OpenAPI schema from {url}")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=5.0)
                resp.raise_for_status()
                schema = resp.json()
                return self._parse_openapi(schema)
        except Exception as e:
            logger.warning(f"Failed to fetch OpenAPI schema from {url}: {e}")
            return []

    def _parse_openapi(self, schema: Dict[str, Any]) -> List[EndpointInfo]:
        endpoints = []
        paths = schema.get("paths", {})
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.lower() not in ["get", "post", "put", "delete", "patch", "options", "head"]:
                    continue
                endpoints.append(EndpointInfo(
                    path=path,
                    method=method.upper(),
                    summary=details.get("summary"),
                    tags=details.get("tags", [])
                ))
        return endpoints
