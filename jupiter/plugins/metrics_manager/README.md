# Metrics Manager Plugin

## Overview

The Metrics Manager plugin provides centralized observation, visualization, and management of all Jupiter metrics. It serves as a companion to the core `metrics.py` module, offering a user-friendly interface for monitoring system health and plugin performance.

## Features

- **Real-time System Metrics**: Monitor uptime, metrics collected, and counter tracking
- **Plugin Metrics Dashboard**: View metrics from all installed plugins
- **Counter & Gauge Tables**: Detailed breakdown of all tracked metrics
- **Metric History Charts**: Visualize metric trends over time
- **Alert System**: Configurable thresholds for warning and critical alerts
- **Export Capabilities**: Export metrics in JSON or Prometheus format
- **Live Logs**: Real-time log streaming with filtering

## Installation

The plugin is included by default with Jupiter. No additional installation required.

## Configuration

Configuration is stored in `config.yaml` within the plugin directory. Key settings:

```yaml
enabled: true
refresh_interval: 5000  # UI refresh rate in ms
history_size: 100       # Data points per metric
export_format: json     # json or prometheus
chart_type: line        # line, bar, or area

alert_thresholds:
  error_rate_warn: 0.05
  error_rate_critical: 0.15
  response_time_warn: 1000
  response_time_critical: 5000
```

## API Endpoints

All endpoints are prefixed with `/api/v1/plugins/metrics_manager/`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Plugin info |
| `/health` | GET | Health status |
| `/metrics` | GET | Plugin's own metrics |
| `/all` | GET | All collected metrics |
| `/system` | GET | System metrics only |
| `/plugins` | GET | Plugin metrics only |
| `/counters` | GET | All counters |
| `/history/{name}` | GET | Metric history |
| `/export` | GET | Export metrics |
| `/record` | POST | Record custom metric |
| `/reset` | POST | Reset all metrics |
| `/alerts` | GET | Active alerts |
| `/alerts` | DELETE | Clear alerts |
| `/stream` | GET | SSE metrics stream |
| `/logs` | GET | Download logs |
| `/logs/stream` | GET | SSE log stream |

## Usage

### WebUI

Navigate to the Metrics Manager panel from the sidebar to access:
- System metrics overview
- Active alerts panel
- Counter and gauge tables
- Metric history charts
- Plugin metrics breakdown
- Live log viewer

### Recording Custom Metrics

```python
from jupiter.core.bridge.metrics import get_metrics_collector

collector = get_metrics_collector()
collector.record("my_metric", 42.5, labels={"component": "scanner"})
collector.increment("operations.count")
```

## Version History

See `CHANGELOG.md` for detailed version history.

## License

MIT License - Jupiter Project
