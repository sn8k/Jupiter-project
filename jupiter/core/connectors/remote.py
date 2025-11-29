import httpx
from typing import Any, Dict, Optional
from jupiter.core.connectors.base import BaseConnector

class RemoteConnector(BaseConnector):
    """Connector for a remote Jupiter API."""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    async def scan(self, options: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/scan",
                json=options,
                headers=self.headers,
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()

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

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/analyze",
                params=params,
                headers=self.headers,
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()

    async def run_command(self, command: list[str], with_dynamic: bool = False) -> Dict[str, Any]:
        payload = {
            "command": command,
            "with_dynamic": with_dynamic
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/run",
                json=payload,
                headers=self.headers,
                timeout=None # Run commands can be long
            )
            response.raise_for_status()
            
            # The API returns RunResponse which has stdout, stderr, returncode, dynamic_analysis
            # BaseConnector expects Dict[str, Any]
            data = response.json()
            # Map API response to what LocalConnector returns (which is basically the same structure)
            # LocalConnector returns result.dict() which has stdout, stderr, returncode, dynamic_data
            # API returns dynamic_analysis instead of dynamic_data
            
            return {
                "stdout": data.get("stdout", ""),
                "stderr": data.get("stderr", ""),
                "returncode": data.get("returncode", 0),
                "dynamic_data": data.get("dynamic_analysis")
            }

    def get_api_base_url(self) -> Optional[str]:
        return self.base_url
