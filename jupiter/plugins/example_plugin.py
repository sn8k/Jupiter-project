"""Example plugin for Jupiter."""

from typing import Any, Dict

class ExamplePlugin:
    """An example plugin that adds a custom field to the report."""

    name = "example_plugin"
    version = "0.1.0"
    description = "A simple example plugin."

    def on_scan(self, report: Dict[str, Any]) -> None:
        """Add a custom message to the scan report."""
        if "plugins_data" not in report:
            report["plugins_data"] = {}
        report["plugins_data"][self.name] = {"message": "Hello from Example Plugin (Scan)!"}

    def on_analyze(self, summary: Dict[str, Any]) -> None:
        """Add a custom message to the analysis summary."""
        if "plugins_data" not in summary:
            summary["plugins_data"] = {}
        summary["plugins_data"][self.name] = {"message": "Hello from Example Plugin (Analyze)!"}
