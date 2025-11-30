# Changelog - Real Login Implementation

## Added
- **Login System**: Implemented a real login system with Username and Password (Token).
    - Updated `jupiter/web/index.html` with a new Login Modal containing Username, Password, and Remember Me fields.
    - Updated `jupiter/web/app.js` to handle the new login flow, including auto-login via localStorage/sessionStorage.
    - Added `/login` endpoint in `jupiter/server/api.py` to verify credentials against configured users.
- **Security**:
    - Updated `verify_token` in `jupiter/server/api.py` to check against the `users` list in the configuration.
    - The Web UI now forces the login modal to stay open if the user is not authenticated, effectively blocking access to the rest of the UI.

## Changed
- `jupiter/server/api.py`: Added `LoginRequest` model and `/login` endpoint. Updated `verify_token` logic.
- `jupiter/web/app.js`: Refactored `handleLogin`, `logout`, and `checkAutoLogin` to support the new authentication mechanism.
