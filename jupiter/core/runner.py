"""Command execution utilities."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
import tempfile
import json
import sys
import os

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CommandResult(BaseModel):
    """Result of an executed command."""

    stdout: str
    stderr: str
    returncode: int
    dynamic_data: Optional[Dict[str, Any]] = None


def run_command(command: List[str], cwd: Path, with_dynamic: bool = False) -> CommandResult:
    """Executes a command and captures its output."""
    logger.info("Running command: %s in %s (dynamic=%s)", " ".join(command), cwd, with_dynamic)
    
    dynamic_data = None
    temp_file = None
    
    final_command = command
    
    if with_dynamic:
        # Only support python commands for now
        if len(command) > 0 and (command[0].endswith("python") or command[0].endswith("python.exe") or command[0] == "python3"):
             # Create temp file for output
             fd, temp_path = tempfile.mkstemp(suffix=".json")
             os.close(fd)
             temp_file = temp_path
             
             # Construct wrapped command: python -m jupiter.core.tracer <temp_file> <cwd> <script> <args>
             # command[0] is python executable
             # command[1] should be the script
             if len(command) > 1:
                 script = command[1]
                 args = command[2:]
                 
                 # We need to run the tracer module using the SAME python interpreter
                 final_command = [
                     command[0],
                     "-m",
                     "jupiter.core.tracer",
                     temp_file,
                     str(cwd),
                     script
                 ] + args
        else:
            logger.warning("Dynamic analysis requested but command does not look like a Python script execution. Ignoring.")

    try:
        process = subprocess.run(
            final_command,
            capture_output=True,
            text=True,
            cwd=cwd,
            check=False,  # Do not raise exception for non-zero exit codes
        )
        
        if temp_file and os.path.exists(temp_file):
            try:
                with open(temp_file, "r") as f:
                    dynamic_data = json.load(f)
            except Exception as e:
                logger.error("Failed to read dynamic analysis data: %s", e)
            finally:
                os.remove(temp_file)

        return CommandResult(
            stdout=process.stdout,
            stderr=process.stderr,
            returncode=process.returncode,
            dynamic_data=dynamic_data
        )
    except Exception as e:
        logger.error("Failed to run command '%s': %s", final_command, e)
        return CommandResult(stdout="", stderr=str(e), returncode=-1)
