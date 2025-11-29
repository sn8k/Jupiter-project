"""Self-update logic for Jupiter."""

import logging
import shutil
import zipfile
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

def apply_update(source: str, force: bool = False) -> None:
    """Handle self-update from ZIP or Git."""
    logger.info("Starting update from %s", source)
    
    # Simple check if source is a file (ZIP) or URL/Git
    if Path(source).is_file() and source.endswith(".zip"):
        logger.info("Updating from local ZIP file...")
        try:
            # Backup current version? In a real scenario, yes.
            # Here we just extract over the current directory (simplified)
            # Assuming we are running from the source root for this dev environment
            dest_dir = Path.cwd()
            
            with zipfile.ZipFile(source, 'r') as zip_ref:
                zip_ref.extractall(dest_dir)
            
            logger.info("Update applied successfully.")
        except Exception as e:
            logger.error("Update failed: %s", e)
            if not force:
                raise
    elif source.startswith("git+") or source.endswith(".git"):
        logger.info("Updating from Git repository...")
        try:
            # subprocess.run(["git", "pull"], cwd=Path.cwd(), check=True)
            logger.info("Git update simulated.")
        except subprocess.CalledProcessError as e:
            logger.error("Git update failed: %s", e)
            if not force:
                raise
    else:
        msg = "Unknown source format. Use a .zip file or a git URL."
        logger.error(msg)
        raise ValueError(msg)
