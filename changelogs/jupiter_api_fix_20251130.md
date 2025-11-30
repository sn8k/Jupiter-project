# Fixes: API Config Persistence & UI

## Changes

- **Config**: Fixed `JupiterConfig.from_dict` in `jupiter/config/config.py` to correctly read the `api` section from `jupiter.yaml` (it was looking for `project_api` but saving as `api`). This fixes the issue where the API connector setting was lost after restart.
- **Frontend**: Updated `renderApi` in `jupiter/web/app.js` to better handle cases where the API is configured but no endpoints are returned (e.g. connection error or empty API), showing a "Connected" badge instead of "Not Configured".

## Impact

- **Persistence**: The "Local (Jupiter)" connector setting (and other API settings) will now persist correctly across restarts.
- **UI**: The API view will now correctly reflect the connection status even if no endpoints are found initially.
