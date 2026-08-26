from __future__ import annotations

import re
from pathlib import Path

_SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def find_repo_root(start: str | Path | None = None) -> Path:
    """Find the nearest repository or installed skill root containing VERSION."""
    current = Path(start).resolve() if start is not None else Path(__file__).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "VERSION").is_file():
            return candidate
    raise FileNotFoundError(f"VERSION not found from {current}")


def get_version(repo_root: str | Path | None = None) -> str:
    root = find_repo_root(repo_root)
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not _SEMVER.fullmatch(version):
        raise ValueError(f"invalid VERSION value: {version!r}")
    return version
