# Changelog: jupiter/web – Log Level Setting Restoration

## Version 1.3.2

### Fixed
- **Log Level Setting Restored**: The global log level setting was accidentally removed during the Settings UX refactor (v1.3.1). It has been restored in the Security section of the Settings page.

### Changes

#### index.html
- Added log level dropdown (`conf-log-level`) in the Security section
- Options: DEBUG, INFO (default), WARNING, ERROR, CRITICAL
- Uses i18n keys `settings_log_level_label` and `settings_log_level_hint`

#### app.js
- Updated `saveSecuritySettings()` to include `log_level` in the config payload
- Log level is applied immediately via `applyLogLevel()` after successful save

### i18n Keys Used
- `settings_log_level_label`: "Log level" / "Niveau de log"
- `settings_log_level_hint`: Hint text explaining verbosity levels

### Related Files
- `jupiter/web/index.html`
- `jupiter/web/app.js`
- `jupiter/web/lang/fr.json` (v1.0.2)
- `jupiter/web/lang/en.json` (v1.0.2)
