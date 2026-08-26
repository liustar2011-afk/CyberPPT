"""Retired OCR reconstruction entry point.

The repository's only production route for an editable PPTX reconstructed from
page images is the high-fidelity Stage 02 Quick adapter in
``scripts.image_to_pptx_runtime.stage02_adapter``. This module remains as a
stable import target so older callers fail closed with an actionable message
instead of silently generating a lower-fidelity deck.
"""

from __future__ import annotations

from pathlib import Path

from scripts.image_to_pptx_runtime.stage02_adapter import CANONICAL_EDITABLE_PPTX_ROUTE


LEGACY_ROUTE_ERROR = (
    "The legacy OCR/image-to-editable-SVG route is disabled. "
    f"Use the canonical high-fidelity Quick route: {CANONICAL_EDITABLE_PPTX_ROUTE} "
    "via `final-script-pages --production-build`; it requires an audited manifest "
    "with hand-authored authoring_svg files."
)


def run_image_to_editable_svg(
    *,
    project: Path | str,
    manifest_path: Path | str,
    output_dir: Path | str | None = None,
    requested_pages: list[int] | None = None,
) -> dict:
    """Reject the retired route rather than publishing a non-Quick PPTX."""
    del project, manifest_path, output_dir, requested_pages
    raise RuntimeError(LEGACY_ROUTE_ERROR)
