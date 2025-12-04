# Changelog - jupiter/web/js/plugin_settings_frame.js

## v0.2.0
### Added
- Check for update button and `checkForUpdate()` method
- View changelog button and `viewChangelog()` method with modal display
- Debug mode toggle with auto-disable timer
- Update plugin functionality with `updatePlugin()` method
- Update available badge display
- Timer countdown for debug mode auto-disable
- `_showUpdateAvailable()` method
- `_showChangelogModal()` method
- `toggleDebugMode()` method
- `_startDebugTimer()` and `_clearDebugTimer()` methods
- `_loadDebugState()` method
- `_escapeHtml()` utility method
- New UI elements: updateBadge, debugBar, debugToggle, debugTimer, checkUpdateBtn, viewChangelogBtn
- `showDebugToggle` option in constructor

### Changed
- Updated settings info section to include meta container with version and update badge
- Added debug bar section to settings UI
- Enhanced `_renderPluginInfo()` to show/hide debug bar based on plugin capabilities

## v0.1.0
### Added
- Initial release
- Settings frame UI with header, info, tabs, form container, footer
- Plugin loading and form rendering
- Import/export settings functionality
- Reset to defaults functionality
- Unsaved changes indicator
- AutoForm integration for dynamic form generation
- Tab-based settings organization
- Live preview of settings JSON
- Form validation and error display
- Success/error notifications
