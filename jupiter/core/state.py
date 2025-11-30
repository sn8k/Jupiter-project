"""Persistent helpers for storing global Jupiter state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

_STATE_DIR = Path.home() / ".jupiter"
_STATE_FILE = _STATE_DIR / "state.json"


def _ensure_state_dir() -> None:
    """Ensure the hidden state directory exists."""
    _STATE_DIR.mkdir(parents=True, exist_ok=True)


def _write_state(data: Dict[str, Any]) -> None:
    """Persist the provided state dictionary."""
    _ensure_state_dir()
    _STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _read_state() -> Dict[str, Any]:
    """Return the current state dictionary, even if empty."""
    if not _STATE_FILE.exists():
        return {}
    try:
        return json.loads(_STATE_FILE.read_text(encoding="utf-8")) or {}
    except json.JSONDecodeError:
        return {}


def save_last_root(root: Path) -> None:
    """Store the last-served project root for subsequent launches."""
    data = _read_state()
    data["last_root"] = str(root.resolve())
    _write_state(data)


def load_last_root() -> Path | None:
    """Return the previously saved root, if any, only if it still exists."""
    data = _read_state()
    root = data.get("last_root")
    if not root:
        return None
    candidate = Path(root)
    if not candidate.exists() or not candidate.is_dir():
        return None
    return candidate


def load_default_project_root() -> Path | None:
    """
    Return the default project root from the global registry, if it exists.

    This uses the multi-project registry stored under ``~/.jupiter`` so the CLI
    can reopen the last project activated from the Web UI even if the local
    state file is stale.
    """
    try:
        from jupiter.config.config import load_global_config
    except Exception:
        return None

    global_config = load_global_config()
    if not global_config.default_project_id:
        return None

    project = next((p for p in global_config.projects if p.id == global_config.default_project_id), None)
    if not project or not project.path:
        return None

    candidate = Path(project.path).expanduser()
    try:
        resolved = candidate.resolve()
    except OSError:
        return None

    if resolved.exists() and resolved.is_dir():
        return resolved
    return None
