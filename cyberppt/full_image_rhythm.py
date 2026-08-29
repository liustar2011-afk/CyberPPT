"""Deck-level visual rhythm utilities for audited Stage 02 full images.

This module operates only on finished full images that already passed
the per-page text/image gate. It never OCRs, rewrites, or redesigns a
page. The contact sheet is a review artifact used before those images
are frozen as editable-reconstruction visual authority.
"""

from __future__ import annotations

from hashlib import sha256
from math import ceil
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw, ImageOps


CONTACT_SHEET_SCHEMA = "cyberppt.full_image_contact_sheet.v1"


def audited_full_image_entries(manifest: Mapping[str, object]) -> tuple[tuple[int, Path], ...]:
    entries: list[tuple[int, Path]] = []
    pairs = manifest.get("pairs")
    if not isinstance(pairs, list):
        raise ValueError("Stage 02 manifest pairs must be an array")
    for raw_pair in pairs:
        if not isinstance(raw_pair, Mapping):
            continue
        page_number = int(raw_pair.get("page_number") or 0)
        full = raw_pair.get("full")
        full = full if isinstance(full, Mapping) else {}
        audit = full.get("text_audit")
        audit = audit if isinstance(audit, Mapping) else {}
        path = Path(str(full.get("path") or ""))
        if page_number <= 0:
            raise ValueError("full-image contact sheet requires positive page numbers")
        if audit.get("valid") is not True:
            raise ValueError(f"page {page_number} full image has not passed text audit")
        if not path.is_file():
            raise FileNotFoundError(f"page {page_number} audited full image is missing: {path}")
        entries.append((page_number, path))
    if not entries:
        raise ValueError("full-image contact sheet requires at least one audited full image")
    entries.sort(key=lambda item: item[0])
    if len({page for page, _ in entries}) != len(entries):
        raise ValueError("full-image contact sheet page numbers must be unique")
    return tuple(entries)


def build_full_image_contact_sheet(
    entries: Sequence[tuple[int, Path]],
    output_path: Path,
    *,
    thumbnail_size: tuple[int, int] = (480, 240),
    columns: int = 4,
    padding: int = 16,
    label_height: int = 28,
) -> dict[str, Any]:
    """Build one deterministic review sheet from audited full images."""

    if not entries:
        raise ValueError("contact sheet requires at least one image")
    if columns <= 0 or padding < 0 or label_height < 0:
        raise ValueError("invalid contact sheet geometry")
    thumb_w, thumb_h = thumbnail_size
    if thumb_w <= 0 or thumb_h <= 0:
        raise ValueError("contact sheet thumbnail size must be positive")

    ordered = sorted(((int(page), Path(path)) for page, path in entries), key=lambda item: item[0])
    if len({page for page, _ in ordered}) != len(ordered):
        raise ValueError("contact sheet page numbers must be unique")
    for page, path in ordered:
        if page <= 0:
            raise ValueError("contact sheet page numbers must be positive")
        if not path.is_file():
            raise FileNotFoundError(path)

    rows = ceil(len(ordered) / columns)
    cell_w = thumb_w + padding * 2
    cell_h = thumb_h + label_height + padding * 2
    sheet = Image.new("RGB", (cell_w * columns, cell_h * rows), "white")
    draw = ImageDraw.Draw(sheet)

    page_records: list[dict[str, Any]] = []
    for index, (page_number, path) in enumerate(ordered):
        row, col = divmod(index, columns)
        x0 = col * cell_w + padding
        y0 = row * cell_h + padding
        with Image.open(path) as source:
            source_rgb = source.convert("RGB")
            fitted = ImageOps.contain(source_rgb, (thumb_w, thumb_h), method=Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (thumb_w, thumb_h), "white")
        paste_x = (thumb_w - fitted.width) // 2
        paste_y = (thumb_h - fitted.height) // 2
        tile.paste(fitted, (paste_x, paste_y))
        sheet.paste(tile, (x0, y0))
        draw.rectangle((x0, y0, x0 + thumb_w - 1, y0 + thumb_h - 1), outline="black", width=1)
        draw.text((x0, y0 + thumb_h + 6), f"P{page_number:02d}", fill="black")
        page_records.append({
            "page_number": page_number,
            "source_path": str(path),
            "source_sha256": sha256(path.read_bytes()).hexdigest(),
        })

    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)
    return {
        "schema": CONTACT_SHEET_SCHEMA,
        "path": str(output_path),
        "sha256": sha256(output_path.read_bytes()).hexdigest(),
        "page_count": len(ordered),
        "pages": page_records,
        "thumbnail_size": [thumb_w, thumb_h],
        "columns": columns,
        "sheet_size": list(sheet.size),
    }


def build_manifest_contact_sheet(
    manifest: Mapping[str, object],
    output_path: Path,
    **kwargs: object,
) -> dict[str, Any]:
    return build_full_image_contact_sheet(
        audited_full_image_entries(manifest),
        output_path,
        **kwargs,
    )


__all__ = [
    "CONTACT_SHEET_SCHEMA",
    "audited_full_image_entries",
    "build_full_image_contact_sheet",
    "build_manifest_contact_sheet",
]
