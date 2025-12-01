# Changelog - Web Interface Fixes

## 2025-12-01 - API View Interactive Features
- Added interactive API testing capabilities to the API view.
- Implemented `testApiEndpoint()` to directly test GET/HEAD/OPTIONS endpoints.
- Implemented `openApiInteract()` to open modal for building custom requests.
- Implemented `sendApiRequest()` to send custom API requests with parameters, body, and headers.
- Added `showApiResponse()` to display API responses in a dedicated panel.
- Added `copyApiCurl()` and `copyCurlFromModal()` to copy cURL commands.
- Added `refreshApiEndpoints()` and `exportApiCollection()` for API management.
- Added HTTP method styling in CSS (`.method-get`, `.method-post`, etc.) with color-coded pills.
- Added API tag styling (`.tag` class).
- Added text utility classes (`.text-success`, `.text-error`, `.text-warning`, `.text-info`).
- Added badge active state styling.
- Added i18n keys for API actions in en.json and fr.json.
- Connected form submission handler for API interaction modal.

## 2025-12-01 - Watch Feature Implementation
- Implemented real-time function call tracking via Watch feature.
- Added `state.watch` object to track active status, call counts, and total events.
- Added `startWatch()` and `stopWatch()` functions that call `/watch/start` and `/watch/stop` API.
- Added `updateWatchStats()` to update UI elements with watch status.
- Modified WebSocket message handler to process `FUNCTION_CALLS`, `WATCH_STARTED`, `WATCH_STOPPED`, `WATCH_CALLS_RESET`, and `FILE_CHANGE` events.
- Updated `renderFunctions()` to use live watch call counts in addition to report dynamic data.
- Functions with calls > 0 are highlighted in green; unused functions in orange.
- Added i18n keys for watch feature (`watch_active`, `watch_inactive`, `watch_started`, `watch_stopped`, `functions_empty`).

## 2025-12-01 - Enhanced Alerts Section
- Enhanced `renderAlerts()` to display all attention points, not just Meeting status.
- Added `buildPluginAlerts()` to show alerts for plugins with errors, pending, or disabled status.
- Added `buildQualityAlerts()` to show alerts for high complexity files (score > 20) and code duplications.
- Added new i18n keys for plugin alerts (`alert_plugin_error_*`, `alert_plugin_pending_*`, `alert_plugin_disabled_*`).
- Added new i18n keys for quality alerts (`alert_complexity_*`, `alert_duplication_*`).
- Added `alerts_none` key for when there are no alerts.
- Icons are now contextual: 🔍 unused functions, 🔌 disabled plugins, 🔥 complexity, 📋 duplication, etc.

## 2025-12-01 - Meeting Alert Real Implementation
- Replaced placeholder Meeting alert with real functionality in `renderAlerts()`.
- Added `buildMeetingAlert()` function to build dynamic alerts based on `state.meeting`.
- Added CSS classes for alert types: `alert-success`, `alert-warning`, `alert-error`, `alert-info`.
- Added new i18n keys for Meeting status messages (licensed, trial, expired, not configured).
- Updated `fetchMeetingStatus()` to also re-render alerts when Meeting status changes.

## Fixed
- Fixed "frozen" UI issue caused by ES Module scope isolation.
- Removed inline `onclick` handlers in `app.js` and `index.html`.
- Refactored `showOnboarding` and `renderPluginList` to use `data-action` attributes.
- Updated `handleAction` to support `create-config`, `close-onboarding`, and `toggle-plugin`.
- Improved event delegation in `bindActions`.
