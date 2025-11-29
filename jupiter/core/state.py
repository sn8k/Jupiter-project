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
