from __future__ import annotations

from scripts.imagegen_pipeline.page_manifest import require_generated

from .delivery_stage import run_delivery_stage
from .image_stage import bind_reconstruction_visual_sources, normalize_audited_manifest_images, run_image_stage
from .manifest_stage import prepare_manifest
from .models import Stage02ProductionResult, Stage02RunOptions
from .preflight import prepare_preflight, write_json
from .reconstruction_stage import run_reconstruction_stage
from .rhythm_stage import run_full_image_rhythm_stage


def run_production(options: Stage02RunOptions) -> Stage02ProductionResult:
    context = prepare_preflight(options)
    manifest = prepare_manifest(context, options)
    images = run_image_stage(context, manifest, options)
    if options.require_images or (options.production_build and not options.dry_run_images):
        normalize_audited_manifest_images(images.manifest)
        require_generated(images.manifest)
        if context.assembly_mode in {"editable", "both"}:
            rhythm_qa = run_full_image_rhythm_stage(
                images.manifest,
                build_dir=context.build_dir,
            )
            # Persist the deck-level QA result before any reconstruction authority is
            # frozen so a blocked run remains recoverable and inspectable.
            write_json(manifest.manifest_path, images.manifest)
            if rhythm_qa.get("status") == "blocked":
                raise RuntimeError(
                    "FULL_IMAGE_DECK_RHYTHM_BLOCKED: audited full images repeat the same "
                    "composition pattern across consecutive pages; review the rhythm receipt "
                    f"before reconstruction: {rhythm_qa.get('receipt_path', '')}"
                )
            bind_reconstruction_visual_sources(images.manifest)
        write_json(manifest.manifest_path, images.manifest)
    reconstruction = run_reconstruction_stage(context, manifest, images, options)
    delivery = run_delivery_stage(context, manifest, images, reconstruction, options)
    return Stage02ProductionResult(
        context=context,
        manifest=manifest,
        images=images,
        reconstruction=reconstruction,
        delivery=delivery,
    )
