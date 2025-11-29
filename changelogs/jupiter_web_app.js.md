# Changelog – jupiter/web/app.js
- Refactored event handling to use `data-action` delegation, fixing "frozen" UI issues with ES Modules.
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
- Added backend management: `fetchBackends` and `renderBackendSelector`.
- Updated `startScan` and `runCommand` to pass `backend_name` to the API.
- Added `backends` and `currentBackend` to application state.
- Added `loadCachedReport` plus `/reports/last` integration so the UI restores the last scan on startup and when the served root changes before issuing a new scan.


