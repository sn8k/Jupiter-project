"""Example plugin for Jupiter."""

import logging
from typing import Any, Dict

PLUGIN_VERSION = "0.1.1"

logger = logging.getLogger(__name__)

class ExamplePlugin:
    """An example plugin that adds a custom field to the report."""

    name = "example_plugin"
    version = PLUGIN_VERSION
    description = "A simple example plugin."

    def on_scan(self, report: Dict[str, Any]) -> None:
        """Add a custom message to the scan report."""
        logger.info("ExamplePlugin running on_scan")
        if "plugins_data" not in report:
            report["plugins_data"] = {}
        report["plugins_data"][self.name] = {"message": "Hello from Example Plugin (Scan)!"}
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("ExamplePlugin report keys after scan=%s", list(report.keys()))

    def on_analyze(self, summary: Dict[str, Any]) -> None:
        """Add a custom message to the analysis summary."""
        logger.info("ExamplePlugin running on_analyze")
        if "plugins_data" not in summary:
            summary["plugins_data"] = {}
        summary["plugins_data"][self.name] = {"message": "Hello from Example Plugin (Analyze)!"}
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("ExamplePlugin summary keys after analyze=%s", list(summary.keys()))
