from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cyberppt.reconstruction_visual_authority import validate_reconstruction_visual_authority
from scripts.imagegen_pipeline.deliverable_prompt import parse_pages
from scripts.image_to_pptx_runtime.clean_base_generator import prepare_clean_bases
from scripts.image_to_pptx_runtime.stage02_adapter import run_stage02_reconstruction

from .dependencies import Stage02Dependencies
from .models import ImageStageResult, ManifestStageResult, ReconstructionStageResult, Stage02BuildContext, Stage02RunOptions
from .preflight import read_json, sha256_file, write_json


def _run_image_to_editable_svg_build(
    *,
    project: Path,
    manifest_path: Path,
    output_dir: Path,
    pages_raw: str,
    assembly_mode: str = "editable",
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    available_pages = {
        int(value)
        for value in manifest.get("requested_pages", [])
        if isinstance(value, int) or str(value).isdigit()
    }
    requested_pages = parse_pages(pages_raw, available_pages)
    return run_stage02_reconstruction(
        project=project,
        manifest_path=manifest_path,
        output_dir=output_dir / "editable_svg",
        requested_pages=requested_pages,
        assembly_mode=assembly_mode,
    )


def _initial_status(options: Stage02RunOptions) -> str:
    if options.blueprint_only:
        return "blueprint_created"
    if options.generate_images and not options.dry_run_images:
        return "image_assets_generated"
    return "ready_for_image_generation" if not options.require_images else "image_assets_verified"


def run_reconstruction_stage(
    context: Stage02BuildContext,
    manifest_result: ManifestStageResult,
    image_result: ImageStageResult,
    options: Stage02RunOptions,
    dependencies: Stage02Dependencies | None = None,
) -> ReconstructionStageResult:
    status = _initial_status(options)
    if not options.production_build:
        return ReconstructionStageResult(status=status)

    manifest = image_result.manifest
    clean_base_generation: dict[str, Any] | None = None
    if context.assembly_mode in {"editable", "both"}:
        # The accepted full image is the only visual authority entering editable
        # reconstruction. Verify it before any text-only clean-base derivation.
        validate_reconstruction_visual_authority(manifest, require_clean_base=False)
        clean_base_generation = prepare_clean_bases(
            manifest,
            output_dir=context.build_dir / "authoring" / "assets",
        )
        # A clean base may remove only native-text pixels; it must remain bound
        # to the exact same audited full-image SHA that Stage 02 froze.
        validate_reconstruction_visual_authority(manifest, require_clean_base=True)
        write_json(manifest_result.manifest_path, manifest)

    current_context = read_json(manifest_result.build_context_path)
    current_context["artifacts"]["page_image_pairs"]["sha256"] = sha256_file(manifest_result.manifest_path)
    write_json(manifest_result.build_context_path, current_context)

    build_fn = (
        dependencies.reconstruction_build
        if dependencies is not None and dependencies.reconstruction_build is not None
        else _run_image_to_editable_svg_build
    )
    build = build_fn(
        project=context.project,
        manifest_path=manifest_result.manifest_path,
        output_dir=context.build_dir,
        pages_raw=context.pages_raw,
        assembly_mode=context.assembly_mode,
    )
    production_readiness = build["delivery_readiness"]
    tool_consumption = production_readiness["tool_consumption"]
    return ReconstructionStageResult(
        clean_base_generation=clean_base_generation,
        build=build,
        production_readiness=production_readiness,
        tool_consumption=tool_consumption,
        status=str(build["status"]),
    )
