"""Compatibility facade for the typed Stage 02 production pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cyberppt.stage02_production import compat as _compat

BODY_IMAGE_CANVAS_CONTRACT = _compat.BODY_IMAGE_CANVAS_CONTRACT
CANONICAL_EDITABLE_PPTX_ROUTE = _compat.CANONICAL_EDITABLE_PPTX_ROUTE
FULL_IMAGE_MODE = _compat.FULL_IMAGE_MODE
ensure_output_size = _compat.ensure_output_size
require_generated = _compat.require_generated
run_codex_image = _compat.run_codex_image
run_officecli_render_qa = _compat.run_officecli_render_qa

from cyberppt.stage02_production import image_stage as _image_stage
from cyberppt.stage02_production import orchestrator as _orchestrator
from cyberppt.stage02_production.delivery_stage import _append_ledger, _artifact_record
from cyberppt.stage02_production.dependencies import Stage02Dependencies
from cyberppt.stage02_production.manifest_stage import _template_text_lock
from cyberppt.stage02_production.models import Stage02RunOptions
from cyberppt.stage02_production.preflight import (
    LEDGER_PATH,
    STAGE_DIR,
    TEMPLATE_LOCK_DIR,
    build_id_for as _build_id,
    explicit_output_dir as _explicit_output_dir,
    page_range_slug as _page_range_slug,
    read_json as _read_json,
    read_style_lock as _read_style_lock,
    sha256_file as _sha256,
    utc_now as _utc_now,
    versioned_output_dir as _versioned_output_dir,
    write_json as _write_json,
)
from cyberppt.stage02_production.reconstruction_stage import _run_image_to_editable_svg_build


def _sync_legacy_patch_points() -> None:
    """Retained historical hook; production no longer mutates module globals."""

    return None


def _generate_manifest_images(*args: Any, **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("run_codex_image_fn", run_codex_image)
    kwargs.setdefault("ensure_output_size_fn", ensure_output_size)
    return _image_stage._generate_manifest_images(*args, **kwargs)


def _normalize_audited_manifest_images(manifest: dict[str, Any]) -> None:
    _image_stage.normalize_audited_manifest_images(
        manifest,
        ensure_output_size_fn=ensure_output_size,
    )


def run_final_script_pages(
    *,
    project: Path,
    script: Path,
    pages_raw: str,
    style_lock: Path | None = None,
    style_id: int | None = None,
    style_name: str | None = None,
    output_dir: Path | None = None,
    semantic_plan_dir: Path | None = None,
    require_images: bool = False,
    run_rebuild: bool = False,
    rebuild_args: list[str] | None = None,
    production_build: bool = False,
    production_mode: str = FULL_IMAGE_MODE,
    assembly_mode: str = "editable",
    generate_images: bool = False,
    image_model: str = "gpt-image-2",
    image_quality: str = "high",
    image_timeout: int = 600,
    force_images: bool = False,
    dry_run_images: bool = False,
    prompt_enrich: str = "off",
    require_send_approval: bool = False,
    build_id: str | None = None,
    external_script: bool = False,
    lightweight_stage01_confirmed: bool = False,
    allow_script_edit: bool = False,
    autonomous_contract: Path | None = None,
    blueprint_only: bool = False,
    no_style_reference: bool = False,
    skip_image_text_audit: bool = False,
    allow_prompt_edit: bool = False,
    prompt_overrides_dir: Path | None = None,
    reuse_audited_images_from: Path | None = None,
) -> dict[str, Any]:
    _ = lightweight_stage01_confirmed, rebuild_args, style_id, style_name
    if run_rebuild:
        raise ValueError("--run-rebuild was removed; use --production-build for image-to-editable-svg")
    dependencies = Stage02Dependencies(
        require_generated=require_generated,
        run_codex_image=run_codex_image,
        ensure_output_size=ensure_output_size,
        reconstruction_build=_run_image_to_editable_svg_build,
        officecli_render_qa=run_officecli_render_qa,
        append_ledger=_append_ledger,
    )
    result = _orchestrator.run_production(
        Stage02RunOptions(
            project=project,
            script=script,
            pages_raw=pages_raw,
            style_lock=style_lock,
            # Stage 02 uses the repository's single production visual style.
            style_id=None if style_lock is not None else 9,
            style_name=None,
            output_dir=output_dir,
            semantic_plan_dir=semantic_plan_dir,
            require_images=require_images,
            production_build=production_build,
            production_mode=production_mode,
            assembly_mode=assembly_mode,
            generate_images=generate_images,
            image_model=image_model,
            image_quality=image_quality,
            image_timeout=image_timeout,
            force_images=force_images,
            dry_run_images=dry_run_images,
            prompt_enrich=prompt_enrich,
            require_send_approval=require_send_approval,
            build_id=build_id,
            external_script=external_script,
            autonomous_contract=autonomous_contract,
            blueprint_only=blueprint_only,
            no_style_reference=no_style_reference,
            skip_image_text_audit=skip_image_text_audit,
            allow_script_edit_requested=allow_script_edit,
            allow_prompt_edit=allow_prompt_edit,
            prompt_overrides_dir=prompt_overrides_dir,
            reuse_audited_images_from=reuse_audited_images_from,
        ),
        dependencies=dependencies,
    )
    return result.delivery.summary
