"""Lightweight static server for the Jupiter web UI."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import ThreadingTCPServer
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WebUISettings:
    """Configuration used to start the GUI server."""

    root: Path
    host: str = "127.0.0.1"
    port: int = 8050


class JupiterWebUI:
    """Serve the static Jupiter GUI bundled in the package."""

    def __init__(self, settings: WebUISettings) -> None:
        self.settings = settings
        self.web_root = Path(__file__).parent
        self._server: ThreadingTCPServer | None = None

    def _build_handler(self) -> Callable[..., SimpleHTTPRequestHandler]:
        """Return an HTTP handler exposing context metadata and static assets."""

        web_root = self.web_root
        context = {"root": str(self.settings.root)}

        class _Handler(SimpleHTTPRequestHandler):  # type: ignore[misc]
            def do_GET(self) -> None:  # noqa: N802 (SimpleHTTPRequestHandler interface)
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


def launch_web_ui(root: Path, host: str = "127.0.0.1", port: int = 8050) -> None:
    """Helper to run the GUI with minimal setup."""

    JupiterWebUI(WebUISettings(root=root, host=host, port=port)).start()
