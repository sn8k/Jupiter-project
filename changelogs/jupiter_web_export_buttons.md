# Changelog - Export Buttons for AI & Quality

## Added
- **Export Buttons**: Added "Export Report" buttons to the "Quality" and "AI Suggestions" views in the web interface.
- **Structured Export**: The exported JSON files now include context (project root, timestamp) along with the raw data, making them suitable for processing by AI coding agents.

## Modified
- `jupiter/web/index.html`: Added buttons and headers.
- `jupiter/web/app.js`: Implemented export logic and `exportData` helper.
