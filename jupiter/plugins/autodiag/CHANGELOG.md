# Autodiag Plugin Changelog

## v1.4.0
- **Fixed**: Router resolution error caused by `Union[Dict, JSONResponse]` type annotation
  - Changed `update_report()` to use `response_model=None` instead of Union type
  - This was preventing the plugin API from being mounted in FastAPI
- **Fixed**: Synchronized JavaScript functions with new HTML element IDs
- **Fixed**: Tab switching now properly shows/hides content
- **Fixed**: Scenario filtering now works correctly with table rows
- **Added**: Quick settings bindings in sidebar (skip CLI, API, plugins)
- **Added**: Load confidence data button functionality
- **Improved**: Dashboard stats now update properly with accuracy rate
- **Improved**: Tab badge counts update automatically

## v1.3.0
- **Added**: 2-column layout with sidebar (main content + aside)
- **Added**: Quick Settings panel in sidebar
- **Added**: How to Use panel with step-by-step instructions
- **Added**: Confidence Legend panel explaining badge meanings
- **Added**: Server Status panel with live indicator
- **Added**: Complete French and English translations for all new UI elements
- **Added**: Plugin API router for `/api/plugins/autodiag/state` and `/report` endpoints
- **Improved**: Scenarios displayed in full table format with columns for type, status, duration, errors, triggered functions
- **Improved**: CSS reorganized with full dark theme support

## v1.2.0
- **Fixed**: API endpoint URLs now use correct prefix `/diag/run` and `/diag/health` instead of `/run` and `/health`
- **Added**: Inline CSS injection for plugin-specific styles (dark theme compatible)
- **Added**: Complete styling for status cards, tabs, scenario list, function list, confidence table
- **Improved**: CSS follows same pattern as ai_helper plugin for consistency

## v1.1.1
- Fixed manifest schema compliance

## v1.1.0
- Initial Bridge v2 implementation
- Web UI with status cards, tabs, and export functionality
- Settings panel for configuration
- Integration with Jupiter autodiag server on port 8081

## v1.0.0
- Initial release
