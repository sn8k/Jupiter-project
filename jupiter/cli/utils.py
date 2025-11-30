from pathlib import Path
from jupiter.core.state import load_last_root

def _clean_root_argument(root: Path | None) -> Path | None:
    """Return a sanitized path if the CLI argument was provided."""
    if root is None:
        return None
    return Path(str(root).strip('"\''))


def resolve_root_argument(root_arg: Path | None) -> Path:
    """Resolve the active root, using persisted state if none is explicitly provided."""
    explicit_root = _clean_root_argument(root_arg)
    if explicit_root:
        return explicit_root
    remembered = load_last_root()
    if remembered:
        return remembered
    return Path.cwd()
