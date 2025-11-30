# Web UI Wizard Fixes

## Fixed
- **Browse Button Inactive**: Fixed an issue where the "Browse" button in the Project Wizard was inactive because the `/fs/list` endpoint required authentication, which is not available during initial setup.
- **API Endpoint**: Updated `GET /fs/list` in `jupiter/server/routers/system.py` to use `Depends(verify_token)` as a parameter rather than a dependency in the decorator, allowing the `verify_token` logic (which permits admin access in setup mode) to function correctly.
- **Frontend Fetch**: Updated `fetchFs` in `jupiter/web/app.js` to handle requests without a token when in setup mode, ensuring the file browser works for the wizard.
