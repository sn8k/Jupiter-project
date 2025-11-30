# Fixes: API Tab "Not Configured"

## Changes

- **Backend**: Updated `AnalyzeResponse` model in `jupiter/server/models.py` to include the `api` field.
- **Backend**: Updated `get_analyze` endpoint in `jupiter/server/api.py` to pass the `api` data from `summary_dict` to the response.

## Impact

- **UI**: The API tab in the frontend will now correctly display the API endpoints (or connection status) when "Local (Jupiter)" or another connector is configured, as the data is now properly propagated from the backend to the frontend.
