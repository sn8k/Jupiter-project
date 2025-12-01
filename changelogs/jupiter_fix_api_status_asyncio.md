# Fix: API Status Notifications & Asyncio Error

## Context
1. **Asyncio Error**: On Windows, `uvicorn` + `asyncio` Proactor loop often emits `ConnectionResetError` when clients disconnect abruptly. This is noisy but harmless.
2. **API Status Confusion**: The UI was displaying "Project API Connected" when it was actually checking the **Jupiter Server** status. The user requested specific notifications for the **Project API** status (Not Configured, Unreachable, OK).

## Changes
- **jupiter/server/api.py**:
  - Suppressed `asyncio` log noise on Windows by setting the logger level to CRITICAL.
- **jupiter/web/lang/*.json**:
  - Renamed `notifications_api_online` to "Jupiter Server Connected" to clarify what is being checked by the heartbeat.
- **jupiter/server/routers/system.py**:
  - Added `GET /projects/{id}/api_status` endpoint to check the configured project API.
- **jupiter/web/app.js**:
  - Updated `checkApiHeartbeat` to also call `checkProjectApiStatus` if the server is online.
  - Added `handleProjectApiStatus` to display notifications based on the project API state:
    - "No API configured"
    - "API Unreachable (url)"
    - "API OK (url)"

## Impact
- Cleaner server logs on Windows.
- Clear distinction between Jupiter Server status and Project API status in the UI.
- Users now get feedback on their project's API configuration connectivity.
