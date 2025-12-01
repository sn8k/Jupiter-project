# Changelog – jupiter/server/meeting_adapter.py

## 2025-06-01 – Heartbeat Implementation
- Added `_send_heartbeat()` private method:
  - POSTs to `/api/devices/{device_key}/online` after each license check
  - Includes `Authorization: Bearer {auth_token}` header when token is configured
  - Records timestamp and HTTP status code
  - Errors are logged but don't affect license validation
- Added `heartbeat()` public method for manual heartbeat trigger.
- Added `notify_online()` method to explicitly notify Meeting that Jupiter is online.
- Added `last_heartbeat` and `last_heartbeat_status` tracking attributes.
- Heartbeat is sent automatically when `check_jupiter_devicekey()` succeeds.

## 2025-06-01 – Meeting License Verification
- Added `MeetingLicenseStatus` enum with status values: `VALID`, `INVALID`, `NETWORK_ERROR`, `CONFIG_ERROR`.
- Added `MeetingLicenseCheckResult` dataclass for detailed license verification results.
- Implemented `check_jupiter_devicekey()` method:
  - Makes HTTP GET request to Meeting API (`/devices/{device_key}`)
  - Validates business rules: `authorized == true`, `device_type == "Jupiter"`, `token_count > 0`
  - Handles HTTP errors (404, 500, etc.) gracefully
  - Handles network errors (timeout, connection refused) with proper status
  - Handles malformed JSON responses
- Added `refresh_license()` method to force license re-check.
- Added `get_license_status()` method to retrieve current license result.
- Added `is_licensed()` method for quick license validity check.
- Extended `MeetingAdapter` constructor with new parameters:
  - `base_url`: Meeting API base URL (default: `https://meeting.ygsoft.fr/api`)
  - `device_type_expected`: Expected device type (default: `"Jupiter"`)
  - `timeout_seconds`: HTTP request timeout (default: 5.0)
  - `auth_token`: Optional authentication token for Meeting API
- License is verified automatically at adapter initialization.
- `to_dict()` method on `MeetingLicenseCheckResult` for JSON serialization.

## Previous Changes
- Introduced `MeetingAdapter` placeholder with status payload and enablement checks.
- Implemented `check_license` with trial mode logic (10-minute timer).
- Added `validate_feature_access` to enforce restrictions on `run`, `watch`, and `dynamic_scan`.

