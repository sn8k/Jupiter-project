# Changelog - jupiter/web/js/plugin_settings_frame.js

## v0.4.0
- Added Dry-run support for settings validation
- New `dryRunSave()` method validates without applying changes
- Dry-run button in settings footer next to Save button
- API call to `PUT /plugins/{id}/settings?dry_run=true`
- Success/error feedback with i18n support (dry_run_success, dry_run_error)
- Preview panel shows validation results in dry-run mode

## v0.3.0
- Hot Reload button in developer mode debug bar
- Calls `/plugins/v2/{plugin_id}/reload` API endpoint
- Loading state with spinner during reload
- Success/error feedback with i18n support
- Automatic plugin refresh after successful reload

## v0.2.0
- Check for update button with version comparison
- Update plugin button with confirmation and rollback
- View changelog button shows changelog.md in modal
- Debug mode toggle with auto-disable timeout
- Settings versioning with export/import support

## v0.1.0
- Initial creation of PluginSettingsFrame module
- Dynamic form generation from plugin manifest settings schema
- Settings validation against JSON Schema
- Dirty state tracking with unsaved changes indicator
- Save settings to API endpoint
- Reset to defaults functionality
- Import settings from JSON file
- Export settings to JSON file
- Tab-based settings organization via schema groups
- Fallback form rendering when AutoForm not available
- Integration with jupiterBridge for notifications
- Preview panel for JSON representation
- Error highlighting on validation failures
