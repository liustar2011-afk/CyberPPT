"""Resolve concrete font files for typography fitting."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import shutil
import subprocess


SUPPORTED_WEIGHTS = frozenset({"light", "regular", "bold"})


@lru_cache(maxsize=32)
def resolve_font_face(family: str, weight: str) -> Path:
    """Return the exact font file selected by fontconfig for a family/weight."""

    normalized_family = str(family).strip()
    normalized_weight = str(weight).strip().lower()
    if not normalized_family:
        raise ValueError("font family must not be empty")
    if normalized_weight not in SUPPORTED_WEIGHTS:
        raise ValueError(f"unsupported font weight: {weight}")
    executable = shutil.which("fc-match")
    if executable is None:
        raise FileNotFoundError("fc-match is required to resolve font files")
    query = f"{normalized_family}:weight={normalized_weight}"
    result = subprocess.run(
        [executable, "-f", "%{file}\n", query],
        check=True,
        text=True,
        capture_output=True,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise FileNotFoundError(f"font face is unavailable: {normalized_family} {normalized_weight}")
    path = Path(lines[0]).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"font face is unavailable: {normalized_family} {normalized_weight}: {path}")
    return path
