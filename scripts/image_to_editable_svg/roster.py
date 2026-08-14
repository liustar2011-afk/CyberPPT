"""Canonical full-image page roster and non-destructive normalization."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from PIL import Image

from .contracts import NormalizedFrame


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_full_page(*, page_number: int, source: Path | str, output_dir: Path | str) -> NormalizedFrame:
    """Archive one page image as a PNG without trimming or rescaling canvas pixels."""
    if page_number < 1:
        raise ValueError("page_number must be positive")
    source_path = Path(source).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"canonical full image not found: {source_path}")
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as image:
        pixel_size = tuple(int(value) for value in image.size)
        if not all(pixel_size):
            raise ValueError(f"canonical full image has empty canvas: {source_path}")
        target = target_dir / f"p{page_number:02d}-canonical.png"
        # Pillow's PNG write preserves the exact raster canvas.  Copying a PNG
        # source verbatim also preserves ancillary image metadata where useful.
        if source_path.suffix.lower() == ".png":
            shutil.copy2(source_path, target)
        else:
            image.convert("RGBA" if "A" in image.getbands() else "RGB").save(target, format="PNG")
    return NormalizedFrame(page_number, str(source_path), sha256_file(source_path), str(target), pixel_size)


def build_roster(*, pages: list[tuple[int, Path | str]], output_dir: Path | str) -> list[NormalizedFrame]:
    """Normalize explicitly mapped individual files; reject duplicate page mappings."""
    numbers = [number for number, _ in pages]
    if len(numbers) != len(set(numbers)):
        raise ValueError("ambiguous full-image roster: a page maps to more than one frame")
    return [normalize_full_page(page_number=number, source=source, output_dir=output_dir) for number, source in sorted(pages)]
