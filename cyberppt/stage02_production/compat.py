"""Legacy patch-point bridge kept outside the Stage 02 command facade.

Only the two ImageGen call sites still require module-global patch translation.
The other historical patch fields remain enumerable for backward compatibility
but are now passed through :class:`Stage02Dependencies` instead of mutating
production modules.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scripts.imagegen_pipeline.imagegen_handoff import IMAGEGEN_CANVAS_CONTRACT as BODY_IMAGE_CANVAS_CONTRACT
from scripts.imagegen_pipeline.page_manifest import FULL_IMAGE_MODE, require_generated
from scripts.imagegen_pipeline.providers.codex_oauth_image import ensure_output_size, run_codex_image
from scripts.image_to_pptx_runtime.stage02_adapter import CANONICAL_EDITABLE_PPTX_ROUTE
from cyberppt.commands.production_qa import run_officecli_render_qa


@dataclass(frozen=True)
class LegacyPatchSet:
    """Finite compatibility surface for historical facade monkey patches.

    Six field names remain stable so old tests/callers can still patch the
    command facade. Four fields are now explicit dependencies; only the two
    ImageGen fields are translated to module globals until image-stage migration
    is completed.
    """

    run_codex_image: Any
    ensure_output_size: Any
    require_generated: Any
    reconstruction_build: Any
    officecli_render_qa: Any
    append_ledger: Any


LEGACY_PATCH_FIELDS = tuple(LegacyPatchSet.__dataclass_fields__)


def apply_legacy_patch_set(
    *,
    image_stage: Any,
    orchestrator: Any,
    reconstruction_stage: Any,
    delivery_stage: Any,
    patches: LegacyPatchSet,
) -> None:
    """Apply only the compatibility patches that still need module mutation."""

    _ = orchestrator, reconstruction_stage, delivery_stage
    image_stage.run_codex_image = patches.run_codex_image
    image_stage.ensure_output_size = patches.ensure_output_size


def sync_legacy_patch_points(
    *,
    image_stage: Any,
    orchestrator: Any,
    reconstruction_stage: Any,
    delivery_stage: Any,
    run_codex_image_patch: Any,
    ensure_output_size_patch: Any,
    require_generated_patch: Any,
    reconstruction_patch: Any,
    officecli_patch: Any,
    append_ledger_patch: Any,
) -> None:
    """Backward-compatible wrapper for callers using the old keyword API."""

    apply_legacy_patch_set(
        image_stage=image_stage,
        orchestrator=orchestrator,
        reconstruction_stage=reconstruction_stage,
        delivery_stage=delivery_stage,
        patches=LegacyPatchSet(
            run_codex_image=run_codex_image_patch,
            ensure_output_size=ensure_output_size_patch,
            require_generated=require_generated_patch,
            reconstruction_build=reconstruction_patch,
            officecli_render_qa=officecli_patch,
            append_ledger=append_ledger_patch,
        ),
    )


__all__ = [
    "BODY_IMAGE_CANVAS_CONTRACT",
    "CANONICAL_EDITABLE_PPTX_ROUTE",
    "FULL_IMAGE_MODE",
    "LEGACY_PATCH_FIELDS",
    "LegacyPatchSet",
    "apply_legacy_patch_set",
    "ensure_output_size",
    "require_generated",
    "run_codex_image",
    "run_officecli_render_qa",
    "sync_legacy_patch_points",
]
