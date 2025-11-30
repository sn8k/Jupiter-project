"""Stub plugin for code quality metrics."""

from __future__ import annotations

import logging
from typing import Any
from jupiter import __version__

logger = logging.getLogger(__name__)

class CodeQualityPlugin:
    """A simple plugin that adds dummy quality metrics."""

    name = "code_quality_stub"
    version = __version__
    description = "Adds basic code quality metrics (stub)."

    def on_scan(self, report: dict[str, Any]) -> None:
        """Add quality metrics to the scan report."""
        logger.info("CodeQualityPlugin: processing scan report.")
        # We add a dedicated section for this plugin's data
        report["code_quality_stub"] = {
            "status": "ok",
            "metrics": {
                "complexity": "low",
                "maintainability": "high"
            }
        }

    def on_analyze(self, summary: dict[str, Any]) -> None:
        """Add quality metrics to the analysis summary."""
        logger.info("CodeQualityPlugin: processing analysis summary.")
        summary["code_quality_stub"] = {
            "score": 95,
            "issues": []
        }
