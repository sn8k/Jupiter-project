# Changelog – jupiter/core/cache.py

## Schema normalization & persistence fixes
- Added `_normalize_report()` so cached payloads always serialize plugins as lists and flatten dict-based `files` entries when needed.
- Applied normalization to both `save_last_scan()` and `load_last_scan()` to heal existing cache files that previously stored plugin metadata as dictionaries.
- Ensured dynamic analysis merges continue to reuse the normalized writer so `/reports/last` stays in sync with the API schema.
