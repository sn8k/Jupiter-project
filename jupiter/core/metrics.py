from typing import Dict, Any, List
from jupiter import __version__
from jupiter.core.history import HistoryManager
from jupiter.core.plugin_manager import PluginManager

class MetricsCollector:
    """Collects and aggregates metrics for the Jupiter instance."""

    def __init__(self, history_manager: HistoryManager, plugin_manager: PluginManager):
        self.history_manager = history_manager
        self.plugin_manager = plugin_manager

    def collect(self) -> Dict[str, Any]:
        """Collect all metrics."""
        snapshots = self.history_manager.list_snapshots()
        
        total_scans = len(snapshots)
        avg_files = 0
        avg_size = 0
        avg_functions = 0
        
        if total_scans > 0:
            avg_files = sum(s.file_count for s in snapshots) / total_scans
            avg_size = sum(s.total_size_bytes for s in snapshots) / total_scans
            avg_functions = sum(s.function_count for s in snapshots) / total_scans

        plugins_info = self.plugin_manager.get_plugins_info()
        active_plugins = [p["name"] for p in plugins_info if p["enabled"]]

        return {
            "scans": {
                "total": total_scans,
                "avg_files": round(avg_files, 2),
                "avg_size_bytes": round(avg_size, 2),
                "avg_functions": round(avg_functions, 2),
            },
            "plugins": {
                "total": len(plugins_info),
                "active_count": len(active_plugins),
                "active_list": active_plugins,
            },
            "system": {
                "version": __version__,
            }
        }
