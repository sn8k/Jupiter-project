# Fixes: API Info in Scan Report

## Changes

- **Backend**: Added `get_api_info` method to `LocalConnector` in `jupiter/core/connectors/local.py` to encapsulate API fetching logic.
- **Backend**: Updated `ScanReport` model in `jupiter/server/models.py` to include the `api` field.
- **Backend**: Updated `post_scan` in `jupiter/server/api.py` to call `get_api_info` and populate the `api` field in the report.

## Impact

- **UI**: The "Scan" button (which calls `/scan`) will now return API information in the report, allowing the API tab to display the configuration status and endpoints immediately after a scan.
