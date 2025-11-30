# Changelog – jupiter/server/routers/analyze.py
- `/analyze` now forwards optional `locations` evidence from refactoring recommendations so AI duplication hints expose file:line occurrences in responses.
- Added forwarding of `code_excerpt` to surface a snippet of the duplicated block directly in API responses.
- Replaced local `_history_manager` helper with `SystemState.history_manager()` to avoid duplicated code across routers.
