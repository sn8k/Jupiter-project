# Changelog – jupiter/web/lang/en.json

## Plugin i18n Architecture Change

### Changed
- Plugin-specific translations are now loaded dynamically from each plugin's `web/lang/` directory
- Main lang files only contain menu/title keys for plugins (`plugin.*.title`, `plugin.*.suggestions_panel`)
- Removed duplicate ai_helper translations that now live in `jupiter/plugins/ai_helper/web/lang/en.json`

### Rationale
- Follows the architecture described in `docs/plugins_architecture.md`
- Each plugin owns its translations
- No duplication between main app and plugins
- Translations loaded at plugin mount time via `/plugins/{name}/lang/{lang}` API

## Plugin Activity Widget i18n (Phase 4.2.1)

### Added
- `plugin_activity_loading`: "Loading metrics..."
- `plugin_activity_disabled`: "Activity tracking disabled"
- `plugin_activity_never`: "Never" (for last activity when none)
- `plugin_activity_requests`: "Requests"
- `plugin_activity_requests_tooltip`: Tooltip for request count
- `plugin_activity_errors`: "Errors"
- `plugin_activity_errors_tooltip`: Tooltip for error count
- `plugin_activity_error_rate`: "Error Rate"
- `plugin_activity_error_rate_tooltip`: Tooltip for error rate
- `plugin_activity_last`: "Last Activity"
- `plugin_activity_last_tooltip`: Tooltip for last activity timestamp

## Trust Badge & Circuit Breaker i18n

### Added
- Trust badge translations:
  - `trust_official`: "Official" - for Jupiter-signed plugins
  - `trust_verified`: "Verified" - for third-party verified plugins  
  - `trust_community`: "Community" - for community plugins
  - `trust_unsigned`: "Unsigned" - for plugins without signature
  - `trust_experimental`: "Experimental" - for experimental plugins
  - `trust_tooltip_official`: Tooltip explaining official status
  - `trust_tooltip_verified`: Tooltip explaining verified status
  - `trust_tooltip_community`: Tooltip explaining community status
  - `trust_tooltip_unsigned`: Warning about unsigned plugins
  - `trust_tooltip_experimental`: Warning about experimental plugins
- Circuit breaker translations:
  - `circuit_closed`: "Healthy" - normal operation
  - `circuit_half_open`: "Recovering" - testing recovery
  - `circuit_open`: "Degraded" - circuit open, calls blocked
  - `circuit_tooltip_closed`: Tooltip explaining healthy state
  - `circuit_tooltip_half_open`: Tooltip explaining recovery state
  - `circuit_tooltip_open`: Tooltip explaining degraded state

---

- Added strings for restored Analysis, Diagnostics, Files, and Plugins views plus status badges and API/CORS context messaging.
- Added `suggestions_refresh_*` keys so the UI can show progress/success/error messages when refreshing AI suggestions.
- Added Projects dashboard wording (hero, metrics, shortcuts, empty state) and relative time labels for the redesigned page.
- Added log-level settings strings so the UI can describe the new logging control.
- Tweaked config-related strings to mention the new `.jupiter.yaml` naming pattern.
- Added labels/hint for the log file path field in Settings.
- Added `suggestions_more_locations` translation to describe truncated duplication evidence lists.
- (UI) Suggestions tab now also shows code excerpts for duplication hints; existing keys remain valid.
- Added keys for per-project ignore globs editing on the Projects page.
- Added keys for the new Project API connector form (title, subtitle, save feedback).
- Added `update_current_version` so the update panel can label the displayed Jupiter version.
- Added strings for the Code Quality dashboard tab plus the refreshed settings card (hints, duplication chunk size, dashboard eyebrow).
