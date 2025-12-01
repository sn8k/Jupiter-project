# Fix: 401 Unauthorized on /projects

## Context
The Web UI was attempting to fetch the project list (`/projects`) immediately on page load, before the authentication token was retrieved from local storage and verified. This resulted in a `401 Unauthorized` error in the server logs.

## Changes
- **jupiter/web/app.js**:
  - Removed the `setTimeout(checkProjectStatus, 1000)` call from `DOMContentLoaded`.
  - Moved the `checkProjectStatus()` call to:
    1. The success callback of `checkAutoLogin` (after token verification).
    2. The success path of `handleLogin` (after manual login).

## Impact
- Eliminates the spurious 401 error on startup.
- Ensures project status is only checked when a valid user session is established.
