from __future__ import annotations

from pathlib import Path
import shlex
from typing import Any
from xml.etree import ElementTree as ET

from scripts.image_to_pptx_runtime.stage02_adapter import CANONICAL_EDITABLE_PPTX_ROUTE
from scripts.image_to_pptx_runtime.final_visible_text_qa import audit_final_visible_text, write_final_visible_text_qa
from cyberppt.artifact_ledger import append_artifacts
from cyberppt.commands.production_qa import run_officecli_render_qa
from cyberppt.script_quality.parsing import parse_script_path

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
        return shlex.join([".venv/bin/python3", "-m", "cyberppt", "run-autonomous", str(context.autonomous_contract), "--resume"])
    args = [".venv/bin/python3", "-m", "cyberppt", "final-script-pages", str(context.project),
            "--script", str(context.canonical_script), "--pages", context.pages_raw,
            "--style-lock", str(context.style_lock), "--production-mode", context.production_mode,
            "--assembly-mode", context.assembly_mode, "--output-dir", str(context.build_dir),
            "--build-id", context.build_id, "--image-model", options.image_model,
            "--image-quality", options.image_quality, "--image-timeout", str(options.image_timeout),
            "--prompt-enrich", options.prompt_enrich]
    for enabled, flag in (
        (options.generate_images or options.production_build, "--generate-images"),
        (options.production_build, "--production-build"),
        (context.source_mode == "external_script", "--external-script"),
        (options.allow_script_edit_requested, "--allow-script-edit"),
        (options.allow_prompt_edit, "--allow-prompt-edit"),
        (options.no_style_reference, "--no-style-reference"),
        (options.require_send_approval, "--require-send-approval"),
    ):
        if enabled:
            args.append(flag)
    for path, flag in ((options.prompt_overrides_dir, "--prompt-overrides-dir"),
                       (options.reuse_audited_images_from, "--reuse-audited-images-from")):
        if path is not None:
            args.extend([flag, str(path.expanduser().resolve())])
    # Force-redraw and audit bypasses are never inherited by a normal resume.
    return shlex.join(args)


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


def _final_visible_text_contract(
    manifest: dict[str, Any],
    script: Path,
    page_number: int,
) -> tuple[list[str], list[str]]:
    document = parse_script_path(script)
    page = next((item for item in document.pages if item.sequence == page_number), None)
    expected: list[str] = ["中国电力企业联合会", str(page_number)]
    if page is not None:
        expected.extend([page.title, *(line.strip() for line in page.onscreen_text.splitlines() if line.strip())])
        if page.page_type == "chapter":
            expected.extend(["章节导览", page.heading, "".join(page.heading.split())])
    authorized: list[str] = []
    pair = next(
        (item for item in manifest.get("pairs", []) if isinstance(item, dict) and item.get("page_number") == page_number),
        None,
    )
    if not isinstance(pair, dict):
        return expected, authorized
    # An authored SVG may intentionally split a source sentence across several
    # native text lines to preserve its column geometry.  Those line fragments
    # are editable and verified local content, so include their exact values
    # in the visible-text ownership contract before OCR is evaluated.
    authored_svg = Path(str(pair.get("authoring_svg") or ""))
    if authored_svg.is_file():
        try:
            root = ET.parse(authored_svg).getroot()
            expected.extend(
                "".join(node.itertext()).strip()
                for node in root.iter()
                if node.tag.rsplit("}", 1)[-1] == "text" and "".join(node.itertext()).strip()
            )
        except (OSError, ET.ParseError):
            # The reconstruction path has its own authored-SVG preflight; do
            # not hide an invalid file behind the final OCR gate.
            pass
    full = pair.get("full") if isinstance(pair.get("full"), dict) else {}
    debug = full.get("debug_receipt") if isinstance(full.get("debug_receipt"), dict) else {}
    expected.extend(str(item) for item in debug.get("visible_text", []) if str(item).strip())
    truth = pair.get("image_text_truth") if isinstance(pair.get("image_text_truth"), dict) else {}
    if str(truth.get("script_text") or "").strip():
        expected.append(str(truth["script_text"]))
    policy = pair.get("graphic_text_policy") if isinstance(pair.get("graphic_text_policy"), dict) else {}
    for item in policy.get("items", []) if isinstance(policy.get("items"), list) else []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or item.get("observed_text") or "").strip()
        if not text:
            continue
        if item.get("treatment") == "native_text":
            expected.append(text)
        elif item.get("treatment") == "preserved_in_image" or (
            item.get("treatment") == "decorative_glyph"
            and isinstance(item.get("visual_review"), dict)
            and item["visual_review"].get("status") == "passed"
        ):
            authorized.append(text)
    return expected, authorized


