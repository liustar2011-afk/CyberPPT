from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.image_to_pptx_runtime.stage02_adapter import CANONICAL_EDITABLE_PPTX_ROUTE
from cyberppt.artifact_ledger import append_artifacts
from cyberppt.commands.production_qa import run_officecli_render_qa

from .dependencies import Stage02Dependencies
from .models import DeliveryStageResult, ImageStageResult, ManifestStageResult, ReconstructionStageResult, Stage02BuildContext, Stage02RunOptions
from .preflight import LEDGER_PATH, page_range_slug, sha256_file, utc_now, write_json


def _artifact_record(
    *,
    stage: str,
    page: str,
    path: Path,
    status: str,
    depends_on: list[Path],
    resume_command: str,
    supersedes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "stage": stage,
        "page": page,
        "path": str(path),
        "status": status,
        "depends_on": [str(item) for item in depends_on],
        "supersedes": supersedes or [],
        "resume_command": resume_command,
        "sha256": sha256_file(path),
        "updated_at": utc_now(),
    }


def _append_ledger(project: Path, records: list[dict[str, Any]], *, build_id: str) -> Path:
    return append_artifacts(project / LEDGER_PATH, records, build_id=build_id)


def _resume_command(context: Stage02BuildContext, options: Stage02RunOptions) -> str:
    if context.autonomous_contract is not None:
        return f"python -m cyberppt run-autonomous {context.autonomous_contract} --resume"
    prompt_overrides_dir = options.prompt_overrides_dir.expanduser().resolve() if options.prompt_overrides_dir else None
    return (
        f"python -m cyberppt final-script-pages {context.project} --script {context.canonical_script} "
        f"--pages {context.pages_raw} --style-lock {context.style_lock} --production-mode {context.production_mode} "
        f"--assembly-mode {context.assembly_mode} --output-dir {context.build_dir} --build-id {context.build_id}"
        + (" --generate-images" if options.generate_images else "")
        + (" --production-build" if options.production_build else "")
        + (" --allow-script-edit" if options.allow_script_edit_requested else "")
        + (" --allow-prompt-edit" if options.allow_prompt_edit else "")
        + (f" --prompt-overrides-dir {prompt_overrides_dir}" if prompt_overrides_dir else "")
    )


def _run_office_qa(
    *,
    context: Stage02BuildContext,
    reconstruction: ReconstructionStageResult,
    production_build: bool,
    officecli_render_qa_fn: Any = None,
) -> tuple[dict[str, dict[str, Any]], list[Path]]:
    if not production_build:
        return {}, []
    build = reconstruction.build
    if not isinstance(build, dict):
        raise RuntimeError("Stage 02 production build did not return reconstruction artifacts")
    exports_by_mode = build.get("artifacts_by_mode") or {}
    if not exports_by_mode:
        primary_export = build["artifacts"].get("exported_pptx")
        exports_by_mode = {context.assembly_mode: primary_export} if primary_export else {}
    if not isinstance(exports_by_mode, dict):
        raise RuntimeError("Stage 02 assembly returned invalid exported_pptx_by_mode artifacts")
    if not exports_by_mode:
        raise RuntimeError("Stage 02 assembly did not return an exported PPTX for OfficeCLI render QA")
    qa_fn = officecli_render_qa_fn or run_officecli_render_qa
    reports: dict[str, dict[str, Any]] = {}
    export_paths: list[Path] = []
    for mode, exported_path in exports_by_mode.items():
        if not isinstance(mode, str) or not isinstance(exported_path, str):
            raise RuntimeError("Stage 02 assembly returned invalid exported PPTX mapping")
        export_path = Path(exported_path)
        export_paths.append(export_path)
        reports[mode] = qa_fn(export_path, context.build_dir / "qa-delivery" / mode)
    failed_modes = [mode for mode, report in reports.items() if not report["passed"]]
    if failed_modes:
        report_paths = ", ".join(str(reports[mode]["report_path"]) for mode in failed_modes)
        raise RuntimeError(
            "OfficeCLI render QA failed for assembly mode(s) "
            f"{', '.join(failed_modes)}; see {report_paths}"
        )
    return reports, export_paths


