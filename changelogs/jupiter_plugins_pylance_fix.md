# Pylance Plugin Fix

## Context
Users reported "No Pylance data available" even after scanning. This was traced to `pyright` execution failing silently or returning an error code, which the UI interpreted as "no data".

## Changes
- **jupiter/plugins/pylance_analyzer.py**:
  - Updated `_check_pyright_available` to store the full path to the executable.
  - Updated `_run_pyright` to use the full path and return error details.
  - Updated `on_scan` to include error messages in the report.
  - Updated `get_ui_html` to include an error card.
  - Updated `get_ui_js` to display specific error messages when analysis fails.

## Impact
- Users will now see "Pyright is not installed" if it's missing.
- Users will see "Analysis failed" with the specific error message (e.g., exit code, timeout, JSON error) if pyright runs but fails.
- Improved reliability of pyright execution on Windows by using full path.
