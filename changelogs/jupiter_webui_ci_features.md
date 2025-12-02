# Changelog – jupiter/web (CI & UI Parity Features)

## [1.2.0] – 2025-01-XX

### Added

#### CI / Quality Gates View
- New "CI" navigation tab with complete quality gates workflow
- CI metrics dashboard: avg complexity, max lines/function, doc coverage, duplications
- Configurable thresholds with localStorage persistence
- Violations list with file and message details
- CI history table tracking pass/fail status over time
- Export CI report functionality

#### Enhanced Scan Modal
- "No cache" option to force full scan (skip incremental cache)
- "Don't save snapshot" option to disable snapshot persistence
- "Snapshot label" text input for custom snapshot naming

#### Snapshot Detail Panel (History View)
- View button to open detailed snapshot info
- Export button to download individual snapshots as JSON
- Summary display: files, functions, lines, timestamp, label

#### License Details (Settings View)
- License details grid showing type, status, device key, session ID, expiry, features
- Refresh button to update license information from Meeting service

### Technical Details

#### Files Modified
- `jupiter/web/index.html` – Added CI view, enhanced scan modal, snapshot panel, license details
- `jupiter/web/app.js` – Added handlers for all new features:
  - `loadCIView()`, `runCICheck()`, `renderCIResult()`, `renderCIHistory()`
  - `openThresholdsConfig()`, `saveThresholds()`, `exportCIReport()`
  - `viewSnapshotDetail()`, `renderSnapshotDetail()`, `closeSnapshotDetail()`, `exportSnapshot()`
  - `refreshLicenseDetails()`, `renderLicenseDetails()`
  - Updated `startScanWithOptions()` with new fields
  - Updated `handleAction()` with new action cases
  - Updated `setView()` to handle CI view
- `jupiter/web/lang/en.json` – Added 60+ new translation keys
- `jupiter/web/lang/fr.json` – Added French equivalents for all new keys

#### API Endpoints Used
- `POST /ci` – Run CI check with thresholds (new endpoint)
- `GET /snapshots/{id}` – Fetch snapshot detail
- `GET /meeting/status` – Fetch license details

#### Models Added (jupiter/server/models.py)
- `CIRequest`, `CIResponse`, `CIMetrics`, `CIThresholds`, `CIViolation`

#### New Router (jupiter/server/routers/analyze.py)
- Added `POST /ci` endpoint implementing quality gate logic

### Motivation
This update achieves feature parity between the CLI and WebUI, ensuring all major CLI capabilities are accessible via the web interface. Addresses items documented in `docs/missing_in_UI.md`.

### Breaking Changes
None. All changes are additive.
