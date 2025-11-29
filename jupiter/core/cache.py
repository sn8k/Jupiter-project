"""Cache management for Jupiter."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class CacheManager:
    """Manages the Jupiter cache directory and files."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.cache_dir = project_root / ".jupiter" / "cache"
        self.last_scan_file = self.cache_dir / "last_scan.json"

    def _ensure_cache_dir(self):
        """Ensure the cache directory exists."""
        if not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def load_last_scan(self) -> Optional[Dict[str, Any]]:
        """Load the last scan report from cache."""
        if not self.last_scan_file.exists():
            return None
        try:
            with open(self.last_scan_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to load last scan cache: %s", e)
            return None

    def save_last_scan(self, report_data: Dict[str, Any]):
        """Save the scan report to cache."""
        self._ensure_cache_dir()
        try:
            with open(self.last_scan_file, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save last scan cache: %s", e)

    def load_analysis_cache(self) -> Dict[str, Any]:
        """Load the analysis cache."""
        analysis_cache_file = self.cache_dir / "analysis_cache.json"
        if not analysis_cache_file.exists():
            return {}
        try:
            with open(analysis_cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to load analysis cache: %s", e)
            return {}

    def save_analysis_cache(self, cache_data: Dict[str, Any]):
        """Save the analysis cache."""
        self._ensure_cache_dir()
        analysis_cache_file = self.cache_dir / "analysis_cache.json"
        try:
            with open(analysis_cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save analysis cache: %s", e)

    def clear_cache(self):
        """Clear all cache files."""
        if self.cache_dir.exists():
            import shutil
            shutil.rmtree(self.cache_dir)
            self._ensure_cache_dir()
