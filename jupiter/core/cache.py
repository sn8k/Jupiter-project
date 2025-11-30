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
                data = json.load(f)
            return self._normalize_report(data)
        except Exception as e:
            logger.warning("Failed to load last scan cache: %s", e)
            return None

    def save_last_scan(self, report_data: Dict[str, Any]):
        """Save the scan report to cache."""
        self._ensure_cache_dir()
        normalized = self._normalize_report(report_data)
        try:
            with open(self.last_scan_file, "w", encoding="utf-8") as f:
                json.dump(normalized, f, indent=2)
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

    def merge_dynamic_data(self, dynamic_data: Dict[str, Any]) -> None:
        """Merge dynamic analysis data into the cached last scan report."""
        last_scan = self.load_last_scan()
        if not last_scan:
            return

        dynamic_section: Dict[str, Any] = last_scan.get("dynamic") or {"calls": {}, "times": {}, "call_graph": {}}
        if not isinstance(dynamic_section, dict):
            dynamic_section = {"calls": {}, "times": {}, "call_graph": {}}

        calls = dynamic_section.get("calls") or {}
        times = dynamic_section.get("times") or {}
        call_graph = dynamic_section.get("call_graph") or {}

        if not isinstance(calls, dict):
            calls = {}
        if not isinstance(times, dict):
            times = {}
        if not isinstance(call_graph, dict):
            call_graph = {}

        for func, count in dynamic_data.get("calls", {}).items():
            calls[func] = calls.get(func, 0) + count

        for func, time_val in dynamic_data.get("times", {}).items():
            times[func] = times.get(func, 0.0) + time_val

        for caller, callees in dynamic_data.get("call_graph", {}).items():
            caller_entry = call_graph.setdefault(caller, {})
            if not isinstance(caller_entry, dict):
                caller_entry = {}
                call_graph[caller] = caller_entry
            for callee, count in callees.items():
                caller_entry[callee] = caller_entry.get(callee, 0) + count

        last_scan["dynamic"] = {"calls": calls, "times": times, "call_graph": call_graph}
        self.save_last_scan(last_scan)

    def _normalize_report(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure cached reports match the API schema expectations."""
        normalized = dict(report_data)

        plugins = normalized.get("plugins")
        if isinstance(plugins, dict):
            normalized["plugins"] = [value for value in plugins.values()]
        elif plugins is None:
            normalized.pop("plugins", None)
        elif not isinstance(plugins, list):
            normalized["plugins"] = []

        files = normalized.get("files")
        if isinstance(files, dict):
            normalized["files"] = [value for value in files.values()]

        return normalized
