#!/usr/bin/env python3
"""Shared image helpers for ppt-master similarity / preview scripts.

``resize_rgb`` was duplicated (as ``resize_rgb`` / ``_resize_rgb``) in the
reference-similarity modules. Keeping one copy here avoids drift in the
resampling filter used for pixel-diff comparisons.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image


def resize_rgb(path: Path, size: tuple[int, int]) -> Any:
    """Open ``path``, convert to RGB and resize to ``size`` with LANCZOS."""
    return Image.open(path).convert("RGB").resize(size, Image.Resampling.LANCZOS)
