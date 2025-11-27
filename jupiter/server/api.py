"""Lightweight API server using FastAPI."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from jupiter.core import ProjectAnalyzer, ProjectScanner, ScanReport
from jupiter.core.runner import CommandResult, run_command
from .ws import websocket_endpoint

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Jupiter API",
    description="API for scanning and analyzing projects.",
    version="1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Using app.state to hold the root path, which will be set on server startup.
# This makes it available to endpoint functions.
# A more complex app might use dependency injection.
app.state.root_path = Path.cwd() 

class ScanOptions(BaseModel):
    show_hidden: bool = Field(default=False, description="Include hidden files in the scan.")
    ignore_globs: Optional[List[str]] = Field(default=None, description="Glob patterns to ignore.")

@app.post("/scan")
async def post_scan(options: ScanOptions) -> dict[str, object]:
    """Run a filesystem scan and return a JSON report."""
    root = app.state.root_path
    logger.info("Scanning project at %s with options: %s", root, options)
    scanner = ProjectScanner(
        root=root,
        ignore_hidden=not options.show_hidden,
        ignore_globs=options.ignore_globs,
    )
    report = ScanReport.from_files(root=root, files=scanner.iter_files())
    return report.to_dict()

@app.get("/analyze")
async def get_analyze(top: int = 5, show_hidden: bool = False, ignore_globs: Optional[List[str]] = None) -> dict[str, object]:
    """Scan and analyze a project, returning a summary."""
    root = app.state.root_path
    logger.info("Analyzing project at %s", root)
    scanner = ProjectScanner(root=root, ignore_hidden=not show_hidden, ignore_globs=ignore_globs)
    analyzer = ProjectAnalyzer(root=root)
    summary = analyzer.summarize(scanner.iter_files(), top_n=top)
    return summary.to_dict()


class RunRequest(BaseModel):
    command: List[str] = Field(..., description="The command to execute as a list of strings.")


@app.post("/run", response_model=CommandResult)
async def post_run(request: RunRequest) -> CommandResult:
    """Execute a command in the project root and return its output."""
    root = app.state.root_path
    result = run_command(request.command, cwd=root)
    return result


@app.get("/health")
async def get_health() -> dict[str, str]:
    """Return the health status of the server."""
    return {"status": "ok"}


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket_endpoint(websocket)


@dataclass
class JupiterAPIServer:
    """Server that runs the Jupiter FastAPI application."""

    root: Path
    host: str = "127.0.0.1"
    port: int = 8000

    def start(self) -> None:
        """Start the API server using uvicorn."""
        logger.info("Starting Jupiter API server on %s:%s for root %s", self.host, self.port, self.root)
        app.state.root_path = self.root

        uvicorn.run(
            app,
            host=self.host,
            port=self.port,
            log_level="info",
        )

    def stop(self) -> None:
        """Stop the API server."""
        logger.info("Stopping Jupiter API server is handled by Uvicorn (e.g., Ctrl+C).")