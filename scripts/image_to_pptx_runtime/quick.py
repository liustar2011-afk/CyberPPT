"""Quick-only project preparation for a high-fidelity image reconstruction."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Iterable, Mapping

from PIL import Image

from .contracts import CanonicalPage, QuickProject


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_quick_project(root: Path | str, *, pages: list[tuple[int, Path]], text_by_page: Mapping[int, Iterable[str]]) -> QuickProject:
    """Archive canonical pages and write the visible-evidence reconstruction inventory."""
    base = Path(root).expanduser().resolve()
    sources = base / "sources"
    normalized = base / "images" / "source-pages"
    analysis = base / "analysis"
    for directory in (sources, normalized, analysis, base / "svg_output", base / "images" / "prepared"):
        directory.mkdir(parents=True, exist_ok=True)
    roster: list[CanonicalPage] = []
    for number, raw_path in pages:
        source = Path(raw_path).expanduser().resolve()
        if number < 1 or not source.is_file():
            raise ValueError(f"invalid canonical page {number}: {source}")
        archived = sources / f"p{number:02d}-{source.name}"
        normalized_path = normalized / f"p{number:02d}.png"
        shutil.copy2(source, archived)
        with Image.open(source) as image:
            image.convert("RGBA").save(normalized_path)
            size = image.size
        roster.append(CanonicalPage(number, archived, normalized_path, _sha256(archived), size))
    result = QuickProject(base, tuple(sorted(roster, key=lambda item: item.page_number)), {number: tuple(value for value in lines if str(value).strip()) for number, lines in text_by_page.items()})
    inventory = {"schema": "cyberppt.image_to_pptx.inventory.v1", "pages": [{**page.to_dict(), "visible_text": list(result.text_by_page.get(page.page_number, ())), "regions": [], "note": "Agent-authored visible-region evidence; no delivery-layer choice is implied."} for page in result.roster]}
    (analysis / "reconstruction_inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result
