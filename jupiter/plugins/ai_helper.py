"""AI Helper plugin (placeholder)."""

from __future__ import annotations

from typing import Any

class AIHelperPlugin:
    """Placeholder for AI-based features."""

    name = "ai_helper"
    version = "0.0.1"
    description = "AI-assisted analysis (not implemented)."

    def on_scan(self, report: dict[str, Any]) -> None:
        pass

    def on_analyze(self, summary: dict[str, Any]) -> None:
        pass
