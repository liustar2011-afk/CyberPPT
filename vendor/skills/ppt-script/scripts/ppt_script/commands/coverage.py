from __future__ import annotations

from pathlib import Path
from typing import Callable

from ..pages_index import active_page_files


def page_files(project: Path) -> list[Path]:
    """Return substantive page files in stable assembly order."""
    return active_page_files(project)

def select_pages(project: Path, selector: str | None = None) -> list[Path]:
    pages = page_files(project)
    if not selector:
        return pages
    needle = selector.lower()
    return [path for path in pages if needle in path.stem.lower()]


def summarize(project: Path, extractor: Callable[[str], list[str]]) -> dict[str, list[str]]:
    """Shared deterministic traversal for coverage-style commands."""
    return {
        path.name: extractor(path.read_text(encoding="utf-8"))
        for path in page_files(project)
    }
