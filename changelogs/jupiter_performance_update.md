# Changelog - Performance & Scalability

## Added
- **Performance Configuration**: New `performance` section in `jupiter.yaml` to control parallel scanning, max workers, and graph simplification.
- **CLI Performance Flag**: Added `--perf` flag to `scan` and `analyze` commands to enable performance profiling and logging.
- **Parallel Scanning**: `ProjectScanner` now uses `ThreadPoolExecutor` to scan files in parallel, significantly improving performance on large projects.
- **Graph Simplification**: `GraphBuilder` now supports a `simplify` mode (automatic or manual) that groups files by directory when the node count exceeds a threshold (default 1000).
- **Large File Handling**: Added `large_file_threshold` configuration to skip analysis of very large files (default 10MB).

## Changed
- **Documentation**: Updated `Manual.md`, `docs/user_guide.md`, and `docs/dev_guide.md` to reflect performance features.
- **API**: Updated `/graph` endpoint to accept `simplify` and `max_nodes` parameters.
