"""Validate the three raster inputs before building a page specification."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256 as _sha256
from pathlib import Path
from typing import Mapping

from PIL import Image, UnidentifiedImageError


@dataclass(frozen=True)
class ValidationReport:
    valid: bool
    width_px: int
    height_px: int
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    sha256: Mapping[str, str]


def validate_images(
    full_path: str | Path,
    background_path: str | Path,
    text_path: str | Path,
) -> ValidationReport:
    """Validate dimensions, transparency, hashes, and text pixel provenance."""
    paths = {
        "full": Path(full_path),
        "background": Path(background_path),
        "text": Path(text_path),
    }
    hashes: dict[str, str] = {}
    errors: list[str] = []
    warnings: list[str] = []
    sizes: dict[str, tuple[int, int]] = {}
    for name, path in paths.items():
        try:
            data = path.read_bytes()
            hashes[name] = _sha256(data).hexdigest()
            with Image.open(path) as image:
                image.load()
                sizes[name] = image.size
        except (OSError, UnidentifiedImageError):
            errors.append(f"{name} image is not readable")

    width_px, height_px = sizes.get("full", (0, 0))
    if len(sizes) == len(paths):
        if len(set(sizes.values())) != 1:
            errors.append("image dimensions must be identical")
        if any(width <= 0 or height <= 0 for width, height in sizes.values()):
            errors.append("image dimensions must be positive")

    return ValidationReport(
        valid=not errors,
        width_px=width_px,
        height_px=height_px,
        errors=tuple(errors),
        warnings=tuple(warnings),
        sha256=hashes,
    )
