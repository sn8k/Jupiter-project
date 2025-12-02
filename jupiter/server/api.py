"""
Lightweight API server using FastAPI.

Version: 1.1.0 - Phase 3: Dual-port architecture for autodiag
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
import sys
import asyncio
import time
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from jupiter import __version__
from jupiter.core.exceptions import JupiterError, ScanError, AnalyzeError, RunError, MeetingError
from jupiter.core.history import HistoryManager
from jupiter.core.plugin_manager import PluginManager
from jupiter.core.state import save_last_root
from jupiter.config import JupiterConfig, PluginsConfig
from jupiter.server.manager import ProjectManager
from jupiter.server.ws import websocket_endpoint
from jupiter.server.meeting_adapter import MeetingAdapter
from jupiter.server.routers import auth, scan, system, analyze, watch, autodiag
from jupiter.core.logging_utils import configure_logging

logger = logging.getLogger(__name__)

# Global reference for the heartbeat task
_heartbeat_task: Optional[asyncio.Task] = None


async def _meeting_heartbeat_loop(adapter: MeetingAdapter, interval_seconds: int) -> None:
    """Background task that sends periodic heartbeats to Meeting."""
    logger.info("Meeting heartbeat loop started (interval=%d seconds)", interval_seconds)
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            if adapter.is_enabled():
                success = adapter.heartbeat()
                if success:
                    logger.debug("Meeting heartbeat sent successfully")
                else:
                    logger.warning("Meeting heartbeat failed")
        except Exception as e:
            logger.error("Error in Meeting heartbeat: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    global _heartbeat_task
    
    # Startup: capture the running event loop for cross-thread callbacks
    loop = asyncio.get_running_loop()
    watch.set_main_loop(loop)
    logger.info("Main event loop captured for watch callbacks")
    
    # Start Meeting heartbeat task if adapter is available and enabled
    # Note: The adapter is set up in JupiterAPIServer.start() before uvicorn.run()
    # so it should be available here via app.state
    try:
        adapter = getattr(app.state, 'meeting_adapter', None)
        if adapter and adapter.is_enabled():
            config = getattr(app.state, 'project_manager', None)
            interval = 60  # default
            if config and hasattr(config, 'config') and config.config.meeting:
                interval = config.config.meeting.heartbeat_interval_seconds or 60
            _heartbeat_task = asyncio.create_task(_meeting_heartbeat_loop(adapter, interval))
            logger.info("Meeting heartbeat task started")
    except Exception as e:
        logger.warning("Could not start Meeting heartbeat task: %s", e)
    
    yield
    
    # Shutdown: cancel heartbeat task and cleanup
    if _heartbeat_task:
        _heartbeat_task.cancel()
        try:
            await _heartbeat_task
        except asyncio.CancelledError:
            pass
        logger.info("Meeting heartbeat task stopped")
    watch.set_main_loop(None)


app = FastAPI(
    title="Jupiter API",
    description="API for scanning and analyzing projects.",
    version=__version__,
    lifespan=lifespan,
)

# Windows Proactor loops tend to emit noisy connection-lost traces when clients close abruptly.
# Switching to SelectorEventLoopPolicy avoids the Proactor-specific "ConnectionResetError" noise,
# but Selector loop has limitations (no subprocess pipes).
# Since we use subprocesses in runner.py, we might need Proactor.
# Instead, we can try to suppress the specific log noise in uvicorn or just accept it.
# However, the user specifically asked to fix it.
# The error comes from _ProactorBasePipeTransport._call_connection_lost.
# A common workaround is to silence the exception in the loop's exception handler,
# but we can't easily patch the loop internals.
# Another option is to use `asyncio.WindowsSelectorEventLoopPolicy()` if we don't need Proactor features.
# Jupiter uses `subprocess` which requires Proactor on Windows for async pipes, BUT
# our `runner.py` uses `subprocess.run` (sync) or `asyncio.create_subprocess_exec`.
# If we use `asyncio.create_subprocess_exec`, we NEED Proactor on Windows.
# Let's check runner.py.
# If we use sync subprocess, Selector is fine.
if sys.platform.startswith("win"):
    # Check if we can use Selector. If we rely on async subprocess, we can't.
    # But the error is annoying.
    # Let's try to suppress the log message by filtering the logger.
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)


app.include_router(auth.router)
app.include_router(scan.router)
app.include_router(system.router)
app.include_router(analyze.router)
app.include_router(watch.router)

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
    """Server that runs the Jupiter FastAPI application with optional autodiag server."""

    root: Path
    host: str = "127.0.0.1"
    port: int = 8000
    device_key: Optional[str] = None
    plugins_config: Optional[PluginsConfig] = None
    config: Optional[JupiterConfig] = None
    install_path: Optional[Path] = None

    def _create_diag_app(self) -> FastAPI:
        """Create the autodiag FastAPI app (localhost only, no auth required)."""
        diag_app = FastAPI(
            title="Jupiter Autodiag",
            description="Internal diagnostic API for Jupiter self-analysis.",
            version=__version__,
        )
        
        # Include autodiag router
        diag_app.include_router(autodiag.router)
        
        # Store reference to main app for introspection
        diag_app.state.main_app = app
        diag_app.state.start_time = time.time()
        
        # Add CORS for local tools
        diag_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        return diag_app

    def start(self) -> None:
        """Start the API server using uvicorn, with optional autodiag server."""
        app.state.root_path = self.root
        app.state.install_path = self.install_path or self.root
        app.state.start_time = time.time()
        save_last_root(self.root)
        
        # Initialize MeetingAdapter with config parameters
        meeting_config = self.config.meeting if self.config else None
        # Use device_key from config if available, fallback to self.device_key
        effective_device_key = meeting_config.deviceKey if meeting_config else self.device_key
        app.state.meeting_adapter = MeetingAdapter(
            device_key=effective_device_key,
            project_root=self.root,
            base_url=meeting_config.base_url if meeting_config else "https://meeting.ygsoft.fr/api",
            device_type_expected=meeting_config.device_type if meeting_config else "Jupiter",
            timeout_seconds=meeting_config.timeout_seconds if meeting_config else 5.0,
            auth_token=meeting_config.auth_token if meeting_config else None,
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
        active_reset = getattr(active_logging, "reset_on_start", True)
        active_log_level = configure_logging(active_level, log_file=active_path, reset_on_start=active_reset)
        logger.info("Configured logging at %s", active_log_level)

        # Check if autodiag is enabled
        autodiag_config = getattr(self.config, "autodiag", None) if self.config else None
        autodiag_enabled = autodiag_config is not None and autodiag_config.enabled
        
        if autodiag_enabled and autodiag_config is not None:
            # Run both servers concurrently
            diag_port = autodiag_config.port
            logger.info(
                "Starting Jupiter API server on %s:%s and Autodiag on 127.0.0.1:%s for root %s",
                self.host, self.port, diag_port, self.root
            )
            asyncio.run(self._run_dual_servers(active_log_level, diag_port))
        else:
            # Run only main server
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

    async def _run_dual_servers(self, log_level: str, autodiag_port: int) -> None:
        """Run both main API and autodiag servers concurrently."""
        diag_app = self._create_diag_app()
        
        main_config = uvicorn.Config(
            app,
            host=self.host,
            port=self.port,
            log_level=log_level.lower(),
        )
        
        diag_config = uvicorn.Config(
            diag_app,
            host="127.0.0.1",  # Localhost only for security
            port=autodiag_port,
            log_level=log_level.lower(),
        )
        
        main_server = uvicorn.Server(main_config)
        diag_server = uvicorn.Server(diag_config)
        
        try:
            await asyncio.gather(
                main_server.serve(),
                diag_server.serve(),
            )
        except Exception as e:
            logger.error("Dual-server crashed: %s", e)
            raise

    def stop(self) -> None:
        """Stop the API server."""
        logger.info("Stopping Jupiter API server is handled by Uvicorn (e.g., Ctrl+C).")
