# Changelog - User Management & Update Upload

## Added
- **User Management**: Added a new section in Settings to manage Jupiter users (Name, Token, Role).
    - Users are stored in the global `jupiter.yaml` configuration file (installation directory).
    - Added backend endpoints: `GET /users`, `POST /users`, `DELETE /users/{name}`.
- **Update Upload**: Added a "Browse" button to the Update section in Settings to upload a ZIP file.
    - Added backend endpoint: `POST /update/upload`.

## Changed
- `jupiter/config/config.py`: Added `UserConfig` and updated `JupiterConfig` to include `users`. Updated `save_global_settings` to persist users.
- `jupiter/server/api.py`: Added endpoints for user management and file upload.
- `jupiter/web/index.html`: Updated Settings view with User Management table and Update file input.
- `jupiter/web/app.js`: Added logic for loading/adding/deleting users and handling file uploads.
