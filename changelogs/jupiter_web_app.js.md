# Changelog – jupiter/web/app.js

## Version 1.7.0 – Dynamic Plugin Translations
### Added
- `createPluginBridge(pluginName, pluginTranslations)`: Now accepts plugin-specific translations
  - The bridge's `i18n.t()` function checks plugin translations first, then falls back to global
  - Exposes `i18n.pluginTranslations` for advanced plugin use

### Changed
- `loadPluginViewContent()`: Now fetches plugin translations before mounting v2 plugins
  - Calls `/plugins/{name}/lang/{lang}` API to get plugin-specific translations
  - Passes translations to `createPluginBridge()`
  - Logs number of translations loaded for debugging

### Architecture
- Implements dynamic i18n loading as described in `docs/plugins_architecture.md`
- Each plugin manages its own translations in `web/lang/` directory
- Main lang files only contain menu/title keys for plugins

## Version 1.6.3
### Fixed
- **Critical**: Fixed syntax error in `initializeV2SettingsForm()` - extra closing brace `}` was breaking JavaScript execution
- V2 plugin settings panels now properly display with auto-generated forms
- Added comprehensive logging for debugging settings form initialization

## Version 1.6.2
### Changed
- `loadPluginSettings()`: Improved error handling and logging
  - Now always reloads settings plugins list when opening settings page
  - Added check for API base URL before making requests
  - Better console logging for debugging settings panel issues

## Version 1.6.1
### Fixed
- Plugin settings loading for v2 plugins
- V2 auto-form generation from JSON schema

## Plugin Activity Widgets (Phase 4.2.1)

### Added
- `fetchPluginMetrics(pluginName)`: Async function to fetch metrics for a specific plugin from `/plugins/{name}/metrics`
- `getPluginActivityWidget(plugin, metrics)`: Generates activity widget HTML showing:
  - Request count with icon
  - Error count with visual highlight for errors
  - Error rate percentage
  - Last activity timestamp (relative time)
- `loadPluginActivityWidgets()`: Loads metrics for all enabled plugins asynchronously after render
- `state.pluginsCache`: Cache for plugin data to avoid re-fetching

### Changed
- `renderPluginList()`: Now includes activity widget in each plugin card
  - Widget loads asynchronously to avoid blocking UI
  - Shows loading spinner while fetching metrics
  - Disabled plugins show "Activity tracking disabled"

## Trust Badge & Circuit Breaker WebUI Support

### Added
- `getTrustBadge(plugin)`: Renders trust level badge based on plugin signature verification
  - Shows official/verified/community/unsigned/experimental with appropriate styling
  - Includes i18n support via lang keys (trust_official, trust_verified, etc.)
  - Displays tooltip with verification details
- `getCircuitBreakerBadge(plugin)`: Renders circuit breaker state badge
  - Shows closed/half_open/open states with color-coded styling
  - Includes failure count and last failure time in tooltip
  - Uses i18n keys (circuit_closed, circuit_half_open, circuit_open)

### Changed
- `renderPluginList()`: Now includes trust badge and circuit breaker badge in plugin cards
  - Both badges shown in header area for at-a-glance health status

---

