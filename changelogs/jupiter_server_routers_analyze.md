# Changelog – jupiter/server/routers/analyze.py

## [2025-12-02] – Live Map Plugin Migration

- Marked `GET /graph` endpoint as **deprecated** (use `/plugins/livemap/graph` instead)
- Added deprecation warning and log message when old endpoint is called
- Endpoint will be removed in a future version

---

## [2025-12-02] – Type Fix

- Fixed Pyright type error on line 117: `ci_req: CIRequest = None` → `ci_req: Optional[CIRequest] = None`
- The parameter can legitimately be `None` (defaulting to a new `CIRequest()` inside the function)

---

## Previous Updates

- `/analyze` now forwards optional `locations` evidence from refactoring recommendations so AI duplication hints expose file:line occurrences in responses.
- Added forwarding of `code_excerpt` to surface a snippet of the duplicated block directly in API responses.
- Replaced local `_history_manager` helper with `SystemState.history_manager()` to avoid duplicated code across routers.
