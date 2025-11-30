import httpx
import logging
from typing import Any, Dict, Optional
from jupiter.core.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

class RemoteConnector(BaseConnector):
    """Connector for a remote Jupiter API."""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    async def _request_json(self, method: str, endpoint: str, *, timeout: float, **kwargs) -> Dict[str, Any]:
        """Perform an HTTP request and return parsed JSON with shared error handling."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(method, url, headers=self.headers, timeout=timeout, **kwargs)
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logger.error("Remote %s failed: %s", endpoint, exc)
            raise

    async def scan(self, options: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request_json("POST", "scan", json=options, timeout=60.0)

    async def analyze(self, options: Dict[str, Any]) -> Dict[str, Any]:
        # analyze is a GET request with query params
        # We need to handle list params (ignore_globs) correctly
        params = {}
        if "top" in options:
            params["top"] = options["top"]
        if "show_hidden" in options:
            params["show_hidden"] = str(options["show_hidden"]).lower()
        
        # httpx handles list params by repeating the key, which is what FastAPI expects
        if "ignore_globs" in options and options["ignore_globs"]:
            params["ignore"] = options["ignore_globs"] # API expects 'ignore' query param for ignore_globs

        return await self._request_json("GET", "analyze", params=params, timeout=60.0)

    async def run_command(self, command: list[str], with_dynamic: bool = False) -> Dict[str, Any]:
        payload = {
            "command": command,
            "with_dynamic": with_dynamic
        }
        data = await self._request_json("POST", "run", json=payload, timeout=300.0)  # 5 minutes for run
        # Map API response to what LocalConnector returns (which is basically the same structure)
        return {
            "stdout": data.get("stdout", ""),
            "stderr": data.get("stderr", ""),
            "returncode": data.get("returncode", 0),
            "dynamic_data": data.get("dynamic_analysis")
        }

    def get_api_base_url(self) -> Optional[str]:
        return self.base_url