- Refactored event handling to use `data-action` delegation, fixing "frozen" UI issues with ES Modules.
- Charge et affiche la version globale de Jupiter (badge header + panneau Mise à jour), et protège l'affichage des plugins lorsque `plugin.version` n'est pas fourni.
- Removed inline `onclick` handlers from `showOnboarding` and `renderPluginList`.
- Added `create-config`, `close-onboarding`, and `toggle-plugin` to `handleAction`.
- Unified `startScan` implementation (options-aware) and removed duplicate declarations that prevented the module from executing.
- Rebuilt client logic with multi-view navigation, live log/event feeds, and reusable placeholder actions (Scan/Watch/Run/licence/langue).
- Added richer report rendering (status badges, KPI cards, derived hotspots, analysis stats, plugin grid) while keeping drag-and-drop JSON import.
- Provided sample report data, helper formatting, and safe guards for empty states across dashboard, analyse et fichiers.
- Restored diagnostic/log views, added plugin renderer, bundled sample report, and resolved Scan fetch errors via configurable API base URL inference (`context.json` or `JUPITER_API_BASE`).
- Added client-side Hotspots calculation as fallback when not provided in report.
- Improved Hotspots rendering to filter for Python files and sort by function count.
- Added `fetchMeetingStatus` to poll license status and update UI badges/settings.
- Added `renderQuality` to display complexity and duplication metrics in the new Quality view.
- Updated `renderReport` to include quality metrics rendering.
- Supprimé `renderQuality` et son invocation car le tableau de bord Qualité est désormais géré directement par le plugin Code Quality.
- Added backend management: `fetchBackends` and `renderBackendSelector`.
- Updated `startScan` and `runCommand` to pass `backend_name` to the API.
- Added `backends` and `currentBackend` to application state.
- Added `loadCachedReport` plus `/reports/last` integration so the UI restores the last scan on startup and when the served root changes before issuing a new scan.
- Wired the Suggestions IA "Actualiser" button to call `/analyze`, refresh `state.report.refactoring`, and provide loading feedback.
- WebSocket handler now parses JSON events and renders `PLUGIN_NOTIFICATION` payloads inside the Live Events/log panels so local webhook fallbacks are visible to the user.
- Switched project management calls to `/projects` endpoints, refreshed overview after activation/delete without full reload, and backfilled relative timestamps/auto-report hydration for the Projects dashboard.
- Added wizard close handler, parent folder navigation in the browser modal, and applied danger styling to project delete actions.
- Ensured the project browse modal always exposes parent navigation by auto-inserting a `..` entry when absent.
- History view now filters snapshots to the active project only, clears stale selections on project switch, and blocks diffs against out-of-scope snapshots.
- Context reloads are forced (no-cache) when switching projects so the top bar and History view reflect the newly active project immediately.
- Redesigned project rendering: overview hydration, relative timestamps, refresh action handler, and card-based list with activate/delete buttons powered by `/system/projects`.
- Bound Settings log level selector to the API, normalized client log levels (Debug/Info/Warning/Error/Critical), and reused it to filter the dashboard log stream.
- Settings load/save flows now include an optional log file path so the UI can persist the destination for file logging.
- Projects list now shows the new `<project>.jupiter.yaml` naming by default (with a safe sanitizer) and no longer hardcodes `jupiter.yaml`.
- Suggestions view now renders duplication evidence (file:line list with truncation) and maps `high`/`medium` severities to visible badge styles.
- Suggestions now display the nearest function names and a code excerpt for duplicated blocks to make remediation faster.
- Added `performProjectMutation` helper to factor repeated project activation/deletion request handling.
- Projects page now lets users edit per-project ignore globs (UI inputs + `/projects/{id}/ignore` API call).
- Moved API connector settings to the Projects page with a dedicated form that saves via `/projects/{id}/api_config`.
- Added interactive file/folder exclusion panel with checkboxes for root entries: `loadProjectRootEntries()`, `renderIgnoreEntries()`, `saveProjectIgnores()`, and `setupIgnoreEventListeners()`.
- Exclusion entries support filtering, hidden file toggling, and custom glob patterns input.
- Action handlers added for `refresh-root-entries` and `save-project-ignores`.
- `loadPluginSettings()` vide désormais le conteneur actuel avant de demander aux plugins leurs cartes de configuration, ce qui évite les résidus d'UI quand on recharge la page ou qu'on active un autre projet.
- Les cartes retournées par les plugins sont injectées dans un wrapper `.plugin-settings-card` afin d'aligner leur style avec la nouvelle grille Settings.
- Le wiring du formulaire API projet et de l'upload ZIP passe par `setupProjectApiConnectorForm()` / `setupUpdateFileUpload()` appelés dans `init()`, supprimant le `DOMContentLoaded` isolé qui cassait la compilation TypeScript et l'exécution du thème.

## Version 1.7.1 – Plugin metrics routing
### Fixed
- `fetchPluginMetrics` now targets `/plugins/v2/{plugin}/metrics` (keeps legacy autodiag path) instead of `/plugins/{plugin}/metrics`, eliminating 404s on the plugins page.
- `inferApiBaseUrl` also maps diag port 8081 to API port 8000 to avoid wrong-host calls in multi-port setups.

## Version 1.7.2 – Plugin bridge base URL & metrics fallback
### Fixed
- `createPluginBridge` now exposes `api.baseUrl`, hardens `fetch/get/post` error handling, and infers API host/port (including 8050/8081 → 8000) for plugin consumers like SSE streams.
- Plugin activity metrics request `/plugins/v2/{id}/metrics` first, with legacy autodiag fallback, avoiding 404s and swallowing of bad responses.




