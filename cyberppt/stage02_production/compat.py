"""Legacy patch-point bridge kept outside the Stage 02 command facade.

This module is the only compatibility seam allowed to import concrete ImageGen,
Quick reconstruction and Office rendering backends. The public command facade
only adapts arguments and forwards caller monkey-patches into this seam.
"""
from __future__ import annotations

from typing import Any

from scripts.imagegen_pipeline.imagegen_handoff import IMAGEGEN_CANVAS_CONTRACT as BODY_IMAGE_CANVAS_CONTRACT
from scripts.imagegen_pipeline.page_manifest import FULL_IMAGE_MODE, require_generated
from scripts.imagegen_pipeline.providers.codex_oauth_image import ensure_output_size, run_codex_image
from scripts.image_to_pptx_runtime.stage02_adapter import CANONICAL_EDITABLE_PPTX_ROUTE
from cyberppt.commands.production_qa import run_officecli_render_qa


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
    image_stage.run_codex_image = run_codex_image_patch
    image_stage.ensure_output_size = ensure_output_size_patch
    orchestrator.require_generated = require_generated_patch
    reconstruction_stage._run_image_to_editable_svg_build = reconstruction_patch
    delivery_stage.run_officecli_render_qa = officecli_patch
    delivery_stage._append_ledger = append_ledger_patch


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
