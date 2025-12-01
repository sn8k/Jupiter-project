"""Lightweight static server for the Jupiter web UI."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import ThreadingTCPServer
from typing import Callable

from jupiter import __version__
from jupiter.config.config import get_project_config_path

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WebUISettings:
    """Configuration used to start the GUI server."""

    root: Path
    host: str = "127.0.0.1"
    port: int = 8050
    device_key: str | None = None


class JupiterWebUI:
    """Serve the static Jupiter GUI bundled in the package."""

    def __init__(self, settings: WebUISettings) -> None:
        self.settings = settings
        self.web_root = Path(__file__).parent
        self._server: ThreadingTCPServer | None = None

    def _build_handler(self) -> Callable[..., SimpleHTTPRequestHandler]:
        """Return an HTTP handler exposing context metadata and static assets."""

        web_root = self.web_root
        api_base_url = os.environ.get("JUPITER_API_BASE", "http://127.0.0.1:8000")
        
        # Ensure root path is clean (no quotes)
        root_str = str(self.settings.root).strip('"\'')
        config_path = get_project_config_path(self.settings.root)
        
        project_name = self.settings.root.name
        if config_path.exists():
            try:
                # Simple parse to avoid full dependency if possible, or just use load_config logic
                # But here we want to be lightweight. Let's try to read it.
                import yaml
                with open(config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data and "project_name" in data:
                        project_name = data["project_name"]
            except Exception:
                pass

        context = {
            "root": root_str,
            "project_name": project_name,
            "api_base_url": api_base_url,
            "meeting": {"deviceKey": self.settings.device_key},
            "has_config_file": config_path.exists(),
            "jupiter_version": __version__,
        }

        class _Handler(SimpleHTTPRequestHandler):  # type: ignore[misc]
            def end_headers(self) -> None:
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                super().end_headers()

            def do_GET(self) -> None:  # noqa: N802 (SimpleHTTPRequestHandler interface)
                # Force 200 OK for core files to bypass browser cache issues
                if self.path in ["/", "/index.html", "/app.js"]:
                    fpath = "/index.html" if self.path == "/" else self.path
                    # Remove query params if any (though SimpleHTTPRequestHandler usually strips them before here, 
                    # but self.path might include them depending on implementation. 
                    # Actually self.path includes query string in standard http.server)
                    if "?" in fpath:
                        fpath = fpath.split("?")[0]
                        
                    rel_path = fpath.lstrip("/")
                    full_path = web_root / rel_path
                    
                    if full_path.exists():
                        try:
                            content = full_path.read_bytes()
                            self.send_response(200)
                            ctype = self.guess_type(str(full_path))
                            self.send_header("Content-Type", ctype)
                            self.send_header("Content-Length", str(len(content)))
                            self.end_headers()
                            self.wfile.write(content)
                            return
                        except Exception as e:
                            logger.error(f"Error serving {fpath}: {e}")

                if self.path == "/context.json":
                    payload = json.dumps(context).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return
                return super().do_GET()

        return partial(_Handler, directory=str(web_root))

    def start(self) -> None:
        """Start serving the GUI until interrupted."""

        handler = self._build_handler()
        self._server = ThreadingTCPServer((self.settings.host, self.settings.port), handler)
        logger.info(
            "Serving Jupiter GUI on http://%s:%s (root: %s)",
            self.settings.host,
            self.settings.port,
            self.settings.root,
        )

        try:
            self._server.serve_forever()
        except KeyboardInterrupt:
            logger.info("GUI server interrupted by user")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the GUI server if running."""

        if self._server is None:
            return

        logger.info("Stopping Jupiter GUI server")
        self._server.shutdown()
        self._server.server_close()
        self._server = None


def launch_web_ui(root: Path, host: str = "127.0.0.1", port: int = 8050, device_key: str | None = None) -> None:
    """Helper to run the GUI with minimal setup."""

    JupiterWebUI(WebUISettings(root=root, host=host, port=port, device_key=device_key)).start()
