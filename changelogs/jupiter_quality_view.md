# Quality View Data Pipeline

- **Backend**: Local connector now runs the analyzer during `/scan` to attach `quality` and `refactoring` data.
- **API**: `ScanReport` schema exposes the new fields so Web UI and remote clients get immediate quality metrics.
- **Frontend**: The Qualité tab now receives populated data as soon as a Scan completes or while Watch mode streams updates.
