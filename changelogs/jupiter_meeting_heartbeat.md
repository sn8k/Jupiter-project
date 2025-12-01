# Changelog - Meeting Heartbeat Feature

## Date: 2025-01-14

### Summary
Implemented periodic heartbeat signals to Meeting service and removed the obsolete `meeting_enabled` configuration option.

### Changes

#### Feature: Meeting Heartbeat
- **Background Task**: Added `_meeting_heartbeat_loop()` in `jupiter/server/api.py` that sends periodic heartbeat signals to the Meeting service.
- **Configuration**: New `heartbeat_interval_seconds` field in `MeetingConfig` (default: 60 seconds).
- **UI**: Added Heartbeat Interval input field in Settings → Meeting section (`jupiter/web/index.html`).
- **API**: Updated `ConfigModel` in `jupiter/server/models.py` to include `meeting_heartbeat_interval`.
- **Router**: Updated `jupiter/server/routers/system.py` GET/POST `/config` endpoints to handle heartbeat configuration.

#### Removal: meeting_enabled
The `meeting_enabled` boolean flag was removed as it was redundant. Meeting integration is now considered enabled when a `deviceKey` is configured.

**Files Modified:**
- `jupiter/config/config.py` - Removed `enabled` field from `MeetingConfig`, added `heartbeat_interval_seconds`
- `jupiter/server/models.py` - Replaced `meeting_enabled` with `meeting_heartbeat_interval` in `ConfigModel`
- `jupiter/server/routers/system.py` - Updated config endpoints
- `jupiter/server/system_services.py` - Removed `meeting.enabled` preservation
- `jupiter/cli/main.py` - Simplified deviceKey access (no longer checks `enabled`)
- `jupiter/cli/command_handlers.py` - Simplified deviceKey access in `handle_server` and `handle_app`
- `jupiter/web/index.html` - Removed Meeting Enabled checkbox, added Heartbeat Interval input
- `jupiter/web/app.js` - Updated `loadSettings()` and `saveSettings()` for heartbeat
- `jupiter/web/lang/en.json` - Added `meeting_heartbeat_label` and `meeting_heartbeat_hint`
- `jupiter/web/lang/fr.json` - Added French translations for heartbeat labels

### Behavior
- Heartbeats are sent at the configured interval (default 60 seconds) when Jupiter server starts.
- If Meeting adapter is not configured (no deviceKey), no heartbeats are sent.
- Heartbeat failures are logged as warnings but do not stop the server.
- The heartbeat task is properly cancelled on server shutdown.