def _run_final_visible_text_qa(
    *,
    context: Stage02BuildContext,
    manifest_result: ManifestStageResult,
    reports: dict[str, dict[str, Any]],
) -> dict[str, Path]:
    """Run the residual-text ownership gate for editable delivery renders.

    Picture-PPT pages keep the generated-image typo/gibberish audit as their
    text gate.  They intentionally permit source-grounded rewritten copy, so
    treating every rewritten Chinese run as unowned text would exceed that
    branch's review scope.
    """

    output: dict[str, Path] = {}
    for mode, report in reports.items():
        if mode == "image":
            continue
        rendered = report.get("rendered_pages")
        if "rendered_pages" not in report:
            # Historical unit-test doubles do not model the renderer payload.
            # A real OfficeCLI receipt always includes this field.
            if report.get("schema") == "cyberppt.officecli_render_qa.v1":
                raise RuntimeError(f"final visible-text QA requires rendered pages for assembly mode {mode}")
            continue
        if not isinstance(rendered, list) or not rendered:
            raise RuntimeError(f"final visible-text QA requires rendered pages for assembly mode {mode}")
        page_numbers = list(manifest_result.page_numbers)
        if len(rendered) != len(page_numbers):
            raise RuntimeError(f"final visible-text QA page count mismatch for assembly mode {mode}")
        page_reports: list[dict[str, Any]] = []
        for page_number, rendered_path in zip(page_numbers, rendered):
            expected, authorized = _final_visible_text_contract(
                manifest_result.manifest,
                context.canonical_script,
                page_number,
            )
            page_reports.append(
                audit_final_visible_text(
                    rendered_path,
                    expected_texts=expected,
                    authorized_image_texts=authorized,
                )
            )
        aggregate = {
            "schema": "cyberppt.stage02.final_visible_text_qa.v1",
            "assembly_mode": mode,
            "status": "passed" if all(item.get("valid") is True for item in page_reports) else "failed",
            "pages": page_reports,
        }
        report_path = context.build_dir / "qa-delivery" / mode / "final_visible_text_qa.json"
        write_final_visible_text_qa(report_path, aggregate)
        report["final_visible_text_qa"] = aggregate
        report["final_visible_text_qa_path"] = str(report_path)
        output[mode] = report_path
        if aggregate["status"] != "passed":
            raise RuntimeError(f"final visible-text QA failed for assembly mode {mode}; see {report_path}")
    return output


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
    final_visible_text_qa = _run_final_visible_text_qa(
        context=context,
        manifest_result=manifest_result,
        reports=officecli_render_qa,
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
            "final_visible_text_qa": {mode: str(path) for mode, path in final_visible_text_qa.items()} or None,
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
    if final_visible_text_qa:
        build_context["artifacts"]["final_visible_text_qa"] = {
            mode: {"path": str(path), "sha256": sha256_file(path)}
            for mode, path in final_visible_text_qa.items()
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
    for mode, report_path in final_visible_text_qa.items():
        ledger_records.append(
            _artifact_record(
                stage="05-qa-delivery",
                page=page_label,
                path=report_path,
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
