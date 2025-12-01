# Changelog – Meeting Configuration Persistence Fix

## 2025-06-01 – Fix deviceKey and auth_token persistence across restarts

### Problem
- DeviceKey and auth_token were not persisting after server restart
- Dashboard showed "License Invalid" and empty token field after restart

### Root Causes & Fixes

#### 1. `save_global_settings()` (jupiter/config/config.py)
- **Issue**: `auth_token` was not being saved to YAML
- **Fix**: Added conditional write of `auth_token` to meeting section

#### 2. `save_config()` (jupiter/config/config.py)
- **Issue**: `auth_token` was not included in the saved meeting data
- **Fix**: Added `auth_token` to meeting_data dict with conditional inclusion

#### 3. `rebuild_runtime()` (jupiter/server/system_services.py)
- **Issue**: After config update, only `device_key` was being applied to adapter
- **Fix**: Now also updates `adapter.auth_token` and triggers `refresh_license()` when device_key changes

#### 4. `preserve_meeting_config()` (jupiter/server/system_services.py)
- **Issue**: When switching project roots, `auth_token` was not being carried over
- **Fix**: Added preservation of `auth_token` alongside deviceKey

#### 5. CLI command handlers (jupiter/cli/command_handlers.py)
- **Issue**: `handle_server()` and `handle_app()` were using `load_config()` which only loads project config, not global settings where Meeting config is stored
- **Fix**: Changed to use `load_merged_config()` to properly merge global (Meeting/Server/GUI) and project settings

#### 6. API server initialization (jupiter/server/api.py)
- **Issue**: `device_key` was taken from constructor parameter instead of config
- **Fix**: Now uses `meeting_config.deviceKey` from config if available

### Files Modified
- `jupiter/config/config.py`: save_global_settings, save_config
- `jupiter/config/__init__.py`: Export load_merged_config
- `jupiter/server/system_services.py`: rebuild_runtime, preserve_meeting_config
- `jupiter/server/api.py`: JupiterAPIServer.start()
- `jupiter/cli/command_handlers.py`: handle_server, handle_app (use load_merged_config)

### Testing
After these fixes:
1. Start Jupiter UI
2. Go to Settings > Meeting section
3. Enter deviceKey and auth_token
4. Save configuration
5. Restart Jupiter
6. Verify deviceKey and auth_token are preserved
7. Verify license status is checked automatically
