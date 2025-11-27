"""Command execution utilities."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Result of an executed command."""

    stdout: str
    stderr: str
    returncode: int


def run_command(command: List[str], cwd: Path) -> CommandResult:
    """Executes a command and captures its output."""
    logger.info("Running command: %s in %s", " ".join(command), cwd)
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=cwd,
            check=False,  # Do not raise exception for non-zero exit codes
        )
        return CommandResult(
            stdout=process.stdout,
            stderr=process.stderr,
            returncode=process.returncode,
        )
    except Exception as e:
        logger.error("Failed to run command '%s': %s", command, e)
        return CommandResult(stdout="", stderr=str(e), returncode=-1)