def run_delivery_stage(
    context: Stage02BuildContext,
    manifest_result: ManifestStageResult,
    image_result: ImageStageResult,
    reconstruction: ReconstructionStageResult,
    options: Stage02RunOptions,
    dependencies: Stage02Dependencies | None = None,
) -> DeliveryStageResult:
    officecli_render_qa, officecli_export_paths = _run_office_qa(
        context=context,
        reconstruction=reconstruction,
        production_build=options.production_build,
        officecli_render_qa_fn=(dependencies.officecli_render_qa if dependencies is not None else None),
    )
    resume_command = _resume_command(context, options)
    stage_name = "02-production-build" if options.production_build else "02-blueprint-image-to-editable-svg"
    status = reconstruction.status
    build = reconstruction.build
    prompt_overrides_dir = options.prompt_overrides_dir.expanduser().resolve() if options.prompt_overrides_dir else None
    image_ppt_output_dir = context.build_dir / "editable_svg"

    run_summary = {
        "schema": "cyberppt.final_script_pages_run.v1",
        "build_id": context.build_id,
        "created_at": utc_now(),
        "project": str(context.project),
        "source_script": str(context.canonical_script),
        "source_script_sha256": context.source_script_sha256,
        "pages": list(manifest_result.page_numbers),
        "stage": stage_name,
        "source_mode": context.source_mode,
        "allow_script_edit": options.allow_script_edit_requested,
        "allow_prompt_edit": options.allow_prompt_edit,
        "prompt_overrides_dir": str(prompt_overrides_dir) if prompt_overrides_dir else None,
        "autonomous_contract": str(context.autonomous_contract) if context.autonomous_contract else None,
        "project_created": context.project_created,
        "status": status,
        "production_mode": context.production_mode,
        "assembly_mode": context.assembly_mode,
        "editable_pptx_route": CANONICAL_EDITABLE_PPTX_ROUTE,
        "artifacts": {
            "compiled_deliverable_prompt": str(manifest_result.compiled_script),
            "page_image_pairs": str(manifest_result.manifest_path),
            "template_text_lock": str(manifest_result.template_lock_path),
            "visual_style_lock": str(context.style_lock),
            "output_dir": str(context.build_dir),
            "image_ppt_output_dir": str(image_ppt_output_dir),
            "reconstruction_inventory": build["artifacts"].get("reconstruction_inventory") if build else None,
            "svg_output": build["artifacts"].get("svg_output") if build else None,
            "reconstruction_quality": build["artifacts"].get("reconstruction_quality") if build else None,
            "delivery_readiness": build["artifacts"].get("delivery_readiness") if build else None,
            "exported_pptx": build["artifacts"].get("exported_pptx") if build else None,
            "exported_pptx_by_mode": build.get("artifacts_by_mode") if build else None,
            "officecli_render_qa": {mode: report["report_path"] for mode, report in officecli_render_qa.items()} or None,
            "semantic_plan_dir": str(options.semantic_plan_dir) if options.semantic_plan_dir else None,
        },
        "next_steps": [
            "Generate the audited 2:1 full image, then publish the selected image, editable SVG, or both template-assembled PPTX routes.",
            "Provide the completed high-fidelity authored SVG, then use the vendored Quick runtime for editable export.",
        ],
        "resume_command": resume_command,
        "rebuild": None,
        "image_to_editable_svg_build": build,
        "image_generation": image_result.generation,
        "clean_base_generation": reconstruction.clean_base_generation,
        "prompt_enrich": manifest_result.manifest.get("prompt_enrich"),
        "tool_consumption": reconstruction.tool_consumption,
        "production_readiness": reconstruction.production_readiness,
    }

    build_context = {
        "schema": "cyberppt.build_context.v1",
        "build_id": context.build_id,
        "created_at": run_summary["created_at"],
        "project": str(context.project),
        "source_script": str(context.canonical_script),
        "source_script_sha256": context.source_script_sha256,
        "style_lock": str(context.style_lock),
        "style_lock_sha256": context.style_lock_sha256,
        "page_set": list(manifest_result.page_numbers),
        "production_mode": context.production_mode,
        "assembly_mode": context.assembly_mode,
        "editable_pptx_route": CANONICAL_EDITABLE_PPTX_ROUTE,
        "stage": stage_name,
        "source_mode": context.source_mode,
        "autonomous_contract": (
            {"path": str(context.autonomous_contract), "sha256": sha256_file(context.autonomous_contract)}
            if context.autonomous_contract is not None
            else None
        ),
        "project_created": context.project_created,
        "status": status,
        "artifacts": {
            "compiled_deliverable_prompt": {"path": str(manifest_result.compiled_script), "sha256": sha256_file(manifest_result.compiled_script)},
            "page_image_pairs": {"path": str(manifest_result.manifest_path), "sha256": sha256_file(manifest_result.manifest_path)},
            "template_text_lock": {"path": str(manifest_result.template_lock_path), "sha256": sha256_file(manifest_result.template_lock_path)},
            "visual_style_lock": {"path": str(context.style_lock), "sha256": context.style_lock_sha256},
        },
    }
    if build and build["artifacts"].get("exported_pptx"):
        exported = Path(build["artifacts"]["exported_pptx"])
        build_context["artifacts"]["exported_pptx"] = {"path": str(exported), "sha256": sha256_file(exported)}
    if officecli_render_qa:
        build_context["artifacts"]["officecli_render_qa"] = {
            mode: {"path": report["report_path"], "sha256": sha256_file(Path(report["report_path"]))}
            for mode, report in officecli_render_qa.items()
        }
    write_json(manifest_result.build_context_path, build_context)
    run_summary["artifacts"]["build_context"] = str(manifest_result.build_context_path)

    slug = page_range_slug(manifest_result.page_numbers)
    summary_path = context.build_dir / f"{slug}_final_script_pages_run.json"
    write_json(summary_path, run_summary)

    page_numbers = manifest_result.page_numbers
    page_label = f"{page_numbers[0]}-{page_numbers[-1]}" if len(page_numbers) > 1 else str(page_numbers[0])
    ledger_records = [
        _artifact_record(stage=stage_name, page=page_label, path=manifest_result.compiled_script, status=status, depends_on=[context.canonical_script, context.style_lock], resume_command=resume_command),
        _artifact_record(stage=stage_name, page=page_label, path=manifest_result.manifest_path, status=status, depends_on=[manifest_result.compiled_script], resume_command=resume_command),
        _artifact_record(stage=stage_name, page=page_label, path=manifest_result.template_lock_path, status="approved", depends_on=[context.canonical_script, manifest_result.manifest_path], resume_command=resume_command),
        _artifact_record(stage=stage_name, page=page_label, path=context.style_lock, status="approved", depends_on=[context.canonical_script], resume_command=resume_command),
        _artifact_record(stage=stage_name, page=page_label, path=summary_path, status=status, depends_on=[manifest_result.compiled_script, manifest_result.manifest_path, manifest_result.template_lock_path, context.style_lock], resume_command=resume_command),
        _artifact_record(stage=stage_name, page=page_label, path=manifest_result.build_context_path, status=status, depends_on=[context.canonical_script, manifest_result.compiled_script, manifest_result.manifest_path, manifest_result.template_lock_path, context.style_lock], resume_command=resume_command),
    ]
    exported_pptx = build["artifacts"].get("exported_pptx") if build else None
    if exported_pptx:
        ledger_records.append(
            _artifact_record(
                stage="05-qa-delivery" if status == "production_ready" else stage_name,
                page=page_label,
                path=Path(exported_pptx),
                status="assembled" if status == "production_ready" else status,
                depends_on=[manifest_result.manifest_path, manifest_result.template_lock_path, context.style_lock],
                resume_command=resume_command,
            )
        )
    for mode, report in officecli_render_qa.items():
        ledger_records.append(
            _artifact_record(
                stage="05-qa-delivery",
                page=page_label,
                path=Path(report["report_path"]),
                status="passed",
                depends_on=officecli_export_paths,
                resume_command=resume_command,
            )
        )
    if not options.dry_run_images:
        ledger_fn = dependencies.append_ledger if dependencies is not None and dependencies.append_ledger is not None else _append_ledger
        ledger_fn(context.project, ledger_records, build_id=context.build_id)

    return DeliveryStageResult(
        summary=run_summary,
        summary_path=summary_path,
        build_context_path=manifest_result.build_context_path,
        officecli_render_qa=officecli_render_qa,
    )
