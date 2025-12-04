# Changelog - jupiter/web/js/data_export.js

## [0.1.0] - Initial Release

### Added
- **DataExporter class**: Complete data export component for AI agents
- **Multiple export formats**:
  - JSON: Standard structured JSON
  - NDJSON: Newline-delimited JSON for streaming
  - CSV: Comma-separated values for spreadsheets
  - Markdown: Table format for documentation
- **Source selection**: Export from various data sources
  - Scan results
  - Analysis data
  - Functions list
  - Files list
  - Metrics
  - History/snapshots
  - Custom endpoints
- **Field selection**: Choose specific fields to include in export
- **Filter system**:
  - Equality (=) / Inequality (≠)
  - Greater than / Less than
  - Contains / Starts with
  - Multiple active filters
- **Preview functionality**:
  - Load preview before export
  - Format preview updates live
  - Size estimation
  - Item count display
- **Export actions**:
  - Copy to clipboard
  - Download as file
  - Automatic filename generation
- **Nested field support**: Access nested object properties with dot notation
- **Factory function**: `jupiterDataExport.create()` for easy instantiation

### Features
- Clean, modern UI matching Jupiter design system
- Responsive format selection with radio buttons
- Active filter tags with remove buttons
- Preview limited to avoid performance issues
- Size estimation in human-readable format
- Integration with Jupiter notification system

### API
- `render(container)`: Render export UI
- `loadPreview()`: Load and display preview data
- `getExportData()`: Get filtered/projected data
- `getFormattedContent()`: Get formatted export string
- `copyToClipboard()`: Copy to clipboard
- `downloadFile()`: Download as file
- `destroy()`: Clean up component
- `EXPORT_FORMATS`: Available format definitions
- `getVersion()`: Return module version
