from __future__ import annotations

from .delivery_stage import run_delivery_stage
from .dependencies import Stage02Dependencies, default_stage02_dependencies
from .image_stage import bind_reconstruction_visual_sources, normalize_audited_manifest_images, run_image_stage
from .manifest_stage import prepare_manifest
from .models import (
    DeliveryStageResult,
    ReconstructionStageResult,
    Stage02ProductionResult,
    Stage02RunOptions,
)
from .preflight import prepare_preflight, read_json, write_json
from .reconstruction_stage import run_reconstruction_stage
from .rhythm_stage import run_full_image_rhythm_stage
from .state import classify_manifest


def _expected_action_result(*, context, manifest, images, error: Exception) -> Stage02ProductionResult | None:
    """Convert expected Stage 02 continuation work into a durable result."""

    state_report = classify_manifest(images.manifest)
    if state_report.get("state") != "needs_action":
        return None

    images.manifest["stage02_state"] = state_report
    write_json(manifest.manifest_path, images.manifest)
    summary_path = context.build_dir / "stage02_needs_action.json"
    summary = {
        "schema": "cyberppt.stage02_expected_action.v1",
        "build_id": context.build_id,
        "status": "needs_action",
        "actions": state_report.get("actions") or [],
        "pages": state_report.get("pages") or [],
        "source_error": str(error),
        "manifest": str(manifest.manifest_path),
        "resume_rule": "Complete the listed page actions, then rerun final-script-pages with the same build id and output directory.",
    }
    write_json(summary_path, summary)

    build_context = read_json(manifest.build_context_path)
    build_context["status"] = "needs_action"
    build_context["stage02_state"] = state_report
    artifacts = build_context.get("artifacts")
    if not isinstance(artifacts, dict):
        artifacts = {}
        build_context["artifacts"] = artifacts
    artifacts["needs_action"] = {"path": str(summary_path)}
    write_json(manifest.build_context_path, build_context)

    reconstruction = ReconstructionStageResult(
        production_readiness=state_report,
        status="needs_action",
    )
    delivery = DeliveryStageResult(
        summary=summary,
        summary_path=summary_path,
        build_context_path=manifest.build_context_path,
    )
    return Stage02ProductionResult(
        context=context,
        manifest=manifest,
        images=images,
        reconstruction=reconstruction,
        delivery=delivery,
    )


def run_production(
    options: Stage02RunOptions,
    *,
    dependencies: Stage02Dependencies | None = None,
) -> Stage02ProductionResult:
    deps = dependencies or default_stage02_dependencies()
    context = prepare_preflight(options)
    manifest = prepare_manifest(context, options)
    images = run_image_stage(context, manifest, options)
    if options.require_images or (options.production_build and not options.dry_run_images):
        normalize_audited_manifest_images(images.manifest)
        deps.require_generated(images.manifest)
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
    try:
        reconstruction = run_reconstruction_stage(context, manifest, images, options)
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        expected = _expected_action_result(
            context=context,
            manifest=manifest,
            images=images,
            error=exc,
        )
        if expected is not None:
            return expected
        raise
    delivery = run_delivery_stage(context, manifest, images, reconstruction, options)
    return Stage02ProductionResult(
        context=context,
        manifest=manifest,
        images=images,
        reconstruction=reconstruction,
        delivery=delivery,
    )
