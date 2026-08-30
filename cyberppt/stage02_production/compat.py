"""Read-only compatibility exports for historical Stage 02 callers.

Legacy import names remain available during migration, but this module no
longer mutates the typed production pipeline.  Canonical production dependencies
are resolved by ``cyberppt.stage02_production`` modules themselves.
"""
from __future__ import annotations

from typing import Any

from scripts.imagegen_pipeline.imagegen_handoff import IMAGEGEN_CANVAS_CONTRACT as BODY_IMAGE_CANVAS_CONTRACT
from scripts.imagegen_pipeline.page_manifest import FULL_IMAGE_MODE, require_generated
from scripts.imagegen_pipeline.providers.codex_oauth_image import ensure_output_size, run_codex_image
from scripts.image_to_pptx_runtime.stage02_adapter import CANONICAL_EDITABLE_PPTX_ROUTE
from cyberppt.commands.production_qa import run_officecli_render_qa


def sync_legacy_patch_points(**_kwargs: Any) -> None:
    """Deprecated no-op retained only for source compatibility.

    Previous releases copied facade-level monkey patches into live production
    modules.  That made runtime behavior depend on import order and test patch
    points.  Production is now intentionally non-mutating; callers that need
    substitution must inject it at the owning module/test boundary instead.
    """

    return None


__all__ = [
    "BODY_IMAGE_CANVAS_CONTRACT",
    "CANONICAL_EDITABLE_PPTX_ROUTE",
    "FULL_IMAGE_MODE",
    "ensure_output_size",
    "require_generated",
    "run_codex_image",
    "run_officecli_render_qa",
    "sync_legacy_patch_points",
]
