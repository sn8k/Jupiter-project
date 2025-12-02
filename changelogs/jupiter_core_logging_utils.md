# Changelog – jupiter/core/logging_utils.py

## v1.1.0 (2025-12-03)

### Added
- **Log reset on startup option**: New `reset_on_start` parameter in `configure_logging()`
- **`prepare_log_file()` function**: Prepares log file before logging starts
  - If `reset_on_start=True`: Deletes existing log file for a fresh start
  - If `reset_on_start=False`: Appends a visual separator with timestamp to mark the restart
- **`LOG_RESTART_SEPARATOR` constant**: Formatted banner with timestamp for restart markers

### Changed
- `configure_logging()` now accepts `reset_on_start` parameter (default: `True`)
- Improved docstrings with full parameter documentation

---

## v1.0.0 (Initial)
- Added centralized logging utilities to normalize user-provided levels (Debug/Info/Warning/Error/Critic) and configure root/Uvicorn loggers consistently.
- Added optional log file support to `configure_logging`, creating a file handler when a path is provided and preventing duplicate handlers for the same target.
