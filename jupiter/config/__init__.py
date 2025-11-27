"""Configuration defaults for Jupiter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


@dataclass(slots=True)
class JupiterConfig:
    """In-memory configuration for Jupiter services."""

    root: Path
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    meeting_device_key: str | None = None
