"""Utilities for configuring Jupiter logging consistently."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Optional

# Accepted aliases for UI/API inputs
LEVEL_ALIASES = {
    "CRITIC": "CRITICAL",
    "CRITICAL": "CRITICAL",
    "ERROR": "ERROR",
    "WARN": "WARNING",
    "WARNING": "WARNING",
    "INFO": "INFO",
    "DEBUG": "DEBUG",
}


def normalize_log_level(level_name: str | None) -> str:
    """Return a normalized logging level name (defaults to INFO)."""
    if not level_name:
        return "INFO"
    return LEVEL_ALIASES.get(level_name.strip().upper(), "INFO")


def configure_logging(
    level_name: str | None,
    extra_loggers: Iterable[str] | None = None,
    log_file: Optional[str | Path] = None,
) -> str:
    """Configure root and well-known loggers to the requested level.

    Optionally attach a file handler when ``log_file`` is provided.
    Returns the normalized level name effectively applied.
    """
    normalized = normalize_log_level(level_name)
    numeric_level = getattr(logging, normalized, logging.INFO)

    # Ensure handlers exist to honor updated levels in subsequent calls
    logging.basicConfig(level=numeric_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    for handler in root_logger.handlers:
        handler.setLevel(numeric_level)

    # Keep server logs aligned (uvicorn + FastAPI)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).setLevel(numeric_level)

    for name in extra_loggers or []:
        logging.getLogger(name).setLevel(numeric_level)

    if log_file:
        try:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            root_logger = logging.getLogger()
            already_configured = any(
                isinstance(handler, logging.FileHandler) and getattr(handler, "baseFilename", None) == str(log_path)
                for handler in root_logger.handlers
            )
            if not already_configured:
                file_handler = logging.FileHandler(log_path, encoding="utf-8")
                file_handler.setLevel(numeric_level)
                file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
                root_logger.addHandler(file_handler)
        except Exception as exc:  # pragma: no cover - defensive logging setup
            logging.getLogger(__name__).warning("Failed to attach file handler %s: %s", log_file, exc)

    return normalized
