"""Audited full-image to editable-SVG reconstruction primitives.

This package deliberately has no command-line or batch orchestration surface:
callers supply an audited canonical page frame and receive inspectable evidence.
"""

from .contracts import NormalizedFrame, ReconstructionInventory, page_gate
from .reconstruct import author_page_svg, inspect_page, prepare_scene_layers
from .roster import normalize_full_page

__all__ = [
    "NormalizedFrame",
    "ReconstructionInventory",
    "author_page_svg",
    "inspect_page",
    "normalize_full_page",
    "page_gate",
    "prepare_scene_layers",
]
