"""Small, explicit contracts around the imported Quick reconstruction tools."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CanonicalPage:
    page_number: int
    source_path: Path
    normalized_path: Path
    sha256: str
    pixel_size: tuple[int, int]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["source_path"] = str(self.source_path)
        result["normalized_path"] = str(self.normalized_path)
        result["pixel_size"] = list(self.pixel_size)
        return result


@dataclass(frozen=True)
class QuickProject:
    root: Path
    roster: tuple[CanonicalPage, ...]
    text_by_page: dict[int, tuple[str, ...]]

    def svg_path(self, page_number: int) -> Path:
        return self.root / "svg_output" / f"{page_number:02d}.svg"
