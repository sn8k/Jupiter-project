"""Jupiter package bootstrap."""

from pathlib import Path

__all__ = [
    "__version__",
]

try:
    # Try to read version from VERSION file in the root
    _version_file = Path(__file__).parent.parent / "VERSION"
    if _version_file.exists():
        __version__ = _version_file.read_text().strip()
    else:
        # Fallback if file not found (e.g. installed package without VERSION file included)
        __version__ = "1.0.1"
except Exception:
    __version__ = "1.0.1"
