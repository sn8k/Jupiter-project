# Changelog - Jupiter Web UI Security

## [Unreleased]

### Added
- Login modal for token-based authentication.
- User profile button in the header showing current role.
- Automatic token verification on startup.
- `apiFetch` wrapper to handle `Authorization` header and 401 responses.
- Logout functionality.

### Changed
- Updated all API calls to use `apiFetch` to ensure authentication.
- `loadContext` remains public as it fetches static JSON.
