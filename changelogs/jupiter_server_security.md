# Changelog - Jupiter Server Security

## [Unreleased]

### Added
- Support for multiple authentication tokens in `SecurityConfig`.
- Role-based access control (RBAC) with "admin" and "viewer" roles.
- `TokenConfig` dataclass for structured token configuration.
- `require_admin` dependency for sensitive API endpoints.
- Protected GET endpoints with `verify_token` to ensure authenticated access.

### Changed
- Updated `verify_token` to return the user role instead of just verifying.
- Updated `JupiterConfig.from_dict` to parse `tokens` list.
- Restricted `post_run`, `post_config`, `post_update`, and plugin management to "admin" role.
