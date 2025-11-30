# Changelog - Jupiter Web App

## [0.1.5] - 2024-10-27

### Added
- **API Inspection Settings**: Added configuration fields for API connector, app variable, and main file path in the Settings page.
- **Raw Config Editor**: Added a "Edit Raw YAML" button in Settings to directly edit `jupiter.yaml` via a modal.
- **Tooltips**: Added explanatory tooltips to settings fields for better UX.

### Changed
- **Settings Layout**: Updated the settings form to include the new API Inspection section.
- **Backend API**: Updated `/config` endpoints to handle API configuration fields and added `/config/raw` endpoints for raw file editing.

### Fixed
- **Modal Structure**: Fixed an issue with modal HTML structure in `index.html`.
