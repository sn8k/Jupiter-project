"""Plugin system for Jupiter."""

from __future__ import annotations

from typing import Protocol, Any, runtime_checkable

@runtime_checkable
class Plugin(Protocol):
    """Base interface for Jupiter plugins."""

    name: str
    version: str
    description: str

    def on_scan(self, report: dict[str, Any]) -> None:
        """Hook called after a scan is completed."""
        ...

    def on_analyze(self, summary: dict[str, Any]) -> None:
        """Hook called after an analysis is completed."""
        ...
