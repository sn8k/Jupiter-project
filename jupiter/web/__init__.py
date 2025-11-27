"""Web UI assets and utilities for Jupiter.

This module exposes helpers to serve the static GUI while other
components (scanner, analyzer, API) evolve.
"""

from .app import JupiterWebUI, WebUISettings, launch_web_ui

__all__ = ["JupiterWebUI", "WebUISettings", "launch_web_ui"]
