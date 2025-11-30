from pathlib import Path
from jupiter.core.state import load_last_root, load_default_project_root, save_last_root

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
    default_project_root = load_default_project_root()
    remembered = load_last_root()

    if default_project_root:
        if not remembered or remembered != default_project_root:
            save_last_root(default_project_root)
        return default_project_root

    if remembered:
        return remembered
    return Path.cwd()
