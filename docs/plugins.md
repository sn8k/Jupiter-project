# Jupiter Plugin System

Jupiter is designed to be extensible through a plugin system. Plugins can hook into various stages of the Jupiter lifecycle (scan, analyze, run) to add custom logic, metrics, or integrations.

## Architecture

Plugins are Python classes that adhere to the `Plugin` protocol. They are discovered automatically from the `jupiter.plugins` package.

### Configuration

Plugins are configured in the `jupiter.yaml` file in your project root.

```yaml
plugins:
  enabled:
    - "example_plugin"
    - "security_scanner"
    - "notifications_webhook"
  disabled:
    - "noisy_plugin"

notifications_webhook:
  url: "https://my-service/hooks/jupiter"
  events: ["scan_complete", "unused_function", "meeting_expired"]
```

If `enabled` is provided, only plugins in that list are loaded. If `enabled` is empty, all discovered plugins are loaded unless they are in `disabled`.

## Developing a Plugin

To create a new plugin, add a Python file to the `jupiter/plugins/` directory (or install it as a package that registers itself, though currently only local discovery is fully implemented).

### Structure

A plugin is a class with the following attributes and methods:

```python
from typing import Any, Dict

class MyPlugin:
  name = "my_plugin"
  version = "1.0.1"
    description = "Does amazing things."
  trust_level = "experimental"  # or "trusted"

    def on_scan(self, report: Dict[str, Any]) -> None:
        """Called after a scan is complete.
        
        Args:
            report: The dictionary representation of the ScanReport.
                    You can modify this dictionary in-place.
        """
        print("Scan complete!")
        report["my_plugin_data"] = {"status": "checked"}

    def on_analyze(self, summary: Dict[str, Any]) -> None:
        """Called after an analysis is complete.
        
        Args:
            summary: The dictionary representation of the AnalysisSummary.
        """
        print("Analysis complete!")
```

### Available Hooks

*   **`on_scan(report: Dict[str, Any])`**: Triggered after `jupiter scan`. The `report` dict contains the file list and metadata.
*   **`on_analyze(summary: Dict[str, Any])`**: Triggered after `jupiter analyze`. The `summary` dict contains aggregated metrics, hotspots, and quality scores.
*   **`on_run(result: CommandResult)`** (Planned): Triggered after a command execution.

## Managing Plugins via UI

The Jupiter Web UI provides a view to see active plugins. While you cannot currently install plugins directly from the UI, you can see which ones are active and their version.

## AI Helper Plugin

The `ai_helper` plugin provides an interface for AI-assisted analysis. It is an optional component that can generate refactoring suggestions, documentation improvements, and security alerts.

### Configuration

```yaml
plugins:
  enabled:
    - ai_helper
  ai_helper:
    enabled: true
    provider: "mock" # or "openai", "local"
    api_key: "sk-..." # if required
```

### Interface

The AI plugin hooks into `on_analyze` and populates the `refactoring` list in the analysis summary.

```python
@dataclass
class AISuggestion:
    path: str
    type: str  # refactoring, doc, security, optimization
    details: str
    severity: str  # info, warning, critical
    code_snippet: Optional[str] = None
```

