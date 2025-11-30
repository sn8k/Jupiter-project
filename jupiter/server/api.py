"""Lightweight API server using FastAPI."""

from __future__ import annotations

import logging
from dataclasses import dataclass
import sys
import asyncio
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from jupiter.core.exceptions import JupiterError, ScanError, AnalyzeError, RunError, MeetingError
from jupiter.core.history import HistoryManager
from jupiter.core.plugin_manager import PluginManager
from jupiter.core.state import save_last_root
from jupiter.config import JupiterConfig, PluginsConfig
from jupiter.server.manager import ProjectManager
from jupiter.server.ws import websocket_endpoint
from jupiter.server.meeting_adapter import MeetingAdapter
from jupiter.server.routers import auth, scan, system, analyze
from jupiter.core.logging_utils import configure_logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Jupiter API",
    description="API for scanning and analyzing projects.",
    version="1.0.1",
)

# Windows Proactor loops tend to emit noisy connection-lost traces when clients close abruptly.
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app.include_router(auth.router)
app.include_router(scan.router)
app.include_router(system.router)
app.include_router(analyze.router)

@app.exception_handler(JupiterError)
async def jupiter_exception_handler(request: Request, exc: JupiterError):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": exc.code, "message": str(exc), "details": exc.details}},
    )

@app.exception_handler(ScanError)
async def scan_exception_handler(request: Request, exc: ScanError):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": exc.code, "message": str(exc), "details": exc.details}},
    )

@app.exception_handler(AnalyzeError)
async def analyze_exception_handler(request: Request, exc: AnalyzeError):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": exc.code, "message": str(exc), "details": exc.details}},
    )

@app.exception_handler(RunError)
async def run_exception_handler(request: Request, exc: RunError):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": exc.code, "message": str(exc), "details": exc.details}},
    )

@app.exception_handler(MeetingError)
async def meeting_exception_handler(request: Request, exc: MeetingError):
    return JSONResponse(
        status_code=503,
        content={"error": {"code": exc.code, "message": str(exc), "details": exc.details}},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Using app.state to hold the root path, which will be set on server startup.
app.state.root_path = Path.cwd()

@app.websocket("/ws")
async def ws_endpoint_route(websocket: WebSocket, token: Optional[str] = None):
    # Check security token
    try:
        config = app.state.project_manager.config
        if config.security.token:
            if token != config.security.token:
                await websocket.close(code=1008, reason="Invalid authentication token")
                return
    except AttributeError:
        pass

    # Check license for watch/realtime features
    try:
        app.state.meeting_adapter.validate_feature_access("watch")
    except MeetingError as e:
        await websocket.close(code=1008, reason=str(e))
        return

    await websocket_endpoint(websocket)


@dataclass
class JupiterAPIServer:
    """Server that runs the Jupiter FastAPI application."""

    root: Path
    host: str = "127.0.0.1"
    port: int = 8000
    device_key: Optional[str] = None
    plugins_config: Optional[PluginsConfig] = None
    config: Optional[JupiterConfig] = None
    install_path: Optional[Path] = None

    def start(self) -> None:
        """Start the API server using uvicorn."""
        app.state.root_path = self.root
        app.state.install_path = self.install_path or self.root
        save_last_root(self.root)
        app.state.meeting_adapter = MeetingAdapter(
            device_key=self.device_key,
            project_root=self.root
        )
        app.state.history_manager = HistoryManager(self.root)
        
        # Initialize ProjectManager
        if self.config:
            app.state.project_manager = ProjectManager(self.config)
        else:
            # Fallback if config not passed (should not happen in normal flow)
            # We load it here or create a default one
            logger.warning("JupiterConfig not passed to API Server, loading from root")
            from jupiter.config import load_config
            app.state.project_manager = ProjectManager(load_config(self.root))

        # Initialize plugins
        plugin_manager = PluginManager(config=self.plugins_config)
        plugin_manager.discover_and_load()
        app.state.plugin_manager = plugin_manager
        logger.info("Loaded %d plugins", len(plugin_manager.plugins))

        active_config = getattr(app.state.project_manager, "config", None)
        active_logging = getattr(active_config, "logging", None)
        active_level = getattr(active_logging, "level", None)
        active_path = getattr(active_logging, "path", None)
        active_log_level = configure_logging(active_level, log_file=active_path)
        logger.info("Configured logging at %s", active_log_level)

        logger.info("Starting Jupiter API server on %s:%s for root %s", self.host, self.port, self.root)
        try:
            uvicorn.run(
                app,
                host=self.host,
                port=self.port,
                log_level=active_log_level.lower(),
            )
        except Exception as e:
            logger.error("Server crashed: %s", e)
            raise

    def stop(self) -> None:
        """Stop the API server."""
        logger.info("Stopping Jupiter API server is handled by Uvicorn (e.g., Ctrl+C).")
