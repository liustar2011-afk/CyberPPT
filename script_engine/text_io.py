"""Text output helpers with repository-stable encoding and line endings."""
from __future__ import annotations

from pathlib import Path


def write_text_lf(path: Path, text: str) -> None:
    """Write UTF-8 text with LF line endings on every platform."""
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
