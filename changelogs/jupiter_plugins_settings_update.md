# Changelog - settings_update plugin

## [1.0.0] - 2024-12-01

### Added
- Created new `settings_update` plugin to handle Jupiter self-update functionality
- Plugin provides a dedicated Settings UI section for update management
- Features include:
  - Display current Jupiter version
  - Apply update from ZIP file or Git URL
  - Upload ZIP file for update
  - Force update option to ignore errors
- New API routes:
  - `GET /plugins/settings_update/version` - Get current Jupiter version
  - `POST /plugins/settings_update/apply` - Apply an update from source
  - `POST /plugins/settings_update/upload` - Upload a ZIP update file
- Legacy endpoints `/update` and `/update/upload` are preserved for backward compatibility (they redirect to plugin routes)

### Changed
- Moved update logic from `jupiter/core/updater.py` to `jupiter/plugins/settings_update.py`
- Removed hardcoded Update section from `jupiter/web/index.html` - now dynamically loaded via plugin UI system
- Removed `triggerUpdate()` and `setupUpdateFileUpload()` functions from `jupiter/web/app.js`
- Updated `jupiter/server/routers/system.py` to route update requests through the plugin

### Technical Details
- Plugin follows the standard Jupiter plugin architecture with:
  - `PluginUIConfig` for Settings page integration
  - `get_settings_html()` and `get_settings_js()` methods for UI
  - Business logic methods: `apply_update()`, `upload_update_file()`, `get_current_version()`
- Integration with MeetingAdapter for feature access validation
- Full i18n support with translation keys in `en.json` and `fr.json`

### Files Modified
- `jupiter/plugins/settings_update.py` (new)
- `jupiter/server/routers/system.py`
- `jupiter/web/index.html`
- `jupiter/web/app.js`
- `jupiter/web/lang/en.json`
- `jupiter/web/lang/fr.json`
