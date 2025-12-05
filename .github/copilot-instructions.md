# Copilot Instructions – Jupiter Project

These guidelines are for AI coding agents working inside this repository. They summarize the essential architecture, workflows, and project‑specific conventions. For full details, see `AGENTS.md` (French) and `docs/architecture.md`.

** this file must be kept up to date with project changes. **
** AGENTS.md has the last word in case of conflicts. **
** always check the "docs/" folder for full documentation **

## 1. Scope & Priorities
- Focus on the **Python backend**, **CLI**, **server API**, and **analysis/scan tools**. Frontend (`jupiter/web`) is secondary.
- Do **not** implement deployment logic or destructive operations; prefer code that a human will run.
- Prefer **Python** for new functionality; JS/TS only for Web UI parts.
- Keep the project **simple, lightweight, and extensible**; avoid heavy frameworks unless already used.

## 2. High‑Level Architecture
- `jupiter/core/`: business logic
  - `scanner.py`: filesystem scan, `.jupiterignore`, language detection.
  - `analyzer.py`: aggregates metrics (sizes, hotspots, language insights).
  - `runner.py`: executes shell commands in a controlled way.
  - `tracer.py`: dynamic analysis via `sys.settrace`.
  - `history.py`: snapshot storage & diff; powers `.jupiter/snapshots` and `/snapshots` API.
  - `graph.py`: builds dependency graph for the Live Map.
  - `simulator.py`: impact analysis when “removing” files/functions.
  - `language/`: per‑language analyzers (`python.py`, JS/TS heuristics).
- `jupiter/server/`: API and orchestration
  - `api.py`: FastAPI app exposing scan/analyze/run/snapshots/etc.
  - `manager.py`: project registry & backends (local vs remote connectors).
  - `meeting_adapter.py`: licensing & presence with the external Meeting service (all Meeting logic goes here).
  - `ws.py`: WebSocket for live updates.
- `jupiter/cli/`: CLI entrypoint and commands (`main.py`)
  - Commands: `scan`, `analyze`, `snapshots`, `simulate remove`, `ci`, `server`, `gui`, etc.
  - `scan`, `analyze`, and `ci` now share a **unified workflow builder**; changes to scanning or plugins must keep these paths consistent.
- `jupiter/web/`: HTML/JS UI
  - `index.html`, `app.js`, `styles.css`, `lang/*.json` for i18n.
  - Talks to the API (`/scan`, `/analyze`, `/snapshots`, `/graph`, `/projects`, etc.).
- `jupiter/config/`: config models and loading of `<project>.jupiter.yaml` and global registry (`~/.jupiter/global_config.yaml`).
- `jupiter/plugins/`: plugin system (analysis extensions, webhooks, AI helpers).

## 3. Configuration & State
- Per‑project config lives in `<project>.jupiter.yaml` (not `jupiter.yaml` anymore). Keep this naming consistent in code and docs.
- Global registry: `~/.jupiter/global_config.yaml` (legacy `global.yaml` still handled but normalized).
- Runtime state/cache:
  - `.jupiter/cache/last_scan.json` – last report, must match API schema (`/reports/last`).
  - `.jupiter/snapshots/scan-*.json` – history used by CLI, API, and Web UI History panel.
- Security settings (`security.allow_run`, `security.allowed_commands`, `security.token`) are enforced in core + server; **never** bypass them in new code.

## 4. Web UI & i18n Conventions
- Text must come from `jupiter/web/lang/*.json` (e.g. `en.json`, `fr.json`), not hard‑coded strings.
- Use clear, prefixed keys (e.g. `projects_title`, `project_api_subtitle`, `scan_modal_title`).
- The default theme is **dark**; new UI pieces should match the existing design system in `styles.css`.
- The Projects Control Center, History, Functions, Files, and Quality views are already wired; when adding new data, extend existing tables/panels before inventing new layouts.

## 5. Typical Developer Workflows
- Install deps: `pip install -r requirements.txt` (or via `pyproject.toml` as appropriate).
- Run CLI (dev): `python -m jupiter.cli.main`
  - Examples:
    - `python -m jupiter.cli.main scan`
    - `python -m jupiter.cli.main analyze`
    - `python -m jupiter.cli.main snapshots list|show|diff`
    - `python -m jupiter.cli.main simulate remove <target>`
    - `python -m jupiter.cli.main ci --json`
    - `python -m jupiter.cli.main server` (API only)
    - `python -m jupiter.cli.main gui` (API + Web UI)
- Windows shortcuts:
  - `Jupiter UI.cmd` and `Jupiter Server.cmd` wrap the above for non‑dev users.

## 6. Project‑Specific Patterns
- **Changelogs**: almost every file has a dedicated entry under `changelogs/`. When modifying behavior, add or update the matching `changelogs/*.md` file (e.g. `jupiter_core_scanner.md`, `jupiter_server_api.md`).
- **Global docs**: keep `Manual.md`, `README.md`, and key docs in `docs/` (`user_guide.md`, `api.md`, `architecture.md`, `dev_guide.md`) in sync with behavioral changes.
- **Logging**: use `logging` (no bare `print` except in CLI user messages). Respect the global log level wired via config and the Settings page.
- **Plugins**: new analysis features that could be optional should be modeled as plugins (`jupiter/plugins`) rather than hard‑wired into core.
- **Meeting integration**: all license/session logic must go through `server/meeting_adapter.py`; other modules just consume its interface.

## 7. Coding Style & Safety
- Follow `AGENTS.md` for naming, typing (type hints everywhere), docstrings, and architecture boundaries.
- Prefer clear, readable code over “clever” solutions; keep heuristics isolated and documented.
- Do not introduce new major frameworks without strong justification and alignment with existing choices (FastAPI for server, plain JS for UI, standard `argparse`/lightweight CLI libs).

## 8. How to Contribute with an AI Agent
- When adding features, consider the impact on **CLI**, **API**, and **Web UI** together – many flows are intentionally unified.
- When editing a module, scan for its references (e.g. how `scanner.py` is used by `cli/main.py`, `server/api.py`, and tests) to keep behavior aligned.
- Prefer extending existing patterns (config loading, snapshot management, project registry, plugin hooks) instead of inventing new ones.
- When in doubt, check `AGENTS.md`, `GEMINI.md`, and `docs/architecture.md` and mirror the established approach.
