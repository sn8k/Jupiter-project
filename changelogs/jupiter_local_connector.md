# Feature: Local API Connector

## Changes

- **Frontend**: Added "Local (Jupiter)" option to API Inspection settings.
- **Frontend**: Automatically disables "App Variable" and "Main File Path" inputs when "Local" is selected.
- **Backend**: `ProjectManager` now detects `connector="local"` and automatically configures the `OpenApiConnector` to target the running Jupiter server (`http://localhost:port/openapi.json`).
- **Backend**: Configuration updates now trigger a refresh of the `ProjectManager`, ensuring immediate application of new settings.

## Impact

- Users can now easily inspect Jupiter's own API by selecting "Local (Jupiter)" in the settings, without manually configuring the URL.
