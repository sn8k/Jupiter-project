# Changelog - Security & Hardening

## [Unreleased]

### Added
- **Authentication**: Added `security.token` configuration in `jupiter.yaml`.
- **API Protection**: Protected sensitive endpoints (`/run`, `/update`, `/config`, `/plugins`) with Bearer token authentication.
- **WebSocket Security**: Added token verification for WebSocket connections via query parameter.
- **Meeting Hardening**: Enforced strict validation of `deviceKey` in `MeetingAdapter` to prevent local config bypass.

### Changed
- Updated `docs/api.md`, `docs/dev_guide.md`, and `README.md` to include security information.
