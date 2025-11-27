"""Lightweight API server placeholder."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class JupiterAPIServer:
    """Minimal server placeholder to orchestrate Jupiter services."""

    root: Path
    host: str = "127.0.0.1"
    port: int = 8000

    def start(self) -> None:
        """Start the API server.

        This starter implementation only logs the intent. A later iteration will
        bind a real ASGI application (e.g., FastAPI) to expose scan and analysis
        endpoints.
        """

        logger.info("Starting Jupiter API server on %s:%s for root %s", self.host, self.port, self.root)
        logger.debug("No HTTP server implemented yet; this is a stub for future work.")

    def stop(self) -> None:
        """Stop the API server placeholder."""

        logger.info("Stopping Jupiter API server")
