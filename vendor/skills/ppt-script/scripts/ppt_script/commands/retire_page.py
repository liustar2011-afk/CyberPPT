from __future__ import annotations

from pathlib import Path

from ..pages_index import retire_page_file


def retire_page_command(project: Path, name_or_stem: str) -> Path:
    return retire_page_file(project, name_or_stem)
