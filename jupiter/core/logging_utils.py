"""Utilities for configuring Jupiter logging consistently.

Version: 1.1.0
"""

from __future__ import annotations

import logging
from datetime import datetime
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

# Separator added when log is not reset
LOG_RESTART_SEPARATOR = """

================================================================================
=== JUPITER RESTART - {timestamp} ===
================================================================================

"""


def normalize_log_level(level_name: str | None) -> str:
    """Return a normalized logging level name (defaults to INFO)."""
    if not level_name:
        return "INFO"
    return LEVEL_ALIASES.get(level_name.strip().upper(), "INFO")


def prepare_log_file(log_file: str | Path, reset_on_start: bool = True) -> None:
    """Prepare log file before configuring logging.
    
    If reset_on_start is True, the log file is deleted.
    If reset_on_start is False, a separator with timestamp is appended.
    
    Args:
        log_file: Path to the log file.
        reset_on_start: Whether to clear the log file or append separator.
    """
    if not log_file:
        return
    
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    if reset_on_start:
        # Delete existing log file
        if log_path.exists():
            try:
                log_path.unlink()
            except Exception:
                pass  # Ignore errors, file handler will overwrite anyway
    else:
        # Append separator if file exists
        if log_path.exists():
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                separator = LOG_RESTART_SEPARATOR.format(timestamp=timestamp)
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(separator)
            except Exception:
                pass  # Ignore errors, logging will continue anyway


def configure_logging(
    level_name: str | None,
    extra_loggers: Iterable[str] | None = None,
    log_file: Optional[str | Path] = None,
    reset_on_start: bool = True,
) -> str:
    """Configure root and well-known loggers to the requested level.

    Optionally attach a file handler when ``log_file`` is provided.
    
    Args:
        level_name: Log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        extra_loggers: Additional logger names to configure.
        log_file: Path to log file (optional).
        reset_on_start: If True, clear log file. If False, add restart separator.
    
    Returns:
        The normalized level name effectively applied.
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
                isinstance(handler, logging.FileHandler) and getattr(handler, "baseFilename", None) == str(log_path.resolve())
                for handler in root_logger.handlers
            )
            if not already_configured:
                # Prepare log file (reset or add separator)
                prepare_log_file(log_path, reset_on_start)
                
                file_handler = logging.FileHandler(log_path, encoding="utf-8")
                file_handler.setLevel(numeric_level)
                file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
                root_logger.addHandler(file_handler)
        except Exception as exc:  # pragma: no cover - defensive logging setup
            logging.getLogger(__name__).warning("Failed to attach file handler %s: %s", log_file, exc)

    return normalized

    return normalized
